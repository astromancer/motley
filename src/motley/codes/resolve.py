"""
Does the work to translate colour/effect names to ANSI codes
"""


# std
import numbers
import functools as ftl

# third-party
import numpy as np
import more_itertools as mit

# local
from recipes.dicts import ManyToOneMap
from recipes.string import replace_prefix

# relative
from ..ansi import parse
from ..colors import CSS_TO_RGB
from ._codes import *


# Escape sequence
ESC = '\033'  # All sequences start with this character # equivalent to '\x1b'
CSI = ESC + '['  # Control Sequence Initiator
END = CSI + '0m'


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Movement = {} # TODO


class KeywordResolver(ManyToOneMap):
    """
    Resolve all the various ways in which colours or effects can be specified.
    """
    template = ('{key:r} is not a valid description for a text or '
                'background effect.')

    def __missing__(self, key):
        try:
            return super().__missing__(key)
        except KeyError:
            raise KeyError(self.template.format(key)) from None


class CodeResolver(KeywordResolver):
    """
    Resolve all the various names for colours or effects into ansi codes.
    """
    template = '{key:r} is not a valid colour or effect.'

    def __init__(self, dic=None, **kws):
        super().__init__(dic, **kws)
        # add mappings for matplotlib color names eg: 'r' --> 'red' etc..
        self.add_mapping(colorAliasMap)
        # add a layer that maps to lower case: 'REd' --> 'red'
        self.add_func(str.lower)
        # add light -> bright translation
        # self.add_func(ftl.partial(replace_prefix, old='bright', new='light'))

    def __getitem__(self, key):
        # make sure we always return a str
        return str(super().__getitem__(key))


# additional shorthands for bold / italic text
BG_CODES = CodeResolver(BG_CODES)
FG_CODES = CodeResolver(FG_CODES)
FG_CODES.add_mapping(effectAliasMap)


# Keyword Translator
CODES = KeywordResolver(fg=FG_CODES,
                        bg=BG_CODES)
# alias map for allowed keywords for functions
CODES.many_to_one({
    ('highlight', 'background', 'bg', 'bc', 'bgc'):                     'bg',
    ('text', 'txt', 'colour', 'color', 'c', 'fg', 'foreground', 'rgb'): 'fg'
})

FORMAT_8BIT = KeywordResolver(fg='38;5;{:d}',
                              bg='48;5;{:d}')
FORMAT_24BIT = KeywordResolver(fg='38;2;{:d};{:d};{:d}',
                               bg='48;2;{:d};{:d};{:d}')
COLOR_FORMATTERS = {8:  FORMAT_8BIT,
                    24: FORMAT_24BIT}


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Dispatch functions for translating user input to ANSI codes


class InvalidEffect(Exception):
    """
    Raised when a user input object cannot be resolved to a code for colour or 
    effect.
    """

    def __init__(self, obj, fg_or_bg):
        super().__init__(
            (f'Could not interpret object {obj!r} of type {type(obj)!r} as a '
             f'valid colour or effect for {fg_or_bg!r}')
        )


@ftl.singledispatch
def resolve(obj, fg_or_bg='fg'):
    """default dispatch func for resolving ANSI codes from user input"""
    raise InvalidEffect(obj, fg_or_bg)


@resolve.register(type(None))
def _(obj, fg_or_bg='fg'):
    return
    yield  # sourcery skip: remove-unreachable-code #pylint: disable=unreachable


@resolve.register(str)
def _(obj, fg_or_bg='fg'):
    if obj == '':
        return

    # resolve hex / html / css colours
    if obj.startswith('#'):
        yield hex_to_rgb(obj)
        return

    # try resolve as a named color / effect
    value = CODES[fg_or_bg].get(obj, None)
    if value:
        yield value
        return

    # try resolve as a named CSS color
    value = CSS_TO_RGB.get(obj, None)
    if value:
        yield COLOR_FORMATTERS[24][fg_or_bg].format(*value)
        return

    raise InvalidEffect(obj, fg_or_bg)


