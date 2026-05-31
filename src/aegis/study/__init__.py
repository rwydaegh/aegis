"""Headless population-exposure study.

Walks a synchronized pedestrian crowd through a real city core under a sectored
mmWave deployment, computes each person's coherent absorbed-power exposure, and
writes population exposure CDFs. Deterministic ray-traced arm (Plan 1).
"""

from aegis.study.config import StudyConfig

__all__ = ["StudyConfig"]
