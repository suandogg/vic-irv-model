"""Strict testing-Sheet inputs for the opt-in structured nowcast."""
import copy
from pathlib import Path
import numpy as np
import pandas as pd
from SRC.constants import PARTIES
from SRC.nowcast_uncertainty import validate_config,SOURCES

RAW=Path(__file__).resolve().parents[1]/'data/raw'
FILES={'budget':'NOWCAST BUDGET.csv','correlation':'NOWCAST CORRELATION.csv',
       'contexts':'NOWCAST CONTEXTS.csv'}


def parse_inputs(budget,correlation,contexts,districts):
    if not {'Component','Party / Source','SD','Units','Evidence status','Notes'}.issubset(budget.columns):
        raise ValueError('NOWCAST BUDGET headers missing')
    config={'provenance':'Sheet-controlled development proposal; historical-proxy ALP/LNP/GRN core, inherited minor-party residuals and explicitly judgment-based 2026 source applicability; not calibrated coverage.'}
    seen=set()
    for row in budget.fillna('').to_dict('records'):
        key=(str(row['Component']).strip(),str(row['Party / Source']).strip())
        if key in seen:
            raise ValueError('Duplicate NOWCAST BUDGET component')
        seen.add(key)
        field,party=key
        if field in ('local_sd_pp','region_sd_pp','class_sd_pp') and party in PARTIES:
            config.setdefault(field,{})[party]=float(row['SD'])
        elif field=='transport_log_sd' and party in SOURCES:
            config.setdefault(field,{})[party]=float(row['SD'])
        elif key==('tail_df','ALL'):
            value=float(row['SD'])
            config[field]=None if value==0 else value
        else:
            raise ValueError('Unknown NOWCAST BUDGET component '+str(key))
    required={(f,p) for f in ('local_sd_pp','region_sd_pp','class_sd_pp') for p in PARTIES}
    required|={('transport_log_sd',p) for p in SOURCES}|{('tail_df','ALL')}
    if seen!=required:
        raise ValueError('NOWCAST BUDGET needs all party/source rows; do not silently omit a scale')
    if list(correlation.columns)!=['Party']+PARTIES or len(correlation)!=len(PARTIES):
        raise ValueError('NOWCAST CORRELATION must be one complete six-party matrix')
    if correlation.Party.duplicated().any() or set(correlation.Party)!=set(PARTIES):
        raise ValueError('Invalid NOWCAST CORRELATION party roster')
    config['correlation']=correlation.set_index('Party').loc[PARTIES,PARTIES].astype(float).to_numpy().tolist()
    columns=['District','LocalMultiplier']+[p+'_SD_pp' for p in PARTIES]+['Enabled','ReviewStatus','Notes']
    if list(contexts.columns)!=columns:
        raise ValueError('NOWCAST CONTEXTS headers missing or out of order')
    contexts=contexts.fillna('').copy()
    if contexts.District.duplicated().any() or set(contexts.District)!=set(districts):
        raise ValueError('NOWCAST CONTEXTS must contain every district exactly once')
    config['contexts']={}
    enabled_count=0
    for row in contexts.to_dict('records'):
        flag=str(row['Enabled']).strip().upper()
        if flag not in ('TRUE','FALSE'):
            raise ValueError('Context Enabled must be TRUE or FALSE')
        if row['ReviewStatus'] not in ('UNREVIEWED','REVIEWED'):
            raise ValueError('Context ReviewStatus must be UNREVIEWED or REVIEWED')
        if flag=='FALSE':
            continue
        if row['ReviewStatus']!='REVIEWED' or not str(row['Notes']).strip():
            raise ValueError('Enabled context needs REVIEWED status and an explanatory note')
        enabled_count+=1
        config['contexts'][row['District']]={
            'local_multiplier':{p:float(row['LocalMultiplier']) for p in PARTIES},
            'candidate_sd_pp':{p:float(row[p+'_SD_pp']) if row[p+'_SD_pp']!='' else 0 for p in PARTIES},
            'note':str(row['Notes']).strip()}
    config=validate_config(config,list(districts))
    return config,{'budget':budget.copy(),'correlation':correlation.copy(),'contexts':contexts,
        'unreviewed_contexts':int(contexts.ReviewStatus.eq('UNREVIEWED').sum()),
        'enabled_contexts':enabled_count}


def load_nowcast_inputs(districts,raw_dir=None):
    root=RAW if raw_dir is None else Path(raw_dir)
    missing=[filename for filename in FILES.values() if not (root/filename).exists()]
    if missing:
        raise ValueError('Structured nowcast inputs unavailable: '+', '.join(missing))
    tables={key:pd.read_csv(root/file,dtype=str,keep_default_na=False) for key,file in FILES.items()}
    return parse_inputs(tables['budget'],tables['correlation'],tables['contexts'],districts)


def scale_config(config,multiplier):
    """Scale ALL new SDs for sensitivity comparisons; do not scale correlations."""
    if not np.isfinite(multiplier) or multiplier<0:
        raise ValueError('Invalid nowcast SD multiplier')
    out=copy.deepcopy(config)
    for field in ('local_sd_pp','region_sd_pp','class_sd_pp','transport_log_sd'):
        out[field]={key:value*multiplier for key,value in out[field].items()}
    for context in out['contexts'].values():
        context['candidate_sd_pp']={p:value*multiplier for p,value in context['candidate_sd_pp'].items()}
    return out
