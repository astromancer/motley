"""
Tools for recognising and stripping ANSI codes
"""

import re
from more_itertools import pairwise

pattern = '\033\[[\d;]*[a-zA-Z]'
matcher = re.compile(pattern)


def has_ansi(s):
    return not matcher.search(s) is None


def strip(s):
    """strip ansi codes from str"""
    return matcher.sub('', s)


def pull(s):
    """extract ansi codes from str"""
    return matcher.findall(s)


def split(s):
    """split str at ansi code locations"""
    idxs = []
    for i, match in enumerate(s.matcher.finditer(s)):
        idxs += [match.start(), match.end()]

    if not len(idxs):
        return [s]

    if idxs[0] != 0:
        idxs = [0] + idxs
    if idxs[-1] != len(s):
        idxs += [len(s)]

    parsed = [s[i0:i1] for i0, i1 in pairwise(idxs)]
    return parsed


def length(s, raw=True):
    """Length of the string, either raw, or as it would be displayed."""
    if raw:
        return len(s)
    return length_raw(s)


def length_codes(s):
    """length of the ansi escape sequences in the str"""
    return sum(map(len, pull(s)))


def length_raw(s):
    """
    length of the string as it would be displayed on screen
    i.e. all ansi codes resolved / removed
    """
    return len(strip(s))
