"""
Pretty printed tables for small data sets
"""


# std
import os
import numbers
import unicodedata
import warnings as wrn
import functools as ftl
import itertools as itt
from dataclasses import dataclass
from shutil import get_terminal_size
from typing import Collection, Union
from collections import UserString, abc

# third-party
import numpy as np
import more_itertools as mit

# local
from recipes.oo import coerce
from recipes.iter import coerced
from recipes.sets import OrderedSet
from recipes.functionals import echo0
from recipes.lists import cosort, where
from recipes.logging import LoggingMixin
from recipes import api, dicts, pprint as ppr
from recipes.decorators import catch, raises as bork

# relative
from .. import codes
from ..utils import resolve_alignment
from ..formatter import Formattable, formatter
from . import summary as sm
from .xlsx import XlsxWriter
from .utils import *
from .utils import _underline
from .column import resolve_columns


# from pydantic.dataclasses import dataclass # for validation!

# ---------------------------------------------------------------------------- #
# defaults as module constants
MID_BORDER = '\N{CURLY BRACKET EXTENSION}'           # '⎪' U+23aa Sm
LEFT_BORDER = '\N{LEFT SQUARE BRACKET EXTENSION}'    # '⎢'
RIGHT_BORDER = '\N{RIGHT SQUARE BRACKET EXTENSION}'  # '⎥'
#  '⋮'      #'\N{LVERTICAL ELLIPSIS}'
# '|' ??
OVERLINE = '‾'  # U+203E
# EMDASH = '—' U+2014
HEADER_ALIGN = '^'
# MAX_WIDTH = None  # TODO
# MAX_LINES = None  # TODO
CONTINUED = ' (continued)'

# ---------------------------------------------------------------------------- #

# defines vectorized length
lengths = np.vectorize(len, [int])


StyleType = Union[str, int, Collection[Union[str, int]]]
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

# TODO: subtitle

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


@dataclass
class Title(Formattable):
    text:   str = None
    # fmt:    Union[str, Callable] = '{: {align}|{fg}/{bg}}'
    # align:  str = '^'
    # fg:     StyleType = None
    # bg:     StyleType = None

    def __str__(self):
        return self.fmt(self.text, align=self.align)


class ColumnHeaders(Formattable):
    # fmt: str = '{:^ |bB_}'
    # units: abc.Sequence = None

    def __init__(self, names: abc.Sequence, fmt: str = '{}', units=()):
        super().__init__(fmt)
        self.names = list(names)
        if units:
            assert len(units) == len(names)
        self.units = list(units)


# ---------------------------------------------------------------------------- #
def split_columns(column, split_nested_types):
    if not (set(split_nested_types) & set(map(type, column))):
        yield column
        return

    # wrap strings
    if str not in split_nested_types:
        column = coerced(column, list, wrap=str)

    yield from itt.zip_longest(*column, fillvalue='')


def unpack_dict(data, split_nested_types=set(), group=(''), level=0):
    #
    for name, col in data.items():
        # Dict indicates group of columns
        if isinstance(col, dict):
            # logger.trace(f'{group=}, {name=}, {level=}')
            yield from unpack_dict(col, split_nested_types, [*group, name], level + 1)
        else:
            # print(f'{group=}, {name=}, {level=}')
            for col in split_columns(col, split_nested_types):
                yield [*group, name], col


def _unpack_convert_dict(data, ignore_keys, converters, header_levels,
                         split_nested_types):

    ignore_keys = ignore_keys or {}
    converters = converters or {}
    header_levels = header_levels or {}

    keep = OrderedSet(data.keys()) - set(ignore_keys)
    data = dict(zip(keep, map(data.get, keep)))

    # headings, columns
    headings, columns = zip(*unpack_dict(data, split_nested_types))
    headings = list(itt.zip_longest(*headings, fillvalue=''))

    # get conversion functions
    type_convert, col_converters = resolve_converters(converters)
    col_converters = resolve_input(col_converters, len(columns),
                                   headings, 'converter')

    for i, (headings, column) in enumerate(zip(zip(*headings), columns)):
        # print(headings, column)
        column = map(col_converters.get(i, type_convert), column)

        title = headings[-1]
        if header_levels.get(title, 0) < 0:
            headings = [*headings[1:], '']

        yield *headings, list(column)


