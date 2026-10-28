"""Compare independent ON geographic signals; assign no mixture probabilities."""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]


def main():
    primary=pd.read_csv(ROOT/'data/raw/LEGACY_PRIMARY_INPUTS.csv')
    upper=pd.read_csv(ROOT/'data/raw/UPPER_REGION_PVI_NAMED.csv')
    on=upper[upper.PartyKey.eq('ON')].copy()
    on['region']=on.Region.str.replace('Metropolitan','Metro')
    signal=primary.assign(index=primary.ON_strength**.6).groupby('region')['index'].mean()
    signal=signal/signal.mean()
    alternative=on.set_index('region').RawRegionalLean
    alternative=alternative/alternative.mean()
    if set(signal.index)!=set(alternative.index) or len(signal)!=8:
        raise ValueError('ON signal region rosters do not match')
    table=pd.DataFrame({'Federal_2025_signal_alpha_0_6':signal,'Upper_2022_signal':alternative})
    table['Log_map_contrast']=np.log(table.Upper_2022_signal/table.Federal_2025_signal_alpha_0_6)
    table['Log_map_contrast']-=table.Log_map_contrast.mean()
    table=table.reset_index()
    out=ROOT/'reports/on_independent_signals_2026_10_29'
    out.mkdir(exist_ok=True)
    table.to_csv(out/'regional_signals.csv',index=False)
    (out/'method.json').write_text(json.dumps(dict(
        source='Committed district federal-derived strength index and official 2022 Council regional primary inputs',
        aggregation='Compare means of strength^0.6 across 11 districts per region with Council raw regional lean; each signal renormalised to equal-region mean one',
        limitation='Different years, chambers, campaign and candidate fields. No district-level state-ON inference, no calibrated distribution weight. Signals are pre-calibration, before donor adjustment.',
        active=False),indent=2))
    print(table.to_string(index=False))
    print('Regional signal correlation:',signal.corr(alternative))


if __name__=='__main__':
    main()
