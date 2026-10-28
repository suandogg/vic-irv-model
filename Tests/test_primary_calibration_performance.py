"""Numerical regression against the pre-optimisation implementation."""
import ast
import subprocess
import unittest

import numpy as np
import pandas as pd
import SRC.legacy_primary_model as primary
from Tests.test_forecast_engine import calculator_fixture
from SRC.constants import PARTIES


class CalibrationRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = subprocess.check_output([
            'git','show','25587bd:SRC/legacy_primary_model.py'],text=True)
        names = {'build_corrected_primary_table','_calibrate_primary_components'}
        nodes = [n for n in ast.parse(source).body
                 if isinstance(n,ast.FunctionDef) and n.name in names]
        cls.reference = dict(vars(primary))
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'reference','exec'),cls.reference)
        _,cls.inputs,*_ = calculator_fixture()

    def test_primary_calibration_matches_reference(self):
        for on in (0,19,22,25,50):
            targets = dict(ALP=24.6,LNP=29.1,GRN=13.3,ON=on,IND=5.5,OTH=5.5)
            for alpha in (.2,.6,1.2):
                kwargs = dict(on_alpha=alpha,pvi_strengths={'GRN':.75})
                old = self.reference['build_corrected_primary_table'](self.inputs,targets,**kwargs)
                new = primary.build_corrected_primary_table(self.inputs,targets,**kwargs)
                pd.testing.assert_frame_equal(old,new,check_exact=True)

    def test_component_calibration_matches_reference(self):
        rng = np.random.default_rng(19)
        frame = pd.DataFrame(rng.uniform(size=(88,6)),columns=PARTIES)
        frame.iloc[0,0] = 0
        for on in (22,50):
            targets = dict(ALP=24.6,LNP=29.1,GRN=13.3,ON=on,IND=5.5,OTH=5.5)
            old = self.reference['_calibrate_primary_components'](frame,targets)
            new = primary._calibrate_primary_components(frame,targets)
            pd.testing.assert_frame_equal(old,new,check_exact=True)
        # Preserve the existing component helper's zero-target failure too;
        # changing this behaviour would be a separate correctness change.
        zero_targets = dict(targets,ON=0)
        for function in (primary._calibrate_primary_components,
                         self.reference['_calibrate_primary_components']):
            with self.assertRaises(ZeroDivisionError):
                function(frame,zero_targets)
        for function in (primary._calibrate_primary_components,
                         self.reference['_calibrate_primary_components']):
            with self.assertRaises(ValueError):
                function(frame,targets,iterations=0)

    def test_compiled_precollapse_matches_ordinary(self):
        from SRC.lnp_precollapse_loader import (
            load_lnp_precollapse_inputs,compile_lnp_precollapse,apply_lnp_precollapse)
        inputs = load_lnp_precollapse_inputs()
        targets = dict(ALP=24.6,LNP=29.1,GRN=13.3,ON=22,IND=5.5,OTH=5.5)
        frame = primary.build_corrected_primary_table(self.inputs,targets)
        for rules in (inputs,inputs.iloc[:0]):
            plan = compile_lnp_precollapse(frame.district,rules)
            old = apply_lnp_precollapse(frame,rules)
            new = apply_lnp_precollapse(frame,plan)
            pd.testing.assert_frame_equal(old,new,check_exact=True)
            with self.assertRaises(ValueError):
                apply_lnp_precollapse(frame.iloc[::-1],plan)
        bad = inputs.copy()
        active = bad.index[bad.Enabled]
        bad.loc[active,'ManualOverrideShare'] = 0.0
        with self.assertRaises(ValueError):
            compile_lnp_precollapse(frame.district,bad)
