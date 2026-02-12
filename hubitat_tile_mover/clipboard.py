from __future__ import annotations

import subprocess
import sys

from .util import die


def clipboard_get_text() -> str:
    if sys.platform.startswith("win"):
        try:
            cp = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"],
                capture_output=True,
                text=True,
                check=True,
            )
            return cp.stdout
        except Exception as e:
            die(f"Unable to read clipboard on Windows via PowerShell: {e}")

    if sys.platform == "darwin":
        try:
            cp = subprocess.run(["pbpaste"], capture_output=True, text=True, check=True)
            return cp.stdout
        except Exception as e:
            die(f"Unable to read clipboard on macOS via pbpaste: {e}")

    if sys.platform.startswith("linux"):
        for cmd in (["wl-paste", "--no-newline"], ["xclip", "-selection", "clipboard", "-o"]):
            try:
                cp = subprocess.run(cmd, capture_output=True, text=True, check=True)
                return cp.stdout
            except Exception:
                continue

    # Fallback: tkinter
    try:
        import tkinter  # noqa: PLC0415

        r = tkinter.Tk()
        r.withdraw()
        r.update()
        text = r.clipboard_get()
        r.destroy()
        return text
    except Exception as e:
        die(f"Unable to read clipboard (no suitable method worked): {e}")

    return ""  # unreachable


def clipboard_set_text(text: str) -> None:
    if sys.platform.startswith("win"):
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value ([Console]::In.ReadToEnd())"],
                input=text,
                text=True,
                check=True,
            )
            return
        except Exception as e:
            die(f"Unable to write clipboard on Windows via PowerShell: {e}")

    if sys.platform == "darwin":
        try:
            subprocess.run(["pbcopy"], input=text, text=True, check=True)
            return
        except Exception as e:
            die(f"Unable to write clipboard on macOS via pbcopy: {e}")

    if sys.platform.startswith("linux"):
        for cmd in (["wl-copy"], ["xclip", "-selection", "clipboard"]):
            try:
                subprocess.run(cmd, input=text, text=True, check=True)
                return
            except Exception:
                continue

    # Fallback: tkinter
    try:
        import tkinter  # noqa: PLC0415

        r = tkinter.Tk()
        r.withdraw()
        r.clipboard_clear()
        r.clipboard_append(text)
        r.update()
        r.destroy()
        return
    except Exception as e:
        die(f"Unable to write clipboard (no suitable method worked): {e}")
