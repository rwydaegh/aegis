"""The reduction from per site rows to the cross city table, and the gate on it.

This is the arithmetic behind the study's central object, and it is the place a
wrong number has actually reached the paper. ``AGGREGATE_REBUILD.md`` records the
whole failure: the eleven city figure was copied out of an aggregate that a sweep
was still writing, one square held 3 standpoints where the rest held 80, and the
completeness guard of the day printed nothing and wrote ``"complete": true``.

The guard failed for a reason worth stating precisely, because it is the reason
the fix here is a type rather than a warning. The old guard counted expected sites
inside the loop, next to the counter for finished ones, so the two were equal at
every iteration of a healthy sweep. It could only fire when a site raised, which
is the rarer failure, and it was silent through the mid sweep snapshot, which is
the one that got published.

Three things follow, and they are the whole design of this module.

:class:`Coverage` takes the expected sites as *names*, keyword only and with no
default. A caller cannot pass "how many I have done so far" as a list of the
squares it meant to trace, so the arithmetic that hid the failure is not available
to write.

:class:`CrossCityTable` carries its Coverage as a required field and puts it in
:meth:`CrossCityTable.as_dict`. A partial table is still constructible, because a
sweep that dies at hour two should leave a readable aggregate behind, but there is
no partial table that does not say so in the object.

:class:`PublishedAggregate` is the only thing the figure writers accept, and the
only way to make one is :meth:`CrossCityTable.publish`, which raises. So drawing a
partial eleven city figure is not a discipline any more, it is a type error.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .rows import Row, RowSet
from .stats import summarise

#: The columns the cross city table reduces. Rooftop and isotropic are the two
#: illumination models the figure draws, sky fraction is the geometric quantity
#: that is converged at every crop radius, and the absorbed power density is the
#: body side. Street small cell is deliberately not here: it is in the per site
#: row files and in the paper's spread table, and adding it to this list would
#: change every summary file on disk.
DEFAULT_KEYS: tuple[str, ...] = ("chi_rooftop", "chi_isotropic", "sky_fraction", "rooftop_peak_sab_w_m2")


class IncompleteAggregate(RuntimeError):
    """Raised when a table that is not publishable is asked to be published."""


@dataclass(frozen=True)
class Coverage:
    """Which squares a table holds against which squares it was meant to hold.

    ``expected`` is the set of sites the sweep intended, decided before it started
    and from something durable, which in practice is "the sites with a mesh at this
    crop radius". ``present`` is what actually reached the reduction. Everything
    else here is derived from those two and from the per site counts, so there is
    no field a caller can fill in wrongly and no field that can drift out of step
    with another.
    """

    expected: tuple[str, ...]
    present: tuple[str, ...]
    #: Standpoints per site, over the sites present.
    locations: Mapping[str, int] = field(default_factory=dict)
    #: Lines that failed to parse per site. Normally zero everywhere. Two sweeps
    #: sharing one tag tore records in half at New York and Prague and cost two
    #: whole standpoints, and the files still looked the right length.
    torn: Mapping[str, int] = field(default_factory=dict)

    @property
    def missing(self) -> tuple[str, ...]:
        """Expected and absent. The failure that reached the paper."""
        return tuple(site for site in self.expected if site not in set(self.present))

    @property
    def unexpected(self) -> tuple[str, ...]:
        """Present and not expected. Means the table read files from another sweep."""
        return tuple(site for site in self.present if site not in set(self.expected))

    @property
    def ragged(self) -> bool:
        """Do the sites disagree about how many standpoints they carry?

        A ragged table is not automatically wrong, since a site can legitimately
        yield fewer walkable standpoints than another. It is wrong in the eleven
        city comparison specifically, where the whole design holds the standpoint
        count fixed so that what varies between curves is urban form.
        """
        return len(set(self.locations.values())) > 1

    @property
    def torn_total(self) -> int:
        return sum(self.torn.values())

    @property
    def complete(self) -> bool:
        """Every expected site present, and no site present that was not expected.

        Site set equality and not a count, which is the specific arithmetic that
        failed before. Eleven of eleven where three of the eleven are the wrong
        three is not complete, and a count cannot tell.
        """
        return not self.missing and not self.unexpected

    @property
    def publishable(self) -> bool:
        return self.complete and not self.ragged and self.torn_total == 0

    def complaints(self) -> tuple[str, ...]:
        """Everything wrong with this coverage, in the words a refusal prints."""
        problems: list[str] = []
        if self.missing:
            problems.append(f"missing {len(self.missing)} of {len(self.expected)} sites: {', '.join(self.missing)}")
        if self.unexpected:
            problems.append(f"sites present that were not expected: {', '.join(self.unexpected)}")
        if self.ragged:
            counts = sorted(set(self.locations.values()))
            odd = sorted(site for site, n in self.locations.items() if n != max(counts))
            problems.append(f"ragged standpoint counts {counts}, short at {', '.join(odd)}")
        if self.torn_total:
            torn = sorted(site for site, n in self.torn.items() if n)
            problems.append(f"{self.torn_total} torn lines across {', '.join(torn)}")
        return tuple(problems)

    def as_dict(self) -> dict[str, Any]:
        """The full coverage record, including the fields the summary file predates.

        The summary file on disk carries four of these, and those four are pinned
        by ``tests/golden/cities_250m_all_sites.json``. ``torn_lines_by_site`` and
        the two name lists are newer and go into the figure sidecar rather than
        into that file, so a golden fixture does not have to move for a guard to
        get stronger.
        """
        return {
            "sites_expected": list(self.expected),
            "sites_present": list(self.present),
            "missing_sites": list(self.missing),
            "unexpected_sites": list(self.unexpected),
            "locations_by_site": dict(self.locations),
            "torn_lines_by_site": dict(self.torn),
            "ragged_locations": self.ragged,
            "complete": self.complete,
            "publishable": self.publishable,
        }


@dataclass(frozen=True)
class CrossCityTable:
    """One row per square, and the coverage that says whether the set is whole.

    Built by :meth:`build`, which is the only construction path that reduces rows.
    The dataclass itself is left constructible so a table can be read back from a
    summary file, and :meth:`from_dict` does that.
    """

    coverage: Coverage
    #: ``summarise`` output per site, keyed by site name.
    sites: Mapping[str, dict[str, Any]]
    frequency_hz: float
    reference_s0_w_m2: float
    crop_radius_m: float
    materials: str
    crop_bound_note: str = ""
    keys: tuple[str, ...] = DEFAULT_KEYS
    #: The rows the summary was reduced from, kept so a figure cannot be drawn
    #: from a different row set than the table was built from. That is not a
    #: hypothetical: the published figure and the published table disagreed for a
    #: day because one had been regenerated and the other had not. Left out of
    #: equality and repr, since two tables agree when their statistics do.
    rows: Mapping[str, tuple[Row, ...]] = field(default_factory=dict, compare=False, repr=False)

    @classmethod
    def build(
        cls,
        rows_by_site: Mapping[str, RowSet | Sequence[Row]],
        *,
        expected: Sequence[str],
        frequency_hz: float,
        reference_s0_w_m2: float,
        crop_radius_m: float,
        materials: str,
        crop_bound_note: str = "",
        keys: Sequence[str] = DEFAULT_KEYS,
    ) -> CrossCityTable:
        """Reduce per site rows to the table, with the coverage measured alongside.

        ``expected`` has no default and takes names. That is the fix for the guard
        this module exists to replace: the old one derived expectation from the
        loop that was filling it, so it agreed with itself at every step of a
        sweep that was ten elevenths unfinished.

        Accepts either :class:`~.rows.RowSet` values, which carry a torn line
        count, or bare row sequences, which do not and are recorded as zero torn.
        The plain sequence path exists because the coverage ladder and the per site
        reports already hold rows in memory.
        """
        present: list[str] = []
        locations: dict[str, int] = {}
        torn: dict[str, int] = {}
        sites: dict[str, dict[str, Any]] = {}
        kept: dict[str, tuple[Row, ...]] = {}
        for site, value in rows_by_site.items():
            rows = value.rows if isinstance(value, RowSet) else tuple(value)
            present.append(site)
            locations[site] = len(rows)
            torn[site] = value.torn if isinstance(value, RowSet) else 0
            sites[site] = summarise(rows, list(keys))
            kept[site] = rows
        coverage = Coverage(
            expected=tuple(expected),
            present=tuple(present),
            locations=locations,
            torn=torn,
        )
        return cls(
            coverage=coverage,
            sites=sites,
            frequency_hz=float(frequency_hz),
            reference_s0_w_m2=float(reference_s0_w_m2),
            crop_radius_m=float(crop_radius_m),
            materials=materials,
            crop_bound_note=crop_bound_note,
            keys=tuple(keys),
            rows=kept,
        )

    def median(self, site: str, key: str) -> float:
        """One site's median of one column. The number the between site range is built on."""
        return float(self.sites[site][key]["quantiles"]["0.5"])

    def spread_db(self, site: str, key: str) -> float | None:
        return self.sites[site][key]["spread_db_p95_over_p05"]

    def sites_with(self, key: str) -> tuple[str, ...]:
        """Sites whose summary carries this column at all.

        Not every site has every column. A file written by two code versions is
        missing ``multipath_gain_street_small_cell`` in half its rows, which is on
        disk at Brussels, Madrid and Prague, so a table function that assumes a
        rectangular set will raise on real data.
        """
        return tuple(site for site in self.sites if key in self.sites[site])

    def as_dict(self) -> dict[str, Any]:
        """The summary file's shape, which is pinned by the golden fixtures.

        Four coverage fields are flattened to the top level here rather than nested
        under a ``coverage`` key, because that is where they are in every summary
        file already written and ``tests/golden/cities_250m_all_sites.json`` holds
        them at those paths. The richer record is
        :meth:`Coverage.as_dict`, and the figure sidecar carries that one.
        """
        return {
            "frequency_hz": self.frequency_hz,
            "reference_s0_w_m2": self.reference_s0_w_m2,
            "materials": self.materials,
            "crop_radius_m": self.crop_radius_m,
            "crop_bound_note": self.crop_bound_note,
            "sites_present": len(self.coverage.present),
            "sites_expected": len(self.coverage.expected),
            "complete": self.coverage.complete,
            "locations_by_site": dict(self.coverage.locations),
            "ragged_locations": self.coverage.ragged,
            "sites": dict(self.sites),
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any], *, expected: Sequence[str] | None = None) -> CrossCityTable:
        """Read a summary file back.

        The file records how many sites were expected but not which, so a table
        read back from one has to be told the names or it assumes the sites present
        were the sites intended. That assumption is stated here rather than made
        silently: if the file says eleven expected and holds ten, the missing name
        cannot be recovered and the coverage records ten expected and ten present
        with a count mismatch left for the caller to see in the file.
        """
        present = tuple(document["sites"])
        names = tuple(expected) if expected is not None else present
        return cls(
            coverage=Coverage(
                expected=names,
                present=present,
                locations=dict(document.get("locations_by_site", {})),
                torn={},
            ),
            sites=dict(document["sites"]),
            frequency_hz=float(document["frequency_hz"]),
            reference_s0_w_m2=float(document["reference_s0_w_m2"]),
            crop_radius_m=float(document["crop_radius_m"]),
            materials=str(document.get("materials", "")),
            crop_bound_note=str(document.get("crop_bound_note", "")),
        )

    def publish(self) -> PublishedAggregate:
        """Hand this table to a figure, or refuse and say what is wrong with it.

        The refusal names the squares. ``AGGREGATE_REBUILD.md`` had to be written
        by opening eleven files by hand, and the one thing that would have saved
        that work is a message that says Brussels.
        """
        return PublishedAggregate(self)


