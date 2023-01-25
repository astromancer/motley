"""
Handel resolution of named colors and effects
"""

from .resolve import *
from .utils import *
from . import fg, bg


def _make_named_codes(fg_or_bg):
    # this can be used to create the 'fg.py' and 'bg.py' modules which
    # contain named foreground and background colors respectively
    #
    aliases = dict(fg=effectAliasMap)
    # named code strings as module constants
    return {name.replace(' ', '').upper(): get(**{fg_or_bg: name})
            for name in {**CODES[fg_or_bg],
                         **colorAliasMap,
                         **aliases.get(fg_or_bg, {}),
                         **CSS_TO_RGB}
            if name.replace(' ', '').isalpha()}


def _make_module(fg_or_bg):
    from pathlib import Path
    from recipes.dicts import pformat

    (Path(__file__).parent / f'./{fg_or_bg}.py').write_text(
        pformat(_make_named_codes(fg_or_bg),
                lhs=str, rhs=repr,
                equals=' =', sep='', brackets=False,
                hang=True, tabsize=0)
    )
