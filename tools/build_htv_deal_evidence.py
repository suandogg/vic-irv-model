"""Build the 2018-vs-2022 how-to-vote evidence for the 2026 preference deal switch.

Usage: python tools/build_htv_deal_evidence.py

Inputs (all VEC, no Sheet):
  data/research/vec_2018_distributions/sources/distribution*district.html
      2018 distribution of preferences pages, from
      https://itsitecoreblobvecprd01.blob.core.windows.net/public-files/historical-results/state2018/
      The VEC published no 2018 distribution for 40 districts (no full count was
      needed), including Preston and Footscray.
  data/research/historical_primaries_2026_10_29/candidates.csv  (2018 parties)
  data/development/VEC_2022_DISTRIBUTIONS_LONG.csv and
  data/development/VEC_2022_CANDIDATE_CLASSIFICATION.csv

  data/research/vec_2018_distributions/sources/indicative_2cp/
      fpvbyvotingcentre*.html and tcpbyvotingcentre*.html: 2018 first preferences
      and indicative Labor-v-Greens two-candidate counts by voting centre, for
      seats won on primaries with no published distribution (Preston).

Methods (column `method`):
  distribution: whole Liberal bundle, only Labor and the Greens continuing.
  distribution_third_candidate: a third candidate was still in the count
      (Pascoe Vale 2018, Yildiz). Converted to the Labor share of the part of the
      bundle that went to Labor or the Greens, which assumes the voters who went
      to the third candidate rank Labor and the Greens the same way.
  indicative_2cp: every first preference is counted to Labor or the Greens, so
      at each voting centre Labor's gain = s_lib*Liberal + s_minor*minor votes.
      s_lib and s_minor are fitted by least squares across voting centres.
      This is the Liberal voters' own split, not the bundle at exclusion.

Outputs:
  data/development/VEC_2018_DISTRIBUTIONS_LONG.csv
  data/development/HTV_DEAL_EVIDENCE.csv: for each district where a party's
  whole bundle was distributed with both named recipients continuing, the
  toward share of (toward + away) in 2018 and 2022 and the logit change.
  2018 boundaries predate the 2021 redivision; districts are matched by name.
"""
import math
import re
import numpy as np
from html.parser import HTMLParser
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT/'data/research/vec_2018_distributions/sources'
BASE_URL = 'https://itsitecoreblobvecprd01.blob.core.windows.net/public-files/historical-results/state2018/'
PAIRS = [('LNP', 'ALP', 'GRN'), ('ALP', 'LNP', 'GRN')]


