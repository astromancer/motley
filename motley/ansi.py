"""
Tools for recognising and stripping ANSI codes
"""

import re

import more_itertools as mit

RE_END = r'\x1b\[0?m'  # the ANSI reset pattern
RE_ANSI_CODE = r'''
(?P<csi>\x1b\[)             # Control Sequence Introducer   eg: '\x1b['
(?P<params>[\d;]*)          # Parameters                    eg: '31;1;43'
(?P<final_byte>[a-zA-Z])    # Final byte in code            eg: 'm'        
'''
SRE_ANSI_CODE = re.compile(RE_ANSI_CODE, re.X)

RE_ANSI_NOT_END = r'''
(?P<csi>\x1b\[)             # Control Sequence Introducer   eg: '\x1b['
(?P<params>[^0][\d;]*)      # Parameters                    eg: '31;1;43'
(?P<final_byte>[a-zA-Z])    # Final byte in code            eg: 'm'        
'''  # this one will not match the reset code
SRE_ANSI_NOT_RESET = re.compile(RE_ANSI_NOT_END, re.X)

RE_ANSI_VALID = fr'''
(?P<code>{RE_ANSI_NOT_END})   # the ANSI code
(?P<s>.*?)                      # the string to which the code applies
(?P<end>{RE_END})               # the ANSI reset code
'''
SRE_ANSI_VALID = re.compile(RE_ANSI_VALID, re.X)

# RE_ANSI_OPEN = fr'(?P<code>{RE_ANSI_CODE})(?P<s>.*?)(?!{RE_END})'

# "All common sequences just use the parameters as a series of
#  semicolon-separated numbers such as 1;2;3. Missing numbers are treated as
#  0 (1;;3 acts like the middle number is 0, and no parameters at all in
#  ESC[m acts like a 0 reset code). Some sequences (such as CUU) treat 0 as 1
#  in order to make missing parameters useful.[18]:F.4.2 Bytes other than
#  digits and semicolon seem to not be used."


# sre_end = re.compile(re.escape(END))


# TODO:
# class ANSI(object):
#     def __init__(self, s):
#         *self.codes, self.s, self.end = split(s)
#
#     def __str__(self):
#         return ''.join(self.codes + [self.s + self.end])


def has_ansi(s):
    return SRE_ANSI_CODE.search(s) is not None


def strip(s):
    """strip ansi codes from str"""
    return SRE_ANSI_CODE.sub('', s)


def pull(s):
    """extract ansi codes from str"""
    return SRE_ANSI_CODE.findall(s)


def parse(s):
    """
    A generator that parses the string `s` to separate the ANSI code bits
    from the regular string parts.
    Yields successive 3-tuples of str (code, string, END) where
        - The ANSI code sequence eg: '\x1b[31;1;43m'
        - The enclosed str: That which would be rendered with effect.
        - END is the reset code: '\x1b[0m' or '\x1b[m'
    For parts of the string that do not have any ANSI codes applied to them,
    the CSI and END parts of the tuple will be empty strings.

    Parameters
    ----------
    s
    groups

    Examples
    --------

    Returns
    -------

    """
    idx = 0
    mo = None
    for mo in SRE_ANSI_VALID.finditer(s):
        start = mo.start()
        if start != idx:
            yield '', '', '', s[idx:start], ''
        yield mo.group('csi', 'params', 'final_byte',  's', 'end')
        idx = mo.end()

    if mo is None:
        # no ANSI codes in s
        yield '',  '', '', s, ''


def gen_index_csi(s):
    match = None
    for match in SRE_ANSI_CODE.finditer(s):
        yield match.start()
        yield match.end()

    if match and (match.end() != len(s)):
        yield len(s)


def gen_index_split(s):
    itr = gen_index_csi(s)
    i0 = next(itr)
    if not i0 == 0:
        yield 0
    yield i0
    yield from itr


def split_iter(s):
    for i0, i1 in mit.pairwise(gen_index_split(s)):
        yield s[i0:i1]


def get_split_idx(s):
    return list(gen_index_split(s))


def split(s):
    """Blindly split the str `s` at positions ansi code locations"""
    return list(split_iter(s))


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


def length(s, raw=True):
    """Length of the string, either raw, or as it would be displayed."""
    if raw:
        return len(s)
    return length_raw(s)


def length_codes(s):
    """length of the ansi escape sequences in the str"""
    return sum(map(len, pull(s)))


def length_raw(s):
    """
    length of the string as it would be displayed on screen
    i.e. all ansi codes resolved / removed
    """
    return len(strip(s))
