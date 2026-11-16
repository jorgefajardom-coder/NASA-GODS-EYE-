"""Private hypothetical worlds; IPC releases footprints/traversed poses only."""
from dataclasses import asdict
import json
import os
import queue
import subprocess
import sys
import threading
import traceback

import numpy as np
from scipy.ndimage import gaussian_filter

from mge_planning.core import GeometryCache, MotionProfile, TerrainGrid

from .protocol import array_hash, canonical, digest, peak_memory_bytes


def zero_block_mean(field, protected=(), block=5, valid=None):
    result=np.array(field,dtype=float,copy=True)
    protected=set(tuple(p) for p in protected)
    for r in range(0,result.shape[0],block):
        for c in range(0,result.shape[1],block):
            tile=result[r:r+block,c:c+block]
            editable=np.ones(tile.shape,dtype=bool) if valid is None else np.array(valid[r:r+block,c:c+block],dtype=bool)
            for rr,cc in protected:
                if r<=rr<r+tile.shape[0] and c<=cc<c+tile.shape[1]:
                    editable[rr-r,cc-c]=False
            tile[~editable]=0
            if editable.any():
                tile[editable]-=tile[editable].mean()
    return result


def generate(z, spec):
    rng=np.random.default_rng(np.random.SeedSequence(spec["world_seed"]))
    shape=z.shape
    height=np.array(z,dtype=np.float32,copy=True)
    obstacles=np.zeros(shape,dtype=np.int8)
    family=spec["family"]
    residual=np.zeros(shape)
    if family=="relief":
        if spec.get("directed") and spec.get("target"):
            rr,cc=np.indices(shape)
            tr,tc=spec["target"]
            raw=np.exp(-((rr-tr)**2+(cc-tc)**2)/(2*(spec["correlation_m"]/4.)**2))
        else:
            raw=gaussian_filter(rng.normal(size=shape),spec["correlation_m"]/4.)
        residual=zero_block_mean(raw,[spec["base"]],valid=np.isfinite(z))
        peak=np.abs(residual).max()
        if peak:
            residual*=spec["amplitude_m"]/peak
        height=np.asarray(z+residual,dtype=np.float32)
    if family in {"detour","blocked"}:
        if spec.get("target") is not None:
            r,c=spec["target"]
        else:
            r,c=int(rng.integers(2,shape[0]-2)),int(rng.integers(2,shape[1]-2))
        if family=="blocked" and spec.get("directed"):
            r,c=spec["goal"]
        candidates=[(r,c),(r,c+1),(r+1,c),(r+1,c+1)][:spec["obstacle_cells"]]
        for cell in candidates:
            if 0<=cell[0]<shape[0] and 0<=cell[1]<shape[1] and np.isfinite(z[cell]) and tuple(cell)!=tuple(spec["base"]):
                obstacles[cell]=100
    height[~np.isfinite(z)]=np.nan
    errors=[]
    difference=np.asarray(height,dtype=float)-z
    for r in range(0,shape[0],5):
        for c in range(0,shape[1],5):
            tile=difference[r:r+5,c:c+5]
            if np.isfinite(tile).any():
                errors.append(abs(float(np.nanmean(tile))))
    return height,obstacles,{"world_sha256":digest({"height":array_hash(height),"obstacles":array_hash(obstacles)}),
        "max_abs_relief_m":float(np.nanmax(np.abs(difference))),"max_block_mean_error_m":max(errors,default=0.),
        "hypothetical_obstacle_cells":int((obstacles==100).sum()),"source_kind":"SIMULATED",
        "full_world_exposed":False,"native_resolution_improved":False}


