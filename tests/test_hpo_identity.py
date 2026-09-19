from smartgrid_mlops.models.neural.base import MLP
def test_phase9_neural_identity_is_phase8_pytorch_mlp():
    assert MLP.framework == 'pytorch' and MLP.implementation_id == 'PYTORCH_MLP_V1'
