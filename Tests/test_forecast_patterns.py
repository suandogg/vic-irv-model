import unittest
import numpy as np
from SRC.forecast_patterns import (balance_primary_pattern,strength_contrast,
    centre_region_contrasts,tilt_preference_pattern)


class PatternTests(unittest.TestCase):
    def setUp(self):
        self.base = np.array([[.7,.3,0],[.4,.4,.2],[.2,.5,.3]])

    def test_zero_identity_and_immutable_inputs(self):
        original = self.base.copy()
        x = balance_primary_pattern(self.base,np.zeros_like(self.base))
        np.testing.assert_array_equal(x,self.base)
        x[0,0]=0
        np.testing.assert_array_equal(self.base,original)

    def test_combined_strength_and_regional_conservation(self):
        tilt = strength_contrast(self.base)*np.array([.3,-.2,.5])
        tilt += centre_region_contrasts(['A','A','B'],{'A':[.2,-.1,.4],'B':[-.4,.3,.1]})
        x = balance_primary_pattern(self.base,tilt)
        np.testing.assert_allclose(x.sum(axis=0),self.base.sum(axis=0),atol=1e-9)
        np.testing.assert_allclose(x.sum(axis=1),self.base.sum(axis=1),atol=1e-9)
        self.assertEqual(x[0,2],0)
        self.assertFalse(np.allclose(x,self.base))

    def test_region_weighting_is_by_seat(self):
        x = centre_region_contrasts(['A','A','B'],{'A':[1.,0.],'B':[-1.,2.]})
        np.testing.assert_allclose(x.mean(axis=0),0,atol=1e-15)

    def test_preference_rows_immutable_and_zero_preserved(self):
        row = {'ALP':.6,'LNP':.4,'ON':0.}
        changed = tilt_preference_pattern(row,{'ALP':.3,'ON':1.})
        self.assertAlmostEqual(sum(changed.values()),1)
        self.assertEqual(changed['ON'],0)
        self.assertGreater(changed['ALP'],row['ALP'])
        self.assertEqual(row,{'ALP':.6,'LNP':.4,'ON':0.})
        self.assertEqual(tilt_preference_pattern(row,{}),row)

    def test_invalid_inputs_fail(self):
        with self.assertRaises(ValueError):
            balance_primary_pattern(self.base,np.full_like(self.base,np.nan))
        with self.assertRaises(ValueError):
            tilt_preference_pattern({'ALP':1.},{'ON':.3})
        with self.assertRaises(ValueError):
            tilt_preference_pattern({'ALP':0.},{})
