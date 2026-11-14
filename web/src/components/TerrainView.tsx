import { useEffect, useRef, useState } from "react";
import { AxesHelper, Color, GridHelper, PerspectiveCamera, Scene, WebGLRenderer } from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

/** An empty coordinate preview, not a Mars terrain or a simulated mission. */
export function TerrainView() {
  const host = useRef<HTMLDivElement>(null);
  const [failure, setFailure] = useState(false);
  useEffect(() => {
    const element = host.current!;
    let renderer: WebGLRenderer;
    try { renderer = new WebGLRenderer({ antialias: true }); }
    catch { setFailure(true); return; }
    const scene = new Scene();
    scene.background = new Color("#101c28");
    const grid = new GridHelper(20, 20, "#4b6a7c", "#243e50");
    const axes = new AxesHelper(4);
    scene.add(grid, axes);
    const camera = new PerspectiveCamera(45, 1, 0.1, 100);
    camera.position.set(16, 13, 16);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 0, 0);
    controls.update();
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    element.append(renderer.domElement);
    const render = () => renderer.render(scene, camera);
    const observer = new ResizeObserver(() => {
      const width = element.clientWidth;
      const height = element.clientHeight;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
      render();
    });
    observer.observe(element);
    controls.addEventListener("change", render);
    return () => {
      observer.disconnect();
      controls.dispose();
      grid.geometry.dispose();
      if (Array.isArray(grid.material)) grid.material.forEach(material => material.dispose());
      else grid.material.dispose();
      axes.geometry.dispose();
      if (Array.isArray(axes.material)) axes.material.forEach(material => material.dispose());
      else axes.material.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, []);
  return <div className="terrain" ref={host} role="img" aria-label="Empty local coordinate grid. No Mars terrain loaded.">
    {failure && <p className="webgl-failure">3D preview unavailable. Mission information remains available as text.</p>}
  </div>;
}