def serve():
    state=None
    for line in sys.stdin:
        try:
            msg=json.loads(line)
            op=msg["op"]
            if op=="create":
                with np.load(msg["public_path"],allow_pickle=False) as a:
                    z=np.asarray(a["elevation_m"],dtype=float)
                    z[~a["valid_mask"].astype(bool)]=np.nan
                height,obs,meta=generate(z,msg["spec"])
                state={"height":height,"obstacles":obs,"record":msg["record"],"meta":meta}
                response=meta
            elif op=="observe":
                z=state["height"]; record=state["record"]
                rr,cc=np.indices(z.shape)
                xy=np.array(msg["center_xy"],dtype=float)
                x=record["origin_x_m"]+(cc+.5)*4
                y=record["origin_y_m"]+(rr+.5)*4
                inside=((x-xy[0])**2+(y-xy[1])**2<=msg["radius_m"]**2)&np.isfinite(z)
                # Current-cell measurement is exact simulated pose telemetry;
                # other observations are also noise-free in this bounded v1.
                indices=np.flatnonzero(inside)
                response={"cell_indices":indices.tolist(),"elevations_m":z.ravel()[indices].astype(float).tolist(),
                    "sigmas_m":[.25]*len(indices),"obstacles":state["obstacles"].ravel()[indices].astype(int).tolist(),
                    "sensor_assumption":"ideal/noiseless synthetic height; sigma=.25 m is declared uncertainty, not inferred accuracy"}
            elif op=="walk":
                record=state["record"]; z=state["height"]
                valid=np.isfinite(z)
                mask=np.where(valid,state["obstacles"],-1).astype(np.int8)
                grid=TerrainGrid("private-evaluation",1,z,mask,4,record["origin_x_m"],record["origin_y_m"],sigma_m=np.where(valid,.25,np.inf))
                geom=GeometryCache().get(grid,MotionProfile(**msg["profile"]))
                cells=[tuple(p) for p in msg["cells"]]
                passed=[cells[0]]; reason="PREFIX_REACHED"
                for a,b in zip(cells,cells[1:]):
                    if geom.edge(a,b) is None:
                        reason="HALT_BEFORE_PRIVATE_INADMISSIBLE_SEGMENT"
                        break
                    passed.append(b)
                response={"traversed_points":[grid.point(c) for c in passed],"stop_reason":reason,
                          "current_cell":passed[-1],"private_grid_released":False}
            elif op=="close":
                print(canonical({"ok":True,"response":{"closed":True}}),flush=True)
                return
            elif op=="stats":
                response={"peak_process_memory_bytes":peak_memory_bytes()}
            else:
                raise ValueError("Unsupported private-world operation")
            print(canonical({"ok":True,"response":response}),flush=True)
        except Exception as error:
            print(canonical({"ok":False,"error":str(error),"type":type(error).__name__}),flush=True)


class WorldClient:
    """One private process and one planner process; no full-world array channel."""
    def __init__(self, script, root, stderr_path):
        self.errors=open(stderr_path,"a",encoding="utf-8")
        env={**os.environ,"PYTHONIOENCODING":"utf-8"}
        self.proc=subprocess.Popen([sys.executable,str(script),"world","--root",str(root)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=self.errors,text=True,encoding="utf-8",bufsize=1,env=env)
        self.queue=queue.Queue()
        def reader():
            for line in self.proc.stdout:
                self.queue.put(line)
            self.queue.put(None)
        self.reader=threading.Thread(target=reader,daemon=True)
        self.reader.start()

    def ask(self, **message):
        self.proc.stdin.write(canonical(message)+"\n")
        self.proc.stdin.flush()
        try:
            line=self.queue.get(timeout=30)
        except queue.Empty:
            self.proc.kill()
            raise TimeoutError("Private world operation exceeded 30 s")
        if line is None:
            raise RuntimeError("Private world process exited")
        result=json.loads(line)
        if not result["ok"]:
            raise ValueError(result["type"]+": "+result["error"])
        return result["response"]

    def close(self):
        if self.proc.poll() is None:
            try:
                self.ask(op="close")
                self.proc.wait(timeout=5)
            except Exception:
                self.proc.kill()
                self.proc.wait(timeout=5)
        self.errors.close()
