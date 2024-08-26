"""
Pretty printed tables for small data sets
"""

# std
import os
import typing
import numbers
import unicodedata
import warnings as wrn
import functools as ftl
import itertools as itt
from shutil import get_terminal_size
from collections import UserString, abc, defaultdict

# third-party
import numpy as np
import more_itertools as mit

# local
from recipes.oo.slots import sanitize
from recipes.logging import LoggingMixin
from recipes.functionals import always, echo0
from recipes.oo.property import CachedProperty
from recipes.iter import cofilter, cosplit, flip_lr
from recipes import api, dicts, flow, op, pprint as ppr
from recipes.containers import (cosort, ensure, is_null, is_scalar, not_null,
                                unique, where, where_duplicate)

# relative
from .. import codes
from ..format.formatter import format as mformat
from ..utils import get_width, resolve_alignment
from . import column, summary as sm
from .utils import (NULL, ansi_underline, apportion, convert_astropy_table,
                    is_astropy_table, justify_widths, measure_column_widths,
                    resolve_converters, resolve_input, truncate)


# for validation!
# from pydantic.dataclasses import dataclass

# ---------------------------------------------------------------------------- #
# module constants
MID_BORDER = '\N{CURLY BRACKET EXTENSION}'           # '⎪' U+23aa Sm
LEFT_BORDER = '\N{LEFT SQUARE BRACKET EXTENSION}'    # '⎢'
RIGHT_BORDER = '\N{RIGHT SQUARE BRACKET EXTENSION}'  # '⎥'
#  '⋮'      #'\N{LVERTICAL ELLIPSIS}'
# '|' ??
# OVERLINE = '‾'  # U+203E
# EMDASH = '—' U+2014
HEADER_ALIGN = '^'
# MAX_WIDTH = None  # TODO
# MAX_LINES = None  # TODO
CONTINUED = ' (continued)'

# ---------------------------------------------------------------------------- #

# defines vectorized length
lengths = np.vectorize(len, [int])

# coerce to set[str]
ensure_set = ensure.Ensure(typing.Set[str])

# ---------------------------------------------------------------------------- #

# TODO: print pretty things:
# http://misc.flogisoft.com/bash/tip_colors_and_formatting
# http://askubuntu.com/questions/512525/how-to-enable-24bit-true-color-support-in-gnome-terminal
# https://github.com/robertknight/konsole/blob/master/tests/color-spaces.pl


# TODO: dynamical set attributes like title/headers/nrs/data/totals
# TODO: unit tests!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# TODO: GIST
# TODO: HIGHLIGHT COLUMNS
# TODO: OPTION for ascii row borders?

# TODO: check out wcwidth lib


# FIXME: alignment not nice when mixed negative positive....
#  or mixed float decimal (minimalist)

# NOTE: IPython does not support ansi underline, while unix term does
# Use unicode underline for qtconsole sessions. However, unicode underline does
# not display correctly in notebook!!
# if is_interactive:
#     def _underline(s):
#         # for this to work correctly, the ansi characters must surround the
#           unicode not vice versa
#         return '\u0332'.join(' ' + s)
# else:
#     def _underline(s):
#         return codes.apply(s, 'underline')

# TODO maybe
# class ConsoleWriter:
#     """Write to terminal"""


# ---------------------------------------------------------------------------- #

def is_underlined(style):
    return '4' in codes.resolve(style)


def _hstack(items, fill=''):
    ok = [not_null(item) for item in items]
    if any(ok):
        return np.hstack([items[i] if o else fill for i, o in enumerate(ok)])


def hstack(tables, **kws):

    nrows = set(map(Table.nrows.fget, tables))
    assert len(nrows) == 1
    nrows = nrows.pop()

    stacked = {attr: _hstack(op.AttrVector(attr)(tables))
               for attr in ('col_headers', 'units', 'data')}

    for attr in ('align', 'col_headers'):
        stacked[attr] = _hstack(
            [np.array(v)[..., i:]
             for v, i in op.AttrVector(attr, 'has_row_head')(tables)]
        ).T

    return Table(**stacked,
                 **{**dict(too_wide=False,  # FIXME # LAST COLUMN DROPPED???!!
                           row_headers=tables[0].row_headers),
                    **kws})

    # for k in ('align', 'col_headers'):
    #     stacked[k] = stacked[k].squeeze()[int(tables[0].has_row_head):]


def prefill(data, fill=''):
    return tuple(itt.zip_longest(*flip_lr(data), fillvalue=fill))[::-1]


# ---------------------------------------------------------------------------- #

_AUTOKEY = itt.count()


class _AutoKey:
    # for splitting nested containers into separate columns
    def __init__(self):
        self.key = next(_AUTOKEY)

    def __str__(self):
        return ''


def _split_columns(key, column, split_nested_types):
    if not (set(split_nested_types) & set(map(type, column))):
        yield key, column
        return

    # Ensure each nested object is iterable
    preprocess = ensure.EnsureWrapped(list, is_scalar=tuple({str} - split_nested_types))
    for column in itt.zip_longest(*map(preprocess, column), fillvalue=''):
        yield (*key, _AutoKey()), column


def get_columns(data, ignore_keys=(), convert_key=echo0,
                split_nested_types=set(), group=(''), row_level=-1):

    convert_key = convert_key or echo0
    assert callable(convert_key)

    return _get_columns(data, set(ignore_keys), convert_key, split_nested_types,
                        group, row_level)


def _get_columns(data, ignore_keys, convert_key, split_nested_types, group,
                 level=0, row_level=-1):

    columns = defaultdict(list)
    row_headers = []
    for key, obj in data.items():
        if key in ignore_keys:
            continue

        if level != row_level:
            key = (*group, key)
        else:
            row_headers.append(key)
            key = (key,)

        if is_scalar(obj):
            # Reach data level. Get / create column
            columns[ensure.tuple(convert_key(key))].append(obj)
            continue

        # Dict indicates group of columns
        if isinstance(obj, dict):
            # logger.trace(f'{group=}, {name=}, {level=}')
            row_headers, inner = _get_columns(obj, ignore_keys, convert_key,
                                              split_nested_types, key, level + 1)

            for key, col in inner.items():
                columns[key].extend(col)
            continue

        # Item is iterable => column
        for key, col in _split_columns(key, obj, split_nested_types):
            columns[key] = col

    return row_headers, columns


def _convert_dict(data, converters=(), ignore_keys=(), convert_keys=(),
                  header_levels=(), split_nested_types=set(), row_level=-1):

    ignore_keys = ensure_set(ignore_keys)
    converters = converters or {}
    header_levels = header_levels or {}

    if isinstance(header_levels, numbers.Integral):
        header_levels = defaultdict(lambda: header_levels)

    # get columns as dict[list]
    row_headers, columns = get_columns(data, ignore_keys, convert_keys,
                                       split_nested_types, row_level=row_level)

    headers, columns = zip(*columns.items())
    headers = list(itt.zip_longest(*headers, fillvalue=''))

    # get data conversion functions
    type_convert, col_converters = resolve_converters(converters)
    col_converters = resolve_input(col_converters, len(columns), headers, 'converter')

    for i, (headers, column) in enumerate(zip(zip(*headers), columns)):
        column = map(col_converters.get(i, type_convert), column)

        title = headers[-1]
        if header_levels.get(title, 0) < 0:
            headers = [*headers[1:], '']

        yield *headers, list(column)


def _preprocess_dict(data, converters=(), ignore_keys=(), convert_keys=(),
                     header_levels=(), split_nested_types=set(), order='r',
                     row_level=-1):
    """
    Convert input dict to list of values with keys as column / row_headers
    (depending on `order`)

    Parameters
    ----------
    data
    ignore_keys
    order

    Returns
    -------

    """

    assert isinstance(data, abc.Mapping)

    if isinstance(split_nested_types, type):
        split_nested_types = {split_nested_types}

    *headers, data = zip(*_convert_dict(
        data, converters,
        ignore_keys, convert_keys,
        header_levels, split_nested_types, row_level
    ))

    # transpose if needed
    if order.startswith('r'):
        return (), headers, list(zip(*data))

    if order.startswith('c'):
        *row_groups, row_headers = headers
        return row_headers, (), data

    raise ValueError(f'Invalid value for parameter: {order=!r}')


# def _from_tree(node, row_level=0, level=0):
#     groups = []
#     columns = defaultdict(list)
#     for name, child in node.items():

