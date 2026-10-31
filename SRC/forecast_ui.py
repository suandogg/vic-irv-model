"""On-demand forecast view, separate from the deterministic dashboard."""
import json
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import streamlit as st
from SRC.constants import PARTIES
from SRC.forecast_params import load_forecast_params, parameter_table
from SRC.forecast_engine import fingerprint, simulate, engine_source_hash, uncertainty_profile, STRUCTURAL_EXPERIMENTS
from SRC.display_params import defaults as display_defaults
from SRC.forecast_subregions import load_subregions
from SRC.presentation import table as display_table, seat_intervals, event_bars, party_summary


def render_forecast(primary_inputs,matrices,params,posterior,ideology,targets,
                    seat_adjustments,trial_label,sync_status,central_runner,turnout_weights):
    display = st.session_state.get('_display_settings',display_defaults())
    st.header(display['FORECAST_TITLE'])
    st.warning('Model-based scenario probabilities — provisional, not historically calibrated. '
               'These are conditional on your primary inputs and uncertainty assumptions, not an independent polling forecast.')
    st.caption('The existing calculator is unchanged. This view runs whole-election simulations '
               'around it. Council probabilities are not yet modelled; minority outcomes assume the support specified below.')
    st.caption('Active preference method: '+trial_label)
    st.caption('Enabled candidate records use named counts and their own effect SDs. Review overlap with local residual SDs. The narrower/wider settings comparison holds candidate-sheet SDs fixed.')
    try:
        settings, source = load_forecast_params()
    except ValueError as exc:
        st.error(str(exc))
        return
    st.caption(source+'. Refresh Google Sheet inputs after editing the FORECAST PARAMS tab. '
               'If sync is unavailable, the committed CSV settings are used.')
    with st.expander('Current forecast settings and methodology',expanded=False):
        experiment_label = st.selectbox('Structural uncertainty trial (unvalidated)',
            list(STRUCTURAL_EXPERIMENTS),key='forecast_structural_trial')
        experiment = STRUCTURAL_EXPERIMENTS[experiment_label]
        geographic_label = st.selectbox('Geographic uncertainty grouping',
            ['Upper-house regions (current)','Blend upper-house and sub-regions','Sub-regions only'],
            key='forecast_geographic_trial')
        sub_fraction = {'Upper-house regions (current)':0.,'Blend upper-house and sub-regions':.5,
                        'Sub-regions only':1.}[geographic_label]
        experiment = dict(experiment)
        structured='structured_nowcast' in experiment
        if structured:
            from SRC.nowcast_loader import load_nowcast_inputs
            try:
                config,review=load_nowcast_inputs(list(primary_inputs.district))
            except (ValueError,TypeError) as exc:
                st.error(str(exc))
                return
            experiment['structured_nowcast']=config
            st.warning('Development configuration, not a calibrated replacement forecast. '
                'ALP/LNP/Greens scales are historical proxies; ON/IND/OTH scales are inherited '
                'assumptions. Preference-transport scales come from NOWCAST BUDGET. '
                'This replaces ordinary regional/local primary noise.')
            if 'concentration_log_sd' in experiment:
                st.caption('Combined development mode retains all-party concentration uncertainty '
                    'and replaces only its ordinary district/regional residuals with NOWCAST BUDGET. '
                    'These components can overlap; the combination is a deliberate judgment-based '
                    '2026 assumption, not a historically calibrated probability model.')
            st.caption(f"Candidate/context review: {review['unreviewed_contexts']} unreviewed; "
                       f"{review['enabled_contexts']} enabled. No new candidate appearances are simulated.")
            display_table(review['budget'],hide_index=True,width='stretch')
            display_table(review['correlation'],hide_index=True,width='stretch')
        subregions,subregion_source = None,'Upper-house regions only; SUB-REGIONS not used'
        if sub_fraction:
            try:
                mapping,subregion_source = load_subregions(list(primary_inputs.district))
            except ValueError as exc:
                st.error(str(exc))
                return
            subregions = dict(zip(mapping.district,mapping.subregion))
            experiment['subregion_fraction'] = sub_fraction
        st.caption(subregion_source+'. Geographic primary SD stays fixed; blend splits its '
                   'pre-balancing variance equally between the two crossed groupings. '
                   'Regional preference trials use the same grouping; other trials leave preferences unchanged.')
        if structured and sub_fraction:
            st.caption('The historical regional scale was estimated on historical upper-house regions, '
                       'not these sub-regions. This blend is an additional assumption, not a fitted component.')
        st.caption('Current is the unchanged default. Preference split replaces half the shared '
                   'origin/recipient variance with local variance; Preference added retains shared '
                   'variance and adds an equally scaled local component. Heavy tails t5 changes only '
                   'local primary error shape, preserving variance before balancing. Combined applies '
                   'added local preferences and t5. These are uncalibrated trials; source preference '
                   'rows and Sheet values remain unchanged.')
        if 'concentration_log_sd' in experiment:
            combined = structured
            mapping_label = st.selectbox('Concentration mapping (research)',
                ['Linear (existing stress)','Positive softplus','Positive bounded (0–2)'],
                index=2 if combined else 0,
                key='forecast_combined_concentration_form' if combined else 'forecast_concentration_form')
            form = {'Linear (existing stress)':'linear','Positive softplus':'positive_softplus',
                    'Positive bounded (0–2)':'positive_bounded'}[mapping_label]
            if form!='linear':
                experiment['concentration_form'] = form
                st.caption('Positive forms prevent initial power reversal, not all final seat-rank changes. '
                           'Softplus has no upper power limit; bounded constrains powers between 0 and 2. '
                           'Both match the original near its centre, not its full variance. Neither caps seat counts.')
            experiment['concentration_log_sd'] = st.number_input('Common concentration input width (research)',
                min_value=0.,max_value=1.,value=.3 if combined else .2,step=.05,
                key='forecast_combined_concentration_sd' if combined else 'forecast_concentration_sd')
            st.caption('One coefficient per party per election varies concentration of current positive support, '
                       'then balances all party and seat totals. Positive concentrates, negative flattens. '
                       'This replaces ON alpha uncertainty for this trial, not its central value. '
                       'The width is a judgment-based assumption, not a fitted estimate; '
                       'combined mode starts at the previous trial’s 0.30.')
            if st.checkbox('Use party-specific concentration widths (research)',key='forecast_party_widths'):
                widths = {}
                columns = st.columns(3)
                for index,party in enumerate(PARTIES):
                    with columns[index%3]:
                        widths[party] = st.number_input(party+' concentration input width',min_value=0.,max_value=1.,
                            value=.2,step=.05,key='forecast_concentration_'+party)
                experiment['concentration_by_party'] = widths
                st.caption('Party-specific values override the common width. An ON value of zero retains '
                           'ordinary ON-alpha uncertainty; a positive value replaces it. These controls do not edit Sheets.')
        if experiment.get('preference_region_share',0):
            st.caption('Regional preference trial: existing origin/recipient variance is partitioned '
                       '50% statewide, 25% geographic, 25% local for every party. Source-based SDs '
                       'and the separate class-ON shock stay unchanged. No extra origin/recipient '
                       'variance is added. Flow regimes and source rows are unchanged.')
        display_table(parameter_table(settings),hide_index=True,width='stretch')
        if structured:
            st.caption('In this mode REGION_PRIMARY_SD_PP and SEAT_PRIMARY_SD_PP above are replaced '
                       'by NOWCAST BUDGET. Other FORECAST PARAMS, including statewide uncertainty '
                       'and existing preference SDs, remain active. NOWCAST CONTEXTS affects only '
                       'reviewed, enabled rows. Central candidate overrides are not changed.')
        st.markdown('All SDs are **provisional assumptions**, not fitted estimates. Statewide party errors '
            'start independent, then are constrained to total 100%; a fitted polling covariance is not yet available. '
            'Regional/local shocks preserve each simulated scenario’s underlying equal-seat statewide totals '
            'and do not introduce candidates with zero support. Preference shocks share origin/recipient '
            'directions across seats and fields, with additional ON seat-class movement. '
            'The selected preference architecture stays fixed in a run: this does not cover all structural model uncertainty. '
            'Explicit candidate/seat overrides stay central; local residual variation covers unmodelled local effects.')
    from SRC.candidate_effects import load_candidate_effects
    from SRC.candidate_count import load_candidate_tables
    signature = fingerprint(primary_inputs,matrices,params,posterior,ideology,targets,
                            seat_adjustments,settings,trial_label,experiment,subregions,
                            load_candidate_effects(),load_candidate_tables())
    stored = st.session_state.get('lower_forecast_run')
    if stored and stored['signature']!=signature:
        st.info('Inputs, preference method or settings changed. Previous results are hidden; run again.')
        stored = None
    st.caption(f"{settings['SIMULATIONS']:,} draws; seed {settings['SEED']}. "
               'The default is a 200-draw preview. More draws reduce simulation noise, not uncertainty in the assumptions.')
    if settings['SIMULATIONS']>=1000:
        st.info('Large runs may take several minutes on Streamlit. Start with the preview while reviewing assumptions.')
    if st.button('Run lower-house forecast',type='primary',key='run_lower_forecast'):
        progress = st.progress(0,text='Preparing simulations…')
        def update(done,total):
            if done%5==0 or done==total:
                progress.progress(done/total,text=f'Simulation {done:,} of {total:,}')
        try:
            result = simulate(primary_inputs,matrices,params,posterior,ideology,targets,
                              seat_adjustments,settings,update,experiment=experiment,subregions=subregions)
            central,_,_ = central_runner(primary_inputs,matrices,params,posterior,ideology,
                                         targets,seat_adjustments,turnout_weights)
            result['seats'].insert(1,'Central winner',result['seats'].Seat.map(central.set_index('district').winner))
            stored = {'signature':signature,'result':result,
                      'created_utc':datetime.now(timezone.utc).isoformat(),
                      'trial':trial_label,'sync_message':sync_status.get('message','Unknown input sync status')}
            st.session_state['lower_forecast_run'] = stored
        except (ValueError,KeyError,ArithmeticError) as exc:
            st.error('Forecast not published: '+str(exc))
            return
        finally:
            progress.empty()
    if not stored:
        st.info('Set the statewide primaries above, review the Sheet assumptions, then run the forecast. '
                'Opening this view does not automatically start simulations.')
        return
    result = stored['result']
    st.caption('Structural uncertainty trial: '+experiment_label+' · '+geographic_label)
    with st.expander('Compare narrower / current / wider uncertainty'):
        st.caption('Halve or multiply all uncertainty SDs by 1.5, keeping central inputs, '
                   'preference method, seed and draw count fixed. This is sensitivity testing, '
                   'not calibration. Sheet settings are not changed. Two additional runs are required.')
        if st.button('Run uncertainty comparison',key='compare_forecast_uncertainty'):
            comparison = {'Current':result}
            with st.spinner('Running narrower and wider assumptions…'):
                try:
                    for label,multiplier in [('Narrower (0.5× SD)',.5),('Wider (1.5× SD)',1.5)]:
                        trial_experiment = dict(experiment)
                        if 'concentration_log_sd' in trial_experiment:
                            trial_experiment['concentration_log_sd'] *= multiplier
                        if 'concentration_by_party' in trial_experiment:
                            trial_experiment['concentration_by_party'] = {
                                p:width*multiplier for p,width in trial_experiment['concentration_by_party'].items()}
                        if 'structured_nowcast' in trial_experiment:
                            from SRC.nowcast_loader import scale_config
                            trial_experiment['structured_nowcast']=scale_config(
                                trial_experiment['structured_nowcast'],multiplier)
                        comparison[label] = simulate(primary_inputs,matrices,params,posterior,ideology,
                            targets,seat_adjustments,uncertainty_profile(settings,multiplier),
                            experiment=trial_experiment,subregions=subregions)
                    st.session_state['forecast_uncertainty_comparison'] = (signature,comparison)
                except (ValueError,KeyError,ArithmeticError) as exc:
                    st.error('Comparison not published: '+str(exc))
        comparison = st.session_state.get('forecast_uncertainty_comparison')
        if comparison and comparison[0]==signature:
            for key in ('parties','government'):
                table = pd.concat([value[key].assign(Assumptions=label)
                                   for label,value in comparison[1].items()],ignore_index=True)
                display_table(table,hide_index=True,width='stretch')
                st.download_button('Download comparison '+key,table.to_csv(index=False),
                                   'forecast_uncertainty_'+key+'.csv','text/csv')
    st.caption('Run completed (UTC): '+stored['created_utc']+' · '+stored['sync_message'])
    overview,seats,assumptions = st.tabs(['Parliament','Seat probabilities','Run details'])
    with overview:
        st.subheader('Seat-count distributions')
        st.caption(f"Lower/upper endpoints: {100*settings['LOWER_QUANTILE']:g}th / "
                   f"{100*settings['UPPER_QUANTILE']:g}th percentiles. "
                   'Party medians and interval endpoints need not sum to 88. Every individual draw does. '
                   'Average seats sum to 88 before display rounding; fractional seats represent averages across simulations, not a single election.')
        party_table = result['parties']
        if not display['SHOW_ZERO_SEAT_PARTIES']:
            party_table = party_table[party_table['Upper seats']>0]
        if display['SEAT_CHART_MODE'] in ('intervals','both'):
            seat_intervals(party_table,display)
            st.caption('Wide band: selected lower–upper percentiles; narrow band: middle 50%; black marker: median. The majority line is fixed at 45.')
        if display['SHOW_FORECAST_SEAT_TABLE'] or display['SEAT_CHART_MODE']=='table':
            display_table(party_summary(party_table,display),hide_index=True,width='stretch',
                          column_config={'Average seats':st.column_config.NumberColumn('Average seats',format='%.2f')})
        st.subheader('Majority and parliamentary arithmetic')
        if display['GOVERNMENT_CHART_MODE'] in ('bars','both'):
            event_bars(result['government'],display)
        if display['GOVERNMENT_CHART_MODE'] in ('table','both'):
            display_table(result['government'].iloc[:7],hide_index=True,width='stretch',probabilities=True)
            st.divider()
            display_table(result['government'].iloc[7:],hide_index=True,width='stretch',probabilities=True)
        st.caption('Majority and hung parliament are complementary. The detailed rows can overlap: '
                   'coalition rows require both partners below 45 individually and do not predict an agreement. '
                   'The larger partner determines the leader; equal LNP/ON seat counts are in neither led row. '
                   'ALP minority means ALP is below 45 and ALP + GRN or ALP + IND reaches 45; '
                   'both routes qualifying counts once. It assumes support, not an agreement prediction. '
                   'Deadlock means ALP + GRN = 44 and LNP + ON = 44.')
        histogram = pd.DataFrame({party:result['draws'][party].value_counts().reindex(range(89),fill_value=0)
                                  /settings['SIMULATIONS'] for party in PARTIES})
        histogram.index.name = 'Seats'
        if display['SEAT_CHART_MODE'] in ('histogram','both'):
            order = display['PARTY_ORDER'].split(',')
            st.bar_chart(histogram[order].rename(columns={p:display[p+'_LABEL'] for p in order}),
                         x_label='Seat count',y_label='Fraction of simulations',stack=False,
                         height=display['CHART_HEIGHT_PX'],color=[display[p+'_COLOUR'] for p in order])
    with seats:
        with st.expander('Uncertainty diagnostics · near-certain seats'):
            diagnostics = result.get('diagnostics')
            if diagnostics is not None:
                certain = diagnostics[diagnostics['At least 98%']]
                st.caption(f'{len(certain)} of 88 seats have a leading win frequency of at least 98%. '
                           'MC intervals describe finite simulation precision only—not missing model uncertainty. '
                           'Forced ALP–LNP 2PP spread does not measure every possible final-pair contest. '
                           'Zero-support parties cannot gain support through local shocks.')
                display_table(certain,hide_index=True,width='stretch')
                st.download_button('Download all-seat uncertainty diagnostics',diagnostics.to_csv(index=False),
                                   'forecast_uncertainty_diagnostics.csv','text/csv')
        st.subheader('Five demonstration seats')
        display_table(result['seats'][result['seats'].Seat.isin(
            ['Pakenham','Morwell','Pascoe Vale','Ashwood','Yan Yean'])],hide_index=True,width='stretch')
        st.subheader('All 88 seats')
        display_table(result['seats'],hide_index=True,width='stretch')
        seat = st.selectbox('Inspect a seat',sorted(result['seats'].Seat),key='forecast_seat')
        row = result['seats'].set_index('Seat').loc[seat]
        display_table(pd.DataFrame({'Party':PARTIES,'Win probability (%)':[row[p+' win (%)'] for p in PARTIES]}),hide_index=True)
        st.caption('Winner margin is the winner’s share above 50%, not the incumbent swing. '
                   'Forced ALP–LNP 2PP remains comparable when actual finalists differ.')
        st.download_button('Download seat probabilities',result['seats'].to_csv(index=False),
                           'lower_forecast_seats.csv','text/csv')
    with assumptions:
        st.caption('Monte Carlo standard errors measure simulation noise only. Zero wins means '
                   'none in this finite sample—not that an outcome is impossible. These intervals are '
                   'conditional on this model and omit untested structural errors.')
        primary = result['primary_draws']
        st.subheader('Drawn statewide primaries')
        centre = np.array([targets[p] for p in PARTIES],dtype=float)
        centre = centre/centre.sum()*100
        display_table(pd.DataFrame({'Party':PARTIES,'Central (%)':centre,
            'Draw mean (%)':primary.mean().reindex(PARTIES).to_numpy(),
            '5th percentile (%)':primary.quantile(.05).reindex(PARTIES).to_numpy(),
            '95th percentile (%)':primary.quantile(.95).reindex(PARTIES).to_numpy()}),hide_index=True)
        st.caption('Projection and clipping can shift average draws near boundaries; shown explicitly above.')
        manifest = {k:stored[k] for k in ('signature','created_utc','trial','sync_message')}
        manifest.update(settings=settings,central_targets=targets,engine='forecast-v1',
                        structural_experiment=experiment,
                        subregions=subregions,subregion_source=subregion_source,
                        engine_source_hash=engine_source_hash(),
                        calibration='provisional; not calibrated to high-ON Victorian results')
        st.download_button('Download reproducibility record',json.dumps(manifest,indent=2),
                           'lower_forecast_run.json','application/json')
        st.download_button('Download all seat-count draws',result['draws'].to_csv(index=False),
                           'lower_forecast_draws.csv','text/csv')
        st.download_button('Download statewide primary draws',primary.to_csv(index=False),
                           'lower_forecast_primary_draws.csv','text/csv')
        if result.get('experiment',{}).get('concentration_log_sd',0) or any(
                result.get('experiment',{}).get('concentration_by_party',{}).values()):
            powers = result.get('concentration_exponents')
            if powers is not None:
                reversals = (powers<0).sum()
                if reversals.any():
                    st.warning('Some concentration draws reverse the initial strength ranking '
                               '(negative power), rather than merely flattening it. These are '
                               'uncalibrated stress results; review the diagnostic before adopting widths.')
                display_table(pd.DataFrame({'Party':PARTIES,
                    'Negative initial-power draws':reversals.reindex(PARTIES).to_numpy(),
                    'Minimum initial power':powers.min().reindex(PARTIES).to_numpy(),
                    'Maximum initial power':powers.max().reindex(PARTIES).to_numpy()}),hide_index=True)
                st.download_button('Download concentration power diagnostics',powers.to_csv(index=False),
                                   'forecast_concentration_exponents.csv','text/csv')
            st.download_button('Download concentration pattern coefficients',result['concentration_draws'].to_csv(index=False),
                               'forecast_concentration_draws.csv','text/csv')
            if 'primary_extremes' in result:
                st.download_button('Download primary dispersion diagnostics',result['primary_extremes'].to_csv(index=False),
                                   'forecast_primary_extremes.csv','text/csv')
