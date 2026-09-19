from .feature_drift import normalized_wasserstein
def prediction_signal(reference,current):
    return normalized_wasserstein(reference,current)
