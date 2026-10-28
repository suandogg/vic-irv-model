import unittest
import numpy as np
from tools.fit_historical_lean_budget import components,choose_shrinkage,shrink_correlation


class HistoricalLeanBudgetTests(unittest.TestCase):
    def test_balanced_random_intercept_moments(self):
        # Three groups, two observations: within variance 2, between MS 8.
        x=np.array([[-1.],[1.],[1.],[3.],[3.],[5.]])
        groups=np.array(['A','A','B','B','C','C'])
        result=components(x,groups)
        self.assertAlmostEqual(result['within'][0,0],2)
        self.assertAlmostEqual(result['region_variance'][0],3)
        self.assertAlmostEqual(result['effective_n'],2)
        for group in set(groups):
            self.assertAlmostEqual(result['residual'][groups==group].mean(),0)

    def test_group_variance_never_negative(self):
        result=components(np.array([[-1.],[1.],[-1.],[1.],[-1.],[1.]]),['A','A','B','B','C','C'])
        np.testing.assert_array_equal(result['region_variance'],[0])
        with self.assertRaises(ValueError):
            components(np.ones((3,2)),['A','B','C'])

    def test_covariance_regularisation_and_held_out_scoring(self):
        rng=np.random.default_rng(7)
        x=rng.normal(size=(32,3))
        x[:,1]=-.5*x[:,0]+x[:,1]
        groups=np.repeat(['A','B','C','D'],8)
        result=components(x,groups)
        weight,scores=choose_shrinkage(x,groups)
        self.assertTrue(0<=weight<=1)
        self.assertEqual(len(scores),101)
        self.assertTrue(np.isfinite(scores.Mean_conditional_Gaussian_score).all())
        corr=shrink_correlation(result['within'],weight)
        np.testing.assert_allclose(np.diag(corr),1)
        self.assertGreater(np.linalg.eigvalsh(corr).min(),0)
        # Relabelling group names must not change the fit.
        renamed=np.array(['G'+g for g in groups])
        other,table=choose_shrinkage(x,renamed)
        self.assertEqual(weight,other)
        np.testing.assert_allclose(table.Mean_conditional_Gaussian_score,scores.Mean_conditional_Gaussian_score)


if __name__=='__main__':
    unittest.main()
