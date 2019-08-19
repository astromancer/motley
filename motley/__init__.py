"""
Rocking colours. Just like in the 80s...
"""

import textwrap
import itertools as itt

from . import codes
from .codes import apply as hue
from .utils import *


class ConvenienceFunction(object):
    _doc_tmp = textwrap.dedent(
            """
            %s
            
            Calling this function on a str `s` is equivalent to running:
            >>> codes.apply(s, fg={0!r}, bg={1!r})
            """)

    def __init__(self, fg, bg):
        """
        Api function for applying ANSI codes to strings
        """

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

        # make space underscore: eg: 'light cyan'
        self.__name__ = name.replace(' ', '_')
        self.__doc__ = (self._doc_tmp % (doc0 % action)).format(fg, bg)
        #

    def __call__(self, s):
        return codes.apply(s, fg=self.fg, bg=self.bg)


# can also dynamically generate combination fg, bg colour functions
_colour_names = (
    'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'gray', None)
for fg, bg in itt.product(_colour_names, _colour_names):
    if fg == bg:
        # something like red on red is pointless
        continue

    func = ConvenienceFunction(fg, bg)
    exec(f'{func.__name__} = func')
