"""Hedwig the owl.

On terminals that support an inline image protocol (Kitty, iTerm2, WezTerm, Ghostty,
...) the real artwork at assets/mascot.png is drawn in full colour. Everywhere else
we fall back to pixel art built from half-block characters: each art string below is
one row of pixels, each letter a colour from PALETTE and "." transparent, with two
pixel rows packed into one terminal row via the upper half block so the owl renders
as solid colour rather than line strokes.
"""

import base64
import os
import sys
from pathlib import Path

from rich.console import Console, ConsoleOptions, RenderResult
from rich.style import Style
from rich.table import Table
from rich.text import Text

_MASCOT_PNG = Path(__file__).resolve().parent.parent / "data" / "mascot.png"
_KITTY_CHUNK = 4096

PALETTE = {
    "K": "#2b160d",  # outline
    "B": "#a65a2e",  # brown feathers
    "D": "#74391b",  # dark brown (knuckles)
    "C": "#f7dfb9",  # cream
    "c": "#e6c193",  # cream shade
    "W": "#ffffff",  # eye white
    "E": "#1a0d06",  # pupil
    "O": "#f7a21b",  # beak and feet
    "R": "#e23a2c",  # scarf and cape
    "Q": "#a3201a",  # dark red folds
    "G": "#f5bd2a",  # gold
    "H": "#b9800f",  # dark gold
    "S": "#a9adb8",  # steel
    "L": "#eef0f5",  # light steel
    "N": "#6e3b1f",  # shield wood
}

# Full mascot: sword, glasses, scarf, cape and shield. 39 cols x 16 rows.
HERO = (
    ".....KK................................",
    "....KLSK...............................",
    "....KLSK...............................",
    "....KLSK...............................",
    "....KLSK...KK................KK........",
    "....KLSK..KBBK..KKKKKKKKKK..KBBK.......",
    "....KLSK..KBBBKKBBBBBBBBBBKKBBBK.......",
    "....KLSK.KBBBBBBBBBBBBBBBBBBBBBBK......",
    "....KLSKKBBBCCCCCCCBBBBCCCCCCCBBBK.....",
    "....KLSKKBBCKKKKKCCCCCCCCKKKKKCBBK.....",
    "..KKKKKKKKBKWWWWWKCCCCCCKWWWWWKBBK.....",
    ".KHGGGGGGHKKWWEEWKKKKKKKKWWEEWKKKK.....",
    "..KKKKKKKKBKWEEEWKCCOOCCKWEEEWKBBK.....",
    "..KKKKKKKKBKWWWWWKCCOOCCKWWWWWKBBK.....",
    ".KBDBDBDBBKCKKKKKCCCRRCCCKKKKKCBBK.....",
    ".KBBBBBBBBKCCCCCCCCCCCCCCCCCCCCBK......",
    "..KBBBBBBBKGRRRRRRRRRRRRRRRRRRRRQK.....",
    "...KBBBBBBKRRRRRRRRRRRRRRRRRRRRQQK.....",
    "....KBBBBBBBBBcCCCCCCCCCCCCcBKKKKKKKKKK",
    ".....KBBBBBBBcCCCCCCCCCCCCCCcKGGGGGGGGK",
    "....KRKBBBBBcCCCCCCCCCCCCCCCCKGNNNNNNGK",
    "...KRRRQKBBBcCCCCCCCCCCCCCCCCKGGNNNNGGK",
    "..KRRRQRKBBBcCCCCCCCCCCCCCCCCKGNGGGGNGK",
    ".KRRRQRRKBBBcCCCCCCCCCCCCCCCCKGNNGGNNGK",
    "KRRRQRRRKBBBBcCCCCCCCCCCCCCCcKGNNGGNNGK",
    "KRRQRRRRRKBBBBcCCCCCCCCCCCCcBKGNNNNNNGK",
    ".KKRQRRRRKBBBBBccCCCCCCCCccBBBKGNNNNGK.",
    "...KKQRRRRKBBBBBBccccccccBBBBBKGNNNNGK.",
    ".....KKQRR.KKBBBBBBBBBBBBBBBBKKKGNNGK..",
    ".......KKR...KOOOKKKKKKKKOOOK...KGGK...",
    "............KOOOOOK....KOOOOOK...KK....",
    "............KOKOKOK....KOKOKOK.........",
)

