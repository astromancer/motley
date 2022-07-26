"""
Pretty printed tables for small data sets
"""


# std
import os
import numbers
import warnings as wrn
import functools as ftl
import itertools as itt
from collections import abc
from dataclasses import dataclass
from shutil import get_terminal_size
from typing import Callable, Collection, Union

# third-party
import numpy as np

# local
from recipes.dicts import merge
from recipes.lists import where
from recipes.sets import OrderedSet
from recipes.functionals import echo0
from recipes import api, pprint as ppr
from recipes.logging import LoggingMixin
from recipes.decorators import raises as bork

# relative
from .. import ansi, codes
from .xlsx import XlsxWriter
from .column import resolve_columns, get_default_align
from ..utils import resolve_alignment
from .utils import *
from .utils import _underline
from ..formatter import stylize


# if __name__ == '__main__':
# do Tests
# TODO: print pretty things:
# http://misc.flogisoft.com/bash/tip_colors_and_formatting
# http://askubuntu.com/questions/512525/how-to-enable-24bit-true-color-support-in-gnome-terminal
# https://github.com/robertknight/konsole/blob/master/tests/color-spaces.pl


# defaults as module constants
DOTS = '…'  # single character ellipsis u"\u2026" to indicate truncation
BORDER = '⎪'  # U+23aa Sm CURLY BRACKET EXTENSION ⎪  # '|'
OVERLINE = '‾'  # U+203E
# EMDASH = '—' U+2014
HEADER_ALIGN = '^'
# MAX_WIDTH = None  # TODO
# MAX_LINES = None  # TODO
KNOWN_COMPACT_KEYS = {'header', 'ignore', 'footnote'}

# TODO: dynamical set attributes like title/headers/nrs/data/totals
# TODO: unit tests!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# TODO: GIST
# TODO: HIGHLIGHT COLUMNS
# TODO: OPTION for plain text row borders?

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


# defines vectorized length
lengths = np.vectorize(len, [int])


# from pydantic.dataclasses import dataclass # for validation!


StyleType = Union[str, int, Collection[Union[str, int]]]


@dataclass
class Title:
    text:   str = None
    fmt:    Union[str, Callable] = '{: {align}|{fg}/{bg}}'
    align:  str = '^'
    fg:     StyleType = None
    bg:     StyleType = None

    def __post_init__(self):
        if isinstance(self.fmt, str):
            self.fmt = stylize(self.fmt, fg=self.fg, bg=self.bg).format

    def __str__(self):
        return self.fmt(self.text, align=self.align)


def split_columns(column, split_nested_types):
    if not (set(split_nested_types) & set(map(type, column))):
        yield column
        return

    # wrap strings
    if str not in split_nested_types:
        column = wrap_strings(column)

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


def dict_to_list(data, ignore_keys={}, converters={}, header_levels={},
                 split_nested_types=set(),  order='r'):
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


