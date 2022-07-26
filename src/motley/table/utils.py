
# std
import functools as ftl
import itertools as itt
from typing import OrderedDict
from collections import abc, defaultdict

# third-party
import numpy as np
from loguru import logger

# local
from recipes import pprint as ppr
from recipes.functionals import echo0
from recipes.decorators import raises as bork

# relative
from .. import ansi, codes, formatters
from . import get_width
from .column import resolve_columns


# ---------------------------------------------------------------------------- #


def wrap_strings(column):
    for cell in column:
        yield [cell] if isinstance(cell, str) else cell


def str2tup(keys):
    if isinstance(keys, str):
        keys = (keys, )  # a tuple
    return keys


# ---------------------------------------------------------------------------- #
def apportion(width, n):
    # divide space as equally as possible between `n` columns
    space = np.array([width // n] * n)
    space[:(width % n)] += 1
    return space


def justified_delta(widths, total):
    extra = apportion(total, len(widths)) - widths
    wide = (extra < 0)
    if all(wide):
        return np.zeros_like(widths)

    if any(wide):
        # some columns are wider than average
        narrow = ~wide
        delta = -sum(extra[wide])
        extra[narrow] -= apportion(delta, narrow.sum())
        extra[wide] = 0
    return extra

# def justify_widths(widths, table_width):
#     widths[1::2] += justified_delta(widths.reshape(-1, 2).sum(1) + 3,
#                                         table_width)


def get_column_widths(data, col_headers=None, count_hidden=False):
    """data should be array-like of str types"""

    # data widths
    w = np.vectorize(get_width, [int])(data, count_hidden).max(axis=0)

    if col_headers is not None:
        assert len(col_headers) == data.shape[1]
        hw = np.vectorize(get_width, [int])(col_headers, count_hidden)
        w = np.max([w, hw], 0)

    return w


def resolve_width(width, data, headers=None):
    """

    Parameters
    ----------
    width
    data
    headers

    Returns
    -------

    """
    if width is None:
        # each column will be as wide as the widest data element it contains
        return get_column_widths(data, headers)

    width = np.array(width, int)
    if width.size == 1:
        # The table will be made exactly this wide
        w = get_column_widths(data, headers)
        if w.sum() > width:
            # TODO
            raise NotImplementedError('will need to drop columns')
        else:
            # TODO
            raise NotImplementedError('Add more space to each column until '
                                      'width is reached')

    if width.size == data.shape[1]:
        # each column width specified
        return width

    raise ValueError(f'Cannot interpret width {width!r} for data of shape '
                     f'{data.shape}')


# ---------------------------------------------------------------------------- #


def ensure_list(obj):
    return [] if obj is None else list(obj)


def ensure_dict(obj, n_cols, what='\b'):

    if not obj:  # in (None, False, ()):
        return {}

    if isinstance(obj, abc.Mapping):
        return obj

    # convert obj to dict
    if not isinstance(obj, abc.Collection):
        raise TypeError(f'Cannot resolve {type(obj)} to columns of table.')

    # auto index
    n_obj = len(obj)
    if n_obj == 1:
        # duplicate for all columns
        return dict(enumerate(itt.repeat(obj, n_cols)))

    if n_obj == n_cols:
        return dict(enumerate(obj))

    raise ValueError(
        f'Incorrect number of {what} specifiers ({n_obj}) for table with '
        f'{n_cols} columns.'
    )

# ---------------------------------------------------------------------------- #


def resolve_input(obj, n_cols, aliases, what, converter=None, raises=True,
                  default_factory=None, args=(), **kws):
    """
    Resolve user input for parameters that need to have either
        - the same number of elements as there are columns in the table or
        - need `aliases` to be provided.

    Parameters
    ----------
    obj
    data
    aliases
    what
    converter: callable
    raises
    default_factory
    args
    kws

    Returns
    -------

    """
    out = OrderedDict(ensure_dict(obj, n_cols, what))

    # set action raise / warn
    emit = bork(ValueError) if raises else logger.warning

    # convert column name aliases to index positions
    aliases = list(aliases or ())
    if not aliases and (str in set(map(type, out.keys()))):
        emit(f'Could not assign {what} due to missing `column_headers`')

    if aliases:
        if ... in out:
            # ... to be resolved first. Allows overwriting with later entries
            out.move_to_end(..., last=False)

        # copy dict to prevent RuntimeError on pop
        for key in list(out.keys()):
            item = out.pop(key)
            for i in resolve_columns(key, aliases, n_cols, what, emit):
                out[i] = item

    # convert values
    if converter:
        for i, item in out.items():
            out[i] = converter(item)

    # get default obj
    if default_factory:
        # idx_no_fmt =
        for i in set(range(n_cols)) - set(out.keys()):
            out[i] = default_factory(i, *args, **kws)

    return out


def resolve_converters(converters):
    type_convert = ftl.singledispatch(echo0)
    type_convert.register(np.ma.core.MaskedConstant, formatters.Masked())

    if callable(converters):
        return type_convert, defaultdict(lambda: converters)

    assert isinstance(converters, abc.Mapping)
    col_converters = {}  # defaultdict(lambda: echo0)

    for type_or_col, fun in converters.items():
        if isinstance(type_or_col, type):
            type_convert.register(type_or_col)(fun)
        elif isinstance(type_or_col, str):
            col_converters[type_or_col] = fun
        else:
            raise ValueError(
                f'Converter key {type_or_col!r} (for function {fun}) is '
                f'invalid. Converters should be specified as type-callable '
                f'pairs for type specific conversion, or str-callable pairs '
                f'for column conversion.'
            )

    return type_convert, col_converters


# def convert_column(data, type_convert, func):
#     return map(func or type_convert, data)
#     if func:
#         return map(func, data)
#     return data


# def resolve_borders(obj, ncols, final, default='|'):
#     """
#     Get the list of characters that will make up the column borders

#     Parameters
#     ----------
#     strings
#     where
#     ncols
#     final

#     Returns
#     -------

#     """

#     borders = resolve_input(obj, ncols, aliases, 'border', str, lambda: '|' )

#     # number / header borders can be explicitly indexed by -1j / -2j
#     l = (where == -1j) | (where == -2j)
#     if l.any():
#         # raise ValueError('deprecated')

#     if strings is not None:
#         borders[where] = strings

#     # final column border
#     borders[-1] = frame or ''

#     return borders

# ---------------------------------------------------------------------------- #

# fallback0 = fallback(0, ValueError)


def rindex0(s, char):
    try:
        return s.rindex(char)
    except ValueError as e:
        return 0


def _underline(s):
    """
    Underline last line of multi-line string, or entire string if single line
    """
    idx = rindex0(s, '\n')
    return s[:idx] + codes.apply(s[idx:], 'underline')


def highlight(array, condition, props, formatter=ppr.numeric, **kws):
    out = np.vectorize(formatter, (str, ))(array, **kws)
    if condition in (all, ...):
        condition = np.ones_like(array, bool)

    if condition.any():
        tmp = np.vectorize(codes.apply, (str, ))(out[condition], props)
        dtype = f'U{max(tmp.itemsize, out.itemsize) / 4}'
        out = out.astype(dtype)
        out[condition] = tmp
    return out


def truncate(item, width):
    # TODO: if DOTS more than 1 chr long
    cw = 0  # cumulative width
    s = ''
    for parts in ansi.parse(str(item), named=True):
        *pre, text, end = parts
        cw += len(text)
        if cw > width:
            s += ''.join((*pre, text[:width - 1], DOTS, end))
            break

        s += ''.join(parts)
    return s


# ---------------------------------------------------------------------------- #

def is_astropy_table(obj):
    parents = [f'{kls.__module__}.{kls.__name__}' for kls in type(obj).mro()]
    return 'astropy.table.table.Table' in parents


def convert_astropy_table(tbl):
    data, heads, units = [], [], []
    for name, col in tbl.columns.items():
        data.append(col.data)
        units.append(col.unit)
        heads.append(name)

    if set(units) == {None}:
        units = None

    return data, heads, units
