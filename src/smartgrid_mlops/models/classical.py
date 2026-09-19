from __future__ import annotations

from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def linear_regression(parameters: dict, seed: int | None): return LinearRegression(**parameters)
def ridge(parameters: dict, seed: int | None): return Pipeline([("scaler", StandardScaler()), ("ridge", Ridge(**{k:v for k,v in parameters.items() if k != "scaling"}))])
def random_forest(parameters: dict, seed: int | None): return RandomForestRegressor(**parameters, random_state=seed)
def extra_trees(parameters: dict, seed: int | None): return ExtraTreesRegressor(**parameters, random_state=seed)
def hist_gradient_boosting(parameters: dict, seed: int | None): return HistGradientBoostingRegressor(**parameters, random_state=42)