class Table(LoggingMixin):
    # TODO split ConsoleWriter(TableWriter)
    """
    A table formatter. Good for displaying data. Definitely not for data
    manipulation (yet). Plays nicely with ANSI colours and multi-line cell
    elements.
    """

    _default_border = BORDER  # TODO move to module scope

    # The column format specification:
    #  0 - item; 1 - fill width; 2 - align; 3 - border (rhs); 4 - border (lhs)
    cell_fmt = '{4}{0:{2}{1}}{3}'

    # title_fmt = cell_fmt.join(_default_border * 2)

    _foot_fmt = '{}: {}'

    _nrs_header = '#'

    def resolve_input(self, obj, n_cols=None, what='\r', converter=None,
                      raises=True, default_factory=None, args=(), **kws):
        # resolve aliases from bottommost header line upwards
        aliases = (self._col_headers, *self.col_groups[::-1])
        if n_cols is None:
            n_cols = self.data.shape[1]
        return resolve_input(obj, n_cols, aliases, what, converter, raises,
                             default_factory, args, **kws)

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
        # keep native types by making columns object arrays
        return cls(np.ma.column_stack([np.ma.array(a, 'O') for a in columns]),
                   **kws)

    @classmethod
    def from_dict(cls, data, ignore_keys=(), order='r', **kws):
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
    @api.Synonyms(
        merge({
            'units?':                               'units',
            'footnotes?':                           'footnotes',
            # 'formatters?':                        'formatters',
            'cell_white(space)?':                   'cell_whitespace',
            'minimal(ist)?':                        'minimalist',
            '((col(umn)?)?_?)widths?':              'widths',
            'c(ol(umn)?_?)groups':                  'col_groups',
            '(row_?)?nrs':                          'row_nrs',
            # 'n(um(be)?)?r?_?rows':                  'row_nrs',
            'n((um(ber)?)|r?)_?rows':               'row_nrs',
            'totals?':                              'totals',
            'c(ol(umn)?)?_?borders?':               'col_borders',
            'vlines':                               'col_borders'
        },
            *({f'{p}head(er)?s?':                   f'{rc}_headers',
               f'{p}head(er)?_prop(erties)?':       f'{rc}_head_props'}
              for rc, p in {'row':  'r(ow)?_?',
                            'col':  'c(ol(umn)?)?_?'}.items())
        ),
        mode='regex',
        emit='ignore'
    )
    def __init__(self,
                 data,
                 *args,
                 # TODO: THIS API:
                 # Table(data,  # first argument is usually data. Can be array, list, dict
                 # # to init from  map of columns use `from_columns` constructor
                 #       Title('{"MY DATA TABLE":^s|Bg_/c}'),
                 #       ColumnHeaders(headers, fmt='{:^ |bB_}', units),
                 #       ColumnGroups(group_names, fmt='{:^ |B_}'),
                 #       # starting number for enumeration
                 #       RowHeaders(nrs=0, names=row_names, fmt='<q|B'),
                 #                  nrs_fmt=lambda: '',)
                 #       frame=True, # this is the default, False or None turns it off
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
                 col_borders=_default_border,

                 col_groups=None,
                 core_columns=(),

                 # RowTitles(names, fmt='{:< |bB}', nrs=True)
                 #
                 row_headers=None,
                 row_head_props='bold',
                 row_nrs=False,

                 max_rows=np.inf,
                 hlines=None,

                 # styling
                 frame=True,
                 compact=False,

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
                 cell_whitespace=1,
                 totals=None,

                 flags=None,
                 insert=None,
                 highlight=None,
                 footnotes='',
                 **kws):

        # TODO: style='matrix', 'bare', 'spreadsheet'
        """
        A table representation of `data`.

        Parameters
        ----------
        data : array_like or dict
            input data - must be 1D, 2D
            if dict, keys will be used as row_headers, and values as data
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
        compact : bool or int or str #TODO or list of str ?? or dict
            Suppress columns for which data values are all identical and print
            them in a compact fashion as key-value pairs. There are various
            styles of doing this, depending on the type and value of this
            parameter. Compact representation will only be applied if the table
            contains more than one row of data.
            If str: {'drop', 'footnote', 'header'}
                'drop': Compactable columns are simply ignored.
                'footnote': Compactable columns are printed as key value pairs 
                            in the table footnote.
                'header': Key-value pairs printed in the table header below the
                          table title and above the column headers. An integer
                          value can be used to control the number of columns to
                          use for this compact inset table. By default the
                          maximum allowable number of columns given the
                          available space is used (see below).
            If int: 
                This specifies the number of columns to use in the inset table.
            If True, the default:
                The number of columns will be decided automatically to optimize
                space.
        #TODO: core_columns: tuple or list
            Names of the column's that cannot be removed by compacting.

        ignore_keys : sequence of str
            if dictionary is passed as data, optionally specify the keys that
            will not be printed in table
        order : {'r', 'c', 'row', 'col'}
            Used when table is initialized from dict, or when data is 1
            dimensional to know whether values should be interpreted as
            rows or columns. Default is to interpret 1D data as a column with
            row headers.
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

        cell_whitespace: int
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

        flags: dict
            string type flags that will be appended to the entries of the
            corresponding column

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

        footnotes: str
            Any footnote that will be added to the bottom of the table.
            Useful to explain the meaning of `flags`

        # TODO: list attributes here
        """

        # FIXME: precision etc ignored when init from dict
        # FIXME: hlines with cell elements that have ansi ... effects don't
        #  stack...

        # FIXME: move construction for types dispatch to __new__

        # from recipes import pprint
        # pprint.mapping(locals(), ignore=['self'])

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
        data = np.asanyarray(data, 'O')

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
        self.col_headers = ensure_list(col_headers)
        self.row_headers = ensure_list(row_headers)
        self.frame = bool(frame)
        self.has_row_nrs = hrn = (row_nrs is not False)
        self.has_row_head = hrh = (row_headers is not None)
        self.has_col_head = bool(self._col_headers)
        self.n_head_col = hrh + hrn
        self.col_groups = self.resolve_groups(col_groups, n_cols)

        # units
        self.has_units = (units not in (None, {}))
        self.units = None

        if self.has_units:
            units = self.resolve_input(units, n_cols, 'units')
            self.units = []
            for i in range(n_cols):
                u = units.get(i)
                self.units.append('[{}]'.format(u) if u else '')

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

        # get flags
        flags = self.resolve_input(flags, n_cols, 'flags')

        # calculate column totals if required
        self.totals = self.get_totals(data, totals)
        self.has_totals = (self.totals is not None)

        # FIXME: ALL STUFF BELOW HERE SHOULD BE DYNAMIC!!
        # do formatting
        data = self.formatted(data, self.formatters, str(masked), flags)

        # add totals row
        if self.has_totals:
            # copy this so we keep totals as numeric types for later work.
            totals = self.formatted(self.totals.copy(), self.formatters, '')
            data = np.vstack((data, totals))

        # col borders (rhs)
        borders = self.resolve_input(col_borders, n_cols + 1, 'border', str,
                                     default_factory=lambda: self._default_border)
        self.borders = np.array(list(borders.values()))
        self.lcb = lengths(self.borders)

        # TODO: row / col sort here
        # Add row / column headers
        # self._col_headers = col_headers  # May be None
        # self.row_headers = row_headers
        self.col_head_props = col_head_props
        # todo : don't really need this since we have self.highlight
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
        self.pre_table = self.add_headers(data, row_headers, col_headers,
                                          row_nrs)
        # note `pre_table` is dtype='O'

        self.cell_white = int(cell_whitespace)

        # compactify
        self.compact_items = {}
        self._idx_shown = np.arange(n_cols + hrh + hrn)

        self._compact_footer = False
        self.compact, dont_remove = self._resolve_compact(compact)

        if self.compact:
            self.compactify(dont_remove)
            # requested_width = requested_width[shown]

        # Next get column widths (without borders)
        # These are either those input by the user, or determined from the
        # content of the columns
        self.col_widths = get_column_widths(self.pre_table) + self.cell_white

        # NOTE: next block needs to happen after `self.col_widths` assigned
        self._compact_table = None
        has_compact = self.has_compact()
        if has_compact:
            # this is an instance of `Table`!!
            self._compact_table = self._get_compact_table()

        # check for too-wide title or compacted lines, and amend column widths
        # to match
        # todo method here
        tw = 0
        if self.has_title or has_compact:
            if has_compact:
                tw = self._compact_table.get_width()

            # use explicit split('\n') below instead of splitlines since the
            # former yields a non-empty sequence for title=''
            tw = 0
            if self.has_title:
                tw = max(lengths(self.title.split('\n')).max(), tw)

            w = self.get_width() - 1  # -1 to exclude lhs / rhs borders
            cw = self.col_widths[self._idx_shown]
            if tw > w:
                d = tw - w
                idx = itt.cycle(self._idx_shown)
                while d:
                    self.col_widths[next(idx)] += 1
                    d -= 1

        if width is not None:
            requested_widths = self.resolve_widths(width)
            if np.any(requested_widths <= 0):
                raise ValueError('Column widths must be positive.')

            # if requested widths are smaller than that required to fully
            # display widest item in the column, truncate all too-wide items
            # in that column
            self.truncate_cells(requested_widths)
            self.col_widths = requested_widths

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
        # self.cell_white = cell_whitespace
        # self.col_widths = self.get_column_widths()

        # decide column widths
        # self.col_widths, width_max = self.resolve_width(width)

        # if self.insert:
        #     invalid =  set(map(type, self.insert.values())) - {list, str}

        self.highlight = dict(highlight or {})
        self.highlight[-self.has_units - 1] = col_head_props

        # init rows
        self.rows = []
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
        if footnotes is None:
            footnotes = []
        if isinstance(footnotes, str):
            footnotes = footnotes.splitlines()

        self.footnotes = list(footnotes)

        # if self.compact == 'footnote':

    def __repr__(self):
        # useful in interactive sessions to immediately print the table
        return str(self)

    def __str__(self):
        if self.data.size:
            return self.format()
        return '<Empty Table>'

    def __format__(self, spec):
        return str(self)

    @property
    def n_cols(self):
        return self.data.shape[1]

    @property
    def col_headers(self):
        return self._col_headers

    @col_headers.setter
    def col_headers(self, headers):
        headers = ensure_list(headers)
        if headers:
            assert len(headers) == self.data.shape[1]
        self._col_headers = headers

    @property
    def row_headers(self):
        return self._row_headers

    @row_headers.setter
    def row_headers(self, headers):
        headers = ensure_list(headers)
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
        m = len(self.compact_items) // int(self.compact) if self.compact else 0
        return n + m + self.n_head_rows + self.frame

    @property
    def idx_compact(self):
        n = self.data.shape[1] + self.n_head_col
        return np.setdiff1d(np.arange(n), self._idx_shown)

    def empty_like(self, n_rows, **kws):
        """
        A string representing an empty row of the table. Has the same
        number of columns and column widths as the table.
        """

        filler = [''] * len(self._idx_shown)
        return Table([filler] * n_rows,
                     width=self.get_column_widths()[self._idx_shown],
                     **kws)

    def resolve_groups(self, col_groups, n_cols):
        # handle column group headers
        if col_groups is None:
            return []

        col_groups = list(col_groups)
        assert len(col_groups) == n_cols

        col_groups = itt.chain(itt.repeat('', self.n_head_col), col_groups)
        col_groups = wrap_strings(col_groups)
        col_groups = itt.zip_longest(*col_groups, fillvalue='')
        # FIXME: too wide col_groups should truncate
        return list(col_groups)

    def _resolve_compact(self, compact):
        dont_remove = ()
        if self.allow_compact():
            if isinstance(compact, abc.MutableMapping):
                if (nope := set(compact.keys()) - KNOWN_COMPACT_KEYS):
                    raise ValueError(f'Invalid keys: {nope} in `compact` dict.')

                dont_remove = compact.pop('ignore', ())

                for key in ('header', 'headnotes', 'footnotes'):
                    if key in compact:
                        compact = compact[key]
                        self._compact_footer = key.startswith('foot')
                        break

            elif not isinstance(compact, (numbers.Integral, str)):
                raise ValueError(f'`compact` parameter should be bool, int, '
                                 f'str, dictnot {type(compact)}.')

        elif compact:
            wrn.warn(f'Ignoring request to compact with {compact!r}, since '
                     'table has no column headers, or insufficient data.')
            compact = False

        return compact, dont_remove

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

        if len(types_) == 1:
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

            #  NOTE: single dispatch not a good option here due to formatting
            #   subtleties
            # return formatter.registry[type_](None, precision=precision,
            #                                  compact=minimalist,
            #                                  sign=sign,
            #                                  right_pad=right_pad)

        return ppr.PrettyPrinter(precision=precision, minimalist=short).pformat

    def format_column(self, data, fmt, dot_align, flags):
        # wrap the formatting in try, except since it's usually not
        # critical that it works and getting some info is better than none
        result = []
        for j, cell in enumerate(data):
            try:
                formatted = fmt(cell)
            except Exception as err:
                wrn.warn(f'Could not format cell {j} with {fmt!r} due to:\n'
                         f'{err}')
                formatted = str(cell)

            result.append(formatted)
            # result = np.vectorize(str, (str, ))(data)

        # special alignment on '.' for float columns
        if dot_align:
            result = ppr.align_dot(result)

        # concatenate data with flags
        # flags = flags.get(i)
        if flags:
            try:
                result = np.char.add(result,  # .astype(str)
                                     list(map(str, flags)))
            except Exception as err:
                wrn.warn(f'Could not append flags to formatted data for '
                         f'column due to the following '
                         f'exception:\n{err}')
        return result

    def formatted(self, data, formatters, masked_str='--', flags=None):
        """convert to array of str"""

        # if self.
        flags = flags or {}
        data = np.atleast_2d(data)

        # format custom columns
        for i, fmt in formatters.items():

            # Todo: formatting for row_headers...
            if fmt is None:
                # null format means convert to str, need everything in array
                # to be str to prevent errors downstream
                # (data is dtype='O')
                fmt = str

            col = data[..., i]
            if np.ma.is_masked(col):
                use = np.logical_not(col.mask)
                if ~use.any():
                    continue
            else:
                use = ...

            data[use, i] = self.format_column(col[use], fmt,
                                              i in self.dot_aligned,
                                              flags.get(i, ()))

        # finally set masked str for entire table
        if np.ma.is_masked(data):
            data[data.mask] = masked_str
            data = data.data  # return plain old array

        return data

    def get_default_align(self, col_idx):
        #
        ts = self.col_data_types[col_idx]
        if len(ts) == 1:
            # all data in this column is of the same type
            typ, = ts
            if issubclass(typ, numbers.Integral):
                return '>'
            if issubclass(typ, numbers.Real):
                return '.'

        return '<'

    def resolve_widths(self, width):
        width_min = 0
        width_max = None
        # if width is None:
        #     # each column will be as wide as the widest data element it contains
        #     widths =
        #     #
        #     get_column_widths(self.pre_table)
        width = np.array(width)
        if width.size == self.data.shape[1] + self.has_row_head:
            # each column width specified
            return width

        if np.size(width) == 1:
            # The table will be made exactly this wide
            width = int(width)  # requested width
            # TODO: DECIDE COL WIDTHS
            raise NotImplementedError

        if np.size(width) == self.data.shape[1]:
            # each column width specified
            hcw = self.col_widths[:self.n_head_col]
            return np.r_[hcw, width]

        if isinstance(width, range):
            # maximum table width given.
            raise NotImplementedError
            width_min = width.start
            width_max = width.stop

        raise ValueError(f'Cannot interpret width {str(width)!r}')

        # return col_widths  # , width_max

    def compactable_columns(self, ignore=()):
        if not self.allow_compact():
            return ()

        idx_same, = np.where(np.all(self.data == self.data[0], 0))

        idx_ign = []
        if any(ignore):
            *_, idx_ign = np.where(self.col_headers == np.atleast_2d(ignore).T)

        idx_same = np.setdiff1d(idx_same, idx_ign)  # + self.n_head_col
        return idx_same

    def allow_compact(self):
        """Check if table allows compact representation"""
        return (len(self.data) > 1) and self.has_col_head

    def has_compact(self):
        return bool((self.compact != 'drop') and self.compact_items)

    def _get_ctable_widths(self):
        if not self.has_compact():
            return

        return (
            # Widths for key-val pairs:                            + 3 for ' = '
            np.char.str_len(list(self.compact_items.items())).sum(1) + 3,
            # this is the width of the compacted columns
            self.lcb[self.idx_compact] + self.cell_white
        )

    def _min_ctable_width(self):
        if self.has_compact():
            return sum(self._get_ctable_widths()).max()
        return 0

    def compactify(self, ignore=()):
        """
        check which columns contain single unique value duplicated. These data
        are represented as a sub-header in the table.  This makes for a more
        compact representation of the same data.

        Parameters
        ----------
        data
        col_headers

        Returns
        -------

        """

        # columns for which all data identical
        # end = -1 if self.has_totals else None
        data = self.data
        if (len(data) <= 1) or not self.has_col_head:
            self.logger.warning(
                'Requested `compact` representation, but no column headers '
                'provided. Ignoring.'
            )
            return ...

        # if a total is asked for on a column, make sure we don't suppress it
        idx_squash = np.setdiff1d(self.compactable_columns(ignore),
                                  np.nonzero(self.totals)[0])
        val_squash = self.data[0, idx_squash]
        idx_show = np.setdiff1d(range(self.data.shape[1]), idx_squash)
        idx_show = np.r_[np.arange(self.n_head_col), idx_show + self.n_head_col]
        # check if any data left to display
        if idx_show.size == 0:
            self.logger.warning('No data left in table after compacting '
                                'singular value columns.')

        # remove columns
        # self.col_data_types = np.take(self.col_data_types, idx_show[nhc:] - nhc)
        self._idx_shown = idx_show
        self.compact_items = dict(zip(np.take(self.col_headers, idx_squash),
                                      val_squash))

        # self.pre_table = self.pre_table[:, idx_show]
        # self.col_widths = self.col_widths[idx_show]
        # self.align = self.align[idx_show]
        #
        # if self.col_groups is not None:
        #     self.col_groups = np.take(self.col_groups, idx_show)

        return idx_show  # , col_headers

    def truncate_cells(self, requested_width):
        # this will probably be quite slow ...
        # note textwrap.shorten does this, but won't handle ANSI

        ict, = np.where(requested_width < self.col_widths)
        # fixme: if cells contain coded strings???
        ix = lengths(self.pre_table[:, ict]) > requested_width[ict]

        for l, j, in zip(ix.T, ict):
            w = requested_width[j]
            for i in np.where(l)[0]:
                self.pre_table[i, j] = truncate(self.pre_table[i, j], w)

    def get_column_widths(self, data=None, count_hidden=False,
                          with_borders=False):
        """data should be string type array"""
        # note now pretty much redundant

        if data is None:
            data = self.pre_table

        # get width of columns - widest element in column
        w = get_column_widths(data, count_hidden=count_hidden) + self.cell_white

        # add border size
        if with_borders:
            w += self.lcb
        return w

    def get_width(self, indices=None):
        """get table width"""
        if indices is None:
            indices = self._idx_shown

        # NOTE this excludes the lhs starting border
        width = (self.col_widths[indices] + self.lcb[indices]).sum()
        if self._compact_table:
            return max(width, self._compact_table.get_width() + 1)
        return max(width, self._min_ctable_width())

    def get_alignment(self, align, data, default_factory):
        """get alignment array for columns"""
        alignment = self.resolve_input(align, data.shape[1],
                                       'alignment', resolve_alignment,
                                       default_factory=default_factory)
        # make align an array with same size as nr of columns in table

        # row headers are left aligned
        return '<' * self.n_head_col + ''.join(alignment.values())
        # dot_aligned = np.array(where(align, '.')) - self.n_head_col
        # align = align.replace('.', '<')
        # return align

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
                    totals[i] = sum(filter(None, data[:, i]))
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
        # TODO: error check for len of row/col_headers
        has_row_head = row_headers is not None
        has_col_head = col_headers is not None

        if has_row_head and self.has_totals:
            row_headers = [row_headers, 'Totals']

        if self.has_units:
            data = np.ma.vstack((self.units, data))
            if has_row_head:
                row_headers = ['', *row_headers]

        if has_col_head:
            data = np.ma.vstack((col_headers, data))

            # NOTE: when both are given, the 0,0 table position is ambiguously
            #  both column and row header
            if has_row_head:  # and (len(row_headers) == data.shape[0] - 1):
                row_headers = ['', *row_headers]

        if has_row_head:
            row_head_col = np.atleast_2d(row_headers).T
            data = np.ma.hstack((row_head_col, data))

        # add row numbers
        if self.has_row_nrs:  # (row_nrs is not False)
            nr = int(row_nrs)
            nrs = np.arange(nr, data.shape[0] + nr).astype(str)
            if self.has_units:
                # self.units = [''] + self.units
                nrs = ['', *nrs[:-1]]

            if has_col_head:
                nrs = [self._nrs_header, *nrs[:-1]]

            if self.has_totals:
                nrs[-1] = ''

            data = np.c_[nrs, data]

        return data

    def make_title(self, width, continued=False):
        """make title line"""
        text = self.title + (' (continued)' if continued else '')
        return self.build_long_line(text, width, self.title_align,
                                    self.title_props)

    def gen_multiline_rows(self, cells, widths, alignment, borders,
                           underline=False):
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
        n_lines = max(map(len, lines))

        for i, row_items in enumerate(itt.zip_longest(*lines, fillvalue='')):
            row = self.make_row(row_items, widths, alignment, borders)
            if (i + 1 == n_lines) and underline:
                row = _underline(row)
            yield row

    def make_row(self, cells, widths, alignment, borders):

        # format cells
        first, *cells = map(self.format_cell, cells, widths, alignment, borders)

        # Apply properties to whitespace filled row headers
        if self.has_row_head:
            first = codes.apply(first, self.row_head_props)

        if self.frame:
            first = self._default_border + first

        # stick cells together
        row = ''.join((first, *cells))
        self.rows.append(row)
        return row

    def format_cell(self, text, width, align, border=_default_border, lhs=''):
        # this is needed because the alignment formatting gets screwed up by the
        # ANSI characters (which have length, but are not displayed)
        pad_width = ansi.length_codes(text) + width
        return self.cell_fmt.format(text, pad_width, align, border, lhs)

    def build_long_line(self, text, width, align='<', props=None):
        # table row line that spans `width` of table.  use to build title
        # line and compact inset etc..

        if self.frame:
            b = self._default_border
            width -= len(b)
        else:
            b = ''
        borders = b, b

        if props is None:
            props = []
        props = str2tup(props)

        # only underline last line for multi-line element
        _under = ('underline' in props)
        if _under:
            props = list(props)
            props.remove('underline')

        lines = []
        for line in text.split(os.linesep):
            line = self.format_cell(line, width, align, *borders)
            line = codes.apply(line, props)
            # self.apply_props(line, properties)
            lines.append(line)

        if _under:
            lines[-1] = _underline(lines[-1])
            # codes.apply(lines[-1], 'underline')
        return '\n'.join(lines)

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
            yield self.build_long_line(line, width, *args)

    def format(self):
        """Construct the table and return it as as one long str"""

        # TODO: truncation
        # here data should be an array of str objects.  To do the
        # truncation, we first need to strip
        #  the control characters, truncate, then re-apply control....
        #  ??? OR is there a better way??

        table_width = sum(self.col_widths[self._idx_shown] +
                          self.lcb[self._idx_shown])

        if table_width > self.max_width:
            # if self.handle_too_wide == 'split':
            if self.has_title:
                self.title += '\n'  # to indicate continuation under title line

            #
            split_tables = self.split()

            if self.show_colourbar:
                split_tables[-1] = self.add_colourbar(split_tables[-1])
            table = '\n\n'.join(split_tables)
            return table
        # else:
        #     raise NotImplementedError
        else:
            return '\n'.join(self._build())

    def split(self, max_width=None):
        # TODO: return Table objects??

        max_width = max_width or self.max_width
        split_tables = []

        widths = self.col_widths[self._idx_shown] + self.lcb[self._idx_shown]
        rhw = widths[:self.n_head_col].sum()  # row header width

        # location of current split
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
                '\n'.join(map(str, self._build(idx_show, bool(splix))))
            )

            if endix is None:
                break
            splix = endix

        return split_tables

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
        if column_indices is None:
            column_indices = self._idx_shown

        idx = column_indices
        part_table = self.pre_table[:, idx]
        table_width = self.get_width(idx)

        if self.frame:
            # top line
            # NOTE: ANSI overline not supported (linux terminal) use underlined
            #  whitespace
            lcb = len(self._default_border)
            top_line = _underline(' ' * (table_width + lcb))
            table.append(top_line)

        # title
        if self.has_title:
            title = self.make_title(table_width, continued)
            table.append(title)

        # FIXME: problems with too-wide column

        # compacted columns
        if self.compact and self.compact_items:
            # if isinstance(self.compact, (numbers.Integral)):
            # display compacted columns in single row
            compact_rows = self.build_long_line(str(self._compact_table),
                                                table_width,
                                                props=['underline'])

            table.append(compact_rows)

        if table_width > (cw := (self.col_widths[idx] + self.lcb[idx]).sum()):
            # This means the compact table is wider than the main table and we
            # need to add some space to the columns
            self.col_widths[self._idx_shown] += apportion(table_width - cw,
                                                          len(self._idx_shown))

        # column groups
        for groups in self.col_groups:
            line = self._default_border if self.frame else ''
            lbl = groups[idx[0]]  # name of current group
            gw = 0  # width of current column group header

            # FIXME: this code below in `format cell??`
            for i, j in enumerate(idx):
                name = groups[j]
                w = self.col_widths[j] + self.lcb[j]  # + (j-i)  #
                if name == lbl:  # still within the same group
                    gw += w
                else:  # reached a new group. write previous group
                    if len(lbl) >= gw:
                        lbl = truncate(lbl, gw - 1)

                    line += f'{lbl: ^{gw - 1}}{self.borders[j]}'
                    gw = w
                    lbl = name

            # last bit
            if gw:
                line += f'{lbl: ^{gw - 1}}{self.borders[j]}'
            #
            if self.hlines:
                # only underline if headers are underlined
                line = _underline(line)

            table.append(line)

        # make rows
        start = -(self.has_col_head + self.has_units)

        widths = self.col_widths[idx]
        alignment = itt.chain(itt.repeat(self.col_head_align[idx], -start),
                              itt.repeat(self.align[idx]))
        borders = self.borders[idx]

        used = set()
        for i, row_cells in enumerate(part_table, start):
            insert = self.insert.get(i, None)
            if insert is not None:
                table.extend(self.insert_lines(insert, table_width))
                used.add(i)

            row_props = self.highlight.get(i)
            underline = (i in self.hlines)
            for row in self.gen_multiline_rows(
                    row_cells, widths, next(alignment), borders, underline):
                table.append(codes.apply(row, row_props))
                # fixme: maybe don't apply to border symbols

        # check if all insert lines have been consumed
        unused = set(self.insert.keys()) - used
        for i in unused:
            table.extend(self.insert_lines(self.insert[i], table_width))

        # finally add any footnotes present
        if len(self.footnotes):
            table.extend(self.footnotes)

        # add compact columns as footnotes if requested
        if self._compact_footer and self.compact_items:
            # format footnote table
            compact_rows = self.build_long_line(str(self._compact_table),
                                                table_width,
                                                props=['underline'])
            table.append(compact_rows)

        return table

    def _get_compact_table(self, n_cols=None, justify=True, equals='= '):

        # TODO: should print units here also!

        compact_items = list(self.compact_items.items())
        n_comp = len(self.compact_items)  # number of compacted columns
        # table_width = self.get_width()  # excludes lhs border

        if (n_cols is None) and (self.compact is not True):
            n_cols = self.compact

        auto_ncols = (
            # number of compact columns unspecified
            ((n_cols is None) and (self.compact is True)) or
            # user specified too many compact columns
            ((n_cols is not None) and (n_cols > n_comp))
        )
        if auto_ncols:
            # decide how many columns for compact key-value table
            n_cols = self._auto_ncols()
            self.logger.debug('Auto ncols: {}', n_cols)

        # n items per column
        self.compact = n_cols = int(n_cols)
        n_pc = (n_comp // n_cols) + bool(n_comp % n_cols)
        pad = n_pc * n_cols - n_comp
        compact_items.extend([('', '')] * pad)
        data = np.hstack(np.reshape(compact_items, (n_cols, n_pc, 2)))
        data = np.atleast_2d(data.squeeze())

        # todo row_head_props=self.col_head_props,
        # self._default_border #  u"\u22EE" VERTICAL ELLIPSIS
        col_borders = [equals, self._default_border] * n_cols
        col_borders[-1] = ''

        # widths of actual columns
        widths = lengths(data).max(0)
        widths[::2] += 1           # +1 for column borders

        # justified spacing
        if justify:
            deltas = justified_delta(widths.reshape(-1, 2).sum(1) + 3,
                                     self.get_width())
            if np.any(widths[1::2] <= -deltas):
                wrn.warn('Column justification lead to zero/negative column '
                         'widths. Ignoring!')
            else:
                widths[1::2] += deltas

        return Table(data, col_borders=col_borders, frame=False, width=widths,
                     too_wide=False)

    def _auto_ncols(self):
        # decide how many columns the inset table will have
        # n_cols chosen to be as large as possible given table width
        # this leads to most compact repr
        self.logger.debug('Computing optimal number of columns for compact table.')
        # number of compacted columns
        n_comp = len(self.compact_items)
        table_width = self.get_width()  # excludes lhs border

        # Widths for key-val pairs:                                + 3 for ' = '
        _2widths, extra = self._get_ctable_widths()

        if max(_2widths + extra) >= table_width:
            return 1

        extra = 3  # len(self._default_border) + self.cell_white
        trials = range(table_width // _2widths.max(), round(n_comp / 2) + 1)
        trials = [*trials, n_comp]
        for i, n_cols in enumerate(trials):
            nc, lo = divmod(n_comp, n_cols)
            pad = (nc + bool(lo)) * n_cols - n_comp
            ccw = np.hstack([_2widths, [0] * pad]
                            ).reshape(n_cols, -1).max(1)

            # + extra for column border + cell_white
            if sum(ccw + extra) > table_width:
                if np.any(ccw == 0):
                    continue
                n_cols = trials[i - 1]
                break

        return n_cols

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
