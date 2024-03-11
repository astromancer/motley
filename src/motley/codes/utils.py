"""
Tools for recognising and manipulating strings containing ANSI codes.
"""

# std
import re

# third-party
import more_itertools as mit

# local
from recipes import op
from recipes.functionals import echo
from recipes.oo.slots import SlotHelper


__all__ = [
    'has_ansi', 'strip', 'pull', 'parse', 'split', 'length', 'length_codes',
    'length_seen'
]

# ---------------------------------------------------------------------------- #
# Regexes for parsing

# REGEXES = ConfigNode(
#     # Any valid ANSI code pattern
#     ansi=re.compile(r'''(?x)
#         (?P<csi>\x1b\[)             # Control Sequence Introducer   eg: '\x1b['
#         (?P<params>[\d;]*)          # Parameters                    eg: '31;1;43'
#         (?P<final_byte>[a-zA-Z])    # Final byte in code            eg: 'm'
#     '''),

#     # Any ANSI code pattern that is not the RESET code
#     ansi_open=(opn := r'''
#         (?P<csi>\x1b\[)             # Control Sequence Introducer   eg: '\x1b['
#         (?P<params>[^0][\d;]*)      # Parameters                    eg: '31;1;43'
#         (?P<final_byte>[a-zA-Z])    # Final byte in code            eg: 'm'
#     '''),

#     ansi_close=(close := r'\x1b\[0?m'),
#     # this one will not match the reset code
#     # REGEX_ANSI_NOT_RESET = re.compile(REGEX_ANSI_OPEN, re.X)

#     # matches any
#     encoded=re.compile(fr'''(?x)
#         (?P<code>{opn})     # the ANSI code
#         (?P<text>.*?)                   # the string to which the code applies
#         (?P<end>{close})     # the ANSI reset code
#     ''')
# )

# ANSI reset pattern
REGEX_ANSI_CLOSE = r'\x1b\[0?m'

# Any valid ANSI code pattern
REGEX_ANSI = re.compile(r'''(?x)
    (?P<csi>\x1b\[)             # Control Sequence Introducer   eg: '\x1b['
    (?P<params>[\d;]*)          # Parameters                    eg: '31;1;43'
    (?P<final_byte>[a-zA-Z])    # Final byte in code            eg: 'm'
''')

# Any ANSI code pattern that is not the RESET code
REGEX_ANSI_OPEN = r'''
    (?P<csi>\x1b\[)             # Control Sequence Introducer   eg: '\x1b['
    (?P<params>[^0][\d;]*)      # Parameters                    eg: '31;1;43'
    (?P<final_byte>[a-zA-Z])    # Final byte in code            eg: 'm'
'''

# this one will not match the reset code
# REGEX_ANSI_NOT_RESET = re.compile(REGEX_ANSI_OPEN, re.X)

# matches any
REGEX_ANSI_ENCODED = re.compile(fr'''(?x)
    (?P<code>{REGEX_ANSI_OPEN})     # the ANSI code
    (?P<text>.*?)                   # the string to which the code applies
    (?P<end>{REGEX_ANSI_CLOSE})     # the ANSI reset code
''')

# 
REGEX_8BIT = re.compile(r'[34]8;5;(\d+)')
REGEX_24BIT = re.compile(r'[34]8;2;(\d+);(\d+);(\d+)')

# "All common sequences just use the parameters as a series of
#  semicolon-separated numbers such as 1;2;3. Missing numbers are treated as
#  0 (1;;3 acts like the middle number is 0, and no parameters at all in
#  ESC[m acts like a 0 reset code). Some sequences (such as CUU) treat 0 as 1
#  in order to make missing parameters useful.[18]:F.4.2 Bytes other than
#  digits and semicolon seem to not be used."


# ---------------------------------------------------------------------------- #

