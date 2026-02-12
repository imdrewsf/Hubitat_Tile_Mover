from __future__ import annotations

from typing import Tuple


def ranges_overlap(a1: int, a2: int, b1: int, b2: int) -> bool:
    return not (a2 < b1 or b2 < a1)


def rects_overlap(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> bool:
    ar1, ar2, ac1, ac2 = a
    br1, br2, bc1, bc2 = b
    return ranges_overlap(ar1, ar2, br1, br2) and ranges_overlap(ac1, ac2, bc1, bc2)
