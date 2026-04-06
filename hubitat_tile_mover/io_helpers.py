from __future__ import annotations

from typing import List, Optional, Tuple

from .clipboard import clipboard_get_text, clipboard_set_text
from .util import die, normalize_newlines


def normalize_argv(argv: List[str]) -> List[str]:
    """
    Supports colon variants and quoted/separate sort specs:
      --import:clipboard
      --import:file <path>
      --import:hub <dashboard_url>
      --merge_source:file <path>
      --merge_source:hub <dashboard_url>
      --output_format:full|minimal|bare (legacy: container/list; also accepts legacy --output_shape:*)
      --output_to:terminal
      --output_to:file <path>
      --output_to:hub <dashboard_url>
      --sort_json:rci
      --sort_json "-rci"
      --sort:rci                      (legacy alias)
      --list_tiles:plain[:rci]
      --list_tiles:plain "-hwi"
      --list_tiles plain "-hwi"
      --indent:0

    Converts to argv suitable for argparse.
    """
    out: List[str] = []
    list_kinds = {"plain", "tree", "overlap", "nested", "conflicts"}

    def looks_like_json_sort(tok: str) -> bool:
        return bool(tok) and not tok.startswith("--")

    def looks_like_list_sort(tok: str) -> bool:
        return bool(tok) and not tok.startswith("--")

    i = 0
    while i < len(argv):
        a = argv[i]

        if a.startswith("--sort_json:") or a.startswith("--sort-json:"):
            out.append("--sort_json=" + a.split(":", 1)[1])
        elif a.startswith("--sort:"):
            out.append("--sort_json=" + a.split(":", 1)[1])
        elif a in ("--sort_json", "--sort-json", "--sort"):
            if i + 1 < len(argv) and looks_like_json_sort(argv[i + 1]):
                out.append('--sort_json=' + argv[i + 1])
                i += 1
            else:
                out.append("--sort_json" if a != "--sort" else "--sort")
        elif a.startswith("--order:"):
            out.append("--order=" + a.split(":", 1)[1])
        elif a.startswith("--indent:"):
            out += ["--indent", a.split(":", 1)[1]]
        elif a.startswith("--trim:"):
            out += ["--trim", a.split(":", 1)[1]]
        elif a.startswith("--list_tiles:") or a.startswith("--list-tiles:"):
            spec = a.split(":", 1)[1]
            head = spec.split(":", 1)[0].strip().lower()
            if ":" not in spec and head in list_kinds and i + 1 < len(argv) and looks_like_list_sort(argv[i + 1]):
                spec = spec + ":" + argv[i + 1]
                i += 1
            out.append("--list_tiles=" + spec)
        elif a in ("--list_tiles", "--list-tiles"):
            if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
                first = argv[i + 1]
                spec = first
                head = first.split(":", 1)[0].strip().lower()
                if head in list_kinds:
                    i += 1
                    if ":" not in first and i + 1 < len(argv) and looks_like_list_sort(argv[i + 1]):
                        spec = first + ":" + argv[i + 1]
                        i += 1
                    out.append("--list_tiles=" + spec)
                else:
                    out.append(a)
            else:
                out.append(a)
        # --show_map:* and --show_axis:* are handled directly by argparse (legacy --show_axes:* also accepted)
        elif a.startswith("--import:"):
            out += ["--import", a.split(":", 1)[1]]
        elif a.startswith("--merge_source:") or a.startswith("--merge-source:"):
            out += ["--merge_source", a.split(":", 1)[1]]
        elif a.startswith("--output_format:") or a.startswith("--output-format:"):
            out += ["--output_format", a.split(":", 1)[1]]
        elif a.startswith("--output_shape:") or a.startswith("--output-shape:"):
            out += ["--output_format", a.split(":", 1)[1]]
        elif a.startswith("--output_to:") or a.startswith("--output-to:") or a.startswith("--output:") or a.startswith("--output-:"):
            out += ["--output_to", a.split(":", 1)[1]]
        else:
            out.append(a)
        i += 1
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

    if len(spec) == 2 and spec[0] == "hub":
        return ("hub", spec[1])

    if len(spec) == 2 and spec[0] == "file":
        return ("file", spec[1])

    die("Invalid import. Use --import:clipboard OR --import:file <filename> OR --import:hub <dashboard_url>.")


def parse_merge_source_spec(spec: Optional[List[str]]) -> Tuple[str, Optional[str]]:
    """Parse --merge_source <kind> <arg>.

    Supported:
      --merge_source:file <filename>
      --merge_source:hub <dashboard_url>
    """
    if spec is None:
        return ("", None)
    if len(spec) == 2 and spec[0] == "file":
        return ("file", spec[1])
    if len(spec) == 2 and spec[0] in ("hub", "url"):
        return ("hub", spec[1])
    die("Invalid merge source. Use --merge_source:file <filename> OR --merge_source:hub <dashboard_url>.")


def parse_output_to_specs(specs: Optional[List[List[str]]]) -> List[Tuple[str, Optional[str]]]:
    if specs is None:
        return [("clipboard", None)]

    outs: List[Tuple[str, Optional[str]]] = []
    for s in specs:
        if len(s) == 1 and s[0] in ("terminal", "clipboard"):
            outs.append((s[0], None))
            continue
        if len(s) == 1 and s[0] == "hub":
            outs.append(("hub", None))
            continue
        if len(s) == 2 and s[0] == "hub":
            outs.append(("hub", s[1]))
            continue
        if len(s) == 2 and s[0] == "file":
            outs.append(("file", s[1]))
            continue
        die("Invalid output. Use --output:terminal OR --output:clipboard OR --output:file <filename> OR --output:hub [dashboard_url].")

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