def dict_to_list(data, ignore_keys=None, converters=None, header_levels=None,
                 split_nested_types=set(), order='r'):
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

    *headers, data = zip(*_unpack_convert_dict(
        data, ignore_keys, converters, header_levels, split_nested_types))

    # transpose if needed
    if order.startswith('r'):
        return None, headers, list(zip(*data))

    if order.startswith('c'):
        return headers, None, data

    raise ValueError(f'Invalid value for parameter: {order=!r}')


def check_flag(obj):
    if isinstance(obj, list) or callable(obj):
        return obj

    if isinstance(obj, (str, UserString)):
        return obj.format

    raise TypeError(f'Invalid flag type: {type(obj)}.')


def not_null(obj):
    if obj is None:
        return False

    if isinstance(obj, str):
        return True

    return len(obj) != 0


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

    # The column format specification:
    cell_fmt = '{3}{0:{1}{2}}{4}'
    #  0 - item
    #  1 - alignment
    #  2 - cell width
    #  3 - lhs border
    #  4 - rhs border
    unit_fmt = '[{}]'

    # foot_fmt = None  # '{flag} : {info}'
    _merge_repeat_groups = True
    _nrs_header = '#'

    def resolve_input(self, obj, n_cols=None, what='\b', converter=None,
                      raises=True, default=null, default_factory=None,
                      args=(), **kws):
        # resolve aliases from bottommost header line upwards
        aliases = (self._col_headers, *self.col_groups[::-1])
        if n_cols is None:
            n_cols = self.data.shape[1]

        return resolve_input(obj, n_cols, aliases, what, converter, raises,
                             default, default_factory, args, **kws)

    def resolve_columns(self, key, n_cols, what, raises=True):
        aliases = (self._col_headers, *self.col_groups[::-1])
        # set action raise / warn
        return resolve_columns(key, aliases, n_cols, what,
                               bork(ValueError) if raises else wrn.warn)

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

        # TODO: figure out why it's necessary to explicitly resolve kws here
        synonymns = cls.__init__.__wrapper__.__self__
        args, kws = synonymns.resolve((), kws)
        # keep native types by making columns object arrays
        return cls(np.ma.column_stack([np.ma.array(_, 'O') for _ in columns]),
                   *args, **kws)

    @classmethod
    def from_dict(cls, data, ignore_keys=(), order='r', **kws):

        # keys will be used as row or column headers and values as
        #     data rows or columns, depending on `order` parameter.

        # note that the terse kws will not be replaced here, so you may end up
        # with things like dict(chead=['user given'],
        #                       col_headers=['key in `data` dict'])
        # in which case chead will silently be ignored
        # eg: Table({'hi': [1, 2, 3]}, chead=['haha'])

        # check arguments valid
        assert isinstance(data, dict)
        # assert (order in 'rc'), f'Invalid value for parameter: {order=!r}'

        data, kws = cls._data_from_dict(data, ignore_keys, order, **kws)
        return cls(data, **kws)

    @staticmethod
    def _data_from_dict(data, ignore_keys=(), order='r',  **kws):
        # helper for initialization from dict

        converters = kws.pop('converters', kws.pop('convert', {}))

        *headers, data = dict_to_list(data, ignore_keys, converters,
                                      kws.pop('header_levels', {}),
                                      kws.pop('split_nested', ()),
                                      order)
        row_headers, (*col_groups, col_headers) = headers
        return data, {'row_headers': row_headers,
                      'col_headers': col_headers,
                      'col_groups': zip(*col_groups),
                      **kws}

    # def _resolve_data_and_headers(self, data, **kws):
    #     # special case: dict
    #     if isinstance(data, dict):
    #         data, kws = self._data_from_dict(data, **kws)

    #     if isinstance(data, set):
    #         data = list(data)

    #     # special case: astropy.table.Table
    #     if is_astropy_table(data):
    #         data, col_headers_, units_ = _convert_astropy_table(data)

    #         # replace defaults with those from the astropy table
    #         if col_headers is None:
    #             col_headers = col_headers_
    #         if units is None:
    #             units = units_

    #     # convert to object array
    #     data = np.asanyarray(data, 'O')

    #     # check data shape / dimensions
    #     dim = data.ndim
    #     if dim == 1:
    #         data = data[None]

    #     if dim > 2:
    #         raise ValueError(f'Only 2D data can be tabled! Data is {dim}D')

    #     return data,

    # TODO: test mappings!!

    # mappings for terse kws
    @api.synonyms(
        dicts.merge({
            'units?':                               'units',
            'footnotes?':                           'footnotes',
            # 'formatters?':                        'formatters',
            '(cell_?)white(space)?':                'whitespace',
            'minimal(ist)?':                        'minimalist',
            '((col(umn)?)?_?)widths?':              'widths',
            'c(ol(umn)?_?)groups':                  'col_groups',
            '(row_?)?nrs':                          'row_nrs',
            # 'n(um(be)?)?r?_?rows':                  'row_nrs',
            'n((um(ber)?)|r?)_?rows':               'row_nrs',
            'totals?':                              'totals',
            '(c(ol(umn)?)?_?)?borders?':            'col_borders',
            'vlines':                               'col_borders'
        },
            *({f'{p}head(er)?s?':                   f'{rc}_headers',
               f'{p}head(er)?_prop(erties)?':       f'{rc}_head_props'}
              for rc, p in {'row':  'r(ow)?_?',
                            'col':  'c(ol(umn)?)?_?'}.items())
        ),
        action=None
    )
    def __init__(self,
                 data,
                 *args,
                 # TODO: THIS API:
                 # Table(data,
                 #      # first argument is usually data. Can be array, list, dict
                 #      # to init from  map of columns use `from_columns` constructor.
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
                 # parameters here!

                 title=None,
                 title_align='center',
                 title_props=('underline', ),

                 # ColumnHeaders(names, fmt='{:< |bB}', units)
                 col_headers=None,
                 col_head_props='bold',
                 col_head_align='^',
                 units=None,
                 col_borders=MID_BORDER,

                 col_groups=None,
                 #  core_columns=(),

                 #  order = 'r',
                 # RowHeaders(names, fmt='{:< |bB}', nrs=True)
                 #
                 row_headers=None,
                 row_head_props='bold',
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
        title_props : str, tuple, dict
            ANSICodes property descriptors
        align, title_align, col_head_align: {'left', 'right', 'center', '<', '>', '^', None}
            The column / column header / title alignment
            if None (default)- right align for numerical type data, left align
            for everything else

        col_headers, row_headers  : array_like
            column -, row headers as sequence of str objects.
        col_head_props, row_head_props : str or dict or array_like
            Column header properties.  If `row_nrs` is True,
            the row_head_props will be applied to the number column as well
            TODO: OR a sequence of these, one for each column
        col_groups: array-like
            sequence of strings giving column group names. If given, a group
            header will be added above the columns sharing a common group name.


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
        # logger.debug('SUMMARY {!r}', summary)

        # special case: dict
        if isinstance(data, dict):
            data, kws = self._data_from_dict(data, **kws)
            # return self.__init__(data, **kws)

        if isinstance(data, set):
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
        self.title = title
        self.has_title = title not in (None, False)
        self.title_props = title_props
        self.title_align = resolve_alignment(title_align)

        # get data types of elements for automatic formatting / alignment
        self.col_data_types = []
        for col in data.T:
            use = ~col.mask if np.ma.is_masked(col) else ...
            self.col_data_types.append(set(map(type, col[use])))

        # headers
        self.col_headers = ensure_list(col_headers, str)
        self.row_headers = ensure_list(row_headers, str)
        self.frame = bool(frame)
        self.has_row_nrs = hrn = (row_nrs is not False)
        self.has_row_head = hrh = (row_headers is not None)
        self.n_head_col = hrh + hrn
        self.col_groups = self.resolve_groups(col_groups, n_cols)

        # units
        self.has_units = (units not in (None, {}))
        self.units = None
        if self.has_units:
            units = self.resolve_input(units, n_cols, 'units')
            self.units = list(map(units.get, range(n_cols)))

        # get alignment based on column data types
        self.align = self.get_alignment(align, data, self.get_default_align)
        self.dot_aligned = np.array(where(self.align, '.')) - self.n_head_col
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

        # calculate column totals if required
        self.totals = self.get_totals(data, totals)
        self.has_totals = (self.totals is not None)

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

        # do formatting
        data = self.formatted(data, self.formatters, str(masked), flags, flag_info)

        # add totals row
        if self.has_totals:
            # copy this so we keep totals as numeric types for later work.
            totals = self.formatted(self.totals.copy(), self.formatters, '')
            data = np.vstack((data, totals))

        # column borders
        # print(f'{col_borders = }')
        self.borders = self.resolve_borders(col_borders, frame, n_cols)
        # print(f'{self.borders = } {self.borders.shape = }')

        # Add row / column headers
        # self._col_headers = col_headers  # May be None
        # self.row_headers = row_headers
        self.col_head_props = col_head_props
        # TODO : don't really need this since we have self.highlight
        self.row_head_props = row_head_props

        # insert lines
        self.insert = dict(insert or {})

        # truncate number of rows
        nrows = data.shape[0]
        nomit = nrows - max_rows if np.isfinite(max_rows) else 0
        if nomit > 0:
            self.insert[max_rows - 1] = f'< ... {nomit} rows omitted ... >'
            data = data[:max_rows]

        # add the (row/column) headers / row numbers / totals
        self.pre_table = self.add_headers(data,
                                          row_headers, self.col_headers,
                                          row_nrs)

        # note `pre_table` is dtype='O'
        self.borders = np.array(self.borders)

        self.whitespace = int(whitespace)

        # summarize / compactify
        self.summary = sm.SummaryTable.from_table_api(self, summary)
        self._idx_shown = self.summary.index_shown

        # Next get column widths (without borders)
        # These are either those input by the user, or determined from the
        # content of the columns

        if width is None:
            self.col_widths = measure_column_widths(self.pre_table) + self.whitespace
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

        # row borders
        n_rows, _ = self.pre_table.shape
        # note: headers are index -1
        if hlines is None:
            hlines = []
        elif hlines is ...:
            hlines = np.arange(len(data))
        elif hlines:
            hlines = np.array(hlines)
            hlines[hlines < 0] += n_rows
        else:
            hlines = False

        if hlines is False:
            hlines = []
        else:
            hlines = list(hlines)
            if self.has_col_head:
                hlines.append(-1)

            if self.has_totals and hlines:
                hlines.append(n_rows - self.has_col_head - self.has_units - 2)

        if self.frame:
            hlines.append(n_rows - self.has_col_head - self.has_units - 1)

        self.hlines = sorted(set(hlines))

        # Column specs
        # add whitespace for better legibility
        # self.whitespace = whitespace
        # self.col_widths = self.measure_column_widths()

        # decide column widths
        # self.col_widths, width_max = self.resolve_width(width)

        # if self.insert:
        #     invalid =  set(map(type, self.insert.values())) - {list, str}

        self.highlight = dict(highlight or {})
        self.highlight[-self.has_units - 1] = col_head_props

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

    def resolve_borders(self, col_borders, frame, n_cols):
        # col borders (rhs)
        mid_border = MID_BORDER
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
        # return np.array(list(borders.values()))
        return np.array([*borders.values(), self.RIGHT_BORDER])

        # if self.summarize == 'footnote':

    def __repr__(self):
        # useful in interactive sessions to immediately print the table
        return str(self)

    def __str__(self):
        return self.format() if self.data.size else '<Empty Table>'

    def __format__(self, spec):
        return str(self)

    @property
    def nrows(self):
        return self.data.shape[0]

    @property
    def ncols(self):
        return self.data.shape[1]

    # alias
    n_rows = nrows
    n_cols = ncols

    @property
    def col_headers(self):
        return self._col_headers

    @col_headers.setter
    def col_headers(self, headers):
        if headers := ensure_list(headers, str):
            assert len(headers) == self.data.shape[1]
        self._col_headers = headers

    @property
    def has_col_head(self):
        return bool(self.col_headers)

    @property
    def lcb(self):
        return lengths(self.borders)

    @property
    def row_headers(self):
        return self._row_headers

    @row_headers.setter
    def row_headers(self, headers):
        headers = ensure_list(headers, str)
        if headers:
            assert len(headers) == self.data.shape[0]
        self._row_headers = headers

    @property
    def n_head_rows(self):
        return sum((len(self.col_groups), self.has_col_head, self.has_units))

    @property
    def max_width(self):
        return self._max_width or get_terminal_size()[0]

    @max_width.setter
    def max_width(self, value):
        self._max_width = int(value)

    @property
    def n_head_lines(self):
        """number of newlines in the table header"""
        n = (self.title.count('\n') + 1) if self.has_title else 0
        m = (len(self.summary.items) // self.summary.ncols) if self.summary else 0
        return n + m + self.n_head_rows + self.frame

    def empty_like(self, n_rows, **kws):
        """
        A string representing an empty row of the table. Has the same
        number of columns and column widths as the table.
        """

        filler = [''] * len(self._idx_shown)
        return Table([filler] * n_rows,
                     width=self.measure_column_widths()[self._idx_shown],
                     **kws)

    def allow_summary(self):
        """Check if table allows summarizarion."""
        return (len(self.data) > 1) and self.has_col_head

    def resolve_groups(self, col_groups, n_cols):
        # handle column group headers
        if col_groups is None:
            return []

        col_groups = list(col_groups)
        assert len(col_groups) == n_cols

        col_groups = itt.chain(itt.repeat('', self.n_head_col), col_groups)
        col_groups = coerced(col_groups, list, wrap=str)
        col_groups = itt.zip_longest(*col_groups, fillvalue='')
        # FIXME: too wide col_groups should truncate
        return list(col_groups)

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
        with catch(warn='Could not resolve flags for column {name!r} due '
                   'to the following exception:\n{err}', name=name):
            # get flags
            if callable(flags):
                flags = [flags(val) if val else '' for val in data]

        return flags

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
            with catch(warn='Could not format cell {j} in column {name!r} with'
                       ' formatter {fmt!r} due to the following exception:\n{err}',
                       j=j, name=name, fmt=fmt):
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

    def formatted(self, data, formatters, masked_str='--', flags=None, flag_info=None):
        """convert to array of str"""

        flags = flags or {}
        flag_info = flag_info or {}
        data = np.atleast_2d(data)

        # format custom columns
        for i, fmt in formatters.items():

            col = data[..., i]
            if np.ma.is_masked(col):
                use = np.logical_not(col.mask)
                if ~use.any():
                    continue
            else:
                use = ...

            colname = self.col_headers[i] if self.col_headers else i
            data[use, i], used_flags = self.format_column(
                col[use], fmt, (i in self.dot_aligned), colname, flags.get(i, ()),
            )

            # Create footnotes from flags and info
            for flag in used_flags:
                self._format_column_footnote(i, flag, flag_info)

            if used_flags:
                logger.debug('Columns {} used flags: {}', self.col_headers[i],
                             used_flags)

        # finally set masked str for entire table
        if np.ma.is_masked(data):
            data[data.mask] = masked_str
            data = data.data  # return plain old array

        return data

    def _format_column_footnote(self, i, flag, flag_info):
        foot_fmt = None
        hdr = ''
        if (info := flag_info.get(flag)):
            # footnotes for all columns
            foot_fmt = self.foot_fmt or ' {flag} : {info}'

        elif (info := flag_info.get((hdr := self.col_headers[i]), {}).get(flag)):
            # per column footnotes
            foot_fmt = self.foot_fmt or ' {grp}.{hdr}{flag} : {info}'

        if not foot_fmt:
            wrn.warn(f'Could not resolve description for flag {flag!r} in column {hdr!r}.'
                     + ('You may provide a `dict` to the `footnotes` parameter to'
                        ' describe the flags.' * bool(self.footnotes)))
            return

        if isinstance(foot_fmt, str):
            foot_fmt = foot_fmt.format

        grp = ''
        if self.col_groups:
            grp = self.col_groups[-1][i + self.n_head_col]

        self.footnotes.append(
            foot_fmt(
                flag=flag, info=info, grp=grp, hdr=hdr, tbl=self
            )
        )

    def truncate_cells(self, widths, dots=''):
        # this will probably be quite slow ...
        # note textwrap.shorten does this, but won't handle ANSI

        ict, = np.where(widths < self.col_widths)
        # fixme: if cells contain coded strings???
        ix = lengths(self.pre_table[:, ict]) > widths[ict]

        for l, j, in zip(ix.T, ict):
            w = widths[j]
            for i in np.where(l)[0]:
                self.pre_table[i, j] = truncate(self.pre_table[i, j], w, dots)

    def resolve_widths(self, width):
        # width_min = 0
        # width_max = np.inf

        if width is None:
            # each column will be as wide as the widest data element it contains
            return measure_column_widths(self.pre_table) + self.whitespace

        width = np.array(width)
        if width.size == 1:
            # The table will be made exactly this wide
            width = int(width)  # requested width
            width_ = width - self.lcb.sum()

            # Split table if columns too wide for requested width
            col_widths = measure_column_widths(self.pre_table) + self.whitespace
            if col_widths.sum() > width_:
                self.max_width = width
                return col_widths

            # Apportion column widths
            return justify_widths(col_widths, width_)

        if np.any(width <= 0):
            raise ValueError('Column widths must be positive.')

        if width.size == self.data.shape[1]:
            # each column width specified
            return np.array(width)
            # hcw = self.col_widths[:self.n_head_col]
            # return np.r_[hcw, width]

        if width.size == self.data.shape[1] + self.has_row_head:
            # each column width specified
            return width

        if isinstance(width, range):
            # maximum table width given.
            raise NotImplementedError
            width_min = width.start
            width_max = width.stop

        raise ValueError(f'Cannot interpret width {str(width)!r}')

    def measure_column_widths(self, data=None, count_hidden=False, with_borders=False):
        """data should be string type array"""
        # note now pretty much redundant

        if data is None:
            data = self.pre_table

        # get width of columns - widest element in column
        w = measure_column_widths(data, count_hidden=count_hidden) + self.whitespace

        # add border size
        if with_borders:
            w += self.lcb
        return w

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

        # row headers are left aligned, row nrs right aligned
        return ''.join(('<' * self.has_row_head,
                        '>' * self.has_row_nrs,
                        *cosort(*zip(*alignment.items()))[1]))

        # dot_aligned = np.array(where(align, '.')) - self.n_head_col
        # align = align.replace('.', '<')
        # return align

    def get_default_align(self, col_idx):
        types = self.col_data_types[col_idx]
        if len(types) != 1:
            return '<'

        # all data in this column is of the same type
        type_, = types
        if issubclass(type_, numbers.Integral):
            return '>'

        if issubclass(type_, numbers.Real):
            return '.'

        return '<'

    def get_totals(self, data, col_indices):
        """compute totals for columns at `col_indices`"""

        # suppress totals for tables with single row
        if data.shape[0] <= 1:
            if col_indices is not None:
                self.logger.debug('Suppressing redundant totals line for table '
                                  'with single row of data.')
            return

        if col_indices in (None, False):
            return

        # boolean True ==> compute totals for all
        n_cols = data.shape[1]
        if col_indices is True:
            col_indices = np.arange(n_cols)

        totals = np.ma.masked_all(n_cols, 'O')
        for i in col_indices:
            for i in self.resolve_columns(i, n_cols, 'totals'):
                if totals[i]:
                    continue

                # attempt to compute total
                try:
                    totals[i] = np.sum(list(filter(None, data[:, i])))
                except Exception as err:
                    wrn.warn(
                        f'Could not compute total for column {i} due to the '
                        f'following exception: {err}')

        return totals  # np.ma.array(totals, object)

    # @expose.args()
    # @staticmethod

    def add_headers(self, data,
                    row_headers=None,
                    col_headers=None,
                    row_nrs=False):
        """Add row and column headers to table data"""

        # row and column headers
        rheads, cheads = self.get_header_blocks(row_headers, row_nrs, col_headers)

        if cheads:
            data = np.ma.vstack((cheads, data))

        if rheads:
            data = np.ma.hstack((np.atleast_2d(rheads).T, data))

        return data

    def get_header_blocks(self, row_headers=None, row_nrs=False, col_headers=None):
        # row and column headers
        # TODO: error check for len of row/col_headers
        rheads, cheads = [], []

        has_row_head = not_null(row_headers)
        has_col_head = not_null(col_headers)

        if has_row_head and self.has_totals:
            row_headers = [*row_headers, 'Totals']

        if has_col_head:
            cheads.append(col_headers)

            # NOTE: when both are given, the 0,0 table position is ambiguously
            #  both column and row header
            if has_row_head:  # and (len(row_headers) == data.shape[0] - 1):
                row_headers = ['', *row_headers]
                self.borders = [self.borders[0], *self.borders]
        elif has_row_head:
            row_headers = ['', *row_headers]

        if self.has_units:
            cheads.append(
                [self.unit_fmt.format(u) if u else '' for u in self.units]
            )
            if has_row_head:
                row_headers = ['', *row_headers]

        if has_row_head:
            rheads.append(row_headers)

        # add row numbers
        if self.has_row_nrs:  # (row_nrs is not False)
            nr = int(row_nrs)
            rheads.append([*([self._nrs_header] * has_col_head),
                           *([''] * self.has_units),
                           *np.arange(nr, self.nrows + nr).astype(str),
                           *([''] * self.has_totals)])

            self.borders = [self.borders[0], *self.borders]

        return rheads, cheads
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

        max_width = max_width or self.max_width
        split_tables = []

        widths = self.col_widths[self._idx_shown] + self.lcb[self._idx_shown]
        rhw = widths[:self.n_head_col].sum()  # row header width

        # location of current split
        first = True
        splix = self.n_head_col
        while splix != self._idx_shown[-1]:
            # cumulative total column width
            ctcw = np.cumsum(widths[splix:])
            # indices of columns beyond max allowed width
            ix, = np.where(ctcw + rhw > max_width)
            # idx_shown = self._idx_shown[splix:ix[0]]

            if len(ix):  # need to split
                # need at least one column to build table
                endix = splix + max(ix[0], 1)
                if ix[0] == 0:  # first column + row headers too wide to display
                    'TODO: truncate'
            else:
                endix = None

            # make a table using selection of columns
            idx_show = np.r_[self._idx_shown[:self.n_head_col],
                             self._idx_shown[splix:endix]]

            split_tables.append(
                '\n'.join(map(str, self._build(idx_show, not first and bool(splix))))
            )

            if endix is None:
                break
            splix = endix
            first = False

        return split_tables

    def make_title(self, width, continued=False):
        """make title line"""
        text = self.title + (CONTINUED if continued else '')
        return self.make_merged_cell(text, width, self.title_align,
                                     self.title_props)

    def _get_heading_lines(self, idx, table_width, continued):
        # title
        if self.has_title:
            yield self.make_title(table_width, continued)

        # FIXME: problems with too-wide column

        # summarized columns
        if (self.summary.loc == 0) and self.summary.items:
            # if isinstance(self.summarize, (numbers.Integral)):
            # display summarized columns in single row
            yield self.make_merged_cell(str(self.inset),
                                        table_width,
                                        style=['underline' * self.frame])

        # check inset width
        column_width_total = (len(self.LEFT_BORDER) + self.col_widths[idx] + self.lcb[idx]).sum()
        if table_width > column_width_total:
            # This means the inset table is wider than the main table and we
            # need to add some space to the columns
            self.col_widths[self._idx_shown] += apportion(
                table_width - column_width_total, len(self._idx_shown))

        yield from self._get_group_heading_lines(idx)

    def _get_group_heading_lines(self, idx):
        # column groups
        # see :  xslx.merge_duplicate_cells
        for groups in self.col_groups:
            line = self.LEFT_BORDER if self.frame else ''
            lbl = groups[idx[0]]  # name of current group
            gw = 0  # width of current column group header

            # FIXME: this code below in `format cell??`
            for i, j in enumerate(idx):
                name = groups[j]
                w = self.col_widths[j] + self.lcb[j]  # + (j-i)  #
                if (name == lbl):  # and (self._merge_repeat_groups or gw == 0)
                    # still within the same group
                    gw += w
                else:
                    # reached a new group. write previous group
                    if len(lbl) >= gw:
                        lbl = truncate(lbl, gw - 1)

                    line += f'{lbl: ^{gw - 1}}{self.borders[j]}'

                    gw = w
                    lbl = name

            # last bit
            if gw:
                line += f'{lbl: ^{gw - 1}}{self.RIGHT_BORDER}'
            #
            if self.hlines:
                # only underline if headers are underlined
                line = _underline(line)

            yield line

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
        list of str (table rows)
        """
        table = []
        idx = self._idx_shown if column_indices is None else column_indices
        part_table = self.pre_table[:, idx]
        table_width = self.get_width(idx)

        if self.frame:
            # top line
            # NOTE: ANSI overline not supported (linux terminal) use underlined
            #  whitespace
            top_line = _underline(' ' * table_width)
            table.append(top_line)

        # header block
        table.extend(self._get_heading_lines(idx, table_width, continued))

        # make rows
        start = -(self.has_col_head + self.has_units)

        widths = self.col_widths[idx]
        alignment = itt.chain(itt.repeat(self.col_head_align[idx], -start),
                              itt.repeat(self.align[idx]))

        left = list(mit.padded(self.LEFT_BORDER, '', len(idx)))
        right = self.borders[idx]
        borders = (left, right)

        # left = [self.LEFT_BORDER, [''] * len(indices)]
        # borders = list(itt.zip_longest(self.LEFT_BORDER, self.borders[idx],
        #                           fillvalue=''))

        used = set()
        for i, row_cells in enumerate(part_table, start):
            insert = self.insert.get(i, None)
            if insert is not None:
                table.extend(self.insert_lines(insert, table_width))
                used.add(i)

            row_props = self.highlight.get(i)
            underline = (i in self.hlines)
            table.extend(
                codes.apply(row, row_props)
                for row in self._row_lines(
                    row_cells, widths, next(alignment), borders, underline)
            )
            # fixme: maybe don't apply to border symbols

        # check if all insert lines have been consumed
        unused = set(self.insert.keys()) - used
        for i in unused:
            table.extend(self.insert_lines(self.insert[i], table_width))

        # finally add any footnotes present
        if len(self.footnotes):
            table.extend(self.footnotes)

        return table

    def _row_lines(self, cells, widths, alignment, borders, underline=False):
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
        # from IPython import embed
        # embed(header="Embedded interpreter at 'src/motley/table/table.py':1687")

        # handle multi-line cell elements
        lines = [col.split('\n') for col in cells]
        # NOTE: using str.splitlines here creates empty sequences for cells
        #  with empty strings as contents.  This is undesired since this
        #  generator will then yield nothing instead of a formatted row
        n_lines = max(map(len, lines))

        for i, row_items in enumerate(itt.zip_longest(*lines, fillvalue='')):
            row = self._row_stack_cells(row_items, widths, alignment, borders)
            if (i + 1 == n_lines) and underline:
                row = _underline(row)
            yield row

    def _row_stack_cells(self, cells, widths, alignment, borders):

        # format cells
        first, *cells = map(self.format_cell, cells, widths, alignment, *borders)

        # Apply properties to whitespace filled row headers
        if self.has_row_head:
            first = codes.apply(first, self.row_head_props)

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

        style = coerce(style or [], to=list, wrap=str, ignore=dict)  # list / dict
        lines = text.split(os.linesep)

        if ('underline' in style):
            # only underline last line for multi-line element
            style.remove('underline')
            styles = itt.chain(itt.repeat(style, len(lines) - 1),
                               [(*style, 'underline')])
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
        x = self.pre_table.dtype.itemsize // 4
        self.pre_table = self.pre_table.astype(f'U{x + 15}')

        prop_iter = itt.zip_longest(colours, background, fillvalue='default')
        for i, (txt, bg) in enumerate(prop_iter, 1):
            where = (states == i)
            if np.any(where):
                vapply = np.vectorize(codes.apply)
                self.data[where] = vapply(self.data[where], txt, bg=bg)
            self.state_props.append((txt, dict(bg=bg)))

        # plonk data into pre_table
        # r0 = int(self.has_col_head)
        # c0 = int(self.has_row_head + self.has_row_nrs)
        # self.pre_table[r0:, c0:] = self.data

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

    def to_xlsx(self, path=None, widths=(), **kws):
        # may need to set widths manually eg. for cells that contain formulae
        return XlsxWriter(self, widths, **kws).write(path)
