"""
Pretty printed tables for small data sets
"""


# std
import os
import logging
import numbers
import warnings as wrn
import functools as ftl
import itertools as itt
from shutil import get_terminal_size

# third-party
import numpy as np
from pyxides.grouping import Groups
from pyxides.vectorize import AttrVectorizerMixin

# local
from recipes.lists import where
from recipes import pprint as ppr
from recipes.sets import OrderedSet
from recipes.synonyms import Synonyms
from recipes.decorators import raises as bork
from recipes.logging import LoggingMixin, get_module_logger

# relative
from . import ansi, codes
from .utils import wideness, get_alignment, make_group_title


# from recipes.pprint import PrettyPrinter
# from .utils import formatter


# module level logger
logger = get_module_logger()
logging.basicConfig()
logger.setLevel(logging.INFO)


# defaults as module constants
DOTS = '…'  # single character ellipsis u"\u2026" to indicate truncation
BORDER = '⎪'  # U+23aa Sm CURLY BRACKET EXTENSION ⎪  # '|'
OVERLINE = '‾'  # U+203E
# EMDASH = '—' U+2014
HEADER_ALIGN = '^'
MAX_WIDTH = None  # TODO
MAX_LINES = None  # TODO


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


# defines vectorized length
lengths = np.vectorize(len, [int])


def is_astropy_table(obj):
    parents = [f'{kls.__module__}.{kls.__name__}' for kls in type(obj).mro()]
    return 'astropy.table.table.Table' in parents


def _convert_astropy_table(tbl):
    data, heads, units = [], [], []
    for name, col in tbl.columns.items():
        data.append(col.data)
        units.append(col.unit)
        heads.append(name)

    if set(units) == {None}:
        units = None

    return data, heads, units


def _echo(_):
    return _


def str2tup(keys):
    if isinstance(keys, str):
        keys = keys,  # a tuple
    return keys


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


def get_column_widths(data, col_headers=None, raw=False):
    """data should be array-like of str types"""

    # data widths
    w = np.vectorize(wideness, [int])(data, raw=raw).max(axis=0)

    if col_headers is not None:
        assert len(col_headers) == data.shape[1]
        hw = np.vectorize(wideness, [int])(col_headers, raw=raw)
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
    else:
        raise ValueError('Cannot interpret width %r for data of shape %s' %
                         (width, data.shape))


def resolve_input(obj,
                  data,
                  col_headers,
                  what,
                  converter=None,
                  default_factory=None,
                  args=(),
                  raises=True,
                  **kws):
    """
    Resolve user input for parameters that need to have either
        - the same number of elements as there are columns in the table or
        - need `col_headers` to be provided.

    Parameters
    ----------
    obj
    data
    col_headers
    what
    converter: callable
    raises
    default_factory
    args
    kws

    Returns
    -------

    """
    n_cols = data.shape[1]
    if obj is None:
        obj = {}

    # convert obj to dict
    if not isinstance(obj, dict):
        n_obj = len(obj)
        if n_obj == 1:
            # duplicate for all columns
            obj = [obj] * n_cols

        elif n_obj != n_cols:
            raise ValueError('Incorrect number of specifiers (%i) for %r in '
                             'table with %i columns' % (n_obj, what, n_cols))
        #
        obj = dict(enumerate(obj))

    # set action raise / warn
    emit = bork(ValueError) if raises else logger.warning

    keys = list(obj.keys())
    if (str in set(map(type, keys))) and col_headers is None:
        # only really a problem if formatter is not None
        emit(f'Could not assign {what} due to missing `column_headers`')

    # convert all keys in format dict to int
    if col_headers is not None:
        col_headers = list(col_headers)
        for key, val in obj.copy().items():
            # copy to prevent RuntimeError dictionary changed size during iteration
            if isinstance(key, str):
                if key not in col_headers:
                    emit(f'Could not assign {what}. Key {key!r} not in '
                         '`column_headers`')
                    continue
                #
                new_key = col_headers.index(key)
                # at this point key should be int
                obj[new_key] = obj.pop(key)

            elif not isinstance(key, numbers.Integral):
                emit('Key %r invalid type for mapping to column' % key)

    # convert values
    if converter:
        for i, item in obj.items():
            obj[i] = converter(item)

    # get default obj
    if default_factory:
        idx_no_fmt = set(range(n_cols)) - set(obj.keys())
        for i in idx_no_fmt:
            obj[i] = default_factory(i, *args, **kws)

    return obj


