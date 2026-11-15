"""Run local paired SIMULATED experiments using frozen published producers."""
import argparse
import json
import os
from pathlib import Path
import sys

REPO=Path(__file__).resolve().parents[1]


def bootstrap(config):
    cfg=json.loads(Path(config).read_text(encoding="utf-8"))
    source=Path(cfg["source_root"])
    sys.path[:0]=[str(source/"src"/p) for p in ("mge_mission","mge_planning","mge_mapping","mge_data")]
    import mge_mission
    local=str(REPO/"src/mge_mission/mge_mission")
    if local not in mge_mission.__path__:mge_mission.__path__.append(local)
    return cfg


# Windows spawn imports the entrypoint before unpickling a worker function.
# Reinstall the same explicit extension namespace before that unpickling.
if "MGE_PAIRED_CONFIG" in os.environ:
    bootstrap(os.environ["MGE_PAIRED_CONFIG"])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=("run","block","world"))
    parser.add_argument("--config",type=Path)
    parser.add_argument("--case",type=Path)
    parser.add_argument("--root",type=Path)
    args=parser.parse_args()
    # Private workers inherit frozen source identity through an environment path.
    config=args.config or (Path(os.environ["MGE_PAIRED_CONFIG"]) if "MGE_PAIRED_CONFIG" in os.environ else None)
    if config is None:raise ValueError("Explicit frozen configuration required")
    os.environ["MGE_PAIRED_CONFIG"]=str(config.resolve())
    cfg=bootstrap(config)
    if args.command=="world":
        from mge_mission.research.world import serve
        return serve()
    from mge_mission.research.rigid_adaptive import run_block,run_study
    if args.command=="block":
        print(json.dumps(run_block(cfg,json.loads(args.case.read_text(encoding="utf-8"))),allow_nan=False))
    else:print(json.dumps(run_study(config),allow_nan=False))


if __name__=="__main__":main()
