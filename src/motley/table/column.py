
# std
import numbers
import warnings as wrn
import functools as ftl
import contextlib as ctx

# third-party
import numpy as np

# local
from recipes.lists import where
from recipes import pprint as ppr
from recipes.functionals import echo0
from recipes.logging import LoggingMixin

# relative
from ..utils import resolve_alignment


# ---------------------------------------------------------------------------- #


def get_default_align(data, default='<'):
    #
    types = set(map(type, data))
    if len(types) != 1:
        return default

    # all data in this column is of the same type
    type_ = types.pop()
    if issubclass(type_, numbers.Integral):
        return '>'

    if issubclass(type_, numbers.Real):
        return '.'


# ---------------------------------------------------------------------------- #

# class IndexResolver:
#     se


def letter_to_index(letter):
    assert isinstance(letter, str)
    assert len(letter) == 1
    assert (o := ord(letter)) >= 65
    return o - 65


def resolve_columns(key, headers, ncols, what='column', emit=wrn.warn):
    """
    Resolve column indices (integers) from arbitrary object input.

    Parameters
    ----------
    key : object
        Key to resolve as index or indices.
    headers : list of tuple
        Column header names, optionally followed by tuples of column group
        names. Each tuple should be length `n_cols`.
    ncols : int
        Number of columns.
    what : str, optional
        Name of the attribute that is the target of the index, by default
        'column'. This is used for informative warning or error messages.
    emit : callable, optional
        Function that emits messages, by default `warnings.warn`.

    Returns
    -------
    list
        Integer indices for columns represented by `key`.
    """
    return _resolve_columns(key, headers, ncols, what, emit)


@ftl.singledispatch
def _resolve_columns(key, headers, ncols, what, emit):
    # unknown type. warn
    emit(f'Key {key!r} for {what} has invalid type {type(key)} for '
         f'mapping to a column of the table.')
    return key


@_resolve_columns.register(numbers.Integral)
def _(key, headers, ncols, what, emit):
    # wrap negative indices
    if key < 0:
        return [key + ncols]

    if key > ncols:
        emit(f'Key {key!r} for {what} greater than number of columns '
             f'in table ({ncols}).')
    return [key]


@_resolve_columns.register(str)
def _(key, headers, ncols, what, emit):
    for level in headers:
        if key in level:
            return where(level, key)  # list of int

    # Not a column header str. Try convert from letter to index A -> 0 etc..
    with ctx.suppress(AssertionError):
        return [letter_to_index(key)]

    emit(f'Could not interpret {what}. Key {key!r} not in any '
         f'`column_headers` or `column_groups`: {headers}.')


@_resolve_columns.register(tuple)
@_resolve_columns.register(list)
def _(key, headers, ncols, what, emit):
    # convert column name headers to index positions
    return [_resolve_columns(k, headers, ncols, what, emit) for k in key]


@_resolve_columns.register(type(...))
def _(key, headers, ncols, what, emit):
    return list(range(ncols))

# ---------------------------------------------------------------------------- #


class Column(LoggingMixin):
    # count = itt.count()

    def __init__(self, data, title=None, unit=None, fmt=None, align='.',
                 width=None, total=False, group=None):
        # TODO: fmt = '{:. 14.5?f|gBi_/teal}'
        self.title = title
        self.data = np.atleast_1d(np.asanyarray(data, 'O').squeeze())
        assert self.data.ndim == 1

        self.unit = unit
        self.width = width
        self.align = resolve_alignment(align)
        self.total = self.data.sum() if total else None
        self.dtypes = set(map(type, np.ma.compressed(self.data)))

        if fmt is None:
            fmt = self.get_default_formatter()

        assert callable(fmt)
        self.fmt = fmt

    # def resolve_formatter(self, fmt):
    #     ''

    def get_default_formatter(self, precision, short):
        """
        Selects an appropriate formatter based on the types (classes) of objects 
        in the column


        Parameters
        ----------
        precision
        short

        Returns
        -------

        """

        # dispatching formatters on the cell object type  not a good option here
        # due to formatting subtleties
        if len(self.dtypes) != 1:
            return ppr.PrettyPrinter(
                precision=precision, minimalist=short).pformat

        # If we are here, all data in this column is of the same type
        # NB since it's a set, don't try types_[0]
        type_, = self.dtypes

        if issubclass(type_, str):  # NOTE -  this includes np.str_!
            return echo0  # this function just passes back the original object

        # If dtype not a number, convert to str (this uses g formatting)
        if not issubclass(type_, numbers.Real):
            return str

        # If we are here, the dtype is numeric
        sign = ''
        if issubclass(type_, numbers.Integral):
            # If dtype int, use 0 precision by default
            precision = 0
        else:
            # if short and (self.align[col_idx] in '<>'):
            #     right_pad = precision + 1
            sign = (' ' * int(np.any(self.data < 0)))

        return ftl.partial(ppr.decimal,
                           precision=precision,
                           short=short,
                           sign=sign,
                           thousands=' ')

    def formatted(self, fmt, masked_str='--', flags=None):
        # Todo: formatting for row_headers...
        if fmt is None:
            # null format means convert to str, need everything in array
            # to be str to prevent errors downstream
            # (data is dtype='O')
            fmt = str

        use = (np.logical_not(self.data.mask)
               if np.ma.is_masked(self.data) else ...)
        values = self.data[use]
        # wrap the formatting in try, except since it's usually not
        # critical that it works and getting some info is better than none
        try:
            result = np.vectorize(fmt, (str, ))(values)
        except Exception as err:
            title = self.title or '\b'
            wrn.warn(f'Could not format column {title} with {fmt!r} '
                     f'due to the following exception:\n{err}')
            # try convert to str
            result = np.vectorize(str, (str, ))(values)

        # special alignment on '.' for float columns
        if self.align == '.':
            result = ppr.align_dot(result)

        # concatenate data with flags
        # flags = flags.get(i)
        if flags:
            try:
                result = np.char.add(result, list(map(str, flags)))
            except Exception as err:
                wrn.warn(f'Could not append flags to formatted data for '
                         f'column due to the following '
                         f'exception:\n{err}')

        return result
