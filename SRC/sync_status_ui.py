"""Credential-safe per-tab sync visibility; no change to input selection."""
import streamlit as st


def render_sync_diagnostics(status):
    rows=status.get('diagnostics',[])
    failures=[row for row in rows if row['status']=='error']
    if status.get('errors'):
        names=', '.join(row['tab'] for row in failures)
        st.warning('Google Sheet sync failed for: '+names+'.' if names else
                   'Google Sheet sync had an error. Refresh inputs to obtain per-tab details.')
    if not rows:
        return
    with st.expander('Google Sheet sync details',expanded=bool(failures)):
        for row in rows:
            if row['status']=='synced':
                continue
            st.markdown('**'+row['tab']+'** — '+row['status'])
            st.text(row['reason'])
            available=row.get('saved_csv_available')
            if available is True:
                st.caption('Retaining saved input: '+row['file']+
                    '. File exists; its contents were not validated by sync diagnostics. '
                    'It may be a previous sync or a bundled snapshot.')
                st.caption('Saved file modified (UTC): '+str(row.get('saved_csv_modified_utc')))
            elif available is False:
                st.error('No nonempty saved CSV is available for this tab; its loader may fail if the model requests it.')
            else:
                st.caption('Saved-input availability could not be verified for this entry.')
        st.caption('Successfully synced tabs: '+str(status.get('synced',0))+'. '
                   'The details above do not change the model or its input fallback rules.')