def resolve_borders(col_borders, where, ncols, frame):
    """
    Get the list of characters that will make up the column borders

    Parameters
    ----------
    col_borders
    where
    ncols
    frame

    Returns
    -------

    """
    borders = np.empty(ncols, dtype='<U10')
    # NOTE: these include the upcoming

    if where in (None, ...):
        # default is col borders everywhere
        where = np.arange(ncols)  #

    wcb = np.asarray(where)
    # number / header borders can be explicitly indexed by -1j / -2j
    l = (wcb == -1j) | (wcb == -2j)
    if l.any():
        cx = l.sum()
        wcb[~l] += cx
        wcb[l] = range(cx)
        with wrn.catch_warnings():
            wrn.filterwarnings("ignore", category=np.ComplexWarning)
            wcb = wcb.astype(int)

    if col_borders is not None:
        borders[wcb] = col_borders

    # final column border
    borders[-1] = BORDER if frame else ''

    return borders


def dict_to_list(data, ignore_keys, order):
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
    assert isinstance(data, dict)

    dic = data.copy()
    if ignore_keys is not None:
        for key in ignore_keys:
            dic.pop(key, None)

    headers = list(dic.keys())
    data = list(dic.values())

    row_headers = col_headers = None
    if order.startswith('r'):
        col_headers = headers
        data = np.transpose(data)
    elif order.startswith('c'):
        row_headers = headers
    else:
        raise ValueError('Invalid order: %s' % order)

    return row_headers, col_headers, data


def _rindex(s, char):
    try:
        return s.rindex(char)
    except ValueError as e:
        return 0


def _underline(s):
    """
    Underline last line of multi-line string, or entire string if single line
    """

    idx = _rindex(s, '\n')
    return s[:idx] + codes.apply(s[idx:], 'underline')


def highlight(array, condition, props, formatter=ppr.numeric, **kws):
    out = np.vectorize(formatter, (str, ))(array, **kws)
    if condition in (all, ...):
        condition = np.ones_like(array, bool)

    if condition.any():
        tmp = np.vectorize(codes.apply, (str, ))(out[condition], props)
        dtype = 'U%i' % (max(tmp.itemsize, out.itemsize) / 4)
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