@dataclass(frozen=True)
class PublishedAggregate:
    """A cross city table that has passed the completeness gate.

    Deliberately thin. The value is not in what it holds, it is that a figure
    writer's signature can ask for one, and then no code path draws an eleven city
    curve from ten squares. That was previously a rule in a docstring and a print
    statement, and both were followed right up until the day they were not.
    """

    table: CrossCityTable

    def __post_init__(self) -> None:
        coverage = self.table.coverage
        if not coverage.publishable:
            raise IncompleteAggregate(
                "this aggregate is not publishable: " + " | ".join(coverage.complaints() or ("no reason recorded",))
            )

    @property
    def coverage(self) -> Coverage:
        return self.table.coverage

    @property
    def sites(self) -> Mapping[str, dict[str, Any]]:
        return self.table.sites

    @property
    def locations_per_site(self) -> int:
        """The standpoint count every square carries. Well defined because it is not ragged."""
        return next(iter(self.table.coverage.locations.values()))

    def rows(self) -> Mapping[str, tuple[Row, ...]]:
        """The standpoints the table was reduced from, for a figure to draw.

        A table read back from a summary file has no rows, and asking for them
        raises rather than returning an empty mapping that would draw an empty
        figure. An empty figure is the failure this whole module is about.
        """
        if not self.table.rows:
            raise IncompleteAggregate(
                "this table was read back from a summary file and carries no rows, so nothing can be drawn from it"
            )
        return self.table.rows
