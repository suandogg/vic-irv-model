"""Explicit historical October loader; no Streamlit UI execution or live Sheet sync."""
import ast
from pathlib import Path

def load_trial(historical_calculator_source):
 tree=ast.parse(historical_calculator_source)
 selected=[node for node in tree.body if isinstance(node,(ast.Import,ast.ImportFrom)) or isinstance(node,ast.FunctionDef) and node.name in ('run_model','params_for_scenario')]
 n={'__file__':'app.py','log_checkpoint':lambda *args:None}
 exec(compile(ast.Module(body=selected,type_ignores=[]),'historical-calculator','exec'),n)
 from tools.preference_review_trials import variant
 from tools.trial_vec_field_evidence import attach_vec_fields
 from SRC.oth_matrix_builder import rebuild_oth_matrices
 params=variant(n['load_params'](),'vec_field_coverage')
 primary=n['apply_seat_held_metadata'](n['load_legacy_primary_inputs'](),n['load_seat_held_metadata']())
 matrices=rebuild_oth_matrices(attach_vec_fields(n['load_synth_pref_matrices']()),params)
 posterior=n['apply_production_federal_on_evidence'](n['load_posterior_scenarios']())
 return n,primary,matrices,params,posterior,n['load_ideology_prior'](),n['load_lower_seat_adjustments']()