class Table(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.row, self.cell = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.row = []
        elif tag in ('td', 'th') and self.row is not None:
            self.cell = ''

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None:
            self.row.append(re.sub(r'\s+', ' ', self.cell).strip())
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            self.rows.append(self.row)
            self.row = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell += data


def key(name):
    return re.sub(r'[^a-z]', '', str(name).lower())


def parse_2018():
    rows = []
    for path in sorted(SOURCES.glob('distribution*district.html')):
        table = Table()
        table.feed(path.read_text(encoding='utf-8-sig'))
        names = None
        for cells in table.rows:
            if names is None and cells and cells[-1] == 'TOTAL':
                names = [c for c in cells if c and c != 'TOTAL']
                continue
            if names and cells and cells[0].startswith('Transfer of'):
                match = re.match(r'Transfer of ([\d,]+) ballot papers of (.+?) \((\d+)\w* excluded', cells[0])
                if not match:
                    raise ValueError(f'{path.name}: unreadable transfer row {cells[0]!r}')
                total = 0
                for name, value in zip(names, cells[1:]):
                    value = value.replace(',', '')
                    if value.isdigit():
                        total += int(value)
                        rows.append(dict(file_key=key(path.name[len('distribution'):-len('district.html')]),
                                         Round=int(match.group(3)), EliminatedCandidate=match.group(2),
                                         RecipientCandidate=name, VotesTransferred=int(value),
                                         SourceURL=BASE_URL+path.name))
                if total != int(match.group(1).replace(',', '')):
                    raise ValueError(f'{path.name}: transfers do not sum to the bundle')
        if names is None:
            raise ValueError(f'{path.name}: no distribution table')
    long = pd.DataFrame(rows)
    candidates = pd.read_csv(ROOT/'data/research/historical_primaries_2026_10_29/candidates.csv')
    candidates = candidates[candidates.Year.eq(2018)].assign(file_key=lambda d: d.District.map(key))
    party = candidates.set_index(['file_key', 'Candidate']).BroadCategory
    district = candidates.drop_duplicates('file_key').set_index('file_key').District
    long['District'] = long.file_key.map(district)
    long['From'] = [party.get((k, n)) for k, n in zip(long.file_key, long.EliminatedCandidate)]
    long['To'] = [party.get((k, n)) for k, n in zip(long.file_key, long.RecipientCandidate)]
    if long[['District', 'From', 'To']].isna().any().any():
        raise ValueError('2018 candidates missing from candidates.csv')
    return long.drop(columns='file_key')


def load_2022():
    long = pd.read_csv(ROOT/'data/development/VEC_2022_DISTRIBUTIONS_LONG.csv')
    long = long.groupby(['Electorate', 'Round', 'EliminatedCandidate', 'RecipientCandidate'],
                        as_index=False).VotesTransferred.sum().rename(columns={'Electorate': 'District'})
    party = pd.read_csv(ROOT/'data/development/VEC_2022_CANDIDATE_CLASSIFICATION.csv')
    party = party.set_index(['Electorate', 'CandidateName']).BroadCategory
    long['From'] = [party.get((d, n)) for d, n in zip(long.District, long.EliminatedCandidate)]
    long['To'] = [party.get((d, n)) for d, n in zip(long.District, long.RecipientCandidate)]
    return long


def splits(long, origin, toward, away):
    """One row per district: the party's whole-bundle split, both recipients continuing."""
    rows = []
    for (district, rnd), group in long[long.From.eq(origin)].groupby(['District', 'Round']):
        received = group[group.VotesTransferred > 0].groupby('To').VotesTransferred.sum()
        if received.get(toward, 0) > 0 and received.get(away, 0) > 0:
            rows.append(dict(District=district, round=int(rnd), bundle=int(received.sum()),
                             continuing='+'.join(sorted(received.index)),
                             share=received[toward]/(received[toward]+received[away])))
    out = pd.DataFrame(rows)
    # A seat with two candidates of the origin party keeps the later (larger) bundle.
    return out.sort_values('round').drop_duplicates('District', keep='last') if len(out) else out


def indicative_2cp():
    """Liberal share to Labor from 2018 voting-centre first preferences and 2CP counts."""
    rows = []
    folder = SOURCES/'indicative_2cp'
    for tcp_path in sorted(folder.glob('tcpbyvotingcentre*district.html')):
        name = tcp_path.name[len('tcpbyvotingcentre'):-len('district.html')]
        fp = Table(); fp.feed((folder/f'fpvbyvotingcentre{name}district.html').read_text(encoding='utf-8-sig'))
        tc = Table(); tc.feed(tcp_path.read_text(encoding='utf-8-sig'))
        fp_head = next(r for r in fp.rows if r and r[0] == 'Voting Centres')
        fp_names = next(r for r in fp.rows if len(r) == len(fp_head) and r[0] == '' and r[1])
        tc_head = next(r for r in tc.rows if r and r[0] == 'Voting Centres')
        if tc_head[1:3] != ['AUSTRALIAN LABOR PARTY', 'AUSTRALIAN GREENS']:
            raise ValueError(f'{name}: 2018 indicative count is not Labor v Greens')
        parties = fp_head[1:len(fp_head)-2]

        def counts(table, width):
            out = {}
            for r in table.rows:
                if len(r) > width and r[0] != 'Voting Centres' and 'total' not in r[0].lower() \
                        and all(x.replace(',', '').isdigit() for x in r[1:width+1]):
                    out[r[0]] = [int(x.replace(',', '')) for x in r[1:width+1]]
            return out
        first = pd.DataFrame(counts(fp, len(parties)), index=parties).T
        tcp = pd.DataFrame(counts(tc, 2), index=['ALP2', 'GRN2']).T
        booths = first.join(tcp, how='inner')
        gap = booths[parties].to_numpy().sum()-(booths.ALP2.sum()+booths.GRN2.sum())
        if abs(gap) > .005*booths[parties].to_numpy().sum():  # mis-sorts only
            raise ValueError(f'{name}: voting-centre first preferences and 2CP totals differ by {gap}')
        labor = parties.index('AUSTRALIAN LABOR PARTY')
        greens = parties.index('AUSTRALIAN GREENS')
        liberal = parties.index('LIBERAL')
        minor = [i for i in range(len(parties)) if i not in (labor, greens, liberal)]
        x = np.column_stack([booths.iloc[:, liberal], booths.iloc[:, minor].sum(axis=1)]).astype(float)
        y = (booths.ALP2-booths.iloc[:, labor]).to_numpy(float)
        coef = np.linalg.lstsq(x, y, rcond=None)[0]
        if not ((0 < coef) & (coef < 1)).all():
            raise ValueError(f'{name}: fitted shares outside (0, 1): {coef}')
        rows.append(dict(file_key=key(name), share=float(coef[0]), minor_share=float(coef[1]),
                         booths=len(booths), bundle=int(booths.iloc[:, liberal].sum())))
    return pd.DataFrame(rows)


def main():
    y2018 = parse_2018()
    y2018.to_csv(ROOT/'data/development/VEC_2018_DISTRIBUTIONS_LONG.csv', index=False)
    y2022 = load_2022()
    rows = []
    for origin, toward, away in PAIRS:
        a, b = splits(y2018, origin, toward, away), splits(y2022, origin, toward, away)
        both = a.merge(b, on='District', suffixes=('_2018', '_2022'))
        for r in both.itertuples():
            continuing = set(r.continuing_2018.split('+'))
            method = 'distribution' if continuing == {toward, away} else 'distribution_third_candidate'
            rows.append(dict(District=r.District, origin=origin, toward=toward, away=away, method=method,
                             share_2018=round(r.share_2018, 6), share_2022=round(r.share_2022, 6),
                             continuing_2018=r.continuing_2018, continuing_2022=r.continuing_2022,
                             bundle_2018=r.bundle_2018, bundle_2022=r.bundle_2022,
                             logit_change=round(math.log(r.share_2018/(1-r.share_2018))
                                                - math.log(r.share_2022/(1-r.share_2022)), 6)))
    candidates = pd.read_csv(ROOT/'data/research/historical_primaries_2026_10_29/candidates.csv')
    names = candidates.drop_duplicates('District').assign(k=lambda d: d.District.map(key)).set_index('k').District
    lib_2022 = splits(y2022, 'LNP', 'ALP', 'GRN').set_index('District')
    for r in indicative_2cp().itertuples():
        district = names[r.file_key]
        if any(x['District'] == district and x['origin'] == 'LNP' for x in rows):
            continue
        later = lib_2022.loc[district]
        rows.append(dict(District=district, origin='LNP', toward='ALP', away='GRN', method='indicative_2cp',
                         share_2018=round(r.share, 6), share_2022=round(later.share, 6),
                         continuing_2018=f'ALP+GRN (2CP fit, {r.booths} voting centres, minor share {r.minor_share:.3f})',
                         continuing_2022=later.continuing, bundle_2018=r.bundle, bundle_2022=int(later.bundle),
                         logit_change=round(math.log(r.share/(1-r.share))-math.log(later.share/(1-later.share)), 6)))
    pd.DataFrame(rows).to_csv(ROOT/'data/development/HTV_DEAL_EVIDENCE.csv', index=False)


if __name__ == '__main__':
    main()
