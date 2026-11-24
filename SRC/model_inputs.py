"""Native v6 lower-house run defaults, shared by non-UI engine callers."""
def default_experiment(primary_inputs):
    from SRC.nowcast_loader import load_nowcast_inputs
    from SRC.forecast_subregions import load_subregions
    from SRC.candidate_field import load_field_config
    from SRC.low_base_taper import load_taper_config
    from SRC.oth_scaling import load_oth_scaling_config
    from SRC.htv_deal import load_htv_deal_config
    from SRC.htv_review import load_htv_review_config
    budget,_=load_nowcast_inputs(list(primary_inputs.district))
    mapping,_=load_subregions(list(primary_inputs.district))
    return dict(structured_nowcast=budget,concentration_log_sd=.30,
                concentration_form='positive_bounded',subregion_fraction=.5,
                candidate_field=load_field_config(),low_base_taper=load_taper_config(),
                oth_scaling=load_oth_scaling_config(),htv_deal=load_htv_deal_config(),
                htv_review=load_htv_review_config()),dict(zip(mapping.district,mapping.subregion))
