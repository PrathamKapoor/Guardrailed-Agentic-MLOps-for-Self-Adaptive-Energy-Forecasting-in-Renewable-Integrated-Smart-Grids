def validate_temporal_order(train: list[dict], validation: list[dict]) -> None:
    if train and validation and max(r["target_timestamp"] for r in train) >= min(r["target_timestamp"] for r in validation):
        raise ValueError("training and validation target timestamps overlap or are unordered")

def validate_historical_context(source_timestamp, forecast_origin) -> None:
    if source_timestamp > forecast_origin: raise ValueError("feature source occurs after forecast origin")
