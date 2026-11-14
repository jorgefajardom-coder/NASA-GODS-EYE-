import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { beforeAll, describe, expect, it } from 'vitest';
import { calmClip, clipWalkSpeed, walkTimeScale, WALK_MAX_TIME_SCALE } from '../src/lib/astronautPose';

const GLB = join(dirname(fileURLToPath(import.meta.url)), '..', 'public', 'assets', 'models', 'astronaut.glb');

/** Parses the real GLB in Node. Textures are removed first (no image decoding here); geometry, skeleton and clips are untouched. */
async function loadModel() {
  const buf = readFileSync(GLB);
  const jl = buf.readUInt32LE(12);
  const j = JSON.parse(buf.subarray(20, 20 + jl).toString());
  const bin = buf.subarray(20 + jl + 8);
  delete j.textures;
  delete j.images;
  delete j.samplers;
  delete j.extensionsUsed;
  for (const m of j.materials) {
    delete m.pbrMetallicRoughness?.baseColorTexture;
    delete m.pbrMetallicRoughness?.metallicRoughnessTexture;
    delete m.normalTexture;
    delete m.occlusionTexture;
    delete m.emissiveTexture;
    delete m.extensions;
  }
  let js = Buffer.from(JSON.stringify(j));
  js = Buffer.concat([js, Buffer.alloc((4 - (js.length % 4)) % 4, 0x20)]);
  const out = Buffer.alloc(12 + 8 + js.length + 8 + bin.length);
  out.writeUInt32LE(0x46546c67, 0);
  out.writeUInt32LE(2, 4);
  out.writeUInt32LE(out.length, 8);
  out.writeUInt32LE(js.length, 12);
  out.writeUInt32LE(0x4e4f534a, 16);
  js.copy(out, 20);
  const o = 20 + js.length;
  out.writeUInt32LE(bin.length, o);
  out.writeUInt32LE(0x004e4942, o + 4);
  bin.copy(out, o + 8);
  const ab = out.buffer.slice(out.byteOffset, out.byteOffset + out.length);
  return new Promise<{ scene: THREE.Group; animations: THREE.AnimationClip[] }>((res, rej) => new GLTFLoader().parse(ab, '', res, rej));
}

const deg = (r: number) => (r * 180) / Math.PI;

/** Samples a clip and reports torso lean, pelvis and shoulder roll (degrees) and hip height swing (m). */
function measure(root: THREE.Object3D, clip: THREE.AnimationClip) {
  const find = (re: RegExp) => {
    let f: THREE.Object3D | null = null;
    root.traverse((o) => {
      if (!f && re.test(o.name)) f = o;
    });
    return f!;
  };
  const hips = find(/^Center\d/);
  const head = find(/^head\d/);
  const lHip = find(/^L_Thigh/);
  const rHip = find(/^R_Thigh/);
  const lSh = find(/^L_Arm\d/);
  const rSh = find(/^R_Arm\d/);
  const w = (o: THREE.Object3D) => o.getWorldPosition(new THREE.Vector3());
  const roll = (a: THREE.Object3D, b: THREE.Object3D) => {
    const v = w(a).sub(w(b));
    return deg(Math.atan2(v.y, Math.hypot(v.x, v.z)));
  };
  const mixer = new THREE.AnimationMixer(root);
  const action = mixer.clipAction(clip);
  action.play();
  const r = { lean: [1e9, -1e9], pelvis: [1e9, -1e9], shoulders: [1e9, -1e9], hipY: [1e9, -1e9], hipTravel: 0, netDrift: 0, sway: 0 };
  const start = new THREE.Vector3();
  for (let i = 0; i <= 32; i++) {
    mixer.setTime((clip.duration * i) / 32);
    root.updateMatrixWorld(true);
    const v = w(head).sub(w(hips));
    const lean = deg(Math.acos(v.y / v.length()));
    const p = roll(lHip, rHip);
    const s = roll(lSh, rSh);
    const hp = w(hips);
    if (i === 0) start.copy(hp);
    r.sway = Math.max(r.sway, Math.hypot(hp.x - start.x, hp.z - start.z));
    if (i === 32) r.netDrift = Math.hypot(hp.x - start.x, hp.z - start.z);
    r.lean = [Math.min(r.lean[0], lean), Math.max(r.lean[1], lean)];
    r.pelvis = [Math.min(r.pelvis[0], p), Math.max(r.pelvis[1], p)];
    r.shoulders = [Math.min(r.shoulders[0], s), Math.max(r.shoulders[1], s)];
    r.hipY = [Math.min(r.hipY[0], hp.y), Math.max(r.hipY[1], hp.y)];
  }
  action.stop();
  mixer.uncacheRoot(root);
  return { lean: r.lean, pelvisRoll: r.pelvis, shoulderRoll: r.shoulders, pelvisSwing: r.pelvis[1] - r.pelvis[0], shoulderSwing: r.shoulders[1] - r.shoulders[0], hipSwing: r.hipY[1] - r.hipY[0], netDrift: r.netDrift, sway: r.sway };
}

let model: Awaited<ReturnType<typeof loadModel>>;
beforeAll(async () => {
  model = await loadModel();
});

