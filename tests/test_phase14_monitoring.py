import numpy as np
import pytest
from smartgrid_mlops.monitoring.feature_drift import psi,normalized_wasserstein
from smartgrid_mlops.monitoring.windows import make_windows,validate_development_role
from smartgrid_mlops.monitoring.performance_drift import rolling_mae
from smartgrid_mlops.monitoring.severity import classify_severity
from smartgrid_mlops.monitoring.validation import assert_no_final_test_access
from smartgrid_mlops.monitoring.data_quality import check_quality

def test_window_policy():
    w=make_windows(336); assert w[0].end-w[0].start==168 and w[1].start-w[0].start==24
    assert validate_development_role('F01')=='CALIBRATION'; assert validate_development_role('F04')=='CONTROL'; assert validate_development_role('F06')=='NATURAL_MONITORING'
    with pytest.raises(ValueError): validate_development_role('FINAL_TEST')
def test_distribution_statistics():
    a=np.arange(100.); assert psi(a,a)<1e-8; assert normalized_wasserstein(a,a)<1e-8; assert normalized_wasserstein(a,a+10)>0.1
def test_performance_and_quality():
    y=np.ones(168); assert rolling_mae(y,y)==0; assert rolling_mae(y,y+2)==2
    q=check_quality(np.array([[1.,np.nan],[2.,np.inf]])); assert q['critical'] and q['nan_count']==1 and q['inf_count']==1
def test_severity():
    assert classify_severity([])=='NONE'; assert classify_severity(['FEATURE'])=='WATCH'; assert classify_severity(['A','B'])=='WARNING'; assert classify_severity([],quality_critical=True)=='CRITICAL'
def test_final_test_guard():
    with pytest.raises(ValueError): assert_no_final_test_access('data/final_test/metrics.csv')
