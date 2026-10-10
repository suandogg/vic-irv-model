"""On-demand forecast view, separate from the deterministic dashboard."""
import json
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import streamlit as st
from SRC.constants import PARTIES
from SRC.forecast_params import load_forecast_params, parameter_table
from SRC.forecast_engine import fingerprint, simulate, engine_source_hash, uncertainty_profile


def render_forecast(primary_inputs,matrices,params,posterior,ideology,targets,
                    seat_adjustments,trial_label,sync_status,central_runner,turnout_weights):
    st.header('Lower-house forecast · experimental')
    st.warning('Model-based scenario probabilities — provisional, not historically calibrated. '
               'These are conditional on your primary inputs and uncertainty assumptions, not an independent polling forecast.')
    st.caption('The existing calculator is unchanged. This view runs whole-election simulations '
               'around it. Council probabilities are not yet modelled; minority outcomes assume the support specified below.')
    st.caption('Active preference method: '+trial_label)
    try:
        settings, source = load_forecast_params()
    except ValueError as exc:
        st.error(str(exc))
        return
    st.caption(source+'. Refresh Google Sheet inputs after editing the FORECAST PARAMS tab. '
               'If sync is unavailable, the committed CSV settings are used.')
    with st.expander('Current forecast settings and methodology',expanded=False):
        st.dataframe(parameter_table(settings),hide_index=True,width='stretch')
        st.markdown('All SDs are **provisional assumptions**, not fitted estimates. Statewide party errors '
            'start independent, then are constrained to total 100%; a fitted polling covariance is not yet available. '
            'Regional/local shocks preserve each simulated scenario’s underlying equal-seat statewide totals '
            'and do not introduce candidates with zero support. Preference shocks share origin/recipient '
            'directions across seats and fields, with additional ON seat-class movement. '
            'The selected preference architecture stays fixed in a run: this does not cover all structural model uncertainty. '
            'Explicit candidate/seat overrides stay central; local residual variation covers unmodelled local effects.')
    signature = fingerprint(primary_inputs,matrices,params,posterior,ideology,targets,
                            seat_adjustments,settings,trial_label)
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
                              seat_adjustments,settings,update)
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
    with st.expander('Compare narrower / current / wider uncertainty'):
        st.caption('Halve or multiply all uncertainty SDs by 1.5, keeping central inputs, '
                   'preference method, seed and draw count fixed. This is sensitivity testing, '
                   'not calibration. Sheet settings are not changed. Two additional runs are required.')
        if st.button('Run uncertainty comparison',key='compare_forecast_uncertainty'):
            comparison = {'Current':result}
            with st.spinner('Running narrower and wider assumptions…'):
                try:
                    for label,multiplier in [('Narrower (0.5× SD)',.5),('Wider (1.5× SD)',1.5)]:
                        comparison[label] = simulate(primary_inputs,matrices,params,posterior,ideology,
                            targets,seat_adjustments,uncertainty_profile(settings,multiplier))
                    st.session_state['forecast_uncertainty_comparison'] = (signature,comparison)
                except (ValueError,KeyError,ArithmeticError) as exc:
                    st.error('Comparison not published: '+str(exc))
        comparison = st.session_state.get('forecast_uncertainty_comparison')
        if comparison and comparison[0]==signature:
            for key in ('parties','government'):
                table = pd.concat([value[key].assign(Assumptions=label)
                                   for label,value in comparison[1].items()],ignore_index=True)
                st.dataframe(table,hide_index=True,width='stretch')
                st.download_button('Download comparison '+key,table.to_csv(index=False),
                                   'forecast_uncertainty_'+key+'.csv','text/csv')
    st.caption('Run completed (UTC): '+stored['created_utc']+' · '+stored['sync_message'])
    overview,seats,assumptions = st.tabs(['Parliament','Seat probabilities','Run details'])
    with overview:
        st.subheader('Seat-count distributions')
        st.caption(f"Lower/upper endpoints: {100*settings['LOWER_QUANTILE']:g}th / "
                   f"{100*settings['UPPER_QUANTILE']:g}th percentiles. "
                   'Party medians and interval endpoints need not sum to 88. Every individual draw does.')
        st.dataframe(result['parties'],hide_index=True,width='stretch')
        st.subheader('Majority and parliamentary arithmetic')
        st.dataframe(result['government'],hide_index=True,width='stretch')
        st.caption('Single-party majorities plus hung parliament are mutually exclusive and exhaustive. '
                   'The LNP + ON rows overlap these outcomes and do not predict a coalition agreement. '
                   'ALP minority means ALP is below 45 and ALP + GRN or ALP + IND reaches 45; '
                   'both routes qualifying counts once. It assumes support, not an agreement prediction. '
                   'Deadlock means ALP + GRN = 44 and LNP + ON = 44. These detailed rows overlap hung parliament.')
        histogram = pd.DataFrame({party:result['draws'][party].value_counts().reindex(range(89),fill_value=0)
                                  /settings['SIMULATIONS'] for party in PARTIES})
        histogram.index.name = 'Seats'
        st.bar_chart(histogram,x_label='Seat count',y_label='Fraction of simulations',stack=False)
    with seats:
        st.subheader('Five demonstration seats')
        st.dataframe(result['seats'][result['seats'].Seat.isin(
            ['Pakenham','Morwell','Pascoe Vale','Ashwood','Yan Yean'])],hide_index=True,width='stretch')
        st.subheader('All 88 seats')
        st.dataframe(result['seats'],hide_index=True,width='stretch')
        seat = st.selectbox('Inspect a seat',sorted(result['seats'].Seat),key='forecast_seat')
        row = result['seats'].set_index('Seat').loc[seat]
        st.dataframe(pd.DataFrame({'Party':PARTIES,'Win probability (%)':[row[p+' win (%)'] for p in PARTIES]}),hide_index=True)
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
        st.dataframe(pd.DataFrame({'Party':PARTIES,'Central (%)':centre,
            'Draw mean (%)':primary.mean().reindex(PARTIES).to_numpy(),
            '5th percentile (%)':primary.quantile(.05).reindex(PARTIES).to_numpy(),
            '95th percentile (%)':primary.quantile(.95).reindex(PARTIES).to_numpy()}),hide_index=True)
        st.caption('Projection and clipping can shift average draws near boundaries; shown explicitly above.')
        manifest = {k:stored[k] for k in ('signature','created_utc','trial','sync_message')}
        manifest.update(settings=settings,central_targets=targets,engine='forecast-v1',
                        engine_source_hash=engine_source_hash(),
                        calibration='provisional; not calibrated to high-ON Victorian results')
        st.download_button('Download reproducibility record',json.dumps(manifest,indent=2),
                           'lower_forecast_run.json','application/json')
        st.download_button('Download all seat-count draws',result['draws'].to_csv(index=False),
                           'lower_forecast_draws.csv','text/csv')
        st.download_button('Download statewide primary draws',primary.to_csv(index=False),
                           'lower_forecast_primary_draws.csv','text/csv')
