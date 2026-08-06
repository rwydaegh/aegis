"""The tile texture as a material channel, and what it is honestly worth.

The panorama semantic layer only reaches surfaces a street level capture sees.
Measured at Korenmarkt that is 3.7 percent of the support mesh from one capture
position, and in the adjoint frame with four bounces every interaction after the
first can land outside it. This is the fallback for the rest.

The channel is deliberately built to lose. The panorama resolves 7.7 mm at 20 m
against the texture's 19.5 cm, and the crossover where the texture would win is
near 510 m, outside every crop this study uses. That ordering is encoded in the
``resolution`` term of the emitted
:class:`~semantic_twin.vision.evidence.ObservationQuality` and, where a panorama
has already spoken, in a hard cap that makes it arithmetically impossible for
the texture to move the panorama's winning class. Neither is a downstream
special case.

What the measurement actually found, on 3,204 faces the panorama does label, is
that the ordering above is not what limits this channel. The same descriptor and
the same spatially blocked protocol read off the panorama and then deliberately
box-downsampled to 41 cm, coarser than the texture, still scores 0.473 against
the texture's 0.382. The gap is viewpoint and illumination, not sampling: the
tile texture sees a facade obliquely from above and mostly in shadow. Every
opaque class collapses into one, and only vegetation separates cleanly.

This channel claims material identity only. Roughness stays with the prior, and
:func:`collapsing_pairs` reports the class pairs it cannot separate rather than
letting the exporter bind two permittivities to a decision the imagery never
made.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field

import numpy as np
from scipy import optimize

from .appearance import TextureFeatures
from .evidence import (
    EvidenceAccumulator,
    ObservationQuality,
    SoftAssociation,
    categorical_information,
)
from .tiles import TileMatch

# Street View at zoom 5 is 16384 pixels around, so one panorama pixel subtends
# 2 pi / 16384 radians.  This is the number the resolution term compares the
# texture against, and it is the whole reason the texture is the weaker source.
PANORAMA_WIDTH_PX = 16384


def blocked_folds(
    centroids: np.ndarray,
    *,
    block_m: float = 12.0,
    folds: int = 5,
    seed: int = 7,
) -> np.ndarray:
    """Assign spatial blocks, not individual faces, to cross-validation folds.

    Material is correlated along a building, so a face-wise split lets a model
    memorise the wall it is about to be tested on. Blocking on a horizontal grid
    forces every held-out prediction to be a transfer to a wall the model has
    not seen, which is the only protocol whose number means anything for the
    out-of-view surfaces this channel exists to serve.
    """
    centroids = np.asarray(centroids, dtype=np.float64)
    if centroids.ndim != 2 or centroids.shape[1] < 2:
        raise ValueError("centroids must be [n, >=2]")
    if folds < 2:
        raise ValueError("folds must be at least 2")
    block = np.floor(centroids[:, :2] / float(block_m)).astype(np.int64)
    _, identifier = np.unique(block, axis=0, return_inverse=True)
    order = np.random.default_rng(seed).permutation(int(identifier.max()) + 1)
    return order[identifier] % folds


def fit_softmax(
    features: np.ndarray,
    labels: np.ndarray,
    class_count: int,
    *,
    l2: float = 3.0,
    max_iterations: int = 400,
) -> np.ndarray:
    """Fit a multinomial logistic regression, returning ``[features + 1, classes]``.

    The objective is convex and is minimised with L-BFGS from a zero start, so
    the fit is the global optimum and is reproducible without a seed. The choice
    of a linear model is a statement about the data rather than about
    convenience: with a median of 14 texels per triangle and a few thousand
    labelled faces, the separations that actually survive at 19.6 cm are
    lightness and hue offsets, and a higher-capacity model has nothing left to
    learn from a patch that small.
    """
    features = np.asarray(features, dtype=np.float64)
    labels = np.asarray(labels, dtype=np.int64)
    if features.ndim != 2 or labels.shape != (len(features),):
        raise ValueError("features must be [n, f] and labels [n]")
    if class_count < 2:
        raise ValueError("class_count must be at least 2")
    if labels.size and (labels.min() < 0 or labels.max() >= class_count):
        raise ValueError("labels must index the class list")
    rows, columns = features.shape
    design = np.hstack([features, np.ones((rows, 1))])
    target = np.zeros((rows, class_count))
    target[np.arange(rows), labels] = 1.0

    def objective(flat: np.ndarray) -> tuple[float, np.ndarray]:
        weights = flat.reshape(columns + 1, class_count)
        scores = design @ weights
        scores -= scores.max(axis=1, keepdims=True)
        normaliser = np.log(np.exp(scores).sum(axis=1))
        loss = float((normaliser - (scores * target).sum(axis=1)).mean())
        loss += 0.5 * l2 * float((weights[:-1] ** 2).sum()) / rows
        probability = np.exp(scores - normaliser[:, None])
        gradient = design.T @ (probability - target) / rows
        gradient[:-1] += l2 * weights[:-1] / rows
        return loss, gradient.ravel()

    result = optimize.minimize(
        objective,
        np.zeros((columns + 1) * class_count),
        jac=True,
        method="L-BFGS-B",
        options={"maxiter": max_iterations},
    )
    return result.x.reshape(columns + 1, class_count)


def softmax_probability(
    weights: np.ndarray, features: np.ndarray, *, temperature: np.ndarray | float = 1.0
) -> np.ndarray:
    """Class probabilities of a fitted softmax, optionally temperature-scaled."""
    features = np.asarray(features, dtype=np.float64)
    scores = np.hstack([features, np.ones((len(features), 1))]) @ weights
    scale = np.asarray(temperature, dtype=np.float64)
    if scale.ndim == 1:
        scale = scale[:, None]
    scores = scores / np.maximum(scale, 1e-6)
    scores -= scores.max(axis=1, keepdims=True)
    exponent = np.exp(scores)
    return exponent / exponent.sum(axis=1, keepdims=True)


def fit_temperature(
    scores_probability: np.ndarray, labels: np.ndarray, *, bounds: tuple[float, float] = (0.2, 20.0)
) -> float:
    """Scalar temperature minimising held-out negative log-likelihood.

    Applied to the log of an already normalised probability block, which is the
    same family as scaling the linear scores and avoids having to carry the
    scores around. A temperature above one flattens the prediction, and the
    channel needs that: a face with eight texels must not be allowed to speak
    with the confidence of a face with four hundred.
    """
    probability = np.clip(np.asarray(scores_probability, dtype=np.float64), 1e-12, 1.0)
    labels = np.asarray(labels, dtype=np.int64)
    if not len(labels):
        return 1.0
    scores = np.log(probability)

    def cost(temperature: float) -> float:
        scaled = scores / max(float(temperature), 1e-6)
        scaled -= scaled.max(axis=1, keepdims=True)
        normaliser = np.log(np.exp(scaled).sum(axis=1))
        return float((normaliser - scaled[np.arange(len(labels)), labels]).mean())

    result = optimize.minimize_scalar(cost, bounds=bounds, method="bounded")
    return float(result.x)


@dataclass(frozen=True)
class MaterialClassifier:
    """Texture appearance to material class, with a support-dependent temperature.

    ``support_edges`` are texel-count bin edges and ``support_temperature`` the
    calibration fitted inside each bin on held-out predictions, so the sharpness
    of the prediction is measured against texel support rather than asserted.

    At Korenmarkt it came back flat. Held-out accuracy is 0.856, 0.868, 0.841,
    0.877 and 0.865 across the five bins from 8 texels upward, and the fitted
    temperatures sit between 0.94 and 1.22 with no trend. Texel count is
    confounded with triangle size, and a large triangle is a road or a roof
    rather than a better-observed wall, so the two effects cancel. The
    degradation with support that the emitted evidence does carry therefore
    comes from :func:`support_rows`, which is structural, and not from here.
    Reporting a flat calibration is the point of measuring it.
    """

    weights: np.ndarray
    mean: np.ndarray
    scale: np.ndarray
    class_labels: tuple[str, ...]
    feature_names: tuple[str, ...]
    support_edges: np.ndarray
    support_temperature: np.ndarray
    material_labels: tuple[str, ...] = ()
    material_matrix: np.ndarray | None = None

    def __post_init__(self) -> None:
        if self.weights.shape != (len(self.feature_names) + 1, len(self.class_labels)):
            raise ValueError("weights must be [features + 1, classes]")
        if len(self.support_temperature) != len(self.support_edges) + 1:
            raise ValueError("one temperature per support bin, including both open ends")
        if self.material_matrix is not None and self.material_matrix.shape != (
            len(self.class_labels),
            len(self.material_labels),
        ):
            raise ValueError("material matrix must be [classes, materials]")

    def temperature_for(self, texel_count: np.ndarray) -> np.ndarray:
        index = np.searchsorted(self.support_edges, np.asarray(texel_count, dtype=np.float64), side="right")
        return self.support_temperature[index]

    def predict(self, features: np.ndarray, texel_count: np.ndarray) -> np.ndarray:
        standard = (np.asarray(features, dtype=np.float64) - self.mean) / self.scale
        return softmax_probability(self.weights, standard, temperature=self.temperature_for(texel_count))

    def predict_material(self, features: np.ndarray, texel_count: np.ndarray) -> np.ndarray:
        """Posterior over the RF material taxonomy rather than over visual class."""
        if self.material_matrix is None:
            raise ValueError("this classifier carries no class to material mapping")
        return self.predict(features, texel_count) @ self.material_matrix

    def save(self, path: str | pathlib.Path) -> None:
        payload = {
            "class_labels": list(self.class_labels),
            "feature_names": list(self.feature_names),
            "material_labels": list(self.material_labels),
        }
        arrays = {
            "metadata": np.asarray(json.dumps(payload)),
            "weights": self.weights,
            "mean": self.mean,
            "scale": self.scale,
            "support_edges": self.support_edges,
            "support_temperature": self.support_temperature,
        }
        if self.material_matrix is not None:
            arrays["material_matrix"] = self.material_matrix
        np.savez_compressed(path, **arrays)

    @classmethod
    def load(cls, path: str | pathlib.Path) -> MaterialClassifier:
        with np.load(path, allow_pickle=False) as document:
            metadata = json.loads(str(document["metadata"]))
            matrix = np.asarray(document["material_matrix"]) if "material_matrix" in document.files else None
            return cls(
                weights=np.asarray(document["weights"]),
                mean=np.asarray(document["mean"]),
                scale=np.asarray(document["scale"]),
                class_labels=tuple(metadata["class_labels"]),
                feature_names=tuple(metadata["feature_names"]),
                support_edges=np.asarray(document["support_edges"]),
                support_temperature=np.asarray(document["support_temperature"]),
                material_labels=tuple(metadata["material_labels"]),
                material_matrix=matrix,
            )


def confusion_matrix(truth: np.ndarray, prediction: np.ndarray, class_count: int) -> np.ndarray:
    """Counts of predicted class against true class."""
    matrix = np.zeros((class_count, class_count), dtype=np.float64)
    np.add.at(matrix, (np.asarray(truth, dtype=np.int64), np.asarray(prediction, dtype=np.int64)), 1.0)
    return matrix


def pairwise_separability(matrix: np.ndarray) -> np.ndarray:
    """Class-balanced two-class accuracy for every pair, ignoring the other classes.

    Restricting the confusion matrix to two rows and two columns and averaging
    the two recalls gives a number that is 0.5 for a coin and 1 for a perfect
    split, and unlike a raw pair accuracy it is not carried by whichever of the
    two classes happens to be more common. That matters here because the
    Korenmarkt facade classes differ in frequency by an order of magnitude.
    """
    matrix = np.asarray(matrix, dtype=np.float64)
    count = len(matrix)
    result = np.full((count, count), np.nan)
    for i in range(count):
        for j in range(count):
            if i == j:
                continue
            first = matrix[i, i] + matrix[i, j]
            second = matrix[j, j] + matrix[j, i]
            if first <= 0.0 or second <= 0.0:
                continue
            result[i, j] = 0.5 * (matrix[i, i] / first + matrix[j, j] / second)
    return result


def collapsing_pairs(matrix: np.ndarray, *, threshold: float = 0.55) -> list[tuple[int, int]]:
    """Class pairs the classifier separates no better than a coin.

    Reporting the pair and merging it is honest. Keeping the distinction, and
    letting the exporter bind two different permittivities to a decision the
    imagery never made, is not.
    """
    separability = pairwise_separability(matrix)
    pairs: list[tuple[int, int]] = []
    for i in range(len(matrix)):
        for j in range(i + 1, len(matrix)):
            if np.isfinite(separability[i, j]) and separability[i, j] <= threshold:
                pairs.append((i, j))
    return pairs


def panorama_resolution_ratio(
    range_m: np.ndarray,
    gsd_m: np.ndarray,
    *,
    panorama_width_px: int = PANORAMA_WIDTH_PX,
) -> np.ndarray:
    """Linear resolution of the texture relative to a panorama at the same range.

    A Street View panorama subtends ``2 pi / width`` per pixel, so its ground
    sample distance grows with range while the tile texture's does not. The ratio
    is therefore 1/26 at 20 m at Korenmarkt and reaches one only near 520 m,
    beyond any crop this study uses. Emitting it as the ``resolution`` quality
    term is what makes the texture the weaker source everywhere it matters
    without any downstream branch on which channel is speaking.
    """
    range_m = np.asarray(range_m, dtype=np.float64)
    gsd_m = np.asarray(gsd_m, dtype=np.float64)
    panorama_gsd = range_m * (2.0 * np.pi / float(panorama_width_px))
    ratio = np.divide(panorama_gsd, gsd_m, out=np.zeros_like(gsd_m), where=np.isfinite(gsd_m) & (gsd_m > 0.0))
    return np.clip(np.nan_to_num(ratio, nan=0.0, posinf=0.0), 0.0, 1.0)


def support_rows(texel_count: np.ndarray, *, maximum_rows: int = 32) -> np.ndarray:
    """Effective independent observation count implied by a triangle's texels.

    Texels on one wall are strongly correlated, so the count of independent
    samples grows like the linear extent of the patch rather than like its area.
    The square root is that statement, and the cap keeps a road triangle with
    tens of thousands of texels from outweighing everything else in the scene on
    the strength of one aerial photograph.
    """
    count = np.asarray(texel_count, dtype=np.float64)
    return np.clip(np.rint(np.sqrt(np.maximum(count, 0.0))), 0.0, float(maximum_rows)).astype(np.int64)


def posterior_top_mass(
    concentration: np.ndarray,
    probability: np.ndarray,
    *,
    prior: float = 0.25,
) -> np.ndarray:
    """Winning material's posterior mass if this were a face's only evidence.

    The absolute number of Dirichlet counts a texture observation is worth is
    the one quantity this module cannot derive from its own measurements, and no
    other channel writes into the same accumulator yet to calibrate it against.
    Rather than pick a scale and call it physics, the emitted mass is left as the
    product of terms that each mean something, and this reports what it does to a
    posterior so the weakness is a published number rather than a hidden one. A
    caller who wants the texture to lead on out-of-view faces lowers the
    accumulator's own material prior, which is its decision to make and not this
    channel's.
    """
    concentration = np.asarray(concentration, dtype=np.float64)
    probability = np.asarray(probability, dtype=np.float64)
    if probability.ndim != 2:
        raise ValueError("probability must be [faces, materials]")
    total = prior * probability.shape[1]
    return (prior + concentration * probability.max(axis=1)) / (total + concentration)


def dominance_factor(panorama_alpha: np.ndarray, requested: np.ndarray, *, headroom: float = 0.5) -> np.ndarray:
    """Discount that stops the texture overturning a panorama observation.

    Where the panorama has seen a face, its Dirichlet increment has a margin
    between the best and second-best class. Capping the texture's total emitted
    mass at ``headroom`` times that margin makes it arithmetically impossible for
    the texture to change which class wins, whatever it predicts, because even
    all of its mass landing on the runner-up leaves the margin positive. Where
    the panorama has seen nothing the margin is meaningless and no discount
    applies, which is exactly the regime this channel exists for.
    """
    alpha = np.asarray(panorama_alpha, dtype=np.float64)
    requested = np.asarray(requested, dtype=np.float64)
    if alpha.ndim != 2 or len(alpha) != len(requested):
        raise ValueError("panorama_alpha must be [faces, materials] and match the requested mass")
    if not 0.0 <= headroom < 1.0:
        raise ValueError("headroom must lie in [0, 1)")
    seen = alpha.sum(axis=1) > 0.0
    ordered = np.sort(alpha, axis=1)
    margin = ordered[:, -1] - ordered[:, -2] if alpha.shape[1] >= 2 else ordered[:, -1]
    allowed = headroom * margin
    factor = np.ones(len(requested), dtype=np.float64)
    limited = seen & (requested > 0.0)
    factor[limited] = np.minimum(1.0, allowed[limited] / requested[limited])
    return factor


@dataclass(frozen=True)
class TextureEvidence:
    """Per-face material posterior and the observation rows that carry it."""

    face_index: np.ndarray
    material_probability: np.ndarray
    material_labels: tuple[str, ...]
    rows: np.ndarray
    quality: ObservationQuality
    texel_count: np.ndarray
    gsd_m: np.ndarray
    report: dict[str, float] = field(default_factory=dict)

    def concentration(self) -> np.ndarray:
        """Dirichlet mass this channel adds to each face.

        The accumulator discounts every categorical update by how far the
        prediction sits above uniform, so that factor belongs here too. Without
        it the number would be a budget rather than an amount, and the guarantee
        in :func:`dominance_factor` would be stated about the wrong quantity.
        """
        information = categorical_information(self.material_probability)
        return self.rows.astype(np.float64) * self.quality.combined() * information

    def observations(self) -> tuple[SoftAssociation, ObservationQuality, np.ndarray]:
        """Expand into the association, quality and material blocks of one update.

        A face contributing ``k`` rows becomes ``k`` identical observations, so
        the texel support enters as a count of observations rather than as an
        illegal quality factor above one.
        """
        repeat = np.repeat(np.arange(len(self.face_index)), self.rows)
        association = SoftAssociation(
            surface_indices=self.face_index[repeat][:, None],
            probabilities=np.ones((len(repeat), 1), dtype=np.float64),
        )
        quality = ObservationQuality(
            registration=self.quality.registration[repeat],
            geometry=self.quality.geometry[repeat],
            resolution=self.quality.resolution[repeat],
            incidence=self.quality.incidence[repeat],
            visibility=self.quality.visibility[repeat],
            independence=self.quality.independence[repeat],
        )
        return association, quality, self.material_probability[repeat]

    def apply(self, accumulator: EvidenceAccumulator) -> None:
        """Fold this channel into an accumulator that already holds the taxonomy.

        The entity block is uniform and the attribute block is one half
        throughout, which the accumulator's own information weighting turns into
        exactly zero contribution on those two axes. This channel resolves
        material and nothing else, and encoding that here is safer than
        trusting a caller to pass the right blocks.
        """
        if tuple(accumulator.material_labels) != self.material_labels:
            raise ValueError("accumulator material labels differ from the ones this evidence was built on")
        association, quality, material = self.observations()
        rows = len(association.surface_indices)
        entity = np.full((rows, len(accumulator.entity_labels)), 1.0 / max(len(accumulator.entity_labels), 1))
        attributes = np.full((rows, len(accumulator.attribute_labels)), 0.5)
        accumulator.update(association, quality, entity, material, attributes)


def build_texture_evidence(
    features: TextureFeatures,
    match: TileMatch,
    classifier: MaterialClassifier,
    *,
    face_range_m: np.ndarray,
    panorama_alpha: np.ndarray | None = None,
    headroom: float = 0.5,
    maximum_rows: int = 32,
) -> TextureEvidence:
    """Turn texture features into evidence rows for the support-mesh faces.

    Every quality term is a measured property of this observation rather than a
    tuning constant. ``registration`` is one because the texture is bound to the
    geometry by its own UV map and no pose estimate stands between them.
    ``visibility`` is one for the same reason, with the caveat recorded in the
    report that a tree occluding a facade in the source aerial imagery is baked
    into the texture and cannot be detected here.
    """
    if classifier.material_matrix is None:
        raise ValueError("the classifier must carry a class to material mapping to emit material evidence")
    faces = np.flatnonzero(match.matched)
    tile = match.tile_triangle[faces]
    texels = features.texel_count[tile]
    usable = texels > 0
    faces, tile, texels = faces[usable], tile[usable], texels[usable]
    material = classifier.predict_material(features.values[tile], texels)
    gsd = features.gsd_m[tile]
    range_m = np.asarray(face_range_m, dtype=np.float64)[faces]
    ones = np.ones(len(faces), dtype=np.float64)
    rows = np.maximum(support_rows(texels, maximum_rows=maximum_rows), 1)
    resolution = panorama_resolution_ratio(range_m, gsd)
    incidence = features.texel_anisotropy[tile]
    independence = ones.copy()
    if panorama_alpha is not None:
        # Everything the accumulator will multiply by, except the discount being
        # solved for, so the cap binds the mass that is actually added.
        requested = rows.astype(np.float64) * resolution * incidence * categorical_information(material)
        independence = dominance_factor(np.asarray(panorama_alpha)[faces], requested, headroom=headroom)
    quality = ObservationQuality(
        registration=ones.copy(),
        geometry=ones.copy(),
        resolution=resolution,
        incidence=incidence,
        visibility=ones.copy(),
        independence=independence,
    )
    evidence = TextureEvidence(
        face_index=faces,
        material_probability=material,
        material_labels=tuple(classifier.material_labels),
        rows=rows,
        quality=quality,
        texel_count=texels,
        gsd_m=gsd,
        report={
            "faces_with_texture_evidence": float(len(faces)),
            "median_texels_per_face": float(np.median(texels)) if len(texels) else 0.0,
            "median_gsd_m": float(np.nanmedian(gsd)) if len(gsd) else float("nan"),
            "median_resolution_ratio": float(np.median(resolution)) if len(resolution) else 0.0,
            "median_rows": float(np.median(rows)) if len(rows) else 0.0,
            "visibility_caveat": 1.0,
        },
    )
    evidence.report["median_concentration"] = float(np.median(evidence.concentration())) if len(faces) else 0.0
    return evidence
