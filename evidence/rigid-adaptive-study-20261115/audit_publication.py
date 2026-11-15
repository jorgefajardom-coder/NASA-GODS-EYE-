"""Read-only integrity audit of this separate analytical publication.

Mandatory AI-use metadata: publication-manifest.json and docs/ai_usage.json.
"""
from pathlib import Path
import argparse,csv,gzip,hashlib,json,math

def sha(data):return hashlib.sha256(data).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'),parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',nargs='?',type=Path,default=Path(__file__).resolve().parent)
    args=parser.parse_args();archive=args.archive.resolve();repo=archive.parents[1]
    manifest=read(archive/'publication-manifest.json')
    for entry in manifest['files']:
        p=repo/entry['path']
        assert p.stat().st_size==entry['bytes'] and sha(p.read_bytes())==entry['sha256'],str(p)
    batches={}
    for batch in manifest['batches']:
        path=archive/batch['batch'];compressed=(path/'paired-blocks.jsonl.gz').read_bytes()
        body=gzip.decompress(compressed)
        assert sha(compressed)==batch['gzip_sha256'] and sha(body)==batch['raw_sha256']
        assert body.endswith(b'\n') and len(body.splitlines())==batch['rows']
        source=read(path/'manifest.json');planned={x['block_id'] for x in source['planned_cases']}
        seen=set()
        for seq,line in enumerate(body.splitlines(),1):
            row=json.loads(line)
            assert row['seq']==seq and row['identity']==source['identity']
            assert row['case_id'] not in seen and row['case_id'] in planned
            assert row['payload_sha256']==sha(canonical(row['payload']).encode('utf-8'))
            seen.add(row['case_id'])
        summaries=sorted(path.glob('summary-*.json'))
        assert summaries,'A closed supervisor summary is required'
        close=read(summaries[-1]);assert set(close['remaining_case_ids'])==planned-seen
        assert close['journal_sha256']==sha(body)
        batches[batch['batch']]={'recorded':len(seen),'pending':len(planned-seen),'hashes':'PASS'}
        analysis=path/'analysis/summary.json'
        if analysis.exists():
            results=read(analysis)
            assert results['provenance']['inputs'][0]['sha256']==sha(body)
            assert results['provenance']['protocol_sha256']==sha((archive/'statistical-plan.json').read_bytes())
            assert results['provenance']['script_sha256']==sha((archive/'tooling/analyze_rigid_adaptive.py').read_bytes())
    for name,expected,optional in [('main',-20/1440,317/1440),('directed',33/480,92/480)]:
        summary=read(archive/name/'analysis/summary.json')
        assert math.isclose(summary['metrics']['completion_delta']['estimate'],expected,abs_tol=1e-12)
        assert math.isclose(summary['metrics']['optional_delta']['estimate'],optional,abs_tol=1e-12)
    article=repo/'docs/wiki/10-Adaptive-Planning-Study.md'
    review=read(archive/'article-review.json')
    assert sha(article.read_bytes())==review['article_sha256'] and review['status']=='PASS'
    text=article.read_text(encoding='utf-8')
    assert '**' not in text and '<!-- FINAL_' not in text
    assert 'SIMULATED' in text and 'AI-generated' in text
    ai=read(repo/'docs/ai_usage.json')
    assert any(x.get('kind')=='paired_rigid_adaptive_analytical_research' for x in ai['uses'])
    print(json.dumps({'status':'PASS','files':len(manifest['files']),'batches':batches,
                      'scientific_approval_change':False,'operational_execution_claim':False}))

if __name__=='__main__':main()
