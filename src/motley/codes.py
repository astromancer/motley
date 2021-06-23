"""
Does the work to translate colour/effect names to ANSI codes
"""


# std libs
import numbers
import functools as ftl

# third-party libs
import numpy as np
from matplotlib.colors import to_rgb

# local libs
from recipes.dicts import ManyToOneMap

# relative libs
from .ansi import parse


# source: https://en.wikipedia.org/wiki/ANSI_escape_code
# http://ascii-table.com/ansi-escape-sequences.php

# Escape sequence
ESC = '\033'  # All sequences start with this character # equivalent to \x1b
CSI = ESC + '['  # Control Sequence Initiator
END = CSI + '0m'

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ANSI Codes for Text effects and colours  FG_CODES BG_CODE
FG_CODES = {
    'bold': 1,
    'dim': 2,  # faint
    'italic': 3,
    'underline': 4,
    'blink': 5,  # blink slow
    # 'blink' : 6,           # blink fast
    'invert': 7,
    'hidden': 8,  # conceal
    'strike': 9,
    # ------------------
    # 10	Primary(default) font
    # 11–19	{\displaystyle n} n-th alternate font	Select the {\displaystyle n}
    # n-th alternate font (14 being the fourth alternate font, up to 19 being
    # the 9th alternate font).
    # 20	Fraktur	hardly ever supported
    # 21	Bold: off or Underline: Double	Bold off not widely supported;
    # double underline hardly ever supported.
    # 22	Normal color or intensity	Neither bold nor faint
    # 23	Not italic, not Fraktur
    # 24	Underline: None	Not singly or doubly underlined
    # 25	Blink: off
    # 26	Reserved
    # 27	Image: Positive
    # 28	Reveal  conceal off
    # 29	Not crossed out
    # ------------------
    'black': 30,
    'red': 31,
    'green': 32,
    'yellow': 33,
    'blue': 34,
    'magenta': 35,
    'cyan': 36,
    'light gray': 37,
    # 38	Reserved for extended set foreground color typical supported next
    # arguments are 5;n where {\displaystyle n}￼ is color index (0..255) or
    # 2;r;g;b where {\displaystyle r,g,b}￼ are red, green and blue color
    # channels (out of 255)
    'default': 39,  # Default text color (foreground)
    # ------------------
    'frame': 51,
    'circle': 52,
    'overline': 53,
    # 54	Not framed or encircled
    # 55	Not overlined
    # ------------------
    'dark gray': 90,
    'gray': 90,
    'light red': 91,
    'light green': 92,
    'light yellow': 93,
    'light blue': 94,
    'light magenta': 95,
    'light cyan': 96,
    'white': 97,
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Background Colours
BG_CODES = {
    'black': 40,
    'red': 41,
    'green': 42,
    'yellow': 43,
    'blue': 44,
    'magenta': 45,
    'cyan': 46,
    'light gray': 47,
    # ------------------
    # 48	Reserved for extended set background color	typical supported next
    # arguments are 5;n where {\displaystyle n}￼ is color index (0..255) or
    # 2;r;g;b where {\displaystyle r,g,b}￼ are red, green and blue color
    # channels (out of 255)
    'default': 49,
    # 49	Default background color	implementation defined (according to
    # standard)
    # 50	Reserved
    # ------------------
    # 56–59	Reserved
    # 60	ideogram underline or right side line	hardly ever supported
    # 61	ideogram double underline or double line on the right side	hardly
    # ever supported
    # 62	ideogram overline or left side line	hardly ever supported
    # 63	ideogram double overline or double line on the left side
    # hardly ever supported
    # 64	ideogram stress marking	hardly ever supported
    # 65	ideogram attributes off	hardly ever supported, reset the effects of
    # all of 60–64
    # ------------------
    'dark gray': 100,
    'light red': 101,
    'light green': 102,
    'light yellow': 103,
    'light blue': 104,
    'light magenta': 105,
    'light cyan': 106,
    'white': 107,
}
# TODO: alternate colour names here: https://en.wikipedia.org/wiki/ANSI_escape_code

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Convenient short colour descriptions a la matplotlib
mplShortsMap = {
    'b': 'blue',
    'g': 'green',
    'r': 'red',
    'c': 'cyan',
    'm': 'magenta',
    'y': 'yellow',
    'k': 'black',
    'w': 'white',
}

#
effectShortsMap = {'B': 'bold',
                   'I': 'italic',
                   'U': 'underline',
                   'S': 'strike',
                   'unbold': 'dim',
                   'strikethrough': 'strike',
                   'blink': 'blink_slow',
                   'hide': 'hidden',
                   'faint': 'dim'
                   }
# volcab is translated before keyword mappings in Many2One, so the uppercase
# here works

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# alias map for allowed keywords for functions
kwAliasMap = {
    # text
    'text': 'fg',
    'txt': 'fg',
    'colour': 'fg',
    'color': 'fg',
    'c': 'fg',
    'fg': 'fg',
    'foreground': 'fg',
    'rgb': 'fg',
    # background
    'highlight': 'bg',
    'background': 'bg',
    'bg': 'bg',
    'bc': 'bg',
    'bgc': 'bg'
}


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Movement = {} # TODO


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# def _aliasFactory(codes, aliases):
#     """Create the code translation dict"""
#     Codes = ManyToOneMap(codes)
#     Codes.add_vocab(aliases)
#     Codes.add_map(str.lower)
#     return Codes


class KeyMap(ManyToOneMap):
    """
    Resolve all the various ways in which colours or effects can be specified.
    """

    def __init__(self, dic=None, **kws):
        super().__init__(dic, **kws)
        self.add_vocab(kwAliasMap)  # translation

    def __missing__(self, key):
        try:
            return super().__missing__(key)
        except KeyError:
            pass
        raise KeyError(
            f'{key} is not a valid description for text or background effect.')


class CodeMap(ManyToOneMap):  # CodeMap
    """
    Resolve all the various names for colours or effects into codes
    """

    # def __init__(self, dic=None, **kws):
    #     super().__init__(dic, **kws)
    # add mappings for matplotlib color names eg: 'r' --> 'red' etc..
    # self.add_vocab(mplShortsMap)
    # add a layer that maps to lower case: 'REd' --> 'red'
    # self.add_mapping(str.lower)

    def __getitem__(self, key):
        # make sure we always return a str
        return str(super().__getitem__(key))

    def __missing__(self, key):
        try:
            return super().__missing__(key)
        except KeyError:
            raise KeyError(f'Unknown colour or effect {key!r}') from None


# additional shorthands for bold / italic text
fg_codes = CodeMap(FG_CODES)
fg_codes.add_vocab(effectShortsMap)

codes = KeyMap(fg=fg_codes,
               bg=CodeMap(BG_CODES))

FORMAT_8BIT = KeyMap(fg='38;5;{:d}',
                     bg='48;5;{:d}')
FORMAT_24BIT = KeyMap(fg='38;2;{:d};{:d};{:d}',
                      bg='48;2;{:d};{:d};{:d}')

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Dispatch functions for translating user input to ANSI codes


@ftl.singledispatch
def resolve(obj, fg_or_bg='fg'):
    """default dispatch func for resolving ANSI codes from user input"""
    raise TypeError('Could not interpret %r (type %r) as a colour / effect '
                    'for %r' % (obj, type(obj), fg_or_bg))


# TODO: might want to give the functions below names for more readable traceback

@resolve.register(type(None))
def _(obj, fg_or_bg='fg'):
    return
    yield


@resolve.register(str)
def _(obj, fg_or_bg='fg'):
    if obj == '':
        return

    try:
        yield from resolve(to_24bit(obj), fg_or_bg)
    except ValueError:
        yield codes[fg_or_bg][obj]


@resolve.register(numbers.Integral)
def _(obj, fg_or_bg='fg'):
    # integers are interpreted as 8-bit colour codes
    if 0 <= obj < 256:
        yield FORMAT_8BIT[fg_or_bg].format(obj)
    else:
        raise ValueError('Could not interpret key %r as a 8 bit colour' % obj)


@resolve.register(np.ndarray)
@resolve.register(list)
@resolve.register(tuple)
def _(obj, fg_or_bg='fg'):
    # tuple, lists are interpreted as 24-bit rgb true colour codes
    if is_24bit(obj):
        if all(0 <= _ < 256 for _ in obj):
            yield FORMAT_24BIT[fg_or_bg].format(*obj)
        else:
            raise ValueError(
                f'Could not interpret key {obj!r} as a 24 bit colour'
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


def to_24bit(name):
    return tuple((np.multiply(to_rgb(name), 255).astype(int)))


def _gen_codes(*properties, **kws):
    """

    Parameters
    ----------
    properties
    kws

    Yields
    -------
    code: int
    """

    yield from resolve(properties)
    yield from resolve(kws)


def _get_params(*properties, **kws):
    # get the nrs '34;48;5;22' part of the code
    return ';'.join(_gen_codes(*properties, **kws))


def get(*properties, **kws):
    """
    Get the ANSI code for `properties` and `kws`

    Parameters
    ----------
    properties:
    kws:

    Returns
    -------

    """
    return ''.join((CSI, _get_params(*properties, **kws), 'm'))


def from_list(fg=None, bg=None):
    if fg is not None:
        return list(map(get, fg))

    if bg is not None:
        return [get(bg=_) for _ in bg]


def apply(s, *properties, **kws):
    """
    Apply the ANSI codes mapped to by `properties` and `kws` to the string `s`

    Parameters
    ----------
    s
    properties
    kws

    Returns
    -------

    """
    # first convert to str
    # string = str(s)

    # get code bits eg: '34;48;5;22'
    new_codes = _get_params(*properties, **kws)
    if not len(new_codes):
        return s

    # In order to get the correct representation of the string,
    # we strip and ANSI codes that are in place and stack the new codes
    # This means previous colours are replaced, but effects like 'bold' or
    # 'italic' will stack for recursive invocations.  This also means we get
    # the shortest representation of the string given the parameters which is
    # nice and efficient. If we were to apply blindly our string would be
    # longer than needed by a few (non-display) characters. This might seem
    # innocuous but becomes deadly once you start doing more complicated
    # effects on longer strings
    # note: final byte 'm' only valid for SGR (Select Graphic Rendition) and
    #  not other codes, but this is all we support for now

    return ''.join(''.join((CSI, params, ';', new_codes, 'm', w, END))
                   for _, params, _, w, _ in parse(s)
                   )  # .replace('\n', f'{END}\n{CSI}{new_codes}m'
    #
    # Finally, terminate and restart all codes at a newline boundary so that
    # we can more easily stack text blocks horizontally


def apply_naive(s, *properties, **kws):
    """
    Initial naive implementation of `apply` that blindly wraps the string with
    the ANSI codes.  Use `apply` instead of this function.
    """

    # get code string eg: '34;48;5;22'
    code = get(*properties, **kws)
    if not len(code):
        return s

    return ''.join((code, s, END))
