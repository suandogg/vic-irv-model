import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from SRC.constants import PARTIES
from SRC.candidate_effects import apply_candidate_effects, load_candidate_effects, _allocate
from SRC.candidate_count import candidate_primaries, count_named, FIELD_COLUMNS, PREF_COLUMNS


def baseline():
    return pd.DataFrame([dict(district=d,region='Western Metro',seat_type='Outer Metro',held_by='ALP',
                             **dict(zip(PARTIES,[.3,.3,.1,.1,.1,.1]))) for d in ['A','B','C']])


def effect(cid='new', **extra):
    return dict(district='A',candidate_id=cid,current_model_group='IND',previous_model_group='',
                continuity_status='new',baseline_component_pp=0,personal_vote_retention=0,
                candidate_effect_pp=3,effect_sd_pp=0,preference_profile_id='ip',enabled=True,
                **{f'donor_{p}':1 if p=='LNP' else 0 for p in PARTIES},
                **{f'release_{p}':1 if p=='ALP' else 0 for p in PARTIES}) | extra


class ContinuityTests(unittest.TestCase):
    targets = dict(zip(PARTIES,[30,30,10,10,10,10]))

    def test_live_disabled_records_exact_noop(self):
        original=baseline()
        out,diag=apply_candidate_effects(original,load_candidate_effects(),self.targets)
        pd.testing.assert_frame_equal(original,out,check_exact=True)
        self.assertTrue(diag.empty)

    def test_removal_uses_old_oth_not_ind_or_raw_historical_share(self):
        r=effect(previous_model_group='OTH',current_model_group='LNP',continuity_status='switched',
                 baseline_component_pp=4,previous_primary_pp=99,candidate_effect_pp=0)
        out,diag=apply_candidate_effects(baseline(),pd.DataFrame([r]),self.targets)
        self.assertAlmostEqual(out.iloc[0].OTH,.06)
        self.assertAlmostEqual(out.iloc[0].IND,.1)
        self.assertAlmostEqual(out.iloc[0].ALP,.34)
        self.assertAlmostEqual(diag.iloc[0].removed_pp,4)

    def test_addition_conservation_and_statewide_targets(self):
        out,diag=apply_candidate_effects(baseline(),pd.DataFrame([effect()]),self.targets)
        self.assertAlmostEqual(out.iloc[0].IND,.13)
        self.assertAlmostEqual(out.iloc[0].LNP,.27)
        np.testing.assert_allclose(out[PARTIES].mean()*100,list(self.targets.values()),atol=1e-8)
        np.testing.assert_allclose(out[PARTIES].sum(axis=1),1,atol=1e-10)

    def test_row_permutation_invariant(self):
        rows=pd.DataFrame([effect('x'),effect('y',candidate_effect_pp=2)])
        a,ad=apply_candidate_effects(baseline(),rows,self.targets)
        b,bd=apply_candidate_effects(baseline(),rows.iloc[::-1],self.targets)
        pd.testing.assert_frame_equal(a,b,check_exact=True)
        pd.testing.assert_frame_equal(ad,bd,check_exact=True)

    def test_capacity_redistributes_and_reports_unfunded(self):
        movements=_allocate(np.array([.6,.6]),np.array([[.5,.5],[1.,0.]]),np.array([.2,.5]))
        self.assertAlmostEqual(movements.sum(),.7)
        self.assertTrue((movements.sum(axis=0)<=np.array([.2,.5])+1e-12).all())

    def test_missing_and_overlapping_inputs_rejected(self):
        for r in [effect(effect_sd_pp=''),effect(donor_LNP=0),
                  effect(previous_model_group='OTH',continuity_status='returning',baseline_component_pp=20)]:
            with self.assertRaises(ValueError):
                apply_candidate_effects(baseline(),pd.DataFrame([r]),self.targets)
        adjustments=pd.DataFrame([dict(district='A',party='IND',candidate_strength_pp=1,enabled=True)])
        with self.assertRaisesRegex(ValueError,'Overlapping'):
            apply_candidate_effects(baseline(),pd.DataFrame([effect()]),self.targets,adjustments)

    def test_seeded_candidate_uncertainty(self):
        rows=pd.DataFrame([effect(effect_sd_pp=1)])
        a,ad=apply_candidate_effects(baseline(),rows,self.targets,rng=np.random.default_rng(42))
        b,bd=apply_candidate_effects(baseline(),rows,self.targets,rng=np.random.default_rng(42))
        pd.testing.assert_frame_equal(a,b)
        pd.testing.assert_frame_equal(ad,bd)

    def test_incompatible_targets_rejected(self):
        with self.assertRaises(ValueError):
            apply_candidate_effects(baseline(),pd.DataFrame([effect()]),dict(ALP=50,LNP=50,GRN=0,ON=0,IND=0,OTH=0))

    def test_empty_sheet_clears_saved_rows(self):
        from SRC.live_sheet_sync import worksheet_to_dataframe, FILES
        from unittest.mock import Mock
        sheet=Mock()
        sheet.get_all_values.return_value=[list(effect())]
        frame=worksheet_to_dataframe(sheet,'LOWER_CANDIDATE_EFFECTS')
        self.assertTrue(frame.empty)
        self.assertIn('candidate_id',frame.columns)
        self.assertIn('LOWER_CANDIDATE_FIELD',FILES)


