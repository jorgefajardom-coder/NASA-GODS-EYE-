"""Prepare portable paths for a fresh analytical rerun of an archived batch.

AI-assisted reproducibility tooling; metadata: ../publication-manifest.json.
Original records stay immutable. Time-limited outcomes may depend on host load.
"""
from pathlib import Path
import argparse,json,subprocess

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--batch',default='main')
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    archive=args.archive.resolve();source=args.source.resolve()
    original=json.loads((archive/args.batch/'config.json').read_text(encoding='utf-8'))
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
    if sha!=original['source_sha']:raise ValueError('Use the exact published source SHA')
    config=dict(original)
    config['source_root']=str(source)
    config['output_dir']=str(args.output.resolve()/'results')
    config['prior_root']=str(archive/'runtime/evidence/overnight-mission-research-20261115-v3')
    config['profiles_path']=str(source/'config/science_profiles.proposed.json')
    config['script_path']=str(archive/'runtime/scripts/run_rigid_adaptive_study.py')
    config['map_records']=[str(archive/'public'/Path(p.replace('\\','/')).name) for p in original['map_records']]
    # A fresh explicit deadline is required; do not overwrite or resume an old journal.
    config['deadline_utc']='REPLACE_WITH_FUTURE_UTC_DEADLINE'
    args.output.mkdir(parents=True,exist_ok=False)
    destination=args.output/'config.json'
    destination.write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
    print(destination)

if __name__=='__main__':main()