describe('astronaut GLB', () => {
  it('loads with a skeleton and the clips the viewer uses', () => {
    const names = model.animations.map((a) => a.name);
    expect(names).toEqual(expect.arrayContaining(['idle', 'moon_walk']));
    let skinned = 0;
    model.scene.traverse((o) => {
      if ((o as THREE.SkinnedMesh).isSkinnedMesh) skinned++;
    });
    expect(skinned).toBeGreaterThan(0);
  });

  it('has no root motion in the clips used: a full cycle returns to where it started', () => {
    for (const name of ['idle', 'moon_walk']) {
      const m = measure(model.scene, model.animations.find((a) => a.name === name)!);
      expect(m.netDrift).toBeLessThan(0.01);
    }
  });
});

describe('calmed walk and idle', () => {
  const original = (name: string) => model.animations.find((a) => a.name === name)!;

  it('leaves the loaded clip untouched', () => {
    const before = Array.from(original('moon_walk').tracks[0].values.slice(0, 8));
    calmClip(model.scene, original('moon_walk'));
    expect(Array.from(original('moon_walk').tracks[0].values.slice(0, 8))).toEqual(before);
  });

  it('keeps the torso vertical while walking (no tilt)', () => {
    const raw = measure(model.scene, original('moon_walk'));
    const calm = measure(model.scene, calmClip(model.scene, original('moon_walk')));
    expect(raw.lean[1]).toBeGreaterThan(15); // the original leans a lot
    expect(calm.lean[1]).toBeLessThan(1);
    expect(calm.lean[0]).toBeGreaterThanOrEqual(0);
  });

  it('removes the side-to-side rocking and keeps the hip bob below the original', () => {
    const raw = measure(model.scene, original('moon_walk'));
    const calm = measure(model.scene, calmClip(model.scene, original('moon_walk')));
    expect(raw.pelvisSwing).toBeGreaterThan(5);
    expect(calm.pelvisSwing).toBeLessThan(0.5);
    expect(calm.shoulderSwing).toBeLessThan(0.5);
    expect(calm.hipSwing).toBeLessThan(raw.hipSwing * 0.75); // a walking bob, smaller than the source hop
  });

  it('walks instead of hopping: the lower foot never leaves the ground', () => {
    const lowFoot = (clip: THREE.AnimationClip) => {
      const root = model.scene;
      const pick = (re: RegExp) => {
        let f: THREE.Object3D | null = null;
        root.traverse((o) => {
          if (!f && re.test(o.name)) f = o;
        });
        return f!;
      };
      const l = pick(/^L_Ankle\d/);
      const r = pick(/^R_Ankle\d/);
      const mixer = new THREE.AnimationMixer(root);
      mixer.clipAction(clip).play();
      const a = new THREE.Vector3();
      const ys: number[] = [];
      for (let i = 0; i < 60; i++) {
        mixer.setTime((clip.duration * i) / 60);
        root.updateMatrixWorld(true);
        ys.push(Math.min(l.getWorldPosition(a).y, r.getWorldPosition(a.clone()).y));
      }
      mixer.stopAllAction();
      return Math.max(...ys) - Math.min(...ys); // how far the stance foot rises over the cycle
    };
    const raw = lowFoot(original('moon_walk'));
    const calm = lowFoot(calmClip(model.scene, original('moon_walk')));
    expect(raw).toBeGreaterThan(0.15); // the source clip has a long both-feet-off-the-ground phase
    expect(calm).toBeLessThan(0.02); // planted: the lower foot stays on the ground
  });

  it('measures the walk speed of the clip so the legs can be synced to the ground', () => {
    model.scene.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(model.scene);
    const toMetres = 1.9 / (box.max.y - box.min.y); // drawn at 1.9 m, as AstronautModel does
    const v = clipWalkSpeed(model.scene, calmClip(model.scene, original('moon_walk'))) * toMetres;
    expect(v).toBeGreaterThan(0.2); // a slow suited gait, well below the old 1.05 m/s assumption
    expect(v).toBeLessThan(0.6);
    // Exact sync below the cap: the stance foot moves backwards as fast as the body moves forwards.
    expect(walkTimeScale(1.0, v)).toBeCloseTo(1.0 / v, 9);
    expect(walkTimeScale(100, v)).toBe(WALK_MAX_TIME_SCALE); // fast replay: capped
    expect(walkTimeScale(0, v)).toBe(1);
  });

  it('stands upright when idle', () => {
    const calm = measure(model.scene, calmClip(model.scene, original('idle')));
    expect(calm.lean[1]).toBeLessThan(1);
    expect(calm.pelvisSwing).toBeLessThan(0.5);
  });

  it('keeps the shoulders level in walk and idle (no fixed side tilt)', () => {
    for (const name of ['moon_walk', 'idle']) {
      const calm = measure(model.scene, calmClip(model.scene, original(name)));
      expect(Math.abs(calm.shoulderRoll[0])).toBeLessThan(1);
      expect(Math.abs(calm.shoulderRoll[1])).toBeLessThan(1);
      expect(Math.abs(calm.pelvisRoll[0])).toBeLessThan(1);
      expect(Math.abs(calm.pelvisRoll[1])).toBeLessThan(1);
    }
  });
});
