"""Extract the naked-eye stars of the Yale Bright Star Catalogue (BSC5) for the viewer's sky.

Input: bsc5.dat.gz, the ASCII BSC5 (Hoffleit & Warren 1991; same byte layout as CDS V/50),
from http://tdc-www.harvard.edu/catalogs/bsc5.html. Output: public/assets/sky/bright_stars.json,
one [ra_deg, dec_deg, vmag, b_minus_v] row per star (J2000, epoch 2000) with V <= --max-mag.
Positions are copied, not computed; no proper motion is applied (under 0.1 deg since 2000 for all
but a handful of stars). Usage: python scripts/extract_bright_stars.py PATH/bsc5.dat.gz
"""
import argparse
import gzip
import json
from pathlib import Path


def parse(line: str):
    ra_h, ra_m, ra_s = line[75:77], line[77:79], line[79:83]
    de_sign, de_d, de_m, de_s = line[83], line[84:86], line[86:88], line[88:90]
    vmag, bv = line[102:107], line[109:114]
    if not ra_h.strip() or not vmag.strip():
        return None  # the few non-stellar entries have no J2000 position
    ra = (int(ra_h) + int(ra_m) / 60 + float(ra_s) / 3600) * 15
    dec = int(de_d) + int(de_m) / 60 + int(de_s) / 3600
    if de_sign == '-':
        dec = -dec
    return [round(ra, 3), round(dec, 3), round(float(vmag), 2), round(float(bv), 2) if bv.strip() else 0.6]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('catalog')
    ap.add_argument('--max-mag', type=float, default=5.5)
    ap.add_argument('--out', default=str(Path(__file__).resolve().parents[1] / 'public/assets/sky/bright_stars.json'))
    a = ap.parse_args()
    rows = []
    with gzip.open(a.catalog, 'rt', encoding='latin-1') as f:
        for line in f:
            r = parse(line.rstrip('\n').ljust(197))
            if r and r[2] <= a.max_mag:
                rows.append(r)
    rows.sort(key=lambda r: r[2])
    doc = {
        'source': 'Yale Bright Star Catalogue, 5th revised ed. (Hoffleit & Warren 1991), ASCII BSC5 from SAO/Harvard TDC',
        'columns': ['ra_deg_j2000', 'dec_deg_j2000', 'vmag', 'b_minus_v'],
        'max_vmag': a.max_mag,
        'stars': rows,
    }
    Path(a.out).write_text(json.dumps(doc, separators=(',', ':')) + '\n', encoding='utf-8')
    print(f'{len(rows)} stars -> {a.out}')


if __name__ == '__main__':
    main()
