MASTER_SEEDS = (42, 123, 2020, 2025, 31415)

def seeds_for(stochastic: bool) -> tuple[int | None, ...]:
    return MASTER_SEEDS if stochastic else (None,)
