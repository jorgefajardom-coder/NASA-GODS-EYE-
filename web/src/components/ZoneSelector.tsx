import { useCallback, useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { assetUrl } from '../data/replayAdapter';
import { WORLDS, initialZoneIndex, stepZone, zoneUrl, type WorldInfo } from '../data/worlds';
import HORIZON from '../data/zoneHorizon.json';
import { aimAt, angleDelta, globeDir, leftArc, radialCard } from '../lib/zoneGlobe';
import { arrivalView, coverQuad, easeInOut, lerpQuad, quadMatrix3d, type Quad } from '../lib/arrivalQuad';

/** Session key that carries the card image across the page load, for the arrival fade. */
export const ARRIVAL_KEY = 'mge-zone-arrival';
/** Card-to-screen zoom before the page changes (ms). */
const TRAVEL_MS = 750;

/** Whether this load comes from the selector (the arrival fade will show), without consuming it. */
export function arrivalPending(runId: string): boolean {
  try {
    const raw = window.sessionStorage.getItem(ARRIVAL_KEY);
    return raw != null && (JSON.parse(raw) as { runId?: string }).runId === runId;
  } catch {
    return false;
  }
}

function readArrival(runId: string): string | null {
  try {
    const raw = window.sessionStorage.getItem(ARRIVAL_KEY);
    if (!raw) return null;
    window.sessionStorage.removeItem(ARRIVAL_KEY);
    const a = JSON.parse(raw) as { runId?: string; image?: string };
    return a.runId === runId && typeof a.image === 'string' ? a.image : null;
  } catch {
    return null;
  }
}

/** Arrival timing (ms): least and most time full screen before laying down, the lay-down itself, the fade. */
const ARRIVE_HOLD_MIN = 350;
const ARRIVE_HOLD_MAX = 6000;
const ARRIVE_FIT = 1400;
const ARRIVE_FADE = 800;

/**
 * After travelling from the selector, the zone's card image (the same north-up orthomosaic that is draped on the
 * terrain) covers the screen, edge to edge. Once the scene is drawn it lays itself down on the terrain: its corners
 * move onto the projected corners of the imagery footprint (a perspective warp, recomputed every frame so it follows
 * the camera), then it fades into the draped terrain. Without a footprint in view it simply fades. Nothing is shown
 * on a normal load. Display only.
 */
export function ZoneArrival({ runId }: { runId: string }) {
  const [image] = useState(() => readArrival(runId));
  const [gone, setGone] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  useEffect(() => {
    if (!image) return;
    arrivalView.want = true;
    arrivalView.quad = null;
    const reduced = prefersReducedMotion();
    const t0 = performance.now();
    let fitAt = -1;
    let fadeAt = -1;
    let last: Quad | null = null;
    let raf = 0;
    const frame = (t: number) => {
      const img = imgRef.current;
      const wrap = wrapRef.current;
      const w = img?.naturalWidth ?? 0;
      const h = img?.naturalHeight ?? 0;
      if (img && wrap && w > 0 && h > 0) {
        const cover = coverQuad(w, h, window.innerWidth, window.innerHeight);
        const quad = arrivalView.quad;
        if (quad) last = quad;
        const held = t - t0;
        if (fitAt < 0 && fadeAt < 0) {
          if (quad && !reduced && held > ARRIVE_HOLD_MIN) fitAt = t;
          else if (held > (reduced ? ARRIVE_HOLD_MIN : ARRIVE_HOLD_MAX)) fadeAt = t;
        }
        let q = cover;
        let edge = 0;
        if (fitAt >= 0 && last) {
          const k = Math.min(1, (t - fitAt) / ARRIVE_FIT);
          q = lerpQuad(cover, last, easeInOut(k));
          edge = k;
          if (k >= 1 && fadeAt < 0) fadeAt = t;
        }
        let op = 1;
        if (fadeAt >= 0) {
          const f = Math.min(1, (t - fadeAt) / ARRIVE_FADE);
          op = 1 - f * f;
          if (f >= 1) {
            setGone(true);
            return;
          }
        }
        img.style.width = `${w}px`;
        img.style.height = `${h}px`;
        img.style.transform = quadMatrix3d(w, h, q);
        img.style.opacity = op.toFixed(3);
        img.style.setProperty('--edge', (edge * op).toFixed(3));
        wrap.classList.add('zone-arrival--ready');
      }
      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);
    return () => {
      cancelAnimationFrame(raf);
      arrivalView.want = false;
      arrivalView.quad = null;
    };
  }, [image]);
  if (!image || gone) return null;
  return (
    <div ref={wrapRef} className="zone-arrival" aria-hidden>
      <img ref={imgRef} src={image} alt="" />
    </div>
  );
}

const prefersReducedMotion = () => typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
const fmtLat = (v: number) => `${Math.abs(v).toFixed(2)}° ${v >= 0 ? 'N' : 'S'}`;
const fmtLon = (v: number) => `${Math.abs(v).toFixed(2)}° ${v >= 0 ? 'E' : 'W'}`;

/** Camera distances: pulled back while turning, close in once the zone faces the camera. */
const CAM_FAR = 8.4;
const CAM_NEAR = 6.3;
const GLOBE_R = 1.35;
const GLOBE_X = -0.6;

/** Stitches the Viking MDIM 2.1 tiles (public/zones/globe, scripts/extract-globe-tiles.mjs) into one canvas. */
async function globeCanvas(): Promise<HTMLCanvasElement> {
  const meta = (await (await fetch(assetUrl('zones/globe/manifest.json'))).json()) as { rows: number; cols: number; tile_px: number };
  const c = document.createElement('canvas');
  c.width = meta.cols * meta.tile_px;
  c.height = meta.rows * meta.tile_px;
  const g = c.getContext('2d')!;
  const loads: Promise<void>[] = [];
  for (let r = 0; r < meta.rows; r++) {
    for (let k = 0; k < meta.cols; k++) {
      loads.push(
        new Promise((done) => {
          const im = new Image();
          im.onload = () => {
            g.drawImage(im, k * meta.tile_px, r * meta.tile_px);
            done();
          };
          im.onerror = () => done();
          im.src = assetUrl(`zones/globe/${r}_${k}.jpg`);
        }),
      );
    }
  }
  await Promise.all(loads);
  return c;
}

/**
 * Zone selector: a Mars globe (Viking MDIM 2.1 colour mosaic, NASA/USGS via JPL Mars Trek) with one point per zone
 * at the centre of its scene. The selected zone turns to face the camera and the globe closes in on it; its card,
 * fitted radially against the planet, shows the zone's own orbital image (the one draped on its terrain) and a
 * synopsis. Travel zooms that image to fill the screen and opens the scene; the same image then lays itself down on the
 * terrain it is draped on and fades into it (ZoneArrival). It opens right after the intro on load (instantly, so the scene never shows behind it);
 * travelling to the zone already loaded simply enters it. Keys: left/right, Enter to travel, Esc to go back.
 */
export function ZoneSelector({ runId, onClose, instant = false }: { runId: string; onClose: () => void; instant?: boolean }) {
  const [i, setI] = useState(() => initialZoneIndex(runId));
  const [shown, setShown] = useState(i);
  const [swap, setSwap] = useState(false);
  const [on, setOn] = useState(false);
  const [flight, setFlight] = useState<{ rect: DOMRect; image: string } | null>(null);
  const [tip, setTip] = useState<{ x: number; y: number; zone: WorldInfo } | null>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const sketchRef = useRef<HTMLImageElement>(null);
  const marksRef = useRef<SVGSVGElement>(null);
  const titleRef = useRef<SVGSVGElement>(null);
  const indexRef = useRef(i);
  const pickRef = useRef<(k: number) => void>(() => undefined);
  const zone = WORLDS[i];
  const card = WORLDS[shown];

  const select = useCallback((k: number) => setI(((k % WORLDS.length) + WORLDS.length) % WORLDS.length), []);
  pickRef.current = select;

  // The card slides out and back in with the new zone.
  useEffect(() => {
    indexRef.current = i;
    if (i === shown) return;
    setSwap(true);
    const id = window.setTimeout(() => {
      setShown(i);
      setSwap(false);
    }, 190);
    return () => window.clearTimeout(id);
  }, [i, shown]);

  useEffect(() => {
    const id = requestAnimationFrame(() => requestAnimationFrame(() => setOn(true)));
    return () => cancelAnimationFrame(id);
  }, []);

  // The globe: plain three.js in its own canvas, driven by the selected index.
  useEffect(() => {
    const stage = stageRef.current;
    if (!stage) return;
    const reduced = prefersReducedMotion();
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    renderer.domElement.className = 'zones__globe';
    stage.prepend(renderer.domElement);
    const scene = new THREE.Scene();
    const cam = new THREE.PerspectiveCamera(32, 1, 0.1, 100);
    let camZ = reduced ? CAM_NEAR : 11;
    let camTarget = CAM_FAR;
    cam.position.set(0, 0, camZ);
    scene.add(new THREE.AmbientLight(0x6f86a8, 0.55 * Math.PI)); // three.js r155+ light units: x pi keeps the prototype's look
    const sun = new THREE.DirectionalLight(0xffffff, 1.25 * Math.PI);
    sun.position.set(-3, 2, 4);
    scene.add(sun);
    const world = new THREE.Group();
    world.position.x = GLOBE_X;
    scene.add(world);
    const globe = new THREE.Group();
    world.add(globe);
    const sphereGeo = new THREE.SphereGeometry(GLOBE_R, 128, 96);
    const sphereMat = new THREE.MeshStandardMaterial({ color: 0x9a5a3c, roughness: 1, metalness: 0 });
    globe.add(new THREE.Mesh(sphereGeo, sphereMat));
    let texture: THREE.Texture | null = null;
    let disposed = false;
    void globeCanvas().then((c) => {
      if (disposed) return;
      texture = new THREE.CanvasTexture(c);
      texture.colorSpace = THREE.SRGBColorSpace;
      texture.anisotropy = 8;
      sphereMat.map = texture;
      sphereMat.color.set(0xffffff);
      sphereMat.needsUpdate = true;
    });
    const rimGeo = new THREE.SphereGeometry(GLOBE_R * 1.035, 64, 48);
    const rimMat = new THREE.ShaderMaterial({
      transparent: true,
      side: THREE.BackSide,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      vertexShader: 'varying vec3 n;void main(){n=normalize(normalMatrix*normal);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',
      fragmentShader: 'varying vec3 n;void main(){float i=pow(0.72-dot(n,vec3(0,0,1.)),3.);gl_FragColor=vec4(0.25,0.55,1.,1.)*i*1.6;}',
    });
    world.add(new THREE.Mesh(rimGeo, rimMat));
    const ringGeo = new THREE.RingGeometry(GLOBE_R * 1.32, GLOBE_R * 1.325, 160);
    const ringMat = new THREE.MeshBasicMaterial({ color: 0x2f6fd0, transparent: true, opacity: 0.35, side: THREE.DoubleSide });
    world.add(new THREE.Mesh(ringGeo, ringMat));
    const arcGeo = new THREE.RingGeometry(GLOBE_R * 1.42, GLOBE_R * 1.423, 160, 1, 0, Math.PI * 1.2);
    const arcMat = new THREE.MeshBasicMaterial({ color: 0x58a6ff, transparent: true, opacity: 0.5, side: THREE.DoubleSide });
    const orbit = new THREE.Mesh(arcGeo, arcMat);
    world.add(orbit);
    const dot = document.createElement('canvas');
    dot.width = dot.height = 128;
    const dg = dot.getContext('2d')!;
    dg.strokeStyle = '#9fd0ff';
    dg.lineWidth = 7;
    dg.beginPath();
    dg.arc(64, 64, 40, 0, Math.PI * 2);
    dg.stroke();
    dg.fillStyle = '#ffffff';
    dg.beginPath();
    dg.arc(64, 64, 16, 0, Math.PI * 2);
    dg.fill();
    const dotTex = new THREE.CanvasTexture(dot);
    const markers = WORLDS.map((w, k) => {
      const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: dotTex, transparent: true }));
      const [x, y, z] = globeDir(w.lat, w.lon);
      s.position.set(x * GLOBE_R * 1.01, y * GLOBE_R * 1.01, z * GLOBE_R * 1.01);
      s.scale.setScalar(0.1);
      s.userData = { k };
      globe.add(s);
      return s;
    });

    let aimed = -1;
    let target = aimAt(WORLDS[indexRef.current].lat, WORLDS[indexRef.current].lon);
    const cur = { x: target.x, y: reduced ? target.y : target.y - 1.2 };
    let changedAt = performance.now();
    // The card is laid out once per size against the globe as it ends up (zoomed in), in whole pixels and with a
    // constant content width, so it never moves or reflows while the globe turns and zooms (no shaking).
    let cardArc = '';
    let cardKey = '';
    const layoutCard = () => {
      const el = cardRef.current;
      if (!el) return;
      const near = cam.clone();
      near.position.set(0, 0, CAM_NEAR);
      near.updateMatrixWorld();
      const proj = (v: THREE.Vector3) => {
        const q = v.clone().project(near);
        return { x: ((q.x + 1) / 2) * stage.clientWidth, y: ((1 - q.y) / 2) * stage.clientHeight };
      };
      const gc = proj(new THREE.Vector3(GLOBE_X, 0, 0));
      const gr = Math.abs(gc.y - proj(new THREE.Vector3(GLOBE_X, GLOBE_R, 0)).y);
      const W = stage.clientWidth;
      const margin = Math.max(70, W * 0.06);
      const gapR = Math.round(gr + Math.max(40, gr * 0.16));
      // Narrower content when the screen is tight, so the card fits without its text column changing later.
      const base = Math.round(Math.max(220, Math.min(320, W * 0.27, W - margin - (gc.x + gapR))));
      const half = el.offsetHeight / 2;
      const c = radialCard(gc.x, gapR, half, base, W, margin);
      const left = Math.round(c.left);
      const top = Math.round(gc.y);
      const key = `${left}|${top}|${Math.round(base + c.intrusion)}|${gapR}|${Math.round(half)}`;
      if (key === cardKey) return;
      cardKey = key;
      el.style.left = `${left}px`;
      el.style.top = `${top}px`;
      el.style.width = `${Math.round(base + c.intrusion)}px`;
      el.style.setProperty('--zones-card-pad', `${Math.round(c.intrusion + 14)}px`);
      const mask = `radial-gradient(circle ${gapR}px at ${Math.round(gc.x - left)}px ${Math.round(half)}px, transparent ${gapR - 0.5}px, #000 ${gapR + 0.5}px)`;
      el.style.maskImage = mask;
      el.style.setProperty('-webkit-mask-image', mask);
      cardArc = half < gapR ? `<path d="M${c.edgeX.toFixed(1)} ${top - half} A${gapR} ${gapR} 0 0 1 ${c.edgeX.toFixed(1)} ${top + half}" fill="none" stroke="rgba(88,166,255,.75)" stroke-width="1.5" class="zones__card-arc"/>` : '';
    };
    const resize = () => {
      const w = stage.clientWidth;
      const h = stage.clientHeight;
      renderer.setSize(w, h);
      cam.aspect = w / h;
      cam.updateProjectionMatrix();
      cardKey = '';
      layoutCard();
    };
    resize();
    window.addEventListener('resize', resize);
    const toScreen = (v: THREE.Vector3) => {
      const p = v.clone().project(cam);
      return { x: ((p.x + 1) / 2) * stage.clientWidth, y: ((1 - p.y) / 2) * stage.clientHeight };
    };
    const ray = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    const hit = (e: MouseEvent) => {
      const r = renderer.domElement.getBoundingClientRect();
      mouse.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
      ray.setFromCamera(mouse, cam);
      const h = ray.intersectObjects(markers)[0];
      return h ? (h.object.userData.k as number) : null;
    };
    const onMove = (e: MouseEvent) => {
      const k = hit(e);
      renderer.domElement.style.cursor = k != null ? 'pointer' : 'default';
      setTip(k != null && k !== indexRef.current ? { x: e.clientX, y: e.clientY, zone: WORLDS[k] } : null);
    };
    const onClick = (e: MouseEvent) => {
      const k = hit(e);
      if (k != null) pickRef.current(k);
    };
    renderer.domElement.addEventListener('mousemove', onMove);
    renderer.domElement.addEventListener('click', onClick);
    renderer.domElement.addEventListener('mouseleave', () => setTip(null));

    let raf = 0;
    let t0 = performance.now();
    const frame = (t: number) => {
      const dt = Math.min(0.05, (t - t0) / 1000);
      t0 = t;
      const k = reduced ? 1 : 1 - Math.exp(-dt * 3);
      if (aimed !== indexRef.current) {
        aimed = indexRef.current;
        target = aimAt(WORLDS[aimed].lat, WORLDS[aimed].lon);
        changedAt = t;
        camTarget = CAM_FAR;
      }
      const dy = angleDelta(cur.y, target.y);
      cur.y += dy * k;
      cur.x += (target.x - cur.x) * k;
      globe.rotation.set(cur.x, cur.y, 0, 'XYZ');
      if (Math.abs(dy) < 0.06 && Math.abs(target.x - cur.x) < 0.05 && t - changedAt > 350) camTarget = CAM_NEAR;
      camZ = reduced ? camTarget : camZ + (camTarget - camZ) * (1 - Math.exp(-dt * 2.2));
      cam.position.z = camZ;
      if (!reduced) orbit.rotation.z += dt * 0.12;
      markers.forEach((m, n) => {
        const s = n === aimed ? 0.15 + (reduced ? 0 : 0.02 * Math.sin(t / 300)) : 0.09;
        m.scale.setScalar(m.scale.x + (s - m.scale.x) * Math.min(1, k * 2));
      });
      renderer.render(scene, cam);

      // Screen geometry of the globe: title arcs on its left, card fitted radially on its right, focus marks.
      const gc = toScreen(new THREE.Vector3(GLOBE_X, 0, 0));
      const gr = Math.abs(gc.y - toScreen(new THREE.Vector3(GLOBE_X, GLOBE_R, 0)).y);
      const W = stage.clientWidth;
      const title = titleRef.current;
      if (title) {
        const fs = Math.max(22, Math.min(40, gr * 0.14));
        const edge = Math.max(80, W * 0.07);
        const ri = gr + Math.max(26, gr * 0.12);
        const ro = Math.max(ri + fs * 1.1, Math.min(ri + fs * 1.6, gc.x - edge));
        title.querySelector('#zones-arc-outer')?.setAttribute('d', leftArc(gc.x, gc.y, ro, Math.min(1.0, (520 / ro) * 0.6)));
        title.querySelector('#zones-arc-inner')?.setAttribute('d', leftArc(gc.x, gc.y, ri, Math.min(0.42, 150 / ri)));
        title.style.setProperty('--zones-title-size', `${fs}px`);
        const zoomed = Math.min(1, Math.max(0, (CAM_FAR - camZ) / (CAM_FAR - CAM_NEAR)));
        title.style.setProperty('--zones-title-op', (1 - Math.min(1, zoomed * 1.6)).toFixed(3));
      }
      layoutCard(); // cached: rewrites styles only if the card's size changed (e.g. a longer synopsis)
      const marks = marksRef.current;
      if (marks) {
        const wp = new THREE.Vector3();
        markers[aimed].getWorldPosition(wp);
        const s = toScreen(wp);
        const pulse = reduced ? 0 : Math.sin(t / 300);
        const r = 22 + 4 * pulse;
        const b = r + 10;
        const wave = reduced ? 0 : (t / 25) % 30;
        marks.innerHTML = `${cardArc}<circle cx="${s.x}" cy="${s.y}" r="${r}" fill="none" stroke="#58a6ff" stroke-width="1.5" opacity=".9"/>${reduced ? '' : `<circle cx="${s.x}" cy="${s.y}" r="${r + 14 + wave}" fill="none" stroke="#58a6ff" stroke-width="1" opacity="${(Math.max(0, 1 - wave / 30) * 0.6).toFixed(2)}"/>`}<path d="M${s.x - b} ${s.y - b + 12}v-12h12M${s.x + b} ${s.y - b + 12}v-12h-12M${s.x - b} ${s.y + b - 12}v12h12M${s.x + b} ${s.y + b - 12}v12h-12" fill="none" stroke="#9fd0ff" stroke-width="1.5"/>`;
      }
      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);

    return () => {
      disposed = true;
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', resize);
      renderer.domElement.removeEventListener('mousemove', onMove);
      renderer.domElement.removeEventListener('click', onClick);
      [sphereGeo, rimGeo, ringGeo, arcGeo].forEach((g) => g.dispose());
      [sphereMat, rimMat, ringMat, arcMat].forEach((m) => m.dispose());
      markers.forEach((m) => m.material.dispose());
      dotTex.dispose();
      texture?.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, []);

  const travel = useCallback(() => {
    if (flight) return;
    if (!zone.runId) return;
    if (zone.runId === runId) return onClose();
    const image = zone.image ? assetUrl(zone.image) : '';
    try {
      window.sessionStorage.setItem(ARRIVAL_KEY, JSON.stringify({ runId: zone.runId, image }));
    } catch {
      /* no session storage: travel without the arrival fade */
    }
    const go = () => window.location.assign(zoneUrl(window.location.href, zone.runId!));
    const rect = sketchRef.current?.getBoundingClientRect();
    if (!rect || !image || prefersReducedMotion()) return go();
    setFlight({ rect, image });
    window.setTimeout(go, TRAVEL_MS);
  }, [flight, zone, runId, onClose]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (flight) return;
      if (e.key === 'Escape') onClose();
      else if (e.key === 'ArrowLeft') select(indexRef.current - 1);
      else if (e.key === 'ArrowRight') select(indexRef.current + 1);
      else if (e.key === 'Enter') travel();
      else return;
      e.preventDefault();
      e.stopPropagation();
    };
    window.addEventListener('keydown', onKey, true);
    return () => window.removeEventListener('keydown', onKey, true);
  }, [flight, onClose, travel, select]);

  return (
    <div ref={stageRef} className={`zones${instant ? ' zones--instant' : ''}${on ? ' zones--on' : ''}`} role="dialog" aria-modal="true" aria-label="Select zone">
      <svg className="zones__horizon" viewBox="0 0 1600 220" preserveAspectRatio="none" aria-hidden>
        <defs>
          <linearGradient id="zones-h-far" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#16325a" stopOpacity=".75" />
            <stop offset="1" stopColor="#0a1830" stopOpacity=".95" />
          </linearGradient>
          <linearGradient id="zones-h-near" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#0d2140" />
            <stop offset="1" stopColor="#050b16" />
          </linearGradient>
        </defs>
        <path d={HORIZON.far} fill="url(#zones-h-far)" />
        <path d={HORIZON.far} fill="none" stroke="#3d7fd6" strokeOpacity=".35" strokeWidth="1.2" vectorEffect="non-scaling-stroke" />
        <path d={HORIZON.near} fill="url(#zones-h-near)" />
        <path d={HORIZON.near} fill="none" stroke="#58a6ff" strokeOpacity=".25" strokeWidth="1" vectorEffect="non-scaling-stroke" />
      </svg>
      <svg ref={titleRef} className="zones__title" role="img" aria-label="Select zone, Mars">
        <defs>
          <path id="zones-arc-outer" />
          <path id="zones-arc-inner" />
        </defs>
        <text className="zones__title-main">
          <textPath href="#zones-arc-outer" startOffset="50%" textAnchor="middle">
            SELECT ZONE
          </textPath>
        </text>
        <text className="zones__title-sub">
          <textPath href="#zones-arc-inner" startOffset="50%" textAnchor="middle">
            MARS
          </textPath>
        </text>
      </svg>
      <svg ref={marksRef} className="zones__marks" aria-hidden />

      <div ref={cardRef} className={`zones__card${swap ? ' zones__card--swap' : ''}`} aria-live="polite">
        <div className="zones__frame">
          <div className="zones__idx">
            {String(shown + 1).padStart(2, '0')} / {String(WORLDS.length).padStart(2, '0')}
          </div>
          <h2 className="zones__name">{card.place}</h2>
          <div className="zones__mission">{card.mission}</div>
          <div className="zones__sketch">
            {card.image && <img ref={sketchRef} src={assetUrl(card.image)} alt={card.imageCaption ?? ''} draggable={false} />}
            <span className="zones__scan" aria-hidden />
            <span className="zones__north" aria-hidden>
              N ↑
            </span>
            <span className="zones__scale">3.4 km</span>
          </div>
          <p className="zones__synopsis">{card.synopsis}</p>
          <div className="zones__meta">
            <span>
              {fmtLat(card.lat)} · {fmtLon(card.lon)}
            </span>
            <span title={card.imageCaption ?? undefined}>Orbital image</span>
          </div>
        </div>
      </div>

      {tip && (
        <div className="zones__tip" style={{ left: tip.x + 16, top: tip.y - 40 }} aria-hidden>
          <div>{tip.zone.place}</div>
          {tip.zone.image && <img src={assetUrl(tip.zone.image)} alt="" />}
        </div>
      )}

      <button type="button" className="zones__arrow zones__arrow--prev" onClick={() => select(i - 1)} aria-label={`Previous zone: ${WORLDS[stepZone(i, -1)].place}`}>
        ‹
      </button>
      <button type="button" className="zones__arrow zones__arrow--next" onClick={() => select(i + 1)} aria-label={`Next zone: ${WORLDS[stepZone(i, 1)].place}`}>
        ›
      </button>
      <div className="zones__dots" role="tablist" aria-label="Zones">
        {WORLDS.map((w, k) => (
          <button key={w.id} type="button" role="tab" aria-selected={k === i} aria-label={w.place} className="zones__dot" onClick={() => select(k)} />
        ))}
      </div>
      <button type="button" className="zones__back" onClick={onClose}>
        <kbd>Esc</kbd> Back
      </button>
      <button type="button" className="zones__travel" onClick={travel}>
        Travel <span aria-hidden>→</span>
      </button>

      {flight && (
        <div
          className="zones__flight"
          style={{ ['--x' as string]: `${flight.rect.left}px`, ['--y' as string]: `${flight.rect.top}px`, ['--w' as string]: `${flight.rect.width}px`, ['--h' as string]: `${flight.rect.height}px` }}
          aria-hidden
        >
          <img src={flight.image} alt="" />
        </div>
      )}
    </div>
  );
}
