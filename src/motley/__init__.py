"""
Rocking colours. Just like in the 80s...
"""

import textwrap

from . import codes
from .utils import *
from .ansi import *

hue = codes.apply


class ConvenienceFunction(object):
    _doc_tmp = textwrap.dedent(
            """
            %s
            
            Calling this function on a str `s` is equivalent to running:
            >>> codes.apply(s, fg={0!r}, bg={1!r})
            """)

    def __init__(self, fg, bg=None):
        """
        API function for applying ANSI codes to strings
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

        # join effects eg: 'bold_red'
        if isinstance(fg, tuple):
            name = ' '.join(filter(None, fg))

        # make space underscore: eg: 'light cyan'
        self.__name__ = name.replace(' ', '_')
        self.__doc__ = (self._doc_tmp % (doc0 % action)).format(fg, bg)
        #

    def __call__(self, s):
        return codes.apply(s, fg=self.fg, bg=self.bg)


# can also dynamically generate combination fg, bg colour functions
_colours = ('black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan',
            'gray', 'white', None)
_effects = ('bold', 'dim', 'italic', 'underline', 'blink_slow', 'blink_fast',
            'invert', 'hide', 'strike')

for fg, bg in itt.chain(
        itt.product(_colours, _colours),
        itt.product(_effects, (None,)),
        itt.product(itt.product(('bold', 'italic'), _colours + ('italic',)),
                    (None,))):

    if fg == bg:
        # something like red on red is pointless
        continue

    func = ConvenienceFunction(fg, bg)
    # TODO: 'y_on_g'
    exec(f'{func.__name__} = func')

# remove from module namespace
del func
