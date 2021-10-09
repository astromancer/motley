"""
Rocking colours. Just like in the 80s...
"""

# std
import sys
import textwrap
import itertools as itt

# third-party
from loguru import logger

# relative
from . import codes, image
from .ansi import *
from .utils import *
from .string import Str
from .codes import fg, bg
from .formatter import format, stylize, format_partial


#
logger.disable('motley')

# aliases
apply = hue = codes.apply


class ConvenienceFunction:
    """
    API function for applying ANSI codes to strings
    """
    # # pylint: disable=trailing-whitespace
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
        doc0 = '%s the string `s` '
        action = 'Make'
        if bg:
            if fg:
                doc0 += '{0!r} with'
                name = '%s_on_%s' % (fg, bg)
            else:
                action = 'Give'
                name = '%s_bg' % bg
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
        # TODO: optimization here would be to pre-resolve codes
        return codes.apply(s, fg=self.fg, bg=self.bg)


def _combos():
    # TODO: 'y_on_g'

    # can also dynamically generate combination fg, bg colour functions
    _colours = ('black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan',
                'gray', 'white', None)
    _effects = ('bold', 'dim', 'italic', 'underline', 'blink_slow',
                'blink_fast', 'invert', 'hide', 'strike')

    for fg, bg in itt.chain(
            # simple text effects eg: `underline`, `red` ...
            itt.product(_effects, [None]),
            # `red_on_green` etc
            itt.product(_colours, _colours)
    ):
        if fg == bg:
            # filter `red_on_red` etc
            continue

        yield fg, bg

    # `italic_blue`, `bold_red` ...
    for fg in itt.product(('bold', 'italic'), (*_colours, 'italic')):
        if fg[0] != fg[1]:
            # filter `bold_bold` etc.
            yield fg, None


def _make_funcs():
    for fg, bg in _combos():
        func = ConvenienceFunction(fg, bg)
        thismodule = sys.modules[__name__]
        setattr(thismodule, func.__name__, func)


# create convenience functions
_make_funcs()