@resolve.register(numbers.Integral)
def _(obj, fg_or_bg='fg'):
    # integers are interpreted as 8-bit colour codes
    if 0 <= obj < 256:
        yield COLOR_FORMATTERS[8][fg_or_bg].format(obj)
    else:
        raise ValueError(f'Could not interpret key {obj!r} as a 8 bit colour.')


@resolve.register(np.ndarray)
@resolve.register(list)
@resolve.register(tuple)
def _(obj, fg_or_bg='fg'):
    # tuple, lists are interpreted as 24-bit rgb colour codes
    if is_24bit(obj):
        if all(0 <= _ < 256 for _ in obj):
            yield COLOR_FORMATTERS[24][fg_or_bg].format(*obj)
        else:
            raise ValueError(
                f'Could not interpret key {obj!r} as a 24 bit colour.'
            )
    else:
        for p in obj:
            yield from resolve(p, fg_or_bg)


@resolve.register(dict)
def _(obj, _=''):
    for key, val in obj.items():
        # `val` may have tuple of effects: eg: ((55, 55, 55), 'bold', 'italic')
        # but may also be a rgb tuple eg: (55, 55, 55)
        yield from resolve(val, key)


def is_24bit(obj):
    if len(obj) != 3:
        return False

    return all(isinstance(o, numbers.Integral) for o in obj)


# def to_24bit(name):
#     #
#     return tuple((np.multiply(to_rgb(name), 255).astype(int)))

# to_rgb = to_24bit


def hex_to_rgb(value):
    """#000080 -> (0, 0, 128)"""
    value = value.lstrip('#')
    size = len(value)
    assert size in {3, 6}
    return tuple(int(bit, 16) for bit in mit.sliced(value, size // 3))


def _iter_codes(*effects, **kws):
    """

    Parameters
    ----------
    effects
    kws

    Yields
    -------
    code: int
    """

    yield from resolve(effects)
    yield from resolve(kws)


def get_code_list(*effects, **kws):
    return list(_iter_codes(*effects, **kws))


def get_code_str(*effects, **kws):
    # get the semi-colon separated integers as a string: eg '34;48;5;22'
    return ';'.join(_iter_codes(*effects, **kws))


def get(*effects, **kws):
    """
    Get the ANSI code for `effects` and `kws`

    Parameters
    ----------
    effects:
    kws:

    Returns
    -------

    """
    return ''.join((CSI, get_code_str(*effects, **kws), 'm'))


def from_list(fg=None, bg=None):
    """Vectorized code resolution."""

    if fg is not None:
        return list(map(get, fg))

    if bg is not None:
        return [get(bg=_) for _ in bg]


def apply(s, *effects, **kws):
    """
    Apply the ANSI codes mapped to by `effects` and `kws` to the string `s`

    Parameters
    ----------
    s
    effects
    kws

    Returns
    -------

    """
    # first convert to str
    # string = str(s)

    # get code bits eg: '34;48;5;22'
    new_codes = get_code_str(*effects, **kws)
    if not new_codes:
        return s

    # In order to get the correct representation of the string, we strip and
    # ANSI codes that are in place and stack the new codes This means previous
    # colours are replaced, but effects like 'bold' or 'italic' will stack for
    # recursive invocations of this function.  This also means we get the
    # shortest possible representation of the string given the parameters which
    # is nice and efficient. If we were to apply blindly our string would be
    # longer than needed by a few (non-display) characters. This might seem
    # innocuous but becomes important once you start doing more complicated
    # effects on longer strings.

    # NOTE: final byte 'm' only valid for SGR (Select Graphic Rendition) and not
    # other codes, but this is all we support for now

    return ''.join(f'{CSI}{params};{new_codes}m{w}{END}'
                   for _, params, _, w, _ in parse(s))


def apply_naive(s, *effects, **kws):
    """
    Initial naive implementation of `apply` that blindly wraps the string with
    the ANSI codes.  Use `apply` instead of this function.
    """

    # get code string eg: '34;48;5;22'
    code = get(*effects, **kws)
    if not code:
        return s

    return ''.join((code, s, END))
