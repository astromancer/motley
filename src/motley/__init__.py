"""
Rocking colours. Just like in the 80s...
"""

# pylint: disable=redefined-builtin

# std
import sys
import textwrap
import itertools as itt

# third-party
from loguru import logger

# relative
from . import codes, colors
from .utils import *
from .string import Str
from .formatter import format, format_partial, stylize


# ---------------------------------------------------------------------------- #
logger.disable('motley')


# aliases
apply = hue = codes.apply
# ---------------------------------------------------------------------------- #


class ConvenienceFunction:
    """
    API function for applying ANSI codes to strings.
    """

    # pylint: disable=trailing-whitespace
    _doc_tmp = textwrap.dedent(
        """
        %s
        
        Calling this function on a str `s` is equivalent to running:
        >>> codes.apply(s, fg={0!r}, bg={1!r})
        """
    )

    def __init__(self, fg, bg=None):

        # postfix = 'bg'
        # will postfix all functions referring to the background with '_bg'.
        # eg: `red_bg`

        # get function name / docstring
        doc0 = '%s the text `s` '
        action = 'Make'
        if bg:
            if fg:
                doc0 += '{0!r} with'
                name = f'{fg}_on_{bg}'
            else:
                action = 'Give'
                name = f'{bg}_bg'
            doc0 += ' a {1!r} background.'
        elif fg:
            doc0 += '{0!r}.'
            name = fg
        else:
            raise ValueError

        #
        self.fg = fg
        self.bg = bg

        # join effects eg: 'bold_red'
        if isinstance(fg, tuple):
            name = ' '.join(filter(None, fg))

        # make space underscore: eg: 'light cyan'
        self.__name__ = name.replace(' ', '_')
        self.__doc__ = (self._doc_tmp % (doc0 % action)).format(fg, bg)
        #

    def __call__(self, s):
        # temptation here would be to pre-resolve codes, however this prevents
        # stacking effects appropriately
        return codes.apply(s, fg=self.fg, bg=self.bg)


def _eq(pair):
    # filter `red_on_red` etc `bold_bold` etc.
    return (object.__eq__(*pair) is not True)


def _product(*items):
    yield from filter(_eq, itt.product(*items))


def _combos():
    # can also dynamically generate combination fg, bg colour functions

    _fgc = [None, *codes._codes._fg_colours]
    _bgc = [None, *codes.BG_CODES]
    _shorts = [None, *codes.color_alias_map.keys()]
    yield from itt.chain(
        # simple text effects eg: `underline`, `red` ...
        _product(codes.FG_CODES, [None]),
        # `red_on_green` etc
        _product(_fgc, _bgc),
        # `r_on_g` etc
        _product(_shorts, _shorts),
        # `italic_blue`, `bold_red` ...
        itt.zip_longest(_product(('bold', 'italic'), (*_fgc, 'italic')), ()),
        # CSS foreground colours
        _product(colors.CSS_TO_RGB, [None]),
    )


def _make_funcs():
    for fg, bg in _combos():
        func = ConvenienceFunction(fg, bg)
        setattr(sys.modules[__name__], func.__name__, func)


# create convenience functions
_make_funcs()  # this keeps the namespace clean of "fg", "bg", "func"
