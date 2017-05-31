"""
Convenient coloured strings
"""

import re

import numpy as np
from recipes.iter import as_sequence, pairwise
from recipes.misc import getTerminalSize
from recipes.string import rformat as as_str

from . import codes

# from pprint import pformat
# from decor import expose
# from IPython import embed

pattern = '\033\[[\d;]*[a-zA-Z]'
matcher = re.compile(pattern)


# ansi_nr_extract = '\033\[([\d;]*)[a-zA-Z]'
# ansi_nr_matcher = re.compile(ansi_nr_extract)


# TODO: convenience methods:
# bold
# dim
# underline
# blink
# invert
# hide
# reset / clear
# etc...


def has_ansi(s):
    return not matcher.search(s) is None


def strip(s):
    """strip ansi codes from str"""
    return matcher.sub('', s)


def pull(s):
    """extract ansi codes from str"""
    return matcher.findall(s)


def split(s):
    """split str at ansi code locations"""
    idxs = []
    for i, match in enumerate(s.matcher.finditer(s)):
        idxs += [match.start(), match.end()]

    if not len(idxs):
        return [s]

    if idxs[0] != 0:
        idxs = [0] + idxs
    if idxs[-1] != len(s):
        idxs += [len(s)]

    parsed = [s[i0:i1] for i0, i1 in pairwise(idxs)]
    return parsed


def length(s, bare=False):
    """ """
    if bare and has_ansi(s):
        return len_bare(s)
    return len(s)


def len_codes(s):
    return sum(map(len, pull(s)))


def len_bare(s):
    """
    length of the string as it would be displayed on screen
    ie. all ansi codes resolved / stripped
    """
    return len(strip(s))

# def format(s, ):



# @expose.args()
def as_ansi(obj, props=(), **propkw):  # TODO: rename for clarity as_ansi_array
    '''
    Convert the obj to an array of AnsiStr objects, applying the properties globally.
    Parameters
    ----------
    obj         :       If input is unsized - return its AnsiStr representation
                        If input is 0 size - return empty AnsiStr object
                        Else return array of AnsiStr objects
    '''

    # TODO: hanlde masked data

    precision = propkw.pop('precision', 2)
    minimalist = propkw.pop('minimalist', True)  # minimalist representation for floating point numbers
    ndmin = propkw.pop('ndmin', 0)
    # pretty = propkw.pop('pretty', True)

    # FIXME: fuckup with str type arrays!!!!
    obja = np.array(as_sequence(obj), dtype=object)

    # reshape complex dtype arrays to object arrays
    if obja.dtype.kind == 'V':  # complex dtype as in record array
        # check if all the dtypes are the same.  If so we can change view
        dtypes = next(zip(*obja.dtype.fields.values()))
        dtype0 = dtypes[0]
        if np.equal(dtypes, dtype0).all():
            obja = obja.view(dtype0).reshape(len(obja), -1)
    # else:

    if isinstance(props, dict):
        propkw.update(props)
        props = ()
    else:
        props = np.atleast_1d(props)  # as_sequence( props, return_as=tuple)

    # deal with empty arrays        # ???????
    if not len(obja):               # ???????
        return str(obj)

    # Create array of AnsiStr objects applying codes globally
    fun = lambda s: codes.apply(as_str(s, precision, minimalist),
                                *props, **propkw)
    out = np.vectorize(fun, (str,))(obja)

    if (len(out) == 1) and (out.ndim == 1) and (ndmin == 0):
        out = out[0]  # collapse arrays of shape (1,) to item its if ndmin = 0 asked for

    return out


def banner(*args, **props):
    '''print pretty banner'''
    swoosh = props.pop('swoosh', '=', )
    width = props.pop('width', getTerminalSize()[0])
    # pretty      = props.pop('pretty', True)
    _print = props.pop('_print', True)

    swoosh = swoosh * width
    # TODO: fill whitespace to width?
    # try:
    msg = '\n'.join(as_ansi(args, ndmin=1))  # pretty=pretty
    # except:
    # embed()

    # .center( width )
    info = '\n'.join([swoosh, msg, swoosh])

    info = as_ansi(info).set_property(**props)

    if _print:
        print(info)

    return info

#
#
# def set_property2(s, *properties, **kw):
#     #     '''set the ANSI codes for a string given the properties and kw descriptors'''
#     #     # TODO: strip superfluous ANSI characters - eg. empty coded strings.
#     #     # TODO: combine multiple codes as ; separated and strip extra escape
#     #
#     noprops = properties in [(), None] or None in properties
#     if noprops and not kw:
#         return s
#
#         #     # if s.len_no_ansi() == 0: #empty coded string
#         #     #     return ''
#         #
#         #     # if s.len_ansi() == 0:
#         #     esc, csi, end = ANSICodes.ESC, ANSICodes.CSI, ANSICodes.END
#         #
#     parts = s.ansi_split()
#     new_codes = ANSICodes._get_codes(*properties, **kw)

#     new_parts = []
#     for p in parts:
#         # if p == end:
#         #     continue
#         #extract code nrs and append new codes
#         match = s.ansi_nr_matcher.match(p)
#         if match:
#             cx = match.groups() + new_codes
#             p = '{}{}m'.format(csi, ';'.join(map(str, cx)))
#         new_parts.append(p)
#         # re.sub
#
#     string = ''.join(new_parts)
#
#     if string.startswith(esc):
#         AnsiStr('{}{}'.format(string, end))
#         return string
#
#     code = '{}{}m'.format(csi, ';'.join(map(str, new_codes)))
#     return AnsiStr('{}{}{}'.format(code, string, end))
