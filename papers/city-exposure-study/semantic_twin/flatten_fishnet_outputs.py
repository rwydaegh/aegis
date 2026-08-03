"""Expose per panorama fishnet views at the top of a site's fishnet directory.

`semantic_binding.bind` collects its views with a non recursive
`glob("*_fishnet.npz")` over the directory it is handed. Some sites were built
with every view written into a per panorama subdirectory, which that glob cannot
see, so the fishnets exist on disk and the site still reports no semantic
coverage. Nothing is wrong with either layout and nothing about the fishnets
needs rebuilding, the files are simply one level below where the reader looks.

This script publishes each nested view under a flat name that keeps the
panorama it came from, `pano_00_4Cxfyuve.../h+00_090_fishnet.npz` becoming
`pano_00_4Cxfyuve..._h+00_090_fishnet.npz`, matching the convention already used
by the sites that were flattened by hand. The published entries are relative
symlinks rather than copies, so the per panorama layout stays authoritative and
a rebuild that rewrites a nested view is picked up without republishing.

Run from the `semantic_twin` directory::

    python flatten_fishnet_outputs.py --all --dry-run
    python flatten_fishnet_outputs.py --site prague_staromestske
"""

from __future__ import annotations

import argparse
import pathlib
import sys

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent

#: The suffix `bind` globs for. A published entry has to end in it to be read.
VIEW_SUFFIX = "_fishnet.npz"


def fishnet_directories() -> list[pathlib.Path]:
    """Every site fishnet directory under `outputs`, in site order."""
    root = SCRIPT_DIR / "outputs"
    if not root.is_dir():
        return []
    return sorted(f for f in root.glob("*_fishnet_*") if f.is_dir())


def site_directory(site: str) -> pathlib.Path:
    """The fishnet directory of one site, whatever segmentation it was built with."""
    found = [f for f in fishnet_directories() if f.name.startswith(f"{site}_fishnet_")]
    if not found:
        raise SystemExit(f"no fishnet directory for {site} under outputs")
    if len(found) > 1:
        names = ", ".join(f.name for f in found)
        raise SystemExit(f"{site} has more than one fishnet directory, name one explicitly: {names}")
    return found[0]


def flat_name(panorama: str, view: str) -> str:
    """The published name of a view, carrying the panorama that produced it."""
    return f"{panorama}_{view}"


def nested_views(directory: pathlib.Path) -> list[tuple[pathlib.Path, str]]:
    """Views sitting one level down, as (path, published name) pairs."""
    found = []
    for panorama in sorted(f for f in directory.iterdir() if f.is_dir()):
        for view in sorted(panorama.glob(f"*{VIEW_SUFFIX}")):
            found.append((view, flat_name(panorama.name, view.name)))
    return found


def published_views(directory: pathlib.Path) -> list[pathlib.Path]:
    """Views `bind` can already see, which is what the glob it runs would return."""
    return sorted(directory.glob(f"*{VIEW_SUFFIX}"))


def publish(directory: pathlib.Path, *, dry_run: bool) -> dict[str, int]:
    """Link every nested view into the top of the directory. Safe to repeat."""
    tally = {"published": 0, "already": 0, "occupied": 0}
    for view, name in nested_views(directory):
        link = directory / name
        # A symlink target is resolved against the directory holding the link,
        # which is this directory, so the target is the nested path as written
        # and carries no leading step upwards.
        target = pathlib.Path(view.parent.name) / view.name
        if link.is_symlink():
            if link.readlink() == target:
                tally["already"] += 1
                continue
            if not dry_run:
                link.unlink()
        elif link.exists():
            # A real file already occupies the name. It was put there by
            # something other than this script, so leave it alone and say so.
            tally["occupied"] += 1
            continue
        if not dry_run:
            link.symlink_to(target)
            if not link.exists():
                # A link that does not resolve is worse than no link, because
                # `bind` globs it and then fails on the read.
                link.unlink()
                raise SystemExit(f"published {link} does not resolve to {view}")
        tally["published"] += 1
    return tally


def broken(directory: pathlib.Path) -> list[pathlib.Path]:
    """Published names that glob but do not open, which is the worst outcome."""
    return [path for path in published_views(directory) if not path.exists()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--site", help="Site key, for example prague_staromestske")
    parser.add_argument("--all", action="store_true", help="Every site fishnet directory under outputs")
    parser.add_argument("--dry-run", action="store_true", help="Report what would be published and write nothing")
    args = parser.parse_args(argv)

    if bool(args.site) == bool(args.all):
        raise SystemExit("pass exactly one of --site and --all")

    directories = fishnet_directories() if args.all else [site_directory(args.site)]
    for directory in directories:
        before = len(published_views(directory))
        tally = publish(directory, **{"dry_run": args.dry_run})
        after = before if args.dry_run else len(published_views(directory))
        note = f"{directory.name}: {before} views visible to bind"
        if tally["published"]:
            note += f", publishing {tally['published']}"
        if tally["already"]:
            note += f", {tally['already']} already published"
        if tally["occupied"]:
            note += f", {tally['occupied']} names held by real files"
        if not args.dry_run:
            note += f", now {after}"
        dangling = broken(directory)
        if dangling:
            note += f", {len(dangling)} published names do not resolve"
        print(note)
    return 0


if __name__ == "__main__":
    sys.exit(main())