#         if isinstance(child, type(node)):
#             inner_groups, inner = _from_tree(child, row_level, level + 1)
#             if inner_groups and (len(groups) <= level):
#                 groups.append(inner_groups)

#             for key, dat in inner.items():
#                 if (key not in columns) and (level != row_level):
#                     groups.append(name)
#                 columns[key].extend(dat)
#         else:
#             columns[name].append(child)

#     return groups, columns


def check_flag(obj):
    if isinstance(obj, list) or callable(obj):
        return obj

    if isinstance(obj, (str, UserString)):
        return obj.format

    raise TypeError(f'Invalid flag type: {type(obj)}.')


# ---------------------------------------------------------------------------- #


class Table(LoggingMixin):
    # TODO split ConsoleWriter(TableWriter)
    """
    A table formatter. Good for displaying data. Definitely not for data
    manipulation (yet). Plays nicely with ANSI colours and multi-line cell
    elements.
    """

    MID_BORDER = MID_BORDER
    LEFT_BORDER = LEFT_BORDER
    RIGHT_BORDER = RIGHT_BORDER
    NRS_HEADER = '#'

    # The column format specification:
    cell_fmt = '{3}{0:{1}{2}}{4}'
    #  0 - item
    #  1 - alignment
    #  2 - cell width
    #  3 - lhs border
    #  4 - rhs border
    unit_fmt = '[{}]'

    # foot_fmt = None  # '{flag} : {info}'
    # _merge_repeat_groups = True

    def resolve_input(self, obj, n_cols=None, what='\b', converter=None,
                      raises=True, default=NULL, default_factory=None,
                      args=(), **kws):

        # resolve aliases from bottommost header line upwards
        # aliases = ensure.list(flip_ud(self.col_headers), tuple)
        aliases = self.col_headers[::-1]
        if n_cols is None:
            n_cols = self.n_cols

        return resolve_input(obj, n_cols, aliases, what, converter, raises,
                             default, default_factory, args, **kws)

    def resolve_columns(self, key, n_cols, what, raises=True):
        aliases = self.col_headers[::-1]
        # set action raise / warn
        return column.index(key, aliases, n_cols, what,
                            ValueError if raises else wrn.warn)

    @classmethod
    def from_columns(cls, *columns, **kws):
        """
        Construct the table from a list of columns

        Parameters
        ----------
        columns
        kws

        Returns
        -------

        """
        if len(columns) == 1 and isinstance(*columns, dict):
            return cls._from_column_map(*columns, **kws)

        # TODO: figure out why it's necessary to explicitly resolve kws here
        synonymns = cls.__init__.__wrapper__.__self__
        args, kws = synonymns.resolve((), kws)
        # keep native types by making columns object arrays
        return cls(np.ma.column_stack([np.ma.array(_, 'O') for _ in columns]),
                   *args, **kws)
        
    @classmethod
    def _from_column_map(cls, mapping, **kws):
        mapping = dict(mapping)

        column_to_table = {
            'title':     'headers',
            'unit':      'units',
            'convert':   'converters',
            'fmt':       'formatters',
            'align':     'alignment',
            'flags':     'flags',
            # 'flag_info': 'footnotes'
        }
        
        data = []
        totals = []
        options = defaultdict(dict)
        for name, column in mapping.items():
            data.append(column.data)
            # populate the headers, units, converters, formatters
            for attr, opt in column_to_table.items():
                if (val := getattr(column, attr)):
                    options[opt][name]= val
                
            if col.total:
                totals.append(name)
                    
        return cls(data, totals=totals, **options, **kws)
    
    @classmethod
    def from_rows(cls, *rows, ignore_keys=(), fill='--', sort=None,
                  convert_keys=echo0, **kws):

        assert callable(convert_keys)

        if len(rows) == 1 and isinstance(rows[0], dict):
            kws['row_headers'], rows = zip(*rows[0].items())

        cols = defaultdict(list)
        col_names = set(mit.collapse(map(dict.keys, rows))) - ensure_set(ignore_keys)

        if sort:
            if sort is True:
                sort = None
            kws['row_headers'], rows = cosort(kws['row_headers'], rows, key=sort)

        for row in rows:
            for key in col_names:
                cols[convert_keys(key)].append(row.get(key, fill))

        return cls.from_dict(cols, **kws)

    @classmethod
    @api.synonyms((API_SYNONYMS := dicts.merge({
        'sub_title':                            'subtitle',
        'units?':                               'units',
        'footnotes?':                           'footnotes',
        # 'formatters?':                        'formatters',
        '(cell_?)white(space)?':                'whitespace',
        'minimal(ist)?':                        'minimalist',
        '((col(umn)?)?_?)widths?':              'widths',
        '(c(ol(umn)?)?_?)?_head(er)?_align':    'col_head_align',
        # 'c(ol(umn)?_?)groups':                  'col_headers',
        '(row_?)?nrs':                          'row_nrs',
        # 'n(um(be)?)?r?_?rows':                  'row_nrs',
        'n((um(ber)?)|r?)_?rows':               'row_nrs',
        'totals?':                              'totals',
        '(c(ol(umn)?)?_?)?borders?':            'col_borders',
        'vlines':                               'col_borders',
        # 'title_style':                          'title_style',
    },
        *({f'{p}head(er)?s?':                   f'{rc}_headers',
           f'{p}head(er)?_style':               f'{rc}_head_style'}
          for rc, p in {'row':  'r(ow)?_?',
                        'col':  'c(ol(umn)?)?_?'}.items())
    )),
        action=None)
    def from_table(cls, table, **kws):
        return cls(**{**table._init_kws, **kws})

    @classmethod
    @api.synonyms(
        {
            'convert':                  'converters',
            'split_nested(_types?)?':   'split_nested_types'
        },
        action=None
    )
    def from_dict(cls, data, converters=(), ignore_keys=(), convert_keys=(),
                  order='r', col_sort=None, **kws):

        # keys will be used as row or column headers and values as
        #     data rows or columns, depending on `order` parameter.

        # note that the terse kws will not be replaced here, so you may end up
        # with things like dict(chead=['user given'],
        #                       col_headers=['key in `data` dict'])
        # in which case chead will silently be ignored
        # eg: Table({'hi': [1, 2, 3]}, chead=['haha'])

        # check arguments valid
        # assert (order in 'rc'), f'Invalid value for parameter: {order=!r}'

        data, kws = cls._parse_from_dict(data, converters,
                                         ignore_keys, convert_keys,
                                         order=order, col_sort=col_sort, **kws)

        return cls(data, **kws)

    @staticmethod
    def _parse_from_dict(data, *args, **kws):
        #
        _prekws = ('order', 'row_level', 'header_levels', 'split_nested_types')

        kws, _prekws = dicts.split(kws, _prekws)

        *headers, data = _preprocess_dict(data, *args[:-1], **_prekws)
        row_headers, col_headers = headers

        if col_sort := kws.pop('col_sort', None):
            col_headers, data = cosort(col_headers, zip(*data), key=col_sort)
            data = zip(*data)

        # if row_sort := kws.pop('row_sort', False):
        #     if row_sort is True:
        #         row_sort = None

        #     row_headers, rows = cosort(row_headers, data, key=row_sort)

        return data, {'row_headers': row_headers,
                      'col_headers': col_headers,
                      'order': _prekws.pop('order', 'r'),
                      **kws}

    # TODO: test mappings!!

    # mappings for terse kws
    @api.synonyms(API_SYNONYMS, action=None)
    def __init__(self,
                 data,
                 *args,
                 # TODO: THIS API:
                 # Table(data,
                 #      # first argument is usually data. Can be array, list, dict
                 #      # to init from list of arrays (each being single or multiple columns)
                 #      use `from_columns` constructor.

                 #      # You can also place the data anywhere in the argument sequence
                 #      # if you use the `Data` identifier
                 #      #    eg: `Table(Title('foo'), Data([1,2]))`

                 #       DataFormat(precision, minimalist, align, masked),
                 #       Title('{"MY DATA TABLE":^s|Bg_/c}'),
                 #       ColumnGroups(group_names, fmt='{:^ |B_}'),
                 #       ColumnTitles(headers, fmt='{:^ |bB_}', units),
                 #       RowTitles(nrs=0,  # starting number for enumeration
                 #                   nrs_fmt=lambda: ''
                 #                  names=row_names,
                 #                  fmt='<q|B'),
                 #
                 #       # aesthetics
                 #       frame=True, # this is the default, False or None turns it off
                 #        hlines, borders
                 # )
                 #
                 # TODO: '{"DATA TABLE":^s|Bg_/c}'
                 # Force colours to be specified this way to reduce the number of
                 # parameters here!?

                 title=None,
                 title_align='center',
                 title_style=('underline', ),

                 subtitle=None,
                 subtitle_align=None,
                 subtitle_style=None,

                 # ColumnHeaders(names, fmt='{:< |bB}', units)
                 col_headers=None,
                 col_head_style='bold',
                 col_head_align='^',
                 units=None,
                 col_borders=MID_BORDER,

                 #  order = 'r',
                 # RowHeaders(names, fmt='{:< |bB}', nrs=True)
                 row_headers=None,
                 row_head_style='bold',
                 row_nrs=False,

                 max_rows=np.inf,
                 hlines=None,

                 # styling
                 frame=True,
                 summary=False,

                 # Data format
                 # DataFormat(precision, minimalist, align, masked)
                 formatter=None,
                 formatters=None,
                 masked='--',
                 precision=2,
                 minimalist=False,
                 align=None,

                 width=None,
                 too_wide='split',
                 whitespace=1,
                 totals=None,

                 flags=None,
                 flag_fmt='{}',
                 insert=None,
                 highlight=None,  # FIXME: deprecate in favour of formatters
                 footnotes='',
                 foot_fmt=None,
                 **kws):

        # TODO: style='matrix', 'bare', 'spreadsheet'
        """
        A table representation of `data`.

        Parameters
        ----------
        data : array_like or dict
            input data - must be 1D, 2D
            if dict, keys will be used as row_headers, and values as data. To
            initialize from a dict of columns use `Table.from_dict(data, order='c')`
        units : array_like or dict
            str units that will be appended [in brackets] below the column
            headers in `col_headers`.  If given and no column headers are
            provided,  this parameter is ignored and a warning is emitted.

        title : str
            The table title
        title_style : str, tuple, dict
            ANSICodes property descriptors
        align, title_align, col_head_align: {'left', 'right', 'center', '<', '>', '^', None}
            The column / column header / title alignment
            if None (default)- right align for numerical type data, left align
            for everything else

        col_headers, row_headers  : array_like
            column -, row headers as sequence of str or sequence of tuples of str.

        col_head_style, row_head_style : str or dict or array_like
            Column header properties.  If `row_nrs` is True,
            the row_head_style will be applied to the number column as well
            TODO: OR a sequence of these, one for each column

        col_borders : str, dict
            Character(s) used as column separator. ie column rhs borders
            The table border can be toggled using the `frame' parameter

        hlines: array-like, Ellipsis, optional
            Sequence with row line numbers / below which a solid border will be
            drawn.
            Default is after column headers, and after last data line and after
            totals line if any.
            If an `Ellipsis` ... is given, draw a line after every row.

        row_nrs : bool, int
           Number the rows. Start from this number if int

        precision : int
            Decimal precision to use for representing real numbers (floats)
        minimalist : bool
            Represent floating point numbers with least possible number of
            significant digits
        summary : bool or int or str or dict
            Columns for which data values are all identical will be removed from
            the main table, and instead summarized as as key-value pairs and
            typeset in a compact inset (sub)table. There are various styles of
            doing this, depending on the type and value given with this
            parameter. Summary representations will only be used for Tables that
            contain more than one row of data.

            An integer value can be used to control the number of columns to use
            for the summary table.
            If True, the default:
                The maximum allowable number of columns given the available
                space is used. Using `summary=True`, is the same as
                using`summary={'ncols': any}`.
            If int:
                This specific number of columns will ne use in the inset table.
                Using `summary=2`, is the same as using`summary={'ncols': 2}`.
            If str: {'drop', 'header', 'footer'}
                'drop':   Summarized columns are simply ignored.
                'header': Summary key-value pairs are inset in the table header 
                          below the table title and above the column headers.
                'footer': Summarized columns are printed as key-value pairs
                          in the table footer.

        ignore_keys : sequence of str
            if dictionary is passed as data, optionally specify the keys that
            will not be printed in table
        order : {'r', 'c', 'row', 'col'}
            Used when table is initialized from dict, or when data is 1
            dimensional to know whether values should be interpreted as
            rows or columns. Default is to interpret 1D data as a row with
            column headers.
            note that for 2d data this argument is ignored. To create a
            `Table` from a set of columns use the `Table.from_columns`
            constructor.

        width : int, range, array_like
            Required table (column) width(s)
                If int: The table width.
                If range: The minimum and maximum table width # TODO
                If array_like: One int per column specifying each width
        too_wide: {'split', 'truncate', 'ignore'}
            How to handle case in which table is too wide for display.
             - If 'split' (default) the table is split into multiple tables that
              each respect `max_width`, and print them one after the other.
             - If 'truncate': #TODO

        whitespace: int
            minimal whitespace in each cell
        frame : bool
            whether to draw a frame for the table
        totals : bool or array_like
            Indices or names of columns for which to compute sums. If any
            provided, an extra row with totals for requested columns will be
            added to the table. Will only work for columns with numeric type
            data, i.e. items have an `__add__` method.
            # todo maybe just ignore if non-numeric?
            This will only be done if the table contains more than one row of
            data.

        formatters : function or dict or array_like, optional
            Formatter(s) to use to create the str representation of objects in
            the table.

             - If not given, the formatter is chosen based on the type of
             objects in the column. The default formatter is decided by the
             `get_default_formatter` method of this class. The default
             behaviour is as follows:
                * Integral data types are represented with 0 precision.
                * Real data types (float) are represented with `precision`
                  number of decimals.
                * If the column contains multiple data types a custom
                  `ppr.PrettyPrinter` subclass is used which respects the
                  `precision` and `minimalist` arguments for floats, but
                  still creates nice representations for arbitrarily nested
                  objects. If you use a custom formatter, the `precision` and
                  `minimalist` arguments will be ignored.

             - If an array_like is given, it should provide one formatter per
             table column.
             - If a dict is given, it should be keyed on the column indices for
             which the corresponding formatter function is intended. If
             `col_headers` are provided, the formatter dict can also be keyed
             on any str contained in this list. The default formatter will be
             used for the remaining columns.

        flags: dict[list[str]|callable]
            For each column in the mapping, a list of str flags (one per row) to
            append to the cell values of the corresponding column. If the value
            is a callable, it should take the cell value as the first argument
            and return the flag value str.

        insert: dict
            Insert arbitrary lines into the table before these rows. This
            dict should be keyed on the row numbers (integers). Row numbers
            refer to the data lines - ie. excludes the header row.
            This can for example be used to create arbitrary headers for
            groups of rows within the table. The values of this dict should
            be either str, or tuple. If tuple, it should contain the following:
                - item to insert (will be converted to string if not already so)
                - alignment character (default '<')
                - properties to apply to the string (default None)

        highlight: dict, optional
            Highlight these rows by applying the given effects to the entire
            row.  The dict should be keyed on integer which is the line number

        footnotes: str, list, dict
            Any footnote that will be added to the bottom of the table.
            Useful to explain the meaning of `flags`. If str, will be wrapped 
            in a paragraph as wide as the table and used directly.
            If list[str], each will be added as a line below the table.
            If dict, it specifies the meaning of the `flag` symbols. If you passed  
            the `flags` as dict functions keyed on symbols, the symbols that 
            appear in the table will be appended, each with the description 
            provided by the same key in the `footnotes` dict.

        # TODO: list attributes here
        """

        # FIXME: precision etc ignored when init from dict
        # FIXME: hlines with cell elements that have ansi ... effects don't
        #  stack...

        # FIXME: move construction for types dispatch to __new__

        # from recipes import pprint
        # pprint.mapping(locals(), ignore=['self'])
        # logger.debug('SUMMARY {!r}.', summary)

        self._init_kws = sanitize(locals())

        # special case: dict
        if isinstance(data, dict):
            data, kws = self._parse_from_dict(data, **kws)
            # return self.__init__(data, **kws)

        if isinstance(data, (set, zip)):
            data = list(data)

        # special case: astropy.table.Table
        if is_astropy_table(data):
            data, col_headers_, units_ = convert_astropy_table(data)

            # replace defaults with those from the astropy table
            if col_headers is None:
                col_headers = col_headers_
            if units is None:
                units = units_

        # convert to object array
        try:
            data = np.asanyarray(data, 'O')
        except ValueError as err:  # FIXME
            if 'invalid __array_struct__' in str(err):
                z = np.empty((len(data), len(data[0])), 'O')
                for i, row in enumerate(data):
                    for j, d in enumerate(row):
                        z[i, j] = d
                data = z
            else:
                raise

        # check data shape / dimensions
        dim = data.ndim
        if dim == 1:
            data = data[None]

        if dim > 2:
            raise ValueError(f'Only 2D data can be tabled! Data is {dim}D')

        # FIXME: make this table base for data manipulation and have separate
        # console formatter for ansi...
        # self._object_array = data

        #
        self.data = data
        n_cols = data.shape[1]

        # title
        self.frame = bool(frame)
        self.title = title
        self.subtitle = subtitle

        self.has_title = title not in (None, False)
        self.title_style = codes.standardize(title_style)
        self.title_align = resolve_alignment(title_align)

        self.subtitle_style = subtitle_style or self.title_style
        self.subtitle_align = subtitle_align or self.title_align

        # get data types of elements for automatic formatting / alignment
        self.col_data_types = []
        for col in data.T:
            use = ~col.mask if np.ma.is_masked(col) else ...
            self.col_data_types.append(set(map(type, col[use])))

        # columns headers
        self.col_nrs = ()
        self.col_headers = self.resolve_col_headers(col_headers,
                                                    kws.pop('col_groups', ()))

        # row headers
        self.row_nrs = row_nrs
        self.row_headers = self.resolve_row_headers(row_headers)

        # units
        self.units = None
        if not_null(units):
            units = self.resolve_input(units, n_cols, 'units',
                                       self.unit_fmt.format, default='')
            self.units = list(map(units.get, range(n_cols)))

        # calculate column totals if required (required before resolve row_headers)
        self.totals = self.get_totals(totals)

        # get alignment based on column data types
        self.align = self.get_alignment(align, data, self.get_default_align)
        self.dot_aligned = np.subtract(where(self.align, '.'), self.n_head_cols)
        self.align = np.array(list(self.align.replace('.', '<')), 'U1')

        # column headers will be center aligned unless requested otherwise.
        self.col_head_align = np.array(list(self.get_alignment(
            col_head_align, data, lambda _: HEADER_ALIGN)))

        # column formatters
        if formatter and not formatters:
            formatters = [formatter] * n_cols

        self.formatters = self.resolve_input(
            formatters, n_cols, 'formatters',
            default_factory=self.get_default_formatter,
            args=(precision, minimalist, data)
        )

        # get flags
        flags = self.resolve_input(flags, n_cols, 'flags', check_flag)
        if isinstance(flag_fmt, str):
            flag_fmt = flag_fmt.format
        assert callable(flag_fmt)

        self.flag_fmt = flag_fmt

        # Footnotes
        if foot_fmt:
            if isinstance(foot_fmt, str):
                foot_fmt = foot_fmt.format
            assert callable(foot_fmt)
        self.foot_fmt = foot_fmt

        flag_info = None
        self.footnotes = []
        if isinstance(footnotes, str):
            self.footnotes = footnotes.splitlines()
        elif isinstance(footnotes, dict):
            flag_info = footnotes
        elif footnotes:
            self.footnotes = list(footnotes)

        # FIXME: ALL STUFF BELOW HERE SHOULD BE DYNAMIC!!

        # column borders
        # print(f'{col_borders = }')
        self.borders = self.resolve_borders(col_borders, frame, n_cols)
        # print(f'{self.borders = } {self.borders.shape = }')

        # Add row / column headers
        self.col_head_style = col_head_style
        # TODO : don't really need this since we have self.highlight
        self.row_head_style = row_head_style

        # insert lines
        self.insert = dict(insert or {})

        # truncate number of rows
        nrows = data.shape[0]
        nomit = nrows - max_rows if np.isfinite(max_rows) else 0
        if nomit > 0:
            self.insert[max_rows - 1] = f'< ... {nomit} rows omitted ... >'
            data = data[:max_rows]

        # do formatting
        data = self.formatted(data, self.formatters, str(masked), flags, flag_info)

        # add the (row / column) headers / row numbers / totals
        if self.n_head_cols:
            data = np.ma.hstack((self.row_header_block, data))

        # add totals row
        if self.has_totals:
            data = np.vstack((data, self.totals_block))

        # Row headers + data. still no column headers
        self._formatted = data

        # note `_formatted` is dtype='O'
        self.borders = np.array(self.borders)
        self.whitespace = int(whitespace)

        # summarize / compactify
        self.summary = sm.SummaryTable.from_table_api(self, summary)
        self._idx_shown = self.summary.index_shown

        # Next get column widths (without borders)
        # These are either those input by the user, or determined from the
        # content of the columns
        if width is None:
            self.col_widths = self.measure_column_widths()  # + self.whitespace
        else:
            self.col_widths = self.resolve_widths(width)
            # if requested widths are smaller than that required to fully
            # display widest item in the column, truncate all too-wide items
            # in that column
            self.truncate_cells(self.col_widths)

        # NOTE: next block needs to happen after `self.col_widths` assigned
        self.inset = None
        if (has_inset := bool(self.summary)):
            # this is an instance of `Table`!!
            self.inset = self.summary()

        # check for too-wide title or inset lines, and amend column widths
        # to match
        # todo method here
        tw = 0
        if self.has_title or has_inset:
            if has_inset:
                tw = self.inset.get_width()

            # use explicit split('\n') below instead of splitlines since the
            # former yields a non-empty sequence for title=''
            tw = 0
            if self.has_title:
                tw = max(lengths(self.title.split('\n')).max(), tw)

            w = self.get_width() - 1

            # -1 to exclude lhs / rhs borders
            # cw = self.col_widths[self._idx_shown]
            if tw > w:
                d = tw - w
                idx = itt.cycle(self._idx_shown)
                while d:
                    self.col_widths[next(idx)] += 1
                    d -= 1

        # add summarized columns as footnotes if requested
        if (self.summary.loc == 1) and self.summary.items:
            # add footnote table
            self.footnotes.extend(str(self.inset).splitlines())

            # if self.foot_fmt:
            #     self.footnotes.extend(
            #         (self.foot_fmt(flag=col, info=val)
            #          for col, val in self.summary.items.items())
            #     )
            # else:

        # column borders
        # self.borders = borders
        # self.col_widths = requested_widths
        # otypes=[int] in case borders are empty
        self.hlines = self.resolve_hlines(hlines)

        # Column specs
        # add whitespace for better legibility
        # self.whitespace = whitespace
        # self.col_widths = self.measure_column_widths()

        # decide column widths
        # self.col_widths, width_max = self.resolve_width(width)

        # if self.insert:
        #     invalid =  set(map(type, self.insert.values())) - {list, str}

        self.highlight = dict(highlight or {})
        # for i in range(-self.n_head_rows, 0):
        #     self.highlight[i] = col_head_style

        # init rows
        # self.rows = []
        self.states = []
        self.state_props = []

        # table truncation / split stuff  # TODO...
        self._max_width = None
        if too_wide in ('ignore', False):
            self._max_width = np.inf
        elif too_wide == 'split':
            self._max_width = None
        elif too_wide == 'truncate':
            raise NotImplementedError('TODO: necessary to remove columns')
        else:
            raise ValueError

        #
        # self.handle_too_wide = too_wide
        # self.max_column_width = self.handle_too_wide.get('columns')

        self.show_colourbar = False

    def _resolve_hlines(self, hlines):
        # row borders
        n_rows, _ = self._formatted.shape

        if hlines is ...:
            return np.arange(n_rows)

        if hlines:
            # headers are negatively indexed
            hlines = np.array(hlines)
            hlines[hlines < 0] += n_rows
            return hlines

        return []

    def resolve_hlines(self, hlines):
        # row borders
        n_rows, _ = self._formatted.shape
        hlines = list(self._resolve_hlines(hlines))
        if self.frame:
            if self.has_col_head:
                hlines.append(-1)
                if self.n_head_rows > 2:
                    hlines.append(-self.n_head_rows)

            if self.has_totals:
                hlines.extend(np.subtract(n_rows, (1, 2)))

            # bottom
            hlines.append(n_rows - 1)

        return sorted(set(hlines))

    def resolve_borders(self, col_borders, frame, n_cols):
        # col borders (rhs)
        mid_border = self.MID_BORDER
        if isinstance(col_borders, str):
            mid_border = col_borders
            col_borders = [col_borders]

        # if isinstance(border, abc.Sequence):
        if len(col_borders) == n_cols + 1:
            self.LEFT_BORDER, *col_borders = col_borders
        if not frame:
            self.LEFT_BORDER = self.RIGHT_BORDER = ''

        default_borders = defaultdict(always(mid_border))
        default_borders[n_cols] = self.RIGHT_BORDER
        borders = self.resolve_input(col_borders, n_cols, 'border', str,
                                     default_factory=default_borders.get)

        return np.array([*borders.values(), self.RIGHT_BORDER])

        # if self.summarize == 'footnote':

    def __repr__(self):
        # useful in interactive sessions to immediately print the table
        return str(self)

    def __str__(self):
        return self.format() if self.data.size else '<Empty Table>'

    def __format__(self, spec):
        return str(self)

    # ------------------------------------------------------------------------ #
    @property
    def nrows(self):
        return self.data.shape[0]

    @property
    def ncols(self):
        return self.data.shape[1]

    # alias
    n_rows = nrows
    n_cols = ncols

    # @property
    # def col_headers(self):
    #     return self._col_headers

    # @col_headers.setter
    # def col_headers(self, headers):
    #     self.resolve_headers(headers, 'column', check=True)
    #
    # self._headers_headers, headers = split(headers, excess)

    # save
    # self._col_headers = headers

    # @property
    # def row_headers(self):
    #     return self._row_headers

    # @row_headers.setter
    # def row_headers(self, headers):

    #     if not_null(headers) and (headers := ensure.list(headers, str)):
    #         if (excess := len(headers) - self.nrows):
    #             self._headers_headers, headers = split(headers, excess)

    #     self._row_headers = headers

    @property
    def row_nrs(self):
        return self._row_nrs

    @row_nrs.setter
    def row_nrs(self, row_nrs):
        if row_nrs is not False:
            nr = int(row_nrs)
            row_nrs = np.arange(nr, self.nrows + nr).astype(str)

        self._row_nrs = row_nrs

    @property
    def has_row_nrs(self):
        return self._row_nrs is not False

    @property
    def has_col_nrs(self):
        return not_null(self.col_nrs)

    @property
    def has_row_head(self):
        return not_null(self.row_headers)

    @property
    def n_head_cols(self):
        return int(self.has_row_head) + int(self.has_row_nrs)

    @property
    def row_header_block(self):

        block = np.full((self.nrows, self.n_head_cols), '', 'O')

        # add row numbers
        if self.has_row_nrs:
            block[:self.nrows, 0] = self.row_nrs

        # row headers
        if self.has_row_head:
            block[:, self.has_row_nrs:] = self.row_headers

        # if self.has_totals:
        #     block[-1, -1] = 'Totals'

        return block

    @property
    def has_col_head(self):
        return not_null(self.col_headers)

    @property
    def has_units(self):
        return not_null(self.units)

    @property
    def n_head_rows(self):
        return sum((self.has_col_nrs, len(self.col_headers), self.has_units))

    @property
    def col_groups(self):
        if self.has_col_head:
            return self.col_headers[:-1]

    @property
    def col_header_block(self):

        nhr, nhc = self.n_head_rows, self.n_head_cols
        block = np.full((nhr, self.ncols + nhc), '', 'O')

        if block.size:
            # top left corner
            block[:nhr, :nhc] = self.headers_header_block

        # add col numbers
        if hcn := self.has_col_nrs:
            block[0, :len(self.col_nrs)] = self.col_nrs

        # col headers
        if self.has_col_head:
            block[hcn:len(self.col_headers), nhc:] \
                = self.col_headers

        #  units
        if self.has_units:
            block[-1, nhc:] = self.units

        return block.astype(str)

    @CachedProperty()
    def headers_header_block(self):
        # top left corner headers/headers block
        block = np.full((self.n_head_rows,  self.n_head_cols), '', 'O')
        if self.has_col_head and self.has_row_nrs:
            block[-self.has_units - 1, 0] = self.NRS_HEADER

        return block

    @property
    def has_totals(self):
        return not_null(self.totals)

    @CachedProperty()
    def totals_block(self):
        if not self.has_totals:
            return

        # copy this so we keep totals as numeric types for later work.
        nhc = self.n_head_cols
        totals = np.full((1, self.ncols + nhc), '', 'O')
        totals[0, nhc:] = self.formatted(self.totals, self.formatters, '')

        # if self.n_head_cols:
        #     totals[0, 0] = 'Totals'

        return totals

    @property
    def max_width(self):
        return self._max_width or get_terminal_size()[0]

    @max_width.setter
    def max_width(self, value):
        self._max_width = int(value)

    @property
    def n_head_lines(self):
        """number of newlines in the table header"""
        nsub = self.subtitle.count('\n') if self.subtitle else 0
        n = (self.title.count('\n') + nsub + 1) if self.has_title else 0
        m = (len(self.summary.items) // self.summary.ncols) if self.summary else 0
        return n + m + self.n_head_rows + self.frame

    @property
    def lcb(self):
        return lengths(self.borders)

    # ------------------------------------------------------------------------ #
    def empty_like(self, n_rows, **kws):
        """
        A string representing an empty row of the table. Has the same
        number of columns and column widths as the table.
        """

        filler = [''] * len(self._idx_shown)
        return Table([filler] * n_rows,
                     width=self.measure_column_widths()[self._idx_shown],
                     **kws)

    def hstack(self, other, **kws):

        assert (nrows := self.nrows) == other.nrows

        tables = (self, other)
        stack_attrs = ('col_headers', 'units', 'align', 'data')
        stacked = {attr: _hstack(op.AttrVector(attr)(tables))
                   for attr in stack_attrs}

        for k in ('align', 'col_headers'):
            stacked[k] = stacked[k].squeeze()[int(tables[0].has_row_head):]

        return Table(**stacked,
                     **{**dict(too_wide=False,
                               row_headers=tables[0].row_headers),
                        **kws})

    # ------------------------------------------------------------------------ #
    def _resolve_headers(self, headers, which):
        # headers:  list[tuple|scalar]

        # resolve column group headers
        if is_null(headers):
            return

        allowed = {'row', 'column'}
        assert (which := which.lower().rstrip('s')) in allowed
        # other = (allowed - {which}).pop()
        rc = which[:3]
        nrc = getattr(self, f'n{rc}s')
        # nh = getattr(self, f'n_head_{other}s')
        # allowed_excess = set(range(nh + 1))

        headers = list(headers)
        if is_scalar(headers[0]):
            if (n := len(headers)) != nrc:
                raise ValueError(f'{n} headers for {nrc} {which}.')
            headers = [headers]
            # headers = list(map(ensure.tuple, headers))
        else:
            # 2d
            if (len(headers) != nrc):
                assert set(map(len, headers)) == {nrc}

        #     if len(tmp) == nrc:
        #         headers = tmp

        # ensure we have tuples of same size
        # rows = list(prefill(map(ensure.tuple, headers), ''))
        # nlevels = len(rows)
        for level, row in enumerate(headers):
            # row = tuple(row)
            # n = len(headers)

            # if check:
            #     excess = n - nrc
            #     if (excess >= 0) and (excess in allowed_excess):
            #         self.logger.debug(
            #             'Resolved {} {} headers (at level {}/{}) for table with'
            #             ' {} {}s and {} {} headers).',
            #             n, which, level, nlevels, nrc, which, nh, other
            #         )
            #     elif (short := nh - excess) and _prefill:
            #         headers = [*mit.pad(next(_prefill, ''), '', short), *headers]
            #     else:
            #         raise ValueError(
            #             f'Invalid number of {which} headers: {n} (at level {level}/'
            #             f'{nlevels}) for table with {nrc} {which} (and {nh} header '
            #             f'{which}s).'
            #         )
            # print(row)
            yield tuple(row)

    def resolve_headers(self, headers, which='column'):
        # , check=False, prefill=False
        return list(self._resolve_headers(headers, which))

    def resolve_col_headers(self, headers, groups=()):
        if groups:
            self.logger.warning('Deprecated: "col_groups".')

            new = []
            # ensure(list)
            for grp, hdr in zip(map(ensure.tuple, groups), headers):
                new.append((*grp, hdr))

            headers = zip(*new)

        return self.resolve_headers(headers, 'column')

    def resolve_row_headers(self, headers):
        if is_null(headers):
            return

        return list(zip(*self.resolve_headers(headers, 'row')))

    def get_default_formatter(self, col_idx, precision, short, data):
        """

        Parameters
        ----------
        col_idx
        precision
        short

        Returns
        -------

        """
        # wrn.filterwarnings('error', category=DeprecationWarning)

        types_ = self.col_data_types[col_idx]

        #  NOTE: single dispatch not a good option here due to formatting
        #   subtleties
        # return formatter.registry[type_](None, precision=precision,
        #                                  compact=minimalist,
        #                                  sign=sign,
        #                                  right_pad=right_pad)
        if len(types_) != 1:
            return ppr.PrettyPrinter(precision=precision, minimalist=short).pformat

        type_, = types_  # nb since it's a set, don't try types_[0]
        # all data in this column is of the same type
        if issubclass(type_, str):  # this includes np.str_!
            return echo0

        if not issubclass(type_, numbers.Real):
            return str

        # right_pad = 0
        sign = ''
        if issubclass(type_, numbers.Integral):
            if short:
                precision = 0

        else:  # real numbers
            # if short and (self.align[col_idx] in '<>'):
            #     right_pad = precision + 1
            sign = (' ' * int(np.any(data[:, col_idx] < 0)))

        # print(col_idx,type_, precision, short, sign, right_pad)

        return ftl.partial(ppr.decimal,
                           precision=precision,
                           short=short,
                           sign=sign)
        #    right_pad=right_pad)

    def _get_flags(self, name, data, flags):
        # format flags for column data
        with flow.catch(warn='Could not resolve flags for column {name!r} due '
                        'to the following exception:\n{err}', name=name):
            # get flags
            if callable(flags):
                flags = [flags(val) if val else '' for val in data]

        return flags

    def formatted(self, data, formatters, masked_str='--', flags=None,
                  flag_info=None):
        """
        Convert to array of str
        """

        # FIXME: return copy DONT edit inplace
        # out = np.array(data.shape, 'O')

        flags = flags or {}
        flag_info = flag_info or {}
        data = np.atleast_2d(data).copy()

        # get column names for messages / flags
        if self.has_col_head:
            names = self.col_header_block[len(self.col_headers) - 1]
        else:
            # No headers - use col number
            names = list(formatters.keys())

        for i, fmt in formatters.items():
            col = data[..., i]

            if np.ma.is_masked(col):
                use = np.logical_not(col.mask)
                if ~use.any():
                    continue
            else:
                use = ...

            # format column
            name = names[i]
            data[use, i], used_flags = self.format_column(
                col[use], fmt, (i in self.dot_aligned), name, flags.get(i, ()),
            )

            # Create footnotes from flags and info
            for flag in used_flags:
                self._format_column_footnote(i, flag, flag_info)

            if used_flags:
                self.logger.debug('Columns {} used flags: {}.', name, used_flags)

        # finally set masked str for entire table
        if np.ma.is_masked(data):
            data[data.mask] = masked_str
            data = data.data  # return plain old array

        return data

    def format_column(self, data, fmt, dot_align, name, flags=None):
        # wrap the formatting in try, except since it's usually not
        # critical that it works and getting some info is better than none
        used_flags = set()
        if flags:
            flags = self._get_flags(name, data, flags)
            used_flags |= set(flags) - {''}

        # Todo: formatting for row_headers...
        if fmt is None:
            # null format means convert to str, need everything in array
            # to be str to prevent errors downstream
            # (data is dtype='O')
            fmt = str

        elif isinstance(fmt, str):
            # assume format string
            fmt = fmt.format

        result = []
        for j, (cell, flag) in enumerate(itt.zip_longest(data, flags, fillvalue='')):
            with flow.catch(
                warn='Could not format cell {j} in column {name!r} with '
                     'formatter {fmt!r} due to the following exception:\n{err}',
                j=j, name=name, fmt=fmt
            ):
                # format cell value and concatenate with flag
                cell = fmt(cell)
                # format flag
                if flag:
                    cell += self.flag_fmt(flag, flag=flag)

            # coerce to str in case the block above failed
            result.append(str(cell))

        # special alignment on '.' for float columns
        if dot_align:
            result = ppr.align_dot(result)

        return result, used_flags

    def _format_column_footnote(self, i, flag, flag_info):
        hdr = ''
        foot_fmt = None
        if (info := flag_info.get(flag)):
            # footnotes for all columns
            foot_fmt = self.foot_fmt or ' {flag} : {info}'

        elif (info := flag_info.get((hdr := self.col_headers[0][i]), {}).get(flag)):
            # per column footnotes
            foot_fmt = self.foot_fmt or ' {grp}.{hdr}{flag} : {info}'

        if not foot_fmt:
            wrn.warn(f'Could not resolve description for flag {flag!r} in column {hdr!r}.'
                     + ('You may provide a `dict` to the `footnotes` parameter to'
                        ' describe the flags.' * bool(self.footnotes)))
            return

        if isinstance(foot_fmt, str):
            foot_fmt = foot_fmt.format

        grp = self.col_headers[-1][i] if self.col_headers else ''
        self.footnotes.append(
            foot_fmt(flag=flag, info=info, grp=grp, hdr=hdr, tbl=self)
        )

    def truncate_cells(self, widths, dots=''):
        # this will probably be quite slow ...
        # note textwrap.shorten does this, but won't handle ANSI

        ict, = np.where(widths < self.col_widths)
        # fixme: if cells contain coded strings???
        ix = lengths(self._formatted[:, ict]) > widths[ict]

        for l, j, in zip(ix.T, ict):
            w = widths[j]
            for i in np.where(l)[0]:
                self._formatted[i, j] = truncate(self._formatted[i, j], w, dots)

    def resolve_widths(self, width):
        # width_min = 0
        # width_max = np.inf

        if width is None:
            # each column will be as wide as the widest data element it contains
            return self.measure_column_widths()  # + self.whitespace

        width = np.array(width)
        if width.size == 1:
            # The table will be made exactly this wide
            width = int(width)  # requested width
            width_ = width - self.lcb.sum()

            # Split table if columns too wide for requested width
            col_widths = self.measure_column_widths()  # + self.whitespace
            if col_widths.sum() > width_:
                self.max_width = width
                return col_widths

            # Apportion column widths
            return justify_widths(col_widths, width_)

        if np.any(width <= 0):
            raise ValueError('Column widths must be positive.')

        if width.size == self.n_cols:
            # each column width specified
            return np.array(width)
            # hcw = self.col_widths[:self.n_head_cols]
            # return np.r_[hcw, width]

        if width.size == self.n_cols + self.has_row_head:
            # each column width specified
            return width

        if isinstance(width, range):
            # maximum table width given.
            raise NotImplementedError
            width_min = width.start
            width_max = width.stop

        raise ValueError(f'Cannot interpret width {str(width)!r}')

    def measure_column_widths(self, count_hidden=False, with_borders=False,
                              include_headers=True):
        """"""

        # get width of columns - widest element in column
        widths = measure_column_widths(self._formatted, count_hidden=count_hidden)

        # add header widths
        if include_headers:

            to_measure = list(self.col_header_block) if include_headers else []
            merge_above = int(self.has_units) + self.has_row_head

            if to_measure:
                for depth, headers in enumerate(to_measure[::-1]):
                    indices = set(range(self.ncols + self.n_head_cols))

                    if depth >= merge_above:
                        # count groups only once since cells will be merged
                        if idx := where_duplicate(headers, consecutive=True):
                            rmv = set.union(*map(set, idx))
                            indices -= set(rmv)

                    for i in indices:
                        widths[i] = max(widths[i], get_width(headers[i], count_hidden))

        # add border size
        if with_borders:
            widths += self.lcb

        return widths + self.whitespace

    def get_width(self, indices=None, frame=True):
        """Get table width as displayed."""

        if indices is None:
            indices = self._idx_shown

        # Full width
        width = (self.col_widths[indices] + self.lcb[indices]).sum()

        # note: the two arrays above may be different shapes.
        if frame:
            width += codes.length(self.LEFT_BORDER)
        else:
            width -= codes.length(self.RIGHT_BORDER)

        if self.inset:
            return max(width, self.inset.get_width(frame=True))

        return max(width, 0)

    def get_alignment(self, align, data, default_factory):
        """get alignment array for columns"""
        alignment = self.resolve_input(align, data.shape[1],
                                       'alignment', resolve_alignment,
                                       default_factory=default_factory)
        # make align an array with same size as nr of columns in table

        return ''.join((
            # row headers are left aligned
            '<' * self.has_row_head,
            # row nrs right aligned
            ('<', '>')[len(data) > 10] if self.has_row_nrs else '',
            # data column alignments
            *cosort(*zip(*alignment.items()))[1]
        ))

        # dot_aligned = np.array(where(align, '.')) - self.n_head_cols
        # align = align.replace('.', '<')
        # return align

    def get_default_align(self, col_idx):
        types = self.col_data_types[col_idx]
        if len(types) != 1:
            return '<'

        # all data in this column is of the same type
        type_, = types
        if issubclass(type_, numbers.Integral):
            lr = np.floor(np.log10(np.ma.abs(self.data[:, col_idx]).astype(int))).ptp()
            return '>' if lr else '<'

        if issubclass(type_, numbers.Real):
            return '.'

        return '<'

    def get_totals(self, col_indices):
        """compute totals for columns at `col_indices`"""

        # suppress totals for tables with single row
        if self.nrows <= 1:
            if col_indices is not None:
                self.logger.debug('Suppressing redundant totals line for table '
                                  'with single row of data.')
            return

        if col_indices in (None, False):
            return

        # boolean True ==> compute totals for all
        n_cols = self.ncols
        # n_head = self.n_head_cols
        if col_indices is True:
            col_indices = np.arange(n_cols)

        totals = np.ma.masked_all(n_cols, 'O')
        for i in col_indices:
            for i in self.resolve_columns(i, n_cols, 'totals'):
                if totals[i]:
                    continue

                # attempt to compute total
                with flow.catch(
                    warn='Could not compute total for column {i} due to the '
                         'following exception: {err}', i=i
                ):
                    totals[i] = np.sum(list(filter(None, self.data[:, i])))

        return totals

    # ------------------------------------------------------------------------ #

    def format(self):
        """Construct the table and return it as as one long str"""

        # TODO: truncation
        # here data should be an array of str objects.  To do the
        # truncation, we first need to strip
        #  the control characters, truncate, then re-apply control....
        #  ??? OR is there a better way??

        table_width = sum(self.col_widths[self._idx_shown] +
                          self.lcb[self._idx_shown]) + 1

        if table_width <= self.max_width:
            return '\n'.join(self._build())

        # if self.handle_too_wide == 'split':
        # if self.has_title:
        #     self.title += '\n'  # to indicate continuation under title line
        #
        split_tables = self.split()

        if self.show_colourbar:
            split_tables[-1] = self.add_colourbar(split_tables[-1])
        return '\n\n'.join(split_tables)

    def split(self, max_width=None):
        # TODO: return Table objects??

        max_width = max_width or (self.max_width - self.frame)

        widths = self.col_widths[self._idx_shown] + self.lcb[self._idx_shown]
        # rhw = widths[:self.n_head_cols].sum()  # row header width

        # cumulative total column width
        ctcw = np.cumsum(widths)

        # figure out split
        require_split, = np.where(np.diff(np.array(ctcw / max_width, int)) == 1)

        if (many := len(require_split)):
            if self.has_col_head:
                group_splits = self._get_group_boundaries(-1)
                splits = np.digitize(require_split, group_splits)
                splits = np.take(group_splits, splits)
            else:
                width = ctcw[-1]
                nsplit = int(np.ceil(width / max_width))
                allocation = np.array(ctcw // int(np.ceil(width / nsplit)))
                splits, = np.where(np.diff(allocation) == 1)
        else:
            splits = []

        # location of current split
        first = True
        split_tables = []
        for start, end in mit.pairwise((*sorted({self.n_head_cols, *splits}), None)):
            # make a table using selection of columns
            idx_show = np.r_[self._idx_shown[:self.n_head_cols],
                             self._idx_shown[start:end]]

            lines = map(str, self._build(idx_show, not first and many))
            split_tables.append('\n'.join(lines))
            first = False

        return split_tables

    def _get_group_boundaries(self, i):
        # prefer to split at group boundaries
        return [j for _, (*_, j) in unique(self.col_header_block[i], True)]

    def get_group_boundaries(self, rows=..., columns=...):
        # prefer to split at group boundaries
        if self.has_col_head:
            splits = []
            *top, last = self.col_header_block[rows, columns]
            for groups in top:
                # section = np.take(groups, indices)
                idx = [i for _, (*_, i) in unique(groups, consecutive=True)]
                splits = np.union1d(splits, idx)
                # print(section, splits)
                yield (groups, np.sort(splits).astype(int))

            yield last, np.arange(len(last)).astype(int)

    def make_title(self, width, continued=False):
        """make title line"""
        text = self.title + (CONTINUED if continued else '')
        return self.make_merged_cell(text, width, self.title_align,
                                     self.title_style)

        # return '\n'.join(title, subtitle

    def _get_heading_lines(self, idx, table_width, continued):
        # title
        if self.has_title:
            yield self.make_title(table_width, continued)

        if self.subtitle:
            yield self.make_merged_cell(self.subtitle, table_width,
                                        self.subtitle_align,
                                        self.subtitle_style)

        # FIXME: problems with too-wide column

        # summarized columns
        if (self.summary.loc == 0) and self.summary.items:
            # if isinstance(self.summarize, (numbers.Integral)):
            # display summarized columns in single row
            yield self.make_merged_cell(str(self.inset),
                                        table_width,
                                        style=['underline' * self.frame])

        # check inset width
        column_width_total = (len(self.LEFT_BORDER)
                              + self.col_widths[idx]
                              + self.lcb[idx]).sum()
        if table_width > column_width_total:
            # This means the inset table is wider than the main table and we
            # need to add some space to the columns
            self.col_widths[self._idx_shown] += apportion(
                table_width - column_width_total, len(self._idx_shown))

        yield from self.get_col_header_lines(idx)

    def get_col_header_lines(self, indices):

        # column groups
        heading_splits = list(self.get_group_boundaries(..., indices))

        if heading_splits:
            _, idx = zip(*heading_splits)
            new = [np.setdiff1d(b, a) for a, b in mit.pairwise(idx)]
            ul = dict(zip(range(-self.n_head_rows, 0), new))

        for i, (data, splits) in enumerate(heading_splits, -self.n_head_rows):

            line = self._merged_row(data, indices, splits, ul.get(i, ()))
            line = codes.apply(line, self.col_head_style)

            if i in self.hlines:
                # only underline if headers are underlined
                yield from self._midrule(line)
            else:
                yield line

    def _merged_row(self, data, indices, split_points, ul):
        # see :  xslx.merge_duplicate_cells

        line = self.LEFT_BORDER if self.frame else ''

        groups = cofilter(*zip(*cosplit(data, indices, indices=split_points + 1)))
        for (text, *_), idx in zip(*groups):
            idx = list(idx)

            first, last = idx[0], idx[-1]
            space = (self.col_widths[idx] + self.lcb[idx]).sum()
            if codes.length(text) >= space:
                text = truncate(text, space - self.lcb[last])

            # add formatted group heading for columns
            cell = mformat('{: {}{}}{}',
                           text,
                           self.col_head_align[first],
                           space - self.lcb[last],
                           self.borders[last])

            # underline for top border of next row
            if type(self) is Table and not_null(ul):
                cell = ansi_underline(cell)

            line += cell

        return line

    def _build(self, column_indices=None, continued=False):
        """
        Build partial or full table.

        Parameters
        ----------
        column_indices: array-like of int
            Column indices that will be used
        continued: bool, optional
            whether or not continuation of split table

        Returns
        -------
        list of str (table lines)
        """
        idx = self._idx_shown if column_indices is None else column_indices
        part_table = self._formatted[:, idx]
        table_width = self.get_width(idx)

        # frame
        yield from self._toprule(table_width)

        # title / header block
        yield from self._get_heading_lines(idx, table_width, continued)

        # data
        widths = self.col_widths[idx]
        alignment = itt.repeat(self.align[idx])

        left = list(mit.padded(self.LEFT_BORDER, '', len(idx)))
        right = self.borders[idx]
        borders = (left, right)

        used = set()
        for i, row_cells in enumerate(part_table, 0):
            insert = self.insert.get(i, None)
            if insert is not None:
                yield from self.insert_lines(insert, table_width)
                used.add(i)

            row_props = self.highlight.get(i)

            *lines, final = self._row_lines(row_cells, widths, next(alignment), borders)
            for line in lines:
                # fixme: maybe don't apply to border symbols
                yield codes.apply(line, row_props)

            # underline
            if i in self.hlines:
                yield from self._midrule(final)
            else:
                yield final

        # check if all insert lines have been consumed
        unused = set(self.insert.keys()) - used
        for i in unused:
            yield from self.insert_lines(self.insert[i], table_width)

        # bottom frame
        yield from self._bottomrule(table_width)

        # finally add any footnotes present
        if len(self.footnotes):
            yield from self.footnotes

    def _toprule(self, width):
        if self.frame:
            # top line
            # NOTE: ANSI overline not supported (linux terminal) use underlined
            #  whitespace
            style = (*self.title_style['fg'], '_')
            yield codes.apply(' ' * width, style)

    def _midrule(self, text):
        yield ansi_underline(text)

    def _bottomrule(self, width):
        return
        yield

    def _row_lines(self, cells, widths, alignment, borders):
        """
        handle multi-line cell elements, apply properties to each item in the
        list of columns create a single string

        Parameters
        ----------
        cells
        widths
        alignment
        borders
        underline

        Returns
        -------

        """

        # handle multi-line cell elements
        lines = [col.split('\n') for col in cells]
        # NOTE: using str.splitlines here creates empty sequences for cells
        #  with empty strings as contents.  This is undesired since this
        #  generator will then yield nothing instead of a formatted row

        for i, row_items in enumerate(itt.zip_longest(*lines, fillvalue='')):
            yield self._row_stack_cells(row_items, widths, alignment, borders)

    def _row_stack_cells(self, cells, widths, alignment, borders):

        # format cells
        first, *cells = map(self.format_cell, cells, widths, alignment, *borders)

        # Apply properties to whitespace filled row headers
        if self.has_row_head:
            first = codes.apply(first, self.row_head_style)

        # if self.frame:
        #     first = self.LEFT_BORDER + first

        # stick cells together
        # row = ''.join((first, *cells))
        # self.rows.append(row)
        return ''.join((first, *cells))

    def insert_lines(self, insert, width):
        if isinstance(insert, str):
            insert = [insert]

        for line in insert:
            args = ()
            if isinstance(line, tuple):
                line, *args = line

            if not isinstance(line, str):
                line = str(line)
            #
            yield self.make_merged_cell(line, width, *args)

    def make_merged_cell(self, text, width, align='<', style=None):
        # table row line that spans `width` of table.  use to build title
        # line and summary inset etc..

        # width -= int(self.frame)
        borders = (self.LEFT_BORDER, self.RIGHT_BORDER) if self.frame else ('', '')
        width -= sum(map(len, borders))
        assert width > 0

        if not isinstance(style, dict):
            style = ensure.list(style)

        lines = text.split(os.linesep)

        # only underline last line for multi-line element
        if '4' in (ansi_codes := list(codes.resolve(style))):
            ansi_codes.remove('4')
            styles = itt.chain(itt.repeat(ansi_codes, len(lines) - 1),
                               [ansi_codes + ['4']])
        else:
            styles = itt.repeat(style, len(lines))

        return '\n'.join((
            codes.apply(self.format_cell(line, width, align, *borders),
                        next(styles))
            for line in lines
        ))

    def format_cell(self, text, width, align, lhs='', rhs=MID_BORDER):
        # this is needed because the alignment formatting gets screwed up by the
        # ANSI characters (which have length, but are not displayed)
        # if align == '>':

        # if (pad := (len(text) - width)) > 0:
        #     width += pad
        # TODO: maybe faster to capture pad sizes when splitting the cell content....
        width += codes.length_codes(text) + sum(map(unicodedata.combining, text))
        return self.cell_fmt.format(text, align, width, lhs, rhs)

    # def expand_dtype(self, data):
    #     # enlarge the data type if needed to fit escape codes
    #     _, type_, size = re.split('([^0-9]+)', data.dtype.str)
    #     if int(size) < self.col_widths.max() + 20:high
    #         dtype = type_ + str(int(size) + 20)
    #         data = data.astype(dtype)
    #     return data

    # def highlight_columns(self,  colours, background=()):

    def highlight_cells(self, states, colours, background=()):
        """

        Parameters
        ----------
        states
        colours
        background

        Returns
        -------

        """
        # if less colours than number of states are specified
        # if len(colours) < states.max() + 1:
        #     colours = ('default',) + colours
        #  i.e. index zero corresponds to default colour
        #
        # while len(colours) < states.max() + 1:
        #     colours += colours[-1:]
        #  all remaining higher states will be assigned the same colour
        #

        # increase item size of array dtype to accommodate ansi codes
        x = self._formatted.dtype.itemsize // 4
        self._formatted = self._formatted.astype(f'U{x + 15}')

        prop_iter = itt.zip_longest(colours, background, fillvalue='default')
        for i, (txt, bg) in enumerate(prop_iter, 1):
            where = (states == i)
            if np.any(where):
                vapply = np.vectorize(codes.apply)
                self.data[where] = vapply(self.data[where], txt, bg=bg)
            self.state_props.append((txt, dict(bg=bg)))

        # plonk data into _formatted
        # r0 = int(self.has_col_head)
        # c0 = int(self.has_row_head + self.has_row_nrs)
        # self._formatted[r0:, c0:] = self.data

        self.states = np.unique(states)
        self.show_colourbar = False

        return self.data

    # def flag_headers(self, states, *colours, **kws):
    #
    #     states = np.asarray(states, int)
    #     propList = ansi.get_state_dicts(states, *colours, **kws)
    #
    #     # apply colours implied by maximal states sequentially to headers
    #     for i, s in enumerate(('col', 'row')):
    #         h = getattr(self, '%s_headers' % s)
    #         if h is not None:
    #             flags = np.take(propList, states.max(
    #                     i))  # operator.itemgetter(*states.max(0))(propList)
    #             h = ansi.rainbow(h.ravel(), flags)
    #             setattr(self, '%s_headers' % s, h)

    # if self.has_row_head:
    #     rflags = np.take(propList, states.max(0))
    #     self.row_headers = ansi.rainbow(self.row_headers, rflags)
    #
    # if self.has_col_head:
    #     cflags = np.take(propList, states.max(1))
    #     self.row_headers = ansi.rainbow(self.row_headers, cflags)
    #
    # if self.has_row_head:
    #     rflags = np.take(colours, states.max(0))
    #
    #     self.col_headers = as_ansi(self.col_headers, cflags)

    def add_colourbar(self, table, labels=None):
        # ignore default state in colourbar
        # start = int('default' in self.colours)
        labels = labels or self.states
        cbar = ''
        for lbl, props in zip(labels, self.state_props):
            txt, prop_dict = props
            cbar += codes.apply(str(lbl), txt, **prop_dict)

        # cbar = ''.join(map(as_ansi, self.states[start:], self.colours[start:]))
        return '\n'.join((table, cbar))

    # def truncate(self, table ):
    # w,h = get_terminal_size()
    # if len(table[0]) > w:   #all rows have equal length... #np.any( np.array(list(map(len, table))) > w ):

    # use_width = copy(table_width)
    # trunc = lambda row : row
    #
    # if truncate:
    #     #FIXME!
    #     termW,termH = get_terminal_size()

    #     if table_width > termW:
    #         use_width = termW
    #
    #         cs = np.cumsum(self.col_widths)
    #         iq = first_true_index( cs > termW - self.col_widths_true[-1] )
    #         lidx = cs[iq-1] + termW - cs[iq] - 5
    #         uidx = table_width - self.col_widths_true[-1]
    #         trunc = lambda row : row[:lidx] + '<...>' + row[uidx:]
    #     #FIXME!

    # return table

        # def to_latex(self, longtable=True):
    #     """Convert to latex tabular"""
    #     raise NotImplementedError
    #     # TODO
    # to_xlsx = XlsxWriter().write

    def to_xlsx(self, path=None, sheet=None, formats=(), widths=(),
                overwrite=False, **kws):
        from .xlsx import XlsxWriter

        # may need to set widths manually eg. for cells that contain formulae
        return XlsxWriter(self, widths, **kws).write(path, sheet, formats, overwrite)

    def to_latex(self, path=None, style='table', tabsize=2, overwrite=False, **kws):
        from .latex import LatexWriter

        return LatexWriter(self)(path, style, tabsize, overwrite, **kws)
