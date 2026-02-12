from __future__ import annotations

from typing import List, Optional, Tuple

from .clipboard import clipboard_get_text, clipboard_set_text
from .util import die, normalize_newlines


def normalize_argv(argv: List[str]) -> List[str]:
    """
    Supports colon variants:
      --import:clipboard
      --import:file <path>
      --output_format:full|minimal|bare (legacy: container/list; also accepts legacy --output_shape:*)
      --output_to:terminal
      --output_to:file <path>
      --sort:irc
      --order:rci (legacy)
      --indent:0

    Converts to space-separated argv suitable for argparse.
    """
    out: List[str] = []
    for a in argv:
        if a.startswith("--sort:"):
            out.append("--sort=" + a.split(":", 1)[1])
        elif a.startswith("--order:"):
            out.append("--order=" + a.split(":", 1)[1])
        elif a.startswith("--indent:"):
            out += ["--indent", a.split(":", 1)[1]]
        elif a.startswith("--trim:"):
            out += ["--trim", a.split(":", 1)[1]]
        elif a.startswith("--import:"):
            out += ["--import", a.split(":", 1)[1]]
        elif a.startswith("--output_format:") or a.startswith("--output-format:"):
            out += ["--output_format", a.split(":", 1)[1]]
        elif a.startswith("--output_shape:") or a.startswith("--output-shape:"):
            out += ["--output_format", a.split(":", 1)[1]]
        elif a.startswith("--output_to:") or a.startswith("--output-to:"):
            out += ["--output_to", a.split(":", 1)[1]]
        else:
            out.append(a)
    return out


def assert_singleton_flags(argv: List[str], names: List[str]) -> None:
    counts = {n: 0 for n in names}
    for tok in argv:
        if tok in counts:
            counts[tok] += 1
    dupes = {k: v for k, v in counts.items() if v > 1}
    if dupes:
        parts = ", ".join([f"{k} x{v}" for k, v in dupes.items()])
        die(f"Option(s) may be specified only once: {parts}")


def parse_import_spec(spec: Optional[List[str]]) -> Tuple[str, Optional[str]]:
    if spec is None:
        return ("clipboard", None)

    if len(spec) == 1 and spec[0] == "clipboard":
        return ("clipboard", None)

    if len(spec) == 2 and spec[0] == "file":
        return ("file", spec[1])

    die("Invalid import. Use --import:clipboard OR --import:file <filename>.")


def parse_output_to_specs(specs: Optional[List[List[str]]]) -> List[Tuple[str, Optional[str]]]:
    if specs is None:
        return [("clipboard", None)]

    outs: List[Tuple[str, Optional[str]]] = []
    for s in specs:
        if len(s) == 1 and s[0] in ("terminal", "clipboard"):
            outs.append((s[0], None))
            continue
        if len(s) == 2 and s[0] == "file":
            outs.append(("file", s[1]))
            continue
        die("Invalid output_to. Use --output_to:terminal OR --output_to:clipboard OR --output_to:file <filename>.")

    if not outs:
        return [("clipboard", None)]
    return outs


def read_input_text(import_kind: str, import_path: Optional[str]) -> str:
    if import_kind == "clipboard":
        return clipboard_get_text()
    if import_kind == "file":
        if not import_path:
            die("Import kind is file but no filename was provided.")
        try:
            with open(import_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            die(f"Input file not found: {import_path}")
        except OSError as e:
            die(f"Unable to read input file: {e}")
    die(f"Unknown import kind: {import_kind}")
    return ""


def write_outputs(outputs: List[Tuple[str, Optional[str]]], newline_mode: str, text: str) -> None:
    text = normalize_newlines(text, newline_mode)
    for kind, arg in outputs:
        if kind == "terminal":
            import sys

            sys.stdout.write(text)
            sys.stdout.flush()
        elif kind == "clipboard":
            clipboard_set_text(text)
        elif kind == "file":
            if not arg:
                die("Output kind is file but no filename was provided.")
            try:
                with open(arg, "w", encoding="utf-8", newline="") as f:
                    f.write(text)
            except OSError as e:
                die(f"Unable to write output file '{arg}': {e}")
        else:
            die(f"Unknown output kind: {kind}")