class AnsiEncodedString(SlotHelper):

    __slots__ = ('csi', 'params', 'final_byte', 'text', 'end')

    @property
    def code(self):
        return self.csi + self.params + self.final_byte

    def __str__(self):
        return ''.join(op.attrgetter(*self.__slots__)(self))


# ---------------------------------------------------------------------------- #

def has_ansi(string):
    return REGEX_ANSI.search(string) is not None


def strip(string):
    """strip ANSI codes from str"""
    return REGEX_ANSI.sub('', string)


def pull(string):
    """extract ANSI codes from str"""
    return REGEX_ANSI.findall(string)


def parse(string, named=False):
    """
    A generator that parses the string `s` to separate the ANSI code bits
    from the regular string parts.

    Parameters
    ----------
    s: str
        The string to parse
    named: bool, default False
        If True, returned items will be an 'AnsiEncodedString` namedtuple.  This allows
        you to retrieve different parts of each successive coded string as
        attributes of the returned objects.

    Yields
    ------
    Yields successive 5-tuples of str
        (csi, params, final_byte, string, END) where
        csi :        Control sequence introducer, eg:            '\x1b['
        params :     Semi-colon separated numerical codes, eg:   '31;1;43
        final_byte : Final character in the ANSI code, usualy:   'm'
        string :     The enclosed str: Text which is to be rendered with effect.
        END :        The reset code:                            '\x1b[0m' or '\x1b[m'
    For parts of the string that do not have any ANSI codes applied to them,
    the CSI and END parts of the tuple will be empty strings.

    Examples
    --------
    >>> next(parse(motley.red('hello'), True)).params
    ';31'
    """

    wrapper = AnsiEncodedString if named else echo

    idx = 0
    for mo in REGEX_ANSI_ENCODED.finditer(string):
        start = mo.start()
        if start != idx:
            yield wrapper('', '', '', string[idx:start], '')

        yield wrapper(*mo.group('csi', 'params', 'final_byte', 'text', 'end'))
        idx = mo.end()

    size = len(string)
    if (size == 0) or (size != idx):
        # last part of str
        yield wrapper('', '', '', string[idx:], '')


def _gen_index_csi(string):
    match = None
    for match in REGEX_ANSI.finditer(string):
        yield match.start()
        yield match.end()

    if (match is None) or (match.end() != len(string)):
        yield None


def _gen_index_split(string):
    yield 0
    itr = _gen_index_csi(string)
    i0 = next(itr)
    if i0 != 0:
        yield i0
    yield from itr


def split_iter(string):
    for i0, i1 in mit.pairwise(_gen_index_split(string)):
        yield string[i0:i1]


def get_split_idx(string):
    return list(_gen_index_split(string))


def split(string):
    """Blindly split the str `s` at positions ANSI code locations"""
    return list(split_iter(string))


# def shortest(s):
#     """
#     Removes superfluous control sequence indicators to get the shortest
#     version of the string that will render identical to the original
#
#     Eg: the following two strings will render identically
#         '\033[31;1;43mhi\033[0m'
#         '\x1b[31m\x1b[1m\x1b[43mhi\x1b[0m\x1b[31m\x1b[0m'
#     """
#
#     pattern2 = r'(\x1b\[[\d;]*[a-zA-Z])*(.*)(\x1b\[0m)'


def length(s, raw=False):
    """
    Character length of the string, either raw, or as it would be displayed when
    printed in console, ie. with ANSI styling code points resolved. Note that
    with `raw=True` this function returns the same result as the builtin `len`.
    """
    return len(s) if raw else length_seen(s)


def length_codes(s):
    """length of the ANSI codes in the str"""
    return sum((sum(map(len, part)) for part in pull(s)))


# aliases
length_ansi = len_ansi = len_codes = length_codes


def length_seen(s):
    """
    Length of the string as it would be seen when displayed on screen
    i.e. all ANSI codes resolved / removed
    """
    return len(strip(s))


# aliases
len_seen = len_raw = length_raw = display_width = length_seen
