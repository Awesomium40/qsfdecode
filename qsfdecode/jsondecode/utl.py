from itertools import zip_longest
from typing import Iterable

__all__ = ['chunk']


def chunk(it: Iterable, n: int) -> Iterable:
    marker = object()
    for group in (list(g) for g in zip_longest(*[iter(it)] * n, fillvalue=marker)):
        if group[-1] is marker:
            del group[group.index(marker):]
        yield group


def tab(n: int = 1) -> str:
    return "    " * n
