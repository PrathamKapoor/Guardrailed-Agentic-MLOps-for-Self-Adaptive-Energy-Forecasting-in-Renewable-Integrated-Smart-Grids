# -*- coding: utf-8 -*-
"""Shared logging setup for phase/research scripts.

Scripts must keep their stdout contract (tests assert on printed output), so
this logger writes to stdout. Level is controlled by SMARTGRID_MLOPS_LOG_LEVEL
(default INFO).
"""
from __future__ import annotations

import logging
import os
import sys


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(f"smartgrid_mlops.scripts.{name}")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(os.environ.get("SMARTGRID_MLOPS_LOG_LEVEL", "INFO").upper())
        logger.propagate = False
    return logger
