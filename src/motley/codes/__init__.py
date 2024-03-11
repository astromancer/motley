"""
Handel resolution of named colors and effects
"""


from ..colors import CSS_TO_RGB
from . import bg, fg
from .explain import explain
from .exceptions import InvalidStyle
from ._codes import COLOR_ALIASES, STYLE_ALIASES
from .utils import (AnsiEncodedString, get_split_idx, has_ansi, length,
                    length_codes, length_seen, parse, pull, split, split_iter,
                    strip)
from .resolve import (BG_CODES, CODES, FG_CODES, apply, apply_naive, from_list,
                      get, get_code_list, get_code_str, hex_to_rgb, is_24bit,
                      resolve, to_24bit)


def _make_named_codes(fg_or_bg):
    # this can be used to create the 'fg.py' and 'bg.py' modules which
    # contain named foreground and background colors respectively
    #
    aliases = dict(fg=STYLE_ALIASES)
    # named code strings as module constants
    return {name.replace(' ', '').upper(): get(**{fg_or_bg: name})
            for name in {**CODES[fg_or_bg],
                         **COLOR_ALIASES,
                         **aliases.get(fg_or_bg, {}),
                         **CSS_TO_RGB}
            if name.replace(' ', '').isalpha()}


def _make_module(fg_or_bg):
    from pathlib import Path
    from recipes.containers.dicts import pformat

    #
    (Path(__file__).parent / f'./{fg_or_bg}.py').write_text(
        pformat(_make_named_codes(fg_or_bg),
                lhs=str, rhs=repr,
                equals=' =', sep='', brackets=False,
                hang=True, tabsize=0)
    )
