"""
Does the work to translate colour/effect names to ANSI codes
"""
import warnings

import more_itertools as mit

from recipes.dict import Many2OneMap

# source: https://en.wikipedia.org/wiki/ANSI_escape_code
# http://ascii-table.com/ansi-escape-sequences.php

# Escape sequence
ESC = '\033'  # All sequences start with this character
CSI = ESC + '['  # Control Sequence Initiator
END = CSI + '0m'

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ANSI Codes for Text effects and colours
fgCodes = {
    'bold': 1,
    'dim': 2,  # faint
    'italic': 3,
    'underline': 4,
    'blink': 5,  # blink slow
    # 'blink' : 6,           # blink fast
    'invert': 7,
    'hidden': 8,  # conceal
    'strikethrough': 9,
    # ------------------
    # 10	Primary(default) font
    # 11–19	{\displaystyle n} n-th alternate font	Select the {\displaystyle n} n-th alternate font (14 being the fourth alternate font, up to 19 being the 9th alternate font).
    # 20	Fraktur	hardly ever supported
    # 21	Bold: off or Underline: Double	Bold off not widely supported; double underline hardly ever supported.
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
    # 38	Reserved for extended set foreground color	typical supported next arguments are 5;n where {\displaystyle n}￼ is color index (0..255) or 2;r;g;b where {\displaystyle r,g,b}￼ are red, green and blue color channels (out of 255)
    'default': 39,  # Default text color (foreground)
    # ------------------
    'frame': 51,
    'circle': 52,
    'overline': 53,
    # 54	Not framed or encircled
    # 55	Not overlined
    # ------------------
    'dark gray': 90,
    'gray' : 90,
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
bgCodes = {
    'default': 49,
    'black': 40,
    'red': 41,
    'green': 42,
    'yellow': 43,
    'blue': 44,
    'magenta': 45,
    'cyan': 46,
    'light gray': 47,
    # ------------------
    # 48	Reserved for extended set background color	typical supported next arguments are 5;n where {\displaystyle n}￼ is color index (0..255) or 2;r;g;b where {\displaystyle r,g,b}￼ are red, green and blue color channels (out of 255)
    # 49	Default background color	implementation defined (according to standard)
    # 50	Reserved
    # ------------------
    # 56–59	Reserved
    # 60	ideogram underline or right side line	hardly ever supported
    # 61	ideogram double underline or double line on the right side	hardly ever supported
    # 62	ideogram overline or left side line	hardly ever supported
    # 63	ideogram double overline or double line on the left side	hardly ever supported
    # 64	ideogram stress marking	hardly ever supported
    # 65	ideogram attributes off	hardly ever supported, reset the effects of all of 60–64
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

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Convenient short colour descriptions a la matplotlib
mplShorthands = {
    'b': 'blue',
    'g': 'green',
    'r': 'red',
    'c': 'cyan',
    'm': 'magenta',
    'y': 'yellow',
    'k': 'black',
    'w': 'white',
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# alias map for allowed keywords for functions
aliasMap = {
    'text': 'fg',
    'txt': 'fg',
    'colour': 'fg',
    'color': 'fg',
    'c': 'fg',
    'fg': 'fg',
    'foreground': 'fg',
    'background': 'bg',
    'bg': 'bg',
    'bc': 'bg',
    'bgc': 'bg',
}


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Movement = {} # TODO


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _aliasFactory(codes, aliases):
    """Create the code translation dict"""
    Codes = Many2OneMap(codes)
    Codes.add_vocab(aliases)
    Codes.add_map(str.lower)
    return Codes


class KeyResolver(Many2OneMap):
    """
    Resolve all the various ways in which colours or effects can be specified.
    """

    def __init__(self, dic=None, **kws):
        super().__init__(dic, **kws)
        self.add_vocab(aliasMap)  # translation

    def __missing__(self, key):
        try:
            return super().__missing__(key)
        except KeyError as e:
            pass
        raise KeyError('%r is not a valid property description' % key)


class CodeResolver(Many2OneMap):
    """
    Resolve all the various names for colours or effects into codes
    """
    fmt = '{}'

    def __init__(self, dic=None, **kws):
        super().__init__(dic, **kws)
        # add mappings for matplotlib color names
        self.add_vocab(mplShorthands)
        # add a layer that maps to lower case: REd --> red
        self.add_map(str.lower)

    def __getitem__(self, key):
        # make sure we always return a str
        return str(super().__getitem__(key))

    # class Format256Mixin(CodeResolver):
    def __missing__(self, key):
        try:
            # fromat 256 colour spec
            if str(key).isdigit():
                if int(key) <= 256:
                    return self.fmt.format(key)
                else:
                    raise KeyError('Only 256 colours available.')

            # if not 256 colours resolve at parent
            return super().__missing__(key)
        except KeyError as e:
            raise KeyError('Unknown property %r' % key)


class FGResolver(CodeResolver):
    fmt = '38;5;{}'


class BGResolver(CodeResolver):
    fmt = '48;5;{}'


resolver = KeyResolver(fg=FGResolver(fgCodes),
                       bg=BGResolver(bgCodes))
resolver.fg = resolver['fg']
resolver.bg = resolver['bg']


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# 24bit (3-byte) true color support
# TODO
# NOTE:  Gnome Terminal 24bit support is enabled by default but gnome-terminal
#       has to be in version linked against libvte >= 0.36
#       see: http://askubuntu.com/questions/512525/how-to-enable-24bit-true-color-support-in-gnome-terminal
# TODO


def apply(s, *properties, **kws):
    """
    set the ANSI codes for a string given the properties and kws descriptors
    """

    # first convert to str
    string = str(s)

    # get code string eg: '34;48;5;22'
    code = get_codes(*properties, **kws)
    if not len(code):
        return string

    # still missing END code at this point
    # note `string` may already have previous ANSI codes.
    n_ends = string.count(END)
    if n_ends:
        # next line ensures new ansi code applied across existing ansi code.
        # May overwrite previous colours, but will stack effects like 'bold'
        # or 'italic' for recursive invocations
        string = string.replace(END, END + code, n_ends)

    return code + string + END

# apply = hue


def _gen_codes(*properties, **kws):
    """

    Parameters
    ----------
    properties
    kws

    Returns
    -------

    """

    # flatten nested properties except if dict
    # filter meaningless descriptions like: '' or None
    for p in filter(None, mit.collapse(properties, dict)):
        if isinstance(p, dict):
            twice = set(kws.keys()) - set(p.keys())
            if len(twice):
                warnings.warn('Multiple values received for properties %s.' %
                              twice)
            kws.update(p)
        else:
            yield resolver.fg[p]

    for fg_or_bg, pkw in kws.items():
        for p in filter(None, mit.collapse(pkw)):
            yield resolver[fg_or_bg][p]


# def get_codes(*properties, **kws):
#     return list(_gen_codes(*properties, **kws))


def get_codes(*properties, **kws):
    """

    Parameters
    ----------
    properties:
    kws:

    Returns
    -------

    """
    codes = _gen_codes(*properties, **kws)
    # codes = list(codes)

    cs = ';'.join(codes)
    if len(cs):
        return '{}{}m'.format(CSI, cs)
    # if no properties given, we have an empty string here
    return ''


# def _gen_codes(*properties, **kws):
#     """
#     Get ANSI code given the properties and kws descriptors.
#     properties      - foreground (text) colour(s) and/or effect(s)
#     kws             -
#     """
#     # detect if properties is nested tuple of properties. ie. handle use case
#     # `props = ('italic', 144); codes.apply('yo', props)`
#     #
#     if len(properties) == 1:
#         properties0 = properties[0]
#         if isinstance(properties0, (tuple, list)):
#             properties = properties0
#             # yield from _gen_codes(*properties0)  # recur
#         if isinstance(properties0, dict):
#             # use case: `codes.apply(dict(fg='blue'))`
#             kws.update(properties0)
#             properties = ()
#
#     # filter meaningless descriptions like: '' or None
#     properties = tuple(filter(None, properties))
#     no_props = (len(properties) == 0)
#     if no_props and not kws:
#         return
#     #
#     # everything in `properties` assumed referring to foreground
#     yield from map(get_code, properties)
#
#     # next handle kws: eg. `hue(s, bg='b')
#     for fg_or_bg, properties in kws.items():
#
#         for prop in filter(None, properties):
#             yield get_code(prop, fg_or_bg)

# if isinstance(properties, str):
#     if len(properties.strip()) == 0:
#         continue    # empty string. ignore
#     properties = properties,
#
# if isinstance(properties, int):
#     properties = properties,
#
# for prop in filter(None, properties):
#     yield get_code(prop, fg_or_bg)


#
# def get_fg_code(prop):
#     return get_code(prop)

# def _get_codes_tuple(*properties, **kws):
#     return tuple(_gen_codes(*properties, **kws))


if __name__ == '__main__':
    # Demo 256 colours
    bg256 = (apply('{0:<10}'.format(i), bg=i) for i in range(256))
    print(''.join(bg256))

    # TODO: print pretty things:
    # http://misc.flogisoft.com/bash/tip_colors_and_formatting
    # http://askubuntu.com/questions/512525/how-to-enable-24bit-true-color-support-in-gnome-terminal
    # https://github.com/robertknight/konsole/blob/master/tests/color-spaces.pl

    # TODO: unit tests!!
