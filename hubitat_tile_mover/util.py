from __future__ import annotations

import os
import sys
from typing import List


def _use_color() -> bool:
    """Enable ANSI color on stderr when attached to a TTY (unless NO_COLOR set)."""
    if os.environ.get("NO_COLOR") is not None:
        return False
    return bool(sys.stderr.isatty())


def _c(code: str, s: str) -> str:
    if not _use_color():
        return s
    return f"\x1b[{code}m{s}\x1b[0m"


def err(s: str) -> str:
    return _c("31;1", s)  # bright red


def warn(s: str) -> str:
    return _c("33;1", s)  # bright yellow


def ok(s: str) -> str:
    return _c("32;1", s)  # bright green


def die(msg: str, code: int = 2) -> None:
    print(f"{err('ERROR:')} {msg}", file=sys.stderr)
    raise SystemExit(code)


def wlog(msg: str) -> None:
    print(f"{warn('WARN:')} {msg}", file=sys.stderr, flush=True)


def ilog(msg: str) -> None:
    print(f"INFO: {msg}", file=sys.stderr, flush=True)


def vlog(verbose: bool, msg: str) -> None:
    if verbose:
        print(msg, file=sys.stderr, flush=True)


def dlog(debug: bool, msg: str) -> None:
    if debug:
        print(msg, file=sys.stderr, flush=True)


def normalize_newlines(text: str, mode: str) -> str:
    if mode == "crlf":
        return text.replace("\r\n", "\n").replace("\n", "\r\n")
    if mode == "lf":
        return text.replace("\r\n", "\n")
    return text


def format_id_sample(ids: List[int], max_items: int = 20) -> str:
    ids2 = sorted(ids)
    if len(ids2) <= max_items:
        return ", ".join(map(str, ids2))
    head = ", ".join(map(str, ids2[:max_items]))
    return f"{head}, ... (+{len(ids2) - max_items} more)"


def prompt_yes_no_or_die(
    force: bool,
    prompt: str,
    *,
    what: str = "items",
    details: str | None = None,
    show_details: bool = False,
) -> None:
    if force:
        return
    if not sys.stdin.isatty():
        die(f"This operation will remove {what}. Re-run with --force to proceed (no TTY available for prompt).")
    try:
        ans = input(f"{prompt} [y/N]: ").strip().lower()
    except EOFError:
        die(f"This operation will remove {what}. Re-run with --force to proceed (no input available).")
    if ans not in ("y", "yes"):
        raise SystemExit(1)