class Table(LoggingMixin):
    """
    A table formatter. Good for displaying data. Definitely not for data
    manipulation. Plays nicely with ANSI colours and multi-line cell elements.
    """

    _default_border = BORDER  # TODO odo move to module scope

    # The column format specification:
    #  0 - item; 1 - fill width; 2 - align; 3 - border (rhs); 4 - border (lhs)
    cell_fmt = '{4}{0:{2}{1}}{3}'

    # title_fmt = cell_fmt.join(_default_border * 2)

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
        data, kws = cls._from_dict(data, ignore_keys=(), order='r', **kws)
        return cls(data, **kws)

    @staticmethod
    def _from_dict(data, ignore_keys=(), order='r', **kws):
        # helper for initialization from dict

        # check arguments valid
        assert isinstance(data, dict)
        assert order in 'rc', 'Invalid order: %s' % order

        row_headers, col_headers, data = dict_to_list(
            data, ignore_keys, order)

        kws.setdefault('row_headers', row_headers)
        kws.setdefault('col_headers', col_headers)
        return data, kws

    # TODO: test mappings!!

    # mappings for terse kws
    synonyms = Synonyms({
        'unit[s]':              'units',
        'footnote[s]':          'footnotes',
        'formatter[s]':         'formatters',
        'cell_white[space]':    'cell_whitespace',
        'minimal[ist]':         'minimalist',
        '[column_]width[s]':    '',
        'c[olumn_]groups':      'col_groups',
        '[row_]nrs':            'row_nrs',
        'n[umbe]r_rows':        'row_nrs',
        'total[s]':             'totals'
    })
    for rc, p in {'row':        'r[ow_]',
                  'col':        'c[olumn_]'}.items():
        synonyms.update({
            f'{p}head[ers]':                f'{rc}_headers',
            f'{p}head[er]_prop[erties]':    f'{rc}_head_props',
            f'{p}borders':                  'col_borders'
        })

    def __init__(self,
                 data,

                 #  Title(text, '_', '^')
                 title=None,
                 title_align='center',
                 title_props=('underline', ),

                 # ColumnTitles(names, 'bold', 'blue', '^', nrs=True, units)
                 col_headers=None,
                 col_head_props='bold',
                 col_head_align='^',
                 units=None,
                 col_borders=_default_border,

                 vlines=None,
                 col_groups=None,

                 # RowTitles(names, 'bold', 'blue', nrs=True)
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

        col_borders : str,
            TODO: dict: {0j: '|', 3: '!', 6: '…'}
            character(s) used as column separator. ie column rhs borders
            The table border can be toggled using the `frame' parameter
        col_groups: array-like
            sequence of strings giving column group names. If given, a group
            header will be added above the columns sharing a common group name.

        hlines, vlines: array-like, Ellipsis, optional
            Sequence with row line numbers below which a solid border will be
            drawn.
            Default is after column headers, and after last data line and after
            totals line if any.
            If an `Ellipsis` ... is given, draw a line after every row.
            TODO: dict: {0j: '|', 3: '!', 6: '…'}
            Similarly for `vlines`.

        row_nrs : bool, int
           Number the rows. Start from this number if int

        precision : int
            Decimal precision to use for representing real numbers (floats)
        minimalist : bool
            Represent floating point numbers with least possible number of
            significant digits
        compact : bool or int
            Suppress columns for which data values are all identical and print
            them in a inset table below the title. If an integer is passed,
            this specifies the number of columns to use in the inset table.
            If boolean, the number of columns will be decided automatically
            to optimize space.
            Compact representation will only be applied if the table contains
            more  than one row of data.

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

        # special case: dict
        if isinstance(data, dict):
            data, kws = self._from_dict(data, **kws)
            self.__init__(data, **kws)
            return

        if isinstance(data, set):
            data = list(data)

        # resolve kws
        if kws:
            # remap terse keywords
            self.__init__(data, **self.synonyms.resolve(locals(), **kws))
            return
            # `kws_` now has all the allowed parameters for this function as
            # keywords with either the default or user input as values

        # special case: astropy.table.Table
        if is_astropy_table(data):
            # FIXME: can you do this with from_dict???
            data, col_headers_, units_ = _convert_astropy_table(data)
            # remap terse keywords
            kws_ = self.synonyms.resolve(locals(), **kws)
            # replace defaults with those from the astropy table
            if kws_['col_headers'] is None:
                kws_['col_headers'] = col_headers_
            if kws_['units'] is None:
                kws_['units'] = units_
            # init
            self.__init__(data, **kws_)
            return

        # convert to object array
        data = np.asanyarray(data, 'O')

        # check data shape / dimensions
        dim = data.ndim
        if dim == 1:
            data = data[None]

        if dim > 2:
            raise ValueError('Only 2D data can be tabled! Data is %iD' % dim)

        # column headers
        self._col_headers = col_headers

        # units
        self.has_units = (units not in (None, {}))
        self.units = None
        if self.has_units:
            units = resolve_input(units, data, col_headers, 'units')
            self.units = []
            for i in range(data.shape[1]):
                u = units.get(i)
                self.units.append('[{}]'.format(u) if u else '')

        # title
        # if title is not None:
        #     title = str
        self.title = title
        self.has_title = title is not None
        self.title_props = title_props
        self.title_align = get_alignment(title_align)

        # get data types of elements for automatic formatting / alignment
        self.col_data_types = []
        for col in data.T:
            use = ~col.mask if np.ma.is_masked(col) else ...
            self.col_data_types.append(set(map(type, col[use])))

        # headers
        self.frame = bool(frame)
        self.has_row_nrs = hrn = (row_nrs is not False)
        self.has_row_head = hrh = (row_headers is not None)
        self.has_col_head = (col_headers is not None)
        self.n_head_col = hrh + hrn
        n_cols = data.shape[1] + self.n_head_col

        # get alignment based on column data types
        self.align = self.get_alignment(
            align, data, col_headers, self.get_default_align)
        self.dot_aligned = np.array(where(self.align, '.')) - self.n_head_col
        self.align = np.array(list(self.align.replace('.', '<')), 'U1')

        # column headers will be center aligned unless requested otherwise.
        self.col_head_align = np.array(list(self.get_alignment(
            col_head_align, data, col_headers, lambda _: HEADER_ALIGN)))

        # column formatters
        self.formatters = resolve_input(
            formatters, data, col_headers, 'formatters',
            default_factory=self.get_default_formatter,
            args=(precision, minimalist, data))

        # get flags
        flags = resolve_input(flags, data, col_headers, 'flags')

        # calculate column totals if required
        self.totals = self.get_totals(data, totals)
        self.has_totals = (self.totals is not None)

        # do formatting
        data = self.formatted(data, self.formatters, str(masked), flags)

        # add totals row
        if self.has_totals:
            totals = self.formatted(self.totals, self.formatters, '')
            data = np.vstack((data, totals))

        # col borders (rhs)
        self.borders = resolve_borders(col_borders, vlines, n_cols, frame)
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
        nomit = nrows - max_rows
        if nomit:
            self.insert[max_rows - 1] = f'< ... {nomit} rows omitted ... >'
            data = data[:max_rows]

        # add the (row/column) headers / row numbers / totals
        self.pre_table = self.add_headers(data, row_headers, col_headers,
                                          row_nrs)
        # note `pre_table` is dtype='O'

        self.cell_white = int(cell_whitespace)

        # handle group headers
        if col_groups is not None:
            assert len(col_groups) == self.data.shape[1]
            col_groups = ([''] * self.n_head_col) + list(col_groups)

        self.col_groups = col_groups
        # FIXME: too wide col_groups should truncate

        # compactify
        if not isinstance(compact, numbers.Integral):
            raise ValueError('`compact` must be bool or int')

        self.compact = (False, compact)[self.compactable()]
        self.compact_items = {}
        self._idx_shown = np.arange(self.shape[1])
        if compact:
            if not self.has_col_head:
                self.logger.warning(
                    'Requested `compact` representation, but no column headers '
                    'provided. Ignoring.'
                )
            #
            self.compactify()
            # requested_width = requested_width[shown]
            # borders = borders[shown]

        # get column widths (without borders)
        # these are either those input by the user, or determined from the
        # content of the columns
        # FIXME: too-wide columns in compact table!!
        self.col_widths = get_column_widths(self.pre_table) + self.cell_white

        # next block needs to happen after `self.col_widths` assigned
        self._compact_table = None
        has_compact = compact and self.compact_items
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
        else:
            hlines = np.array(hlines)
            hlines[hlines < 0] += n_rows

        hlines = list(hlines)
        if self.has_col_head:
            hlines.append(-1)

        if self.frame:
            hlines.append(n_rows - self.has_col_head - self.has_units - 1)

        if self.has_totals:
            hlines.append(n_rows - self.has_col_head - self.has_units - 2)

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

    # HACK
    synonyms.func = __init__

    def __repr__(self):
        # useful in interactive sessions to immediately print the table
        return str(self)

    def __str__(self):
        if self.data.size:
            return self.format()
        else:
            return '{0}Empty Table{0}'.format(self._default_border)

    @property
    def data(self):  # FIXME: better to keep data and headers separate ...
        rows = slice(self.has_col_head + self.has_units,
                     -1 if self.has_totals else None)
        return self.pre_table[rows, self.n_head_col:]

    @property
    def shape(self):
        return self.pre_table.shape

    @property
    def col_headers(self):
        # if self.has_col_head:
        return self.pre_table[:self.has_col_head, self.has_row_head:].squeeze()

    @col_headers.setter
    def col_headers(self, value):
        self.pre_table[:self.has_col_head, self.has_row_head:] = value

    @property
    def row_headers(self):
        # if self.has_row_head:
        return self.pre_table[self.has_row_head:, :self.has_col_head]

    @row_headers.setter
    def row_headers(self, value):
        # if self.has_row_head:
        value = np.reshape(value, (self.data.shape[0], 1))
        self.pre_table[self.has_row_head:, :self.has_col_head] = value

    @property
    def n_head_rows(self):
        return sum((self.col_groups is not None,
                    self.has_col_head,
                    self.has_units))

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
        m = 0
        if self.compact:
            m = len(self.compact_items)
            m //= int(self.compact)
        return n + m + self.n_head_rows + self.frame

    @property
    def compact_pre(self):
        return self.pre_table[:, self._idx_shown]

    @property
    def idx_compact(self):
        return np.setdiff1d(np.arange(self.shape[1]), self._idx_shown)

    def empty_like(self, n_rows, **kws):
        """
        A string representing an empty row of the table. Has the same
        number of columns and column widths as the table.
        """

        filler = [''] * len(self._idx_shown)
        return Table([filler] * n_rows,
                     width=self.get_column_widths()[self._idx_shown],
                     **kws)

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
                return _echo

            if not issubclass(type_, numbers.Real):
                return str

            #
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
                               sign=sign,)
            #    right_pad=right_pad)

            #  NOTE: single dispatch not a good option here due to formatting
            #   subtleties
            # return formatter.registry[type_](None, precision=precision,
            #                                  compact=minimalist,
            #                                  sign=sign,
            #                                  right_pad=right_pad)

        return ppr.PrettyPrinter(precision=precision,
                                 minimalist=short).pformat

    def formatted(self, data, formatters, masked_str='--', flags=None):
        """convert to array of str"""

        # if self.
        flags = flags or {}
        data = np.atleast_2d(data)

        # format custom columns
        for i, fmt in formatters.items():  # Todo: formatting for row_headers...
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

            # wrap the formatting in try, except since it's usually not
            # critical that it works and getting some info is better than none
            try:
                data[use, i] = np.vectorize(fmt, (str, ))(col[use])
            except Exception as err:
                wrn.warn(
                    f'Could not format column {i} with {fmt!r} due to the '
                    f'following exception:\n{err}'
                )

                data[use, i] = np.vectorize(str, (str, ))(col[use])

            # special alignment on '.' for float columns
            if i in self.dot_aligned:
                data[use, i] = ppr.align_dot(data[use, i])

            # concatenate data with flags
            # flags = flags.get(i)
            if i in flags:
                try:
                    data[use, i] = np.char.add(data[use, i].astype(str),
                                               list(map(str, flags[i])))
                except Exception as err:
                    wrn.warn(
                        f'Could not append flags to formatted data for column '
                        f'{i} due to the following exception:\n{err}'
                    )

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

        if np.size(width) == self.shape[1]:
            # each column width specified
            return width

        elif np.size(width) == 1:
            # The table will be made exactly this wide
            width = int(width)  # requested width
            # TODO: DECIDE COL WIDTHS
            raise NotImplementedError

        elif np.size(width) == self.data.shape[1]:
            # each column width specified
            hcw = self.col_widths[:self.n_head_col]
            return np.r_[hcw, width]

        elif isinstance(width, range):
            # maximum table width given.
            raise NotImplementedError
            width_min = width.start
            width_max = width.stop

        else:
            raise ValueError('Cannot interpret width %r' % str(width))

        # return col_widths  # , width_max

    def compactable_columns(self, ignore=()):
        if not self.compactable():
            return ()

        idx_same, = np.where(np.all(self.data == self.data[0], 0))
        _, idx_ign = np.where(self.col_headers == np.atleast_2d(ignore).T)
        idx_same = np.setdiff1d(idx_same, idx_ign) + self.n_head_col
        return idx_same

    def compactable(self):
        """Check if table allows compact representation"""
        return (len(self.data) > 1) and self.has_col_head

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
            return ...

        # if a total is asked for on a column, make sure we don't suppress it
        totals = None
        if self.has_totals:
            totals = self.pre_table[-1]

        idx_same = self.compactable_columns(ignore)
        idx_squash = np.setdiff1d(idx_same, np.atleast_1d(totals).nonzero()[0])
        val_squash = self.pre_table[self.n_head_rows, idx_squash]
        idx_show = np.setdiff1d(range(self.shape[1]), idx_squash)
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

    def get_column_widths(self, data=None, raw=False, with_borders=False):
        """data should be string type array"""
        # note now pretty much redundant

        if data is None:
            data = self.pre_table

        # get width of columns - widest element in column
        w = get_column_widths(data, raw=raw) + self.cell_white

        # add border size
        if with_borders:
            w += self.lcb
        return w

    def get_width(self, indices=None):
        """get table width"""
        if indices is None:
            indices = self._idx_shown
        # this excludes the lhs starting border
        return (self.col_widths[indices] + self.lcb[indices]).sum()

    def get_alignment(self, align, data, col_headers, default_factory):
        """get alignment array for columns"""
        alignment = resolve_input(align, data, col_headers, 'alignment',
                                  get_alignment, default_factory)
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
                self.logger.debug(
                    'Suppressing totals line since table has only '
                    'a single row of data.')
            return

        if col_indices in (None, False):
            return

        # boolean True ==> compute totals for all
        if col_indices is True:
            col_indices = np.arange(data.shape[1])

        #
        totals = np.ma.masked_all(data.shape[1], 'O')
        for i in col_indices:
            # handle str keys for total compute
            if isinstance(i, str) and (self._col_headers is not None) and \
                    (i in self._col_headers):
                i = list(self._col_headers).index(i)

            if not isinstance(i, numbers.Integral):
                raise TypeError('Could not interpret %r as a pointer to a '
                                'column of the table.' % i)

            # negative indexing
            if i < 0:
                i += data.shape[1]

            # attempt to compute total
            totals[i] = sum(data[:, i])

        return totals  # np.ma.array(totals, object)

    # @expose.args()
    # @staticmethod
    def add_headers(self,
                    data,
                    row_headers=None,
                    col_headers=None,
                    row_nrs=False):
        """Add row and column headers to table data"""

        # row and column headers
        # TODO: error check for len of row/col_headers
        has_row_head = row_headers is not None
        has_col_head = col_headers is not None

        if has_row_head and self.has_totals:
            row_headers = list(row_headers) + ['Totals']

        if self.has_units:
            data = np.ma.vstack((self.units, data))
            if has_row_head:
                row_headers = [''] + list(row_headers)

        if has_col_head:
            data = np.ma.vstack((col_headers, data))

            # NOTE: when both are given, the 0,0 table position is ambiguously
            #  both column and row header
            if has_row_head:  # and (len(row_headers) == data.shape[0] - 1):
                row_headers = [''] + list(row_headers)

        if has_row_head:
            row_head_col = np.atleast_2d(row_headers).T
            data = np.ma.hstack((row_head_col, data))

        # add row numbers
        if self.has_row_nrs:  # (row_nrs is not False)
            nr = int(row_nrs)
            nrs = np.arange(nr, data.shape[0] + nr).astype(str)
            if self.has_units:
                # self.units = [''] + self.units
                nrs = [''] + list(nrs[:-1])

            if has_col_head:
                nrs = ['#'] + list(nrs[:-1])

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
        cells = list(map(self.format_cell, cells, widths, alignment, borders))

        # Apply properties to whitespace filled row headers
        if self.has_row_head:
            cells[0] = codes.apply(cells[0], self.row_head_props)

        if self.frame:
            cells[0] = self._default_border + cells[0]

        # stick cells together
        row = ''.join(cells)
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

        table_width = sum(self.col_widths[self._idx_shown] +
                          self.lcb[self._idx_shown])

        # table_width = sum(self.col_widths) + self.lcb.sum()

        # TODO: truncation
        # here data should be an array of str objects.  To do the
        # truncation, we first need to strip
        #  the control characters, truncate, then re-apply control....
        #  ??? OR is there a better way??

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
        while True:
            if splix == self._idx_shown[-1]:
                break

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
        # make a list of column indices from which table will be built
        # seg = slice(c0, c1)
        # n_head_col = self.has_row_head + self.has_row_nrs
        # idx_head = np.arange(n_head_col)  # always print header columns
        # idx_cols = np.arange(self.data.shape[1])[seg] + n_head_col
        # idx_cols = np.hstack([idx_head, idx_cols])
        if column_indices is None:
            column_indices = self._idx_shown

        idx = column_indices
        part_table = self.pre_table[:, idx]
        table_width = self.get_width(idx)
        lcb = len(self._default_border)

        if self.frame:
            # top line
            # NOTE: ANSI overline not supported (linux terminal) use underlined
            #  whitespace
            top_line = _underline(' ' * (table_width + lcb))
            table.append(top_line)

        # title
        if self.has_title:
            title = self.make_title(table_width, continued)
            table.append(title)

        # FIXME: problems with too-wide column

        # compacted columns
        if self.compact_items:
            # display compacted columns in single row
            compact_rows = self.build_long_line(str(self._compact_table),
                                                table_width,
                                                props=['underline'])

            table.append(compact_rows)

        # column groups
        if self.col_groups is not None:
            line = self._default_border
            lbl = self.col_groups[idx[0]]  # name of current group
            gw = 0  # width of current column group header

            # FIXME: this code below in `format cell??`
            for i, j in enumerate(idx):
                name = self.col_groups[j]
                w = self.col_widths[j] + self.lcb[j]
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
            table.append(_underline(line))

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

        return table

    def _get_compact_table(self, n_cols=None, justify=True):

        # TODO: should print units here also!

        compact_items = list(self.compact_items.items())
        n_comp = len(self.compact_items)  # number of compacted columns
        table_width = self.get_width()  # excludes lhs border

        if (n_cols is None) and (self.compact is not True):
            n_cols = self.compact

        auto_ncols = (
            # number of compact columns unspecified
            ((n_cols is None) & (self.compact is True)) |
            # user specified too many compact columns
            ((n_cols is not None) and (n_cols > n_comp))
        )
        if auto_ncols:
            # decide how many columns the inset table will have
            # n_cols chosen to be as large as possible given table width
            # this leads to most compact repr       # + 3 for ' = '
            _2widths = lengths(compact_items).sum(1) + 3
            # this is the width of the compacted columns
            extra = len(self._default_border) + self.cell_white
            trials = list(range(table_width // _2widths.max(),
                                round(n_comp / 2) + 1)
                          ) + [n_comp]
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

        # n items per column
        self.compact = n_cols = int(n_cols)
        n_pc = (n_comp // n_cols) + bool(n_comp % n_cols)
        pad = n_pc * n_cols - n_comp
        compact_items.extend([('', '')] * pad)
        data = np.hstack(np.reshape(compact_items, (n_cols, n_pc, 2)))
        data = np.atleast_2d(data.squeeze())

        # todo row_head_props=self.col_head_props,
        # self._default_border #  u"\u22EE" VERTICAL ELLIPSIS
        col_borders = ['= ', self._default_border] * n_cols
        col_borders[-1] = ''

        # widths of actual columns
        widths = lengths(data).max(0)
        widths[::2] += 1           # +1 for column borders

        # justified spacing
        if justify:
            widths[1::2] += justified_delta(widths.reshape(-1, 2).sum(1) + 3,
                                            table_width)

            if np.any(widths <= 0):
                raise Exception('NEGATIVE WIDTHS FIXME!!!')

        return Table(data, col_borders=col_borders, frame=False, width=widths,
                     too_wide=False)

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
        dtype = 'U%i' % (x + 15)
        self.pre_table = self.pre_table.astype(dtype)

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

    #
    # def hstack(self, other):
    #     """plonk two tables together horizontally"""
    #
    #     # FIXME: better to alter data and return Table
    #
    #     lines1 = str(self).splitlines(True)
    #     lines2 = str(other).splitlines(True)
    #     nl = '\n' * max(len(lines1), len(lines2))
    #
    #     print(''.join((map(str.replace, lines1, nl, lines2))))

    # def to_latex(self, longtable=True):
    #     """Convert to latex tabular"""
    #     raise NotImplementedError
    #     # TODO

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


# if __name__ == '__main__':
# do Tests
# TODO: print pretty things:
# http://misc.flogisoft.com/bash/tip_colors_and_formatting
# http://askubuntu.com/questions/512525/how-to-enable-24bit-true-color-support-in-gnome-terminal
# https://github.com/robertknight/konsole/blob/master/tests/color-spaces.pl

def SENTINEL():
    pass


class AttrTable:
    """
    Helper class for tabulating data. Attributes of the objects in the container
    are mapped to the columns of the table.
    """

    def _get_input(self, obj):
        if obj is None:
            return dict()

        if isinstance(obj, dict):
            return obj

        return dict(zip(self.attrs, obj))

    def __init__(self, attrs, aliases=None, formatters=None, units=None, **kws):

        # set default options for table
        self.kws = {**dict(row_nrs=0,
                           precision=5,
                           minimalist=True,
                           compact=True),
                    **kws}

        self.attrs = list(attrs)
        self.formatters = self._get_input(formatters)
        self.units = self._get_input(units)
        self.aliases = self._get_input(aliases)
        self.aliases = dict(zip(attrs, self.get_headers(attrs)))

    def __call__(self, container, attrs=None, **kws):
        """
        Print the table of attributes for this container as a table.

        Parameters
        ----------
        attrs: array_like, optional
            Attributes of the instance that will be printed in the table.
            defaults to the list given upon initialization of the class.
        **kws:
            Keyword arguments passed directly to the `motley.table.Table`
            constructor.

        Returns
        -------


        """
        if isinstance(container, AttrVectorizerMixin):
            return self.get_table(container, attrs, **kws)

        if isinstance(container, Groups):
            return self.get_tables(container, attrs, **kws)

        raise TypeError(f'Cannot tabulate object of type {type(container)}')

    def convert_aliases(self, kws):
        # ok = set(map(self.aliases.get, kws)) - {None}
        if isinstance(kws, dict):
            return {self.aliases.get(k, k): v for k, v in kws.items()}
        elif isinstance(kws, list):
            return [self.aliases.get(k, k) for k in kws]
        raise TypeError

    def get_defaults(self, attrs, which):
        defaults = getattr(self, which)
        out = {}
        for a in attrs:
            alias = self.get_header(a)
            use = defaults.get(a, defaults.get(alias, SENTINEL))
            if use is not SENTINEL:
                out[alias] = use
        return out

    def get_header(self, attr):
        return self.aliases.get(attr, attr.split('.')[-1])

    def get_headers(self, attrs):
        return list(map(self.get_header, attrs))

    def _col_group(self, attrs):
        for a in attrs:
            first, *second = a.split('.')
            yield first if second else ''

    def get_col_groups(self, attrs):
        return list(self._col_group(attrs))

    # def get_formatters(self, attrs):
    #     return {a: self.formatters[a] for a in attrs if a in self.formatters}

    def add_attr(self, attr, column_header=None, formatter=None):

        if not isinstance(attr, str):
            raise ValueError('Attribute must be a str')

        # block below will bork with empty containers
        # obj = self.parent[0]
        # if not hasattr(obj, attr):
        #     raise ValueError('%r is not a valid attribute of object of '
        #                      'type %r' % (attr, obj.__class__.__name__))

        # avoid duplication
        if attr not in self.attrs:
            self.attrs.append(attr)

        if column_header is None:
            column_header = attr  # FIXME split here

        self.headers[attr] = column_header
        if formatter is not None:
            self.formatters[column_header] = formatter

    def get_table(self, container, attrs=None, **kws):
        """
        Keyword arguments passed directly to the `motley.table.Table`
            constructor.

        Returns
        -------
        `motley.table.Table` instance
        """

        if not isinstance(container, AttrVectorizerMixin):
            raise TypeError('Container does not support vectorized attribute '
                            'lookup on items.')

        if len(container) == 0:
            return Table(['Empty'])

        if attrs is None:
            attrs = self.attrs

        headers = self.get_headers(attrs)
        kws = {**self.kws,  # defaults
               **{**dict(title=container.__class__.__name__,
                         col_headers=headers,
                         col_groups=self.get_col_groups(attrs)),
                  **{key: self.get_defaults(attrs, key)
                         for key in ('units', 'formatters')},
                  **kws},  # input
               }
        return Table(container.attrs(*attrs), **kws)

    def get_tables(self, groups, attrs=None, titled=True, filler_text='EMPTY',
                   **kws):
        # TODO: grand total..
        """
        Get a dictionary of tables for the containers in `groups`. This method
        assists working with groups of tables.
        """
        if titled is True:
            titled = make_group_title

        title = kws.pop('title', self.__class__.__name__)
        ncc = kws.pop('compact', False)  # number of columns in compact part
        kws['compact'] = False

        attrs = OrderedSet(self.attrs)
        attrs_grouped_by = ()
        compactable = set()
        # multiple = (len(self) > 1)
        if len(groups) > 1:
            if groups.group_id != ((), {}):
                keys, _ = groups.group_id
                key_types = {gid: list(grp)
                             for gid, grp in itt.groupby(keys, type)}
                attrs_grouped_by = key_types.get(str, ())
                attrs -= set(attrs_grouped_by)

            # check which columns are compactable
            attrs_varies = {key for key in attrs if groups.varies_by(key)}
            compactable = attrs - attrs_varies
            attrs -= compactable

        # column headers
        headers = self.get_headers(attrs)

        # handle column totals
        totals = kws.pop('totals', self.kws['totals'])
        if totals:
            # don't print totals for columns used for grouping since they will
            # not be displayed
            totals = set(totals) - set(attrs_grouped_by) - compactable
            # convert totals to numeric since we remove column headers for
            # lower tables
            totals = list(
                map(headers.index, self.convert_aliases(list(totals))))

        units = kws.pop('units', self.units)
        if units:
            want_units = set(units.keys())
            nope = set(units.keys()) - set(headers)
            units = {k: units[k] for k in (want_units - nope - compactable)}

        tables = {}
        empty = []
        footnotes = OrderedSet()
        for i, (gid, items) in enumerate(groups.items()):
            if items is None:
                empty.append(gid)
                continue

            # get table
            if titled:
                # FIXME: problem with dynamically formatted group title.
                # Table wants to know width at runtime....
                title = titled(gid)
                # title = titled(i, gid, kws.get('title_props'))

            tables[gid] = tbl = self.get_table(items, attrs,
                                               title=title,
                                               totals=totals,
                                               units=units,
                                               # compact=False,
                                               **kws)

            # only first table gets title / headers
            if not titled:
                kws['title'] = None
            if not headers:
                kws['col_headers'] = kws['col_groups'] = None

            # only last table gets footnote
            footnotes |= set(tbl.footnotes)
            tbl.footnotes = []
        #
        tbl.footnotes = list(footnotes)

        # deal with null matches
        first = next(iter(tables.values()))
        if len(empty):
            filler = [''] * first.shape[1]
            filler[1] = filler_text
            filler = Table([filler])
            for gid in empty:
                tables[gid] = filler

        # HACK compact repr
        if ncc and first.compactable():
            first.compact = ncc
            first.compact_items = dict(zip(
                list(compactable),
                self.get_table(first[:1], compactable,
                               chead=None, cgroups=None,
                               row_nrs=False, **kws).pre_table[0]
            ))
            first._compact_table = first._get_compact_table()

        # put empty tables at the end
        # tables.update(empty)
        return tables
