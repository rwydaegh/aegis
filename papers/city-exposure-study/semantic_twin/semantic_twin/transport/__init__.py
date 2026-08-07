"""Transport estimators, their shared tracer, and trace observers."""

from __future__ import annotations

from .escape import EscapeEstimator
from .directional import DirectionalMeasure
from .device_next_event import DeviceNextEventBatch, DeviceNextEventGather
from .model import Estimator, Gather, Surplus, require_credit
from .next_event import MIN_CONNECT_M, NextEventEstimator, NextEventField, NextEventGather
from .observers import TERMINATIONS, BounceEvidenceTally, MultiGather, PathRecord, PathRecorder
from .specular import (
    DEFAULT_SPECULAR_CANDIDATE_BUDGET,
    OneBounceSpecularTransport,
    ReceiverVisibleFaceCandidates,
    SpecularCandidateSet,
    SpecularComplexityError,
    SpecularDiagnostics,
    SpecularPaths,
    SpecularSurfaces,
    SpecularWorkEstimate,
    SourceQuadratureSelection,
    StratifiedSourceQuadrature,
)

# Experimental CPU reference. It is not yet wired into production tracing.
from .specular_sampling import (
    SampledOneBounceSpecularEstimator,
    SampledSpecularDiagnostics,
    SampledSpecularResult,
)
from .tracer import (
    DEFAULT_MAX_BOUNCES,
    PointResult,
    SbrTracer,
    TraceConfig,
    fresnel_power_reflectance,
    specular_share,
    trace_standpoints,
)

__all__ = [
    "DEFAULT_MAX_BOUNCES",
    "DEFAULT_SPECULAR_CANDIDATE_BUDGET",
    "DirectionalMeasure",
    "DeviceNextEventBatch",
    "DeviceNextEventGather",
    "MIN_CONNECT_M",
    "TERMINATIONS",
    "BounceEvidenceTally",
    "EscapeEstimator",
    "Estimator",
    "Gather",
    "MultiGather",
    "NextEventEstimator",
    "NextEventField",
    "NextEventGather",
    "OneBounceSpecularTransport",
    "ReceiverVisibleFaceCandidates",
    "PathRecord",
    "PathRecorder",
    "PointResult",
    "SbrTracer",
    "SampledOneBounceSpecularEstimator",
    "SampledSpecularDiagnostics",
    "SampledSpecularResult",
    "SpecularDiagnostics",
    "SpecularCandidateSet",
    "SpecularComplexityError",
    "SpecularPaths",
    "SpecularSurfaces",
    "SpecularWorkEstimate",
    "SourceQuadratureSelection",
    "StratifiedSourceQuadrature",
    "Surplus",
    "TraceConfig",
    "fresnel_power_reflectance",
    "require_credit",
    "specular_share",
    "trace_standpoints",
]
