"""
Rocking colours. Just like in the 80s...
"""

import textwrap
import itertools as itt

from . import codes
from .codes import apply as hue
from .utils import *


def _functionFactory(fg, bg):
    """
    Creates source code for convenience functions

    """
    # prefix = ''
    # if bg:
    #     # will prefix all functions refering to the background with 'bg_'.
    #     # eg: `bg_red`
    #     prefix = 'bg_'

    if None in (fg, bg):
        if bg is None:
            fname = fg
        if fg is None:
            fname = 'bg_%s' % bg
    else:
        fname = '%s_on_%s' % (fg, bg)
    # make space underscore
    fname = fname.replace(' ', '_')

    template = \
        """
        def {0:s}(s):
            return codes.apply(s, fg={1!r}, bg={2!r})
        """

    source = textwrap.dedent(template).format(fname, fg, bg)
    return source


# dynamically generate some convenience functions based on colour code names
for name in codes.fgCodes:
    exec(_functionFactory(name, None))

for name in codes.bgCodes:
    exec(_functionFactory(None, name))

# can also dynamically generate combination fg, bg colour functions
_colour_names = (
    'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'gray')
for _ in itt.combinations(_colour_names, 2):
    exec(_functionFactory(*_))
