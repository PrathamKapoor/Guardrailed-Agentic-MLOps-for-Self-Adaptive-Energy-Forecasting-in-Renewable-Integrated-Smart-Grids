"""Incremental monitoring — per-target state registry.

`State` is a thin dict-like container keyed on `(target, model)`. It
guarantees that:

  * Observations for one target never enter the window of another.
  * Each target gets its own reference and current windows.
  * Chronology is enforced per (target, model) by the `last_source_timestamp`
    field of the underlying `TargetState`.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Iterator, Tuple

from .windows import EVENT_SOURCE, TargetKey, TargetState


@dataclass
class State:
    """All per-(target, model) state. Created once at processor
    construction; mutable only through `register_observation`."""
    reference_size: int = 168
    current_size: int = 168
    _by_key: Dict[TargetKey, TargetState] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.reference_size <= 0 or self.current_size <= 0:
            raise ValueError("reference_size and current_size must be positive.")

    def keys(self) -> Iterator[TargetKey]:
        return iter(self._by_key)

    def get(self, key: TargetKey) -> TargetState:
        if key not in self._by_key:
            self._by_key[key] = TargetState(target=key[0], model=key[1],
                                            reference=self._new_window(self.reference_size),
                                            current=self._new_window(self.current_size))
        return self._by_key[key]

    def _new_window(self, capacity: int):
        # Local import to avoid a circular dependency in some test
        # discovery paths.
        from .windows import _RingWindow
        w = _RingWindow()
        w.capacity = capacity
        return w

    def all_keys(self) -> list[TargetKey]:
        return list(self._by_key.keys())

    def __len__(self) -> int:
        return len(self._by_key)
