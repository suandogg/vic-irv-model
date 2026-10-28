"""Official candidate-level VEC 2014/2018 primary panel, independent of model.

Fetch from the official summary's district links; preserve raw pages and counts.
No 2018 -> 2022 boundary matching is inferred from district names.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urljoin
from urllib.request import urlopen
import numpy as np
import pandas as pd
from lxml import html

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
OUT=ROOT/'data/research/historical_primaries_2026_10_29'
BASE='https://itsitecoreblobvecprd01.blob.core.windows.net/public-files/historical-results/'


def text(node):
    return ' '.join(node.text_content().split())


def category(party):
    p=' '.join(party.upper().split())
    if p.startswith('AUSTRALIAN LABOR PARTY'):
        return 'ALP'
    if p in {'LIBERAL','THE NATIONALS','NATIONAL PARTY','LIBERAL PARTY'}:
        return 'LNP'
    if p=='AUSTRALIAN GREENS':
        return 'GRN'
    if 'ONE NATION' in p:
        return 'ON'
    if not p or p=='INDEPENDENT':
        return 'IND'
    return 'OTH'


def parse_district(data,year,url):
    tree=html.fromstring(data)
    heading=tree.xpath('//h2')
    if not heading:
        raise ValueError('District heading missing: '+url)
    district=re.sub(r'\s+District$','',text(heading[0]))
    tables=tree.xpath('//table[contains(translate(@title,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz"),"first preference")]')
    if len(tables)!=1:
        raise ValueError(f'Expected one primary table for {district}, got {len(tables)}')
    formal=None
    for tr in tree.xpath('//tr'):
        cells=tr.xpath('./th|./td')
        if len(cells)>=2 and text(cells[0]).rstrip(':').strip()=='Formal Votes':
            formal=int(text(cells[1]).replace(',',''))
    if formal is None or formal<=0:
        raise ValueError('Formal-vote control missing: '+district)
    candidates=[]
    for tr in tables[0].xpath('.//tr'):
        cells=tr.xpath('./td')
        if len(cells)!=4:
            continue
        name,party,votes,share=map(text,cells)
        if not re.fullmatch(r'[\d,]+',votes):
            continue
        votes=int(votes.replace(',',''))
        reported=float(share.replace('%','').strip())/100
        if abs(votes/formal-reported)>.000051:
            raise ValueError('Reported percentage does not reconcile: '+district+' '+name)
        candidates.append(dict(Year=year,District=district,Candidate=name,OfficialParty=party,
            BroadCategory=category(party),Votes=votes,FormalVotes=formal,
            Share=votes/formal,ReportedShare=reported,SourceURL=url))
    if not candidates or sum(c['Votes'] for c in candidates)!=formal:
        raise ValueError('Candidate counts do not equal official formal votes: '+district)
    return candidates


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--offline',action='store_true',help='Require cached official pages')
    args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    provenance=[]
    def fetch(url):
        relative=url.split('/historical-results/',1)[1]
        path=OUT/'sources'/relative
        if path.exists():
            data=path.read_bytes()
        elif args.offline:
            raise FileNotFoundError(path)
        else:
            data=urlopen(url,timeout=40).read()
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data)
        return data,dict(url=url,sha256=hashlib.sha256(data).hexdigest(),
                         cached_path=str(path.relative_to(ROOT)))
    candidates=[]
    controls=[]
    for year in [2014,2018]:
        summary_url=BASE+f'state{year}/summary.html'
        data,record=fetch(summary_url)
        provenance.append(record)
        tree=html.fromstring(data)
        links={urljoin(summary_url,a.get('href')) for a in tree.xpath('//a[@href]')
               if text(a).endswith(' District') and 'district.html' in a.get('href','')}
        if len(links)!=88:
            raise ValueError(f'{year}: expected 88 official district links, got {len(links)}')
        table=tree.xpath('//h2[contains(.,"Overall Lower House")]/following::table[1]')[0]
        for tr in table.xpath('.//tr'):
            cells=tr.xpath('./td')
            if len(cells)>=2 and re.fullmatch(r'[\d,]+',text(cells[1])):
                party=text(cells[0])
                controls.append(dict(Year=year,OfficialParty=party,Votes=int(text(cells[1]).replace(',','')),
                    BroadCategory='IND' if party=='Other Candidates' else category(party),SourceURL=summary_url))
        def one(url):
            data,record=fetch(url)
            return parse_district(data,year,url),record
        with ThreadPoolExecutor(max_workers=5) as pool:
            for index,(rows,record) in enumerate(pool.map(one,sorted(links)),1):
                candidates.extend(rows)
                provenance.append(record)
                if index%22==0:
                    print(year,index,'districts verified',flush=True)
    raw=pd.DataFrame(candidates).sort_values(['Year','District','Candidate'])
    raw.to_csv(OUT/'candidates.csv',index=False)
    control=pd.DataFrame(controls)
    control.to_csv(OUT/'official_statewide_controls.csv',index=False)
    for year in [2014,2018]:
        actual=int(raw.loc[raw.Year.eq(year),'Votes'].sum())
        expected=int(control.loc[control.Year.eq(year)&control.OfficialParty.eq('Total'),'Votes'].iloc[0])
        if actual!=expected:
            raise ValueError(f'{year} statewide total mismatch {actual} vs {expected}')
        for broad in ['ALP','LNP','GRN','ON','IND','OTH']:
            got=int(raw.loc[raw.Year.eq(year)&raw.BroadCategory.eq(broad),'Votes'].sum())
            want=int(control.loc[control.Year.eq(year)&control.BroadCategory.eq(broad)&~control.OfficialParty.eq('Total'),'Votes'].sum())
            if got!=want:
                raise ValueError(f'{year} {broad} official statewide control mismatch {got} vs {want}')
    grouped=raw.groupby(['Year','District','BroadCategory']).Votes.sum().unstack(fill_value=0)
    grouped=grouped.reindex(columns=['ALP','LNP','GRN','ON','IND','OTH'],fill_value=0)
    shares=grouped.div(grouped.sum(axis=1),axis=0)
    records=[]
    for (year,district),row in shares.iterrows():
        field=raw[raw.Year.eq(year)&raw.District.eq(district)]
        records.append(dict(Year=year,District=district,**row.to_dict(),
            FormalVotes=int(field.Votes.sum()),CandidateCount=len(field),
            IndependentCount=int(field.BroadCategory.eq('IND').sum()),
            CoalitionCandidateCount=int(field.BroadCategory.eq('LNP').sum()),
            LargestIndependentShare=float(field.loc[field.BroadCategory.eq('IND'),'Share'].max()) if field.BroadCategory.eq('IND').any() else 0,
            SourceURL=field.SourceURL.iloc[0],BoundaryBasis='2013 redivision; 2014/2018 comparison only',
            ClassificationPolicy='Official-label aggregation; no subjective IND-to-OTH reassignment'))
    panel=pd.DataFrame(records)
    panel.to_csv(OUT/'district_primaries.csv',index=False)
    (OUT/'manifest.json').write_text(json.dumps(dict(created_utc=datetime.now(timezone.utc).isoformat(),
        years=[2014,2018],district_rows=len(panel),candidate_rows=len(raw),
        formal_totals=raw.groupby('Year').Votes.sum().to_dict(),sources=provenance,
        boundary_source='https://www.parliament.vic.gov.au/49950e/globalassets/sections-shared/about/publications/research-papers/the2022victorianstateelection_rp_2023_2.pdf',
        warning='Independent raw historical evidence, not calibrated nowcast errors. Do not join to current districts by name without boundary reconciliation. Candidate labels retained, not production subjective classifications.'),indent=2))
    print(raw.groupby('Year').agg(Candidates=('Votes','size'),FormalVotes=('Votes','sum')).to_string())


if __name__=='__main__':
    main()