class NamedCountTests(unittest.TestCase):
    def fixture(self):
        roster=pd.DataFrame([dict(candidate_id=c,candidate_name=c,model_group=g,
            preference_profile_id=profile,receiving_weight=1) for c,g,profile in
            [('a','ALP',''),('l','LNP',''),('i1','IND','p1'),('i2','IND','p2')]])
        priors={'p1':{'i2':.9,'a':.1,'l':0},'p2':{'a':.8,'l':.2,'i1':0}}
        return roster,{'a':.35,'l':.3,'i1':.1,'i2':.25},priors

    def test_independents_compete_individually_and_conserve_parcels(self):
        roster,votes,priors=self.fixture()
        result=count_named(roster,votes,priors,{},'Outer Metro',{}, {},{})
        self.assertEqual(result['trace'][0]['eliminated'],'i1')
        self.assertAlmostEqual(result['trace'][0]['i2'],.34)
        self.assertAlmostEqual(sum(result['final_votes'].values()),1)
        self.assertNotEqual(result['winner_candidate'],result['runner_up_candidate'])

    def test_profile_with_no_continuing_mass_fails_closed(self):
        roster,votes,priors=self.fixture()
        priors['p1']={'i1':1}
        with self.assertRaisesRegex(ValueError,'no continuing'):
            count_named(roster,votes,priors,{},'Outer Metro',{}, {},{})

    def test_on_holder_special_prior_stays_locked(self):
        roster=pd.DataFrame([dict(candidate_id=c,model_group=g,preference_profile_id='',receiving_weight=1)
            for c,g in [('a','ALP'),('l','LNP'),('on','ON')]])
        with patch('SRC.candidate_count.diagnose_preference_weights',return_value={
            'basis':'ON special prior','final_flows':{'ALP':.2,'LNP':.8}}) as engine:
            result=count_named(roster,{'a':.45,'l':.45,'on':.1},{},{},'Rural',{}, {},{})
        self.assertAlmostEqual(result['final_votes']['l'],.53)
        self.assertEqual(engine.call_args.args[0],'ON')

    def test_missing_current_field_is_not_silently_aggregated(self):
        with self.assertRaisesRegex(ValueError,'complete unique'):
            candidate_primaries(baseline().iloc[0],pd.DataFrame([effect()]),
                pd.DataFrame([dict(candidate_id='new',realised_effect_pp=3)]),
                pd.DataFrame(columns=FIELD_COLUMNS),pd.DataFrame(columns=PREF_COLUMNS))

    def test_pipeline_calculator_and_forecast_use_same_named_result(self):
        from SRC.candidate_count import apply_candidate_pipeline
        from SRC.forecast_engine import forecast_counts
        from SRC.irv import run_irv_all
        from SRC.transform import build_primary_vote_table
        field=pd.DataFrame([dict(district='A',candidate_id=p, candidate_name=p,
            model_group=p,baseline_weight=1,receiving_weight=1,
            preference_profile_id=p+'p' if p in ('IND','OTH') else '',enabled=True) for p in PARTIES])
        field=pd.concat([field,pd.DataFrame([dict(district='A',candidate_id='new',candidate_name='New',
            model_group='IND',baseline_weight=0,receiving_weight=1,preference_profile_id='ip',enabled=True)])],ignore_index=True)
        profiles=pd.DataFrame([dict(district='A',profile_id=profile,recipient_id=recipient,weight=1,enabled=True)
            for owner,profile in [('IND','INDp'),('OTH','OTHp'),('new','ip')]
            for recipient in field.candidate_id if recipient!=owner])
        effects=pd.DataFrame([effect()])
        with patch('SRC.candidate_count.load_candidate_tables',return_value=(field,profiles)):
            adjusted=apply_candidate_pipeline(baseline(),ContinuityTests.targets,effects=effects)
        matrices={d:{'matrix':{}} for d in ['A','B','C']}
        calculator=pd.DataFrame(run_irv_all(build_primary_vote_table(adjusted),matrices,{}, {},{},
            candidate_context=adjusted.attrs['candidate_context'])).set_index('district')
        forecast=forecast_counts(adjusted,matrices,{}, {},{}).set_index('district')
        self.assertEqual(calculator.at['A','winner'],forecast.at['A','winner'])
        self.assertAlmostEqual(calculator.at['A','ALP_2PP'],forecast.at['A','ALP_2PP'])
        self.assertAlmostEqual(calculator.at['A','primary_votes']['new'],.03)

    def test_forced_count_can_protect_absent_major_without_real_field_entry(self):
        roster, votes, profiles=self.fixture()
        result=count_named(roster,votes,profiles,{},'Outer Metro',{}, {},{},forced=('ALP','ON'))
        self.assertEqual(set(result['candidate_groups'][cid] for cid,v in result['final_votes'].items() if v>0),{'ALP','ON'})
        self.assertIn('__forced_ON',result['final_votes'])


if __name__=='__main__':
    unittest.main()
