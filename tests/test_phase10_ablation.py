from smartgrid_mlops.ablation.common_samples import common_timestamp_intersection
from smartgrid_mlops.ablation.selection import relative_mae_change, select_feature_set

def test_common_samples_require_identical_pairs():
    rows={"A":[{"forecast_origin":1,"target_timestamp":2},{"forecast_origin":2,"target_timestamp":3}],"B":[{"forecast_origin":2,"target_timestamp":3}]}
    assert common_timestamp_intersection(rows)=={(2,3)}

def test_selection_uses_simplicity_for_practical_tie():
    assert select_feature_set({"full":100.0,"small":100.4},{"full":12,"small":6},0.5)=="small"
    assert select_feature_set({"full":100.0,"small":100.6},{"full":12,"small":6},0.5)=="full"

def test_relative_mae_change_sign():
    assert relative_mae_change(100,90)==10
    assert relative_mae_change(100,110)==-10
