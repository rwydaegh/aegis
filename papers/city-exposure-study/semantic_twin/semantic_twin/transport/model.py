"""What an estimator is here, and the one number two of them both produce.

This study has two ways of turning a base station population into an exposure
at a standpoint, and they disagree by three to five times on real cities. That
disagreement is a result. It is only readable as a result if the two are
alternatives you can swap, so this module says what they have in common and
refuses to invent anything they do not.

## What the two genuinely share

Read them rather than their names. Both are handed the same
:class:`~.tracer.SbrTracer`, both are asked about one standpoint, and both come
back with two power-like numbers:

- ``direct``, the part that arrives without touching a surface,
- ``total``, everything including that part.

Their ratio is the multipath surplus, and it is the quantity the study compares
across the two estimators and across eleven squares. That is :class:`Surplus`,
and it is the whole return of :meth:`Estimator.estimate`.

Nothing else survives the comparison, and the ratio is why. ``direct`` and
``total`` carry different constants in the two estimators: escape normalises its
density to one over 4 pi so a free space `chi` is exactly 1, while next event
averages over the site set and leaves the antenna count, the transmit power and
a `4 pi` sitting in front of both terms. Those constants cancel in the ratio and
nowhere else, so ``direct`` and ``total`` are comparable **inside** one estimator
and not between two.

## What is deliberately not on the protocol

The angular power spectrum. The escape estimator reduces to `rho(u)` on a few
hundred cell grid, which is what :class:`semantic_twin.exposure.BodyCoupler`
integrates against a phantom. Next event never forms one: it connects a vertex
to a point and accumulates a scalar, and there is no direction grid anywhere in
it. Putting `rho` on the protocol would make next event return an empty array to
satisfy a type. So the dosimetry arm of this study is escape only, and that is a
fact about the physics rather than a gap in the code.

## Which law can feed which estimator

Already answered on the illumination side.
:func:`semantic_twin.illumination.credited_by` reads the protocols a model
satisfies and names the estimators that can score it. :func:`require_credit`
asks it. Nothing here repeats the reasoning, because two copies of it would drift
the first time a third law arrives.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

import numpy as np

from ..illumination.model import IlluminationModel, credited_by


@dataclass(frozen=True)
class Surplus:
    """One standpoint, one estimator, one law: how much more than line of sight.

    ``direct`` and ``total`` are in whatever units the estimator works in and are
    not comparable across estimators. :attr:`surplus_db` is, and it is what every
    cross estimator table in this study quotes.
    """

    estimator: str
    law: str
    direct: float
    total: float
    #: Whatever the estimator can say about itself that the other one cannot.
    #: Read by a report, never by the comparison.
    detail: dict[str, Any] = field(default_factory=dict)

    @property
    def bounced(self) -> float:
        """The part that touched at least one surface."""
        return self.total - self.direct

    @property
    def surplus(self) -> float:
        """``total / direct``, NaN where nothing arrives line of sight."""
        return self.total / self.direct if self.direct > 0.0 else math.nan

    @property
    def surplus_db(self) -> float:
        ratio = self.surplus
        return 10.0 * math.log10(ratio) if ratio > 0.0 else math.nan

    def as_dict(self) -> dict[str, Any]:
        return {
            "estimator": self.estimator,
            "law": self.law,
            "direct": self.direct,
            "total": self.total,
            "bounced": self.bounced,
            "surplus": self.surplus,
            "surplus_db": self.surplus_db,
            **self.detail,
        }


@runtime_checkable
class Estimator(Protocol):
    """Something that scores one standpoint against one illumination model.

    ``name`` is one of :data:`semantic_twin.runconfig.ESTIMATORS` and is what a
    manifest carries, so a result on disk can say which of the two wrote it.
    """

    name: str

    def illumination(self) -> IlluminationModel:
        """The base station population this estimator is scoring."""

    def estimate(self, origin: np.ndarray, *, ground_z_m: float = 0.0, seed: int | None = None) -> Surplus:
        """Score one standpoint. ``seed`` fixes every random draw made there."""


@runtime_checkable
class Gather(Protocol):
    """An observer the tracer calls at every surface interaction.

    The tracer takes one of these as its ``gather``. It is how an estimator that
    deposits at a vertex rather than at an escape gets its hands on the path, and
    it is the hook next event and the monostatic diagnostic both ride.

    The contract is that a gather draws from its own generator and touches none
    of the tracer's accumulators, so attaching one leaves the traced result bit
    identical. :class:`~.observers.MultiGather` runs several at once on the same
    argument, which is only sound because of that.
    """

    def begin(self, origin: np.ndarray, count: int) -> None:
        """A batch of ``count`` rays is about to leave ``origin``."""

    def vertex(
        self,
        index: np.ndarray,
        position: np.ndarray,
        incoming: np.ndarray,
        normal: np.ndarray,
        throughput: np.ndarray,
        share: np.ndarray,
        order: np.ndarray,
        path_length: np.ndarray,
        face: np.ndarray | None = None,
    ) -> None:
        """One surface interaction per live ray.

        ``normal`` is already turned to face ``incoming``, ``throughput`` is
        already multiplied by this interaction's reflectance, and ``share`` is
        the Rayleigh coherent fraction whose complement is the diffuse lobe.
        """


def require_credit(estimator: str, model: IlluminationModel) -> None:
    """Raise unless this law can feed this estimator.

    The band law marginalises its sources into a direction density and has no
    positions to connect to. The facade tip law is a set of positions and has no
    density to read. Handing either to the wrong estimator is a modelling error
    that would otherwise surface as an ``AttributeError`` several hundred
    thousand rays later.
    """
    allowed = credited_by(model)
    if estimator not in allowed:
        raise TypeError(
            f"illumination model {getattr(model, 'name', model)!r} (law {getattr(model, 'law', '?')!r}) "
            f"can be credited by {allowed or 'no estimator'}, not by {estimator!r}"
        )
