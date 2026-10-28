"""Strict forecast-only subregion mapping; no deterministic primary dependency."""
import json
from pathlib import Path
import unicodedata
import pandas as pd

RAW = Path(__file__).resolve().parents[1]/'data/raw'


def seat_key(value):
    return ' '.join(unicodedata.normalize('NFKC',str(value)).strip().upper()
                    .replace('–','-').replace('—','-').split())


def validate_subregions(raw, districts):
    required = {'District','Proposed sub-region'}
    if not required.issubset(raw.columns):
        raise ValueError('SUB-REGIONS needs District and Proposed sub-region columns')
    raw = raw.copy().fillna('')
    raw = raw[raw.apply(lambda row:any(str(v).strip() for v in row),axis=1)]
    raw['_key'] = raw.District.map(seat_key)
    if raw['_key'].eq('').any() or raw['Proposed sub-region'].astype(str).str.strip().eq('').any():
        raise ValueError('SUB-REGIONS contains blank district or group membership')
    if raw['_key'].duplicated().any():
        raise ValueError('SUB-REGIONS contains duplicate district assignments')
    expected = {seat_key(seat):seat for seat in districts}
    if len(expected)!=len(districts):
        raise ValueError('Forecast roster contains duplicate district keys')
    missing,extra = set(expected)-set(raw['_key']),set(raw['_key'])-set(expected)
    if missing or extra:
        raise ValueError(f'SUB-REGIONS roster mismatch: missing {sorted(missing)}; extra {sorted(extra)}')
    raw['district'] = raw['_key'].map(expected)
    raw['subregion'] = raw['Proposed sub-region'].astype(str).str.strip()
    for source,dest in [('Confidence','confidence'),('Rationale / validation priority','notes')]:
        raw[dest] = raw[source].astype(str).str.strip() if source in raw else ''
    return raw.set_index('district').loc[list(districts),['subregion','confidence','notes']].reset_index()


def load_subregions(districts, raw_dir=None):
    root = Path(raw_dir) if raw_dir is not None else RAW
    csv = root/'SUB-REGIONS.csv'
    if csv.exists():
        raw = pd.read_csv(csv,dtype=str,keep_default_na=False)
        source = 'SUB-REGIONS CSV (see app sync status for live versus local input status)'
    else:
        snapshot = root/'SUB-REGIONS.json'
        if not snapshot.exists():
            raise ValueError('SUB-REGIONS mapping unavailable; selected trial cannot run')
        rows = json.loads(snapshot.read_text())['rows']
        raw = pd.DataFrame(rows[1:],columns=rows[0])
        source = 'Committed SUB-REGIONS snapshot (28 October 2026); no synced CSV available'
    return validate_subregions(raw,districts),source
