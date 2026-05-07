"""circa CLI entry point."""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import sys
from pathlib import Path

from server import paths


TEMPLATES = Path(__file__).parent / "templates"


class PidfileBusy(RuntimeError):
    pass


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def write_pidfile(paper_dir: Path, pid: int) -> None:
    pf = paths.pidfile(paper_dir)
    if pf.exists():
        try:
            existing = int(pf.read_text().strip())
        except ValueError:
            existing = -1
        if existing != pid and _pid_alive(existing):
            raise PidfileBusy(f"circa is already running on pid {existing}")
    pf.write_text(str(pid))


def remove_pidfile(paper_dir: Path) -> None:
    pf = paths.pidfile(paper_dir)
    if pf.exists():
        pf.unlink()


def bootstrap_workdir(paper_dir: Path) -> None:
    paths.ensure_workdir(paper_dir)
    if not paths.style_md(paper_dir).exists():
        shutil.copy(TEMPLATES / "style.md", paths.style_md(paper_dir))


def insert_pdfcomment_package(paper_tex: Path) -> bool:
    text = paper_tex.read_text()
    if "\\usepackage[author={circa}]{pdfcomment}" in text:
        return False
    if "\\usepackage{hyperref}" not in text:
        raise RuntimeError(
            "paper.tex does not load \\usepackage{hyperref}; cannot insert pdfcomment after it"
        )
    paper_tex.write_text(
        text.replace(
            "\\usepackage{hyperref}",
            "\\usepackage{hyperref}\n\\usepackage[author={circa}]{pdfcomment}",
            1,
        )
    )
    return True


def _confirm(prompt: str) -> bool:
    try:
        return input(prompt + " [y/N] ").strip().lower() == "y"
    except EOFError:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(prog="circa")
    sub = parser.add_subparsers(dest="cmd", required=False)

    serve = sub.add_parser("serve", help="start the circa server (default)")
    serve.add_argument("paper_tex", type=Path)
    serve.add_argument("--port", type=int, default=7333)
    serve.add_argument("--build-timeout", type=int, default=120)
    serve.add_argument(
        "--batch-timeout", type=int, default=180, help="seconds before an SDK batch call is aborted"
    )
    serve.add_argument("--enable-pdfcomment", action="store_true")

    revert = sub.add_parser("revert", help="revert a batch")
    revert.add_argument("paper_tex", type=Path)
    revert.add_argument("batch_id")
    revert.add_argument("--force", action="store_true")

    clean = sub.add_parser("clean-comments", help="strip circa-emitted markers")
    clean.add_argument("paper_tex", type=Path)
    clean.add_argument("--strip-fences", action="store_true")

    gc = sub.add_parser("gc", help="prune old snapshots/hunks")
    gc.add_argument("paper_tex", type=Path)
    gc.add_argument("--keep", type=int, default=50)

    # If first arg looks like a path (not a known subcommand and not a flag),
    # treat as `serve <path>` for ergonomics. Flags pass through to the top-level
    # parser so `circa --help` shows the multi-subcommand help.
    KNOWN = {"serve", "revert", "clean-comments", "gc"}
    argv = sys.argv[1:]
    if argv and argv[0] not in KNOWN and not argv[0].startswith("-"):
        argv = ["serve", *argv]
    args = parser.parse_args(argv)

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    if args.cmd == "serve":
        paper_tex = args.paper_tex.resolve()
        paper_dir = paper_tex.parent
        bootstrap_workdir(paper_dir)
        write_pidfile(paper_dir, os.getpid())
        actually_pdfcomment = False
        if args.enable_pdfcomment:
            if _confirm(
                f"circa will add \\usepackage[author={{circa}}]{{pdfcomment}} to {paper_tex}; continue?"
            ):
                inserted = insert_pdfcomment_package(paper_tex)
                actually_pdfcomment = True
                if inserted:
                    print("inserted pdfcomment package after hyperref")
        signal.signal(signal.SIGTERM, lambda *_: (remove_pidfile(paper_dir), sys.exit(0)))
        signal.signal(signal.SIGINT, lambda *_: (remove_pidfile(paper_dir), sys.exit(0)))
        from server.main import run_server

        run_server(
            paper_dir=paper_dir,
            port=args.port,
            build_timeout_s=args.build_timeout,
            batch_timeout_s=args.batch_timeout,
            pdfcomment_enabled=actually_pdfcomment,
        )
    elif args.cmd == "revert":
        from server.snapshots import SnapshotManager

        paper_dir = args.paper_tex.parent.resolve()
        # Refuse if a circa server is running for this paper — its in-memory state
        # would be out of sync after we revert paper.tex behind its back.
        pf = paths.pidfile(paper_dir)
        if pf.exists():
            try:
                running_pid = int(pf.read_text().strip())
                if _pid_alive(running_pid) and running_pid != os.getpid():
                    print(f"circa server is running on pid {running_pid}; stop it before running revert")
                    sys.exit(2)
            except ValueError:
                pass
        SnapshotManager(paper_dir).revert(args.batch_id, force=args.force)
        print(f"reverted batch {args.batch_id}")
    elif args.cmd == "clean-comments":
        from server.cleanup import clean_comments

        n = clean_comments(args.paper_tex, strip_fences=args.strip_fences)
        print(f"stripped {n} circa markers")
    elif args.cmd == "gc":
        # Implemented in Task 13's polish step. Stub for now.
        print(f"gc not implemented yet (would keep last {args.keep} batches)")