# Head and scarf only. 26 cols x 8 rows.
BUST = (
    "...KK................KK...",
    "..KBBK..KKKKKKKKKK..KBBK..",
    "..KBBBKKBBBBBBBBBBKKBBBK..",
    ".KBBBBBBBBBBBBBBBBBBBBBBK.",
    "KBBBCCCCCCCBBBBCCCCCCCBBBK",
    "KBBCKKKKKCCCCCCCCKKKKKCBBK",
    "KBBKWWWWWKCCCCCCKWWWWWKBBK",
    "KKKKWWEEWKKKKKKKKWWEEWKKKK",
    "KBBKWEEEWKCCOOCCKWEEEWKBBK",
    "KBBKWWWWWKCCOOCCKWWWWWKBBK",
    "KBBCKKKKKCCCRRCCCKKKKKCBBK",
    ".KBCCCCCCCCCCCCCCCCCCCCBK.",
    "KQRRRRRRRRRRRRRRRRRRRRRRQK",
    "KQQRRRRRRRRRRRRRRRRRRRRQQK",
    "KBBBBBcCCCCCCCCCCCCcBBBBBK",
    ".KKKKKKKKKKKKKKKKKKKKKKKK.",
)

# Tiny badge owl. 16 cols x 7 rows.
MINI = (
    "..KK........KK..",
    ".KBBKKKKKKKKBBK.",
    "KBBBBBBBBBBBBBBK",
    "KBKKKBBBBBBKKKBK",
    "KKWEWKKKKKKWEWKK",
    "KKWEWKCOOCKWEWKK",
    "KBKKKCCOOCCKKKBK",
    "KBCCCCCCCCCCCCBK",
    "KQRRRRRRRRRRRRQK",
    ".KBcCCCCCCCCcBK.",
    "..KBcCCCCCCcBK..",
    "...KKKKKKKKKK...",
    "....KOK..KOK....",
)


def _image_protocol() -> str | None:
    """Return "kitty", "iterm", or None if the terminal can't inline an image."""
    if os.environ.get("HEDWIG_NO_IMAGE") or not sys.stdout.isatty():
        return None
    term = os.environ.get("TERM", "")
    term_program = os.environ.get("TERM_PROGRAM", "")
    if term_program == "vscode":
        return None  # mangles both protocols even when it reports kitty/iterm vars
    if "kitty" in term or os.environ.get("KITTY_WINDOW_ID") or term_program == "WezTerm":
        return "kitty"
    if (
        term_program in ("iTerm.app", "WezTerm", "ghostty", "vscode-insiders")
        or os.environ.get("GHOSTTY_RESOURCES_DIR")
        or os.environ.get("ITERM_SESSION_ID")
    ):
        return "iterm"
    return None


def _kitty_escape(data: bytes, columns: int) -> str:
    b64 = base64.b64encode(data).decode("ascii")
    chunks = [b64[i : i + _KITTY_CHUNK] for i in range(0, len(b64), _KITTY_CHUNK)]
    parts = []
    for i, chunk in enumerate(chunks):
        more = 1 if i < len(chunks) - 1 else 0
        control = f"a=T,f=100,c={columns},m={more}" if i == 0 else f"m={more}"
        parts.append(f"\x1b_G{control};{chunk}\x1b\\")
    return "".join(parts)


def _iterm_escape(data: bytes, columns: int) -> str:
    b64 = base64.b64encode(data).decode("ascii")
    return f"\x1b]1337;File=inline=1;width={columns};preserveAspectRatio=1:{b64}\a"


def mascot_image(columns: int = 30) -> str | None:
    """The owl as a terminal inline-image escape sequence, or None if unsupported."""
    protocol = _image_protocol()
    if protocol is None:
        return None
    try:
        data = _MASCOT_PNG.read_bytes()
    except OSError:
        return None
    build = _kitty_escape if protocol == "kitty" else _iterm_escape
    return build(data, columns)


def _pixel_text(art: tuple[str, ...]) -> Text:
    rows = list(art)
    if len(rows) % 2:
        rows.append("." * len(rows[0]))
    text = Text(no_wrap=True)
    for top_row, bottom_row in zip(rows[::2], rows[1::2], strict=True):
        for top, bottom in zip(top_row, bottom_row, strict=True):
            fg, bg = PALETTE.get(top), PALETTE.get(bottom)
            if fg:
                text.append("▀", Style(color=fg, bgcolor=bg))
            elif bg:
                text.append("▄", Style(color=bg))
            else:
                text.append(" ")
        text.append("\n")
    text.rstrip()
    return text


class Mascot:
    """Renders pixel art, or nothing when the output can't encode block characters."""

    def __init__(self, art: tuple[str, ...] = HERO) -> None:
        self.art = art

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        if options.encoding.lower().startswith("utf"):
            yield _pixel_text(self.art)


def mascot(art: tuple[str, ...] = HERO) -> Mascot:
    return Mascot(art)


def banner() -> Text | Table:
    from hedwig import __version__

    title = Text.assemble(
        ("HEDWIG\n", "bold #f5bd2a"),
        ("threat early warning\n", "italic"),
        (f"v{__version__}", "dim"),
    )

    escape = mascot_image()
    if escape is not None:
        sys.stdout.write(escape + "\n")
        sys.stdout.flush()
        return title

    grid = Table.grid(padding=(0, 3))
    grid.add_column()
    grid.add_column(vertical="middle")
    grid.add_row(mascot(), title)
    return grid
