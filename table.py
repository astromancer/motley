# import functools
import os
import re
import warnings
import itertools as itt
from shutil import get_terminal_size

import numpy as np

from recipes.pprint import PrettyPrinter

from . import codes
from . import core as ansi

as_ansi = ansi.as_ansi

from IPython import embed


# TODO: unit tests!!!!!!!!
# TODO: GIST

# TODO: possibly integrate with astropy.table ...........................
# TODO: HIGHLIGHT ROWS / COLUMNS
# TODO: OPTION for plain text row borders

# NOTE: IPython does not support ansi underline, while unix term does
# Use unicode underline for qtconsole sessions. However, unicode underline does
# not display correctly in notebook!!
# if is_interactive:
#     def _underline(s):
#         # for this to work correctly, the ansi characters must surround the unicode
#         # not vice versa
#         return '\u0332'.join(' ' + s)
# else:
#     def _underline(s):
#         return codes.apply(s, 'underline')

def _underline(s):
    return codes.apply(s, 'underline')


class Table(object):  # TODO: remane as ansi table??
    # map to alignment format characters
    ALIGNMENT_MAP = {'r': '>', 'l': '<', 'c': '^'}  # TODO: move up??
    ALLOWED_KWARGS = []  # TODO

    #
    _default_border = '|'
    # parameters for compacted lines
    _compact_sep = '\n'

    # The column format specification:
    #  0 - item; 1 - fill width; 2 - align; 3 - border (rhs); 4 - border (lhs)
    cell_fmt = '{4}{0:{2}{1}}{3}'

    # title_fmt = cell_fmt.join(_default_border * 2)

    def __init__(self, data,
                 title=None, title_props=('underline',), title_align='center',
                 col_headers=None, col_head_props='bold',
                 col_borders=_default_border,  # TODO: or sequence
                 where_col_borders=None,
                 col_sort=None,
                 row_headers=None, row_head_props='bold', where_row_borders=None,
                 row_sort=None, number_rows=False,
                 align='left',  # TODO: or sequence
                 precision=2, minimalist=False, compact=False,
                 ignore_keys=None, order='c',
                 width=None, too_wide='split',
                 cell_whitespace=1, frame=True,
                 total=None,
                 formatters=None
                 ):
        """
        A table representation of `data`.

        Parameters
        ----------
        data : array_like or dict
            input data - must be 1D, 2D
            if dict, keys will be used as row_headers, and values as data

        title : str
            The table title
        title_props : str, tuple, dict
            ANSICodes property descriptors
        align, title_align : {'left', 'right', 'center', '<', '>', '^'}
            column / title alignment

        col_headers, row_headers  : array_like
            column -, row headers as sequence of str objects.
        col_head_props, row_head_props : str or dict or array_like
            with ANSICodes property descriptors to use as global column header
            properties.  If number_rows is True, the row_head_props will be
            applied to the number column as well
            TODO: OR a sequence of these, one for each column
        col_sort, row_sort:
            TODO callable that operates on strings and returns column sorting order

        col_borders : str, TODO: dict: {0j: '|', 3: '!', 6: '1'}
            character(s) used as column separator. ie column rhs borders
            The table border can be toggled using the `frame' parameter
        where_col_borders, where_row_borders: array-like, optional
            Sequence with row numbers below which a solid border will be drawn.
            Default is after column headers, and after last data line and after
            totals line if any.

        number_rows : bool
            Whether to number the rows

        precision : int
            Decimal precision to use for number representation
        minimalist : bool
            Represent floating point numbers with least possible number of
            significant digits
        compact : bool
            Suppress columns for which data values are all identical and print
            them in a single line at the start of the table below the title.
            This will only be done if the table contains more than one row of
            data.

        ignore_keys : sequence of str
            if dictionary is passed as data, optionally specify the keys that
            will not be printed in table
        order : {'row', 'col'}
            whether to interpret data as row ordered or column ordered

        width : int, range, array_like
            Required table (columnn) width(s)
                If int: The table width.
                If range: The minimum and maximum table width
                If array_like: One int per column specifying each width
        too_wide: {'split', 'truncate'}
            How to handle case in which table is too wide for display.
             - If 'split' (default) the table is split into multiple tables that
              each respect `max_width`, and print them one after the other.
             - If 'truncate': #TODO

        cell_whitespace: int
            minimal whitespace in each cell
        frame : bool
            whether to draw a frame for the table
        total : array_like
            Indices or names of columns for which to compute sums. If any
            provided, an extra row with totals for requested columns will be
            added to the table. Will only work for columns with numeric type
            data. Exceptions when computing sums are emitted as warnings and
            displayed as '??' 'Totals' row of the table.
        formatters : function or dict or array_like, optional
            Formatter(s) to use to create the str representation of objects in the
            table.
             - If not given, a custom `pprint.PrettyPrinter` subclass is used
             which respects the `precision` and `minimalist` arguments for floats,
             and still creates nice reprs for arbitrarily nested objects. If you
             use a custom formatter, the `precision` and `minimalist` arguments
             will be ignored.
             - If a dict is given, it should be keyed on the column indices for
             which the corresponding formatter function is intended. If
             `col_headers` are provided, the formatter dict can also be keyed
             on any str contained therein. The default formatter will be used for
             the remaining columns.
             - If an array_like is given, it should provide one formatter per
             table column.



        #TODO: list attributes here
        """

        # save a backup of the original data
        self.original_data = data
        self._col_headers = col_headers

        # check arguments valid
        assert order in 'rc', 'Invalid order: %s' % order

        if isinstance(data, dict):
            row_headers, col_headers, data = self.convert_dict(
                    data, ignore_keys, order)

        # convert to object array
        data = np.array(data, 'O', ndmin=1)

        # calculate totals if required
        totals = self.get_totals(data, total)
        self.has_totals = np.any(totals)  # first truthy item else False
        if self.has_totals:
            totals = np.array(totals, 'O')
            totals[np.equal(totals, None)] = ''
            data = np.vstack((data, totals))
        self.totals = totals

        # check data shape
        dim = data.ndim
        if dim == 1:
            # default for 1D data is to display in a column with row_headers
            if order.startswith('c'):
                data = data[None].T
        if dim > 2:
            raise ValueError('Only 2D data can be tabled!  Data is %iD' % dim)

        # format
        data = self._apply_format(data, formatters, precision, minimalist)
        # data = as_ansi(data, precision=precision, minimalist=minimalist,
        #                ndmin=1)  # need this else 0D data skips through

        # headers
        self.frame = bool(frame)
        self.has_row_nrs = hrn = bool(number_rows)
        self.has_row_head = hrh = (row_headers is not None)
        self.has_col_head = hch = (col_headers is not None)
        self.n_head_col = nhc = hrh + hrn
        try:
            n_data_col = data.shape[1]
        except:
            from IPython import embed
            embed()
            raise
        ncols = n_data_col + nhc

        # col borders (rhs)
        borders = self.resolve_borders(col_borders, where_col_borders,
                                       ncols, frame)

        # compactify
        if compact and len(data) > 1:
            data, shown, suppressed, col_headers, self.compacted = \
                self.compactify(data, col_headers)
            shown = np.r_[:nhc, shown + nhc]
            borders = borders[shown]
            # FIXME: entire table may be compacted away!
        else:
            self.compacted = []

        # TODO: row / col sort here

        # Add row / column headers
        # self._col_headers = col_headers  # May be None
        # self.row_headers = row_headers
        self.col_head_props = col_head_props
        self.row_head_props = row_head_props
        self.borders = borders
        self.lcb = np.vectorize(len, [int])(self.borders)
        # otypes=[int] in case borders are empty

        # add the (row/column) headers / row numbers / totals
        self.pre_table = pre_table = self.add_headers(
                data, row_headers, col_headers, number_rows)

        self.n_data_rows, self.n_data_col = data.shape
        self.nrows, self.ncols = pre_table.shape  # NOTE: headers are counted as rows
        # np.add(data.shape, (int(self.has_row_head), int(self.has_col_head))  #

        # title
        self.title = title
        self.title_props = title_props
        self.title_align = self.get_alignment(title_align)

        # row borders
        if where_row_borders is not None:
            wrb = np.array(where_row_borders)
            wrb[wrb < 0] += self.nrows
        else:
            wrb = []
            if self.has_col_head:
                wrb.append(0)
            if self.frame:
                wrb.append(self.nrows - 1)
            if np.any(self.totals):
                wrb.append(self.nrows - 2)
        self.where_row_borders = wrb

        # misc
        self.align = self.get_alignment(align)
        # self.precision = precision

        # Column specs
        self.cell_white = cell_whitespace  # add whitespace for better legibility
        self.col_widths_true = self.get_column_widths(pre_table)

        # decide column widths
        self.col_widths, width_max = self.resolve_width(width)

        # init rows
        self.rows = []
        self.states = []
        self.state_props = []

        # table truncation / split stuff
        self._max_width = width_max
        self.handle_too_wide = too_wide
        # self.max_column_width = self.handle_too_wide.get('columns')

        self.show_colourbar = False

    def __repr__(self):
        return str(self)  # useful in interactive sessions to immediately print the table

    def __str__(self):
        if len(self.original_data):
            return self.make_table()
        else:
            return '{0}Empty Table{0}'.format(self._default_border)

    @property
    def data(self):
        return self.pre_table[self.has_col_head:, self.n_head_col:]

    @property
    def col_headers(self):
        # if self.has_col_head:
        return self.pre_table[:self.has_col_head, self.has_row_head:]

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
        value = np.reshape(value, (self.n_data_rows, 1))
        self.pre_table[self.has_row_head:, :self.has_col_head] = value

    @property
    def max_width(self):
        return self._max_width or get_terminal_size()[0]

    @max_width.setter
    def max_width(self, value):
        self._max_width = int(value)

    # def check_data_dim(self):

    def _apply_format(self, data, formatters, precision, minimalist):
        """convert to array of str"""

        # handle masked data
        if np.ma.is_masked(data):
            mask = data.mask
        else:
            mask = False

        ncols = data.shape[1]
        pprint = PrettyPrinter(precision=precision, minimalist=minimalist)

        # embed()

        if formatters is None:
            data = np.vectorize(pprint.pformat, (str,))(data)
        elif isinstance(formatters, dict):
            # format custom columns
            ixCustom = []
            for i, fmt in formatters.items():
                if isinstance(i, str) and (self._col_headers is not None) and \
                        (i in self._col_headers):
                    i = list(self._col_headers).index(i)
                # TODO maybe try except warn for errors
                data[:, i] = np.vectorize(fmt, (str,))(data[:, i])
                ixCustom.append(i)

            # format default columns
            ixDefault = list(set(range(ncols)) - set(ixCustom))
            data[:, ixDefault] = np.vectorize(pprint.pformat, (str,))(
                    data[:, ixDefault])

        elif np.size(formatters):
            if len(formatters) != ncols:
                raise ValueError('Incorrect number of formatters (%i) for table'
                                 'with %i columns' % (len(formatters), ncols))
            for i, fmt in enumerate(formatters):
                data[:, i] = np.vectorize(fmt, (str,))(data[:, i])
        else:
            raise TypeError('Invalid type for formatters: %s' % type(formatters))

        if np.size(mask) > 1:
            data[mask] = ''

        return data

    def resolve_width(self, width):
        width_min = 0
        width_max = None
        if width is None:
            # each column will be as wide as the widest data element it contains
            col_widths = self.get_column_widths(self.pre_table,
                                                as_displayed=True)
        elif np.size(width) == 1:
            # The table will be made exactly this wide
            width = int(width)  # requested width
            # TODO: DECIDE COL WIDTHS
            raise NotImplementedError
        elif np.size(width) == self.n_data_col:
            # each column width specified
            hcw = self.col_widths[:self.n_head_col]
            col_widths = np.r_[hcw, width]
        elif np.size(width) == self.ncols:
            # each column width specified
            col_widths = width
        elif isinstance(width, range):
            # maximum table width given.
            col_widths = self.get_column_widths(self.pre_table,
                                                as_displayed=True)
            width_min = width.start
            width_max = width.stop
        else:
            raise ValueError('Cannot interpret width %r' % str(width))

        return col_widths, width_max

    def resolve_borders(self, col_borders, where_col_borders, ncols, frame):
        borders = np.empty(ncols, dtype='<U10')  # NOTE: these include the upcoming
        if where_col_borders in (None, ...):  # default is col borders everywhere
            where_col_borders = np.arange(ncols)  #
        wcb = np.asarray(where_col_borders)
        # number / header borders can be explicitly indexed by -1j / -2j
        l = (wcb == -1j) | (wcb == -2j)
        if l.any():
            cx = l.sum()
            wcb[~l] += cx
            wcb[l] = range(cx)
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=ComplexWarning)
                wcb = wcb.astype(int)

        if col_borders is not None:
            borders[wcb] = col_borders
        if not frame:
            borders[-1] = ''
        return borders

    def compactify(self, data, col_headers):
        # check which columns can be compactified
        same = np.all(data == data[0], 0)  # columns for which all data identical
        isame, = np.where(same)
        # if a total is asked for on a column, make sure we don't compactify it
        isupp = np.setdiff1d(isame, np.nonzero(self.totals)[0])
        ishown = np.setdiff1d(range(data.shape[1]), isupp)
        suppressed = data[0, isupp]

        compacted = []
        if self.has_col_head:
            sup_head = np.take(col_headers, isupp)
            compacted = (sup_head, suppressed)
            col_headers = np.take(col_headers, ishown)

        return data[:, ~same], ishown, isupp, col_headers, compacted

    def get_column_widths(self, data, as_displayed=False, with_borders=False):
        """data should be string type array"""

        lenf = ansi.len_bare if as_displayed else len
        # deal with cell elements that contain newlines
        length = lambda s: max(map(lenf, s.split(os.linesep)))
        # NOTE: s.splitlines() may be better, but ''.splitlines() returns empty list which borks on map
        w = np.vectorize(length, [int])(data).max(axis=0)

        # add border size
        b = self.lcb if with_borders else 0

        return w + b + self.cell_white

    def get_width(self, data=None):
        if data is None:
            data = self.pre_table
        w = self.get_column_widths(data, as_displayed=True, with_borders=True)
        return sum(w)  # total column width

    def get_alignment(self, align):
        align = self.ALIGNMENT_MAP.get(align.lower()[0], align)
        if align not in '<^>':
            raise ValueError('Unrecognised alignment {!r}'.format(align))
        return align

    def get_totals(self, data, indices):
        if data.ndim < 2:
            return None

        totals = [None] * data.shape[1]
        if indices is not None:
            for i in indices:
                # handle str keys for total compute
                if isinstance(i, str) and (self._col_headers is not None) and \
                        (i in self._col_headers):
                    i = list(self._col_headers).index(i)

                # attempt to compute total
                col = data[:, i]
                try:
                    # TODO: handle masked data
                    # NOTE use sum and not np.nansum to avoid str concatenation
                    totals[i] = sum(col)
                except Exception as err:
                    warnings.warn('Could not calculate total for column %i.'
                                  '\n\n%s' % (i, str(err)))
                    totals[i] = '??'
            return totals

    @staticmethod
    def convert_dict(dic, ignore_keys, order):
        _dic = dic.copy()
        if not ignore_keys is None:
            for key in ignore_keys:
                _dic.pop(key, None)

        headers = list(_dic.keys())
        data = list(_dic.values())

        # h =  (row_headers, col_headers)
        if order.startswith('c'):
            # if row_headers is not None:
            # warn( "Dictionary keys will be superseded by {}." )
            row_headers = headers
        elif order.startswith('r'):
            col_headers = headers
        else:
            raise ValueError('Invalid order: %s' % order)

        return row_headers, col_headers, data

    # @expose.args()
    # @staticmethod
    def add_headers(self, data, row_headers=None, col_headers=None, number_rows=False):
        """Add row and column headers to table data"""
        #

        # row and column headers
        # TODO: error check for len of row/col_headers
        has_row_head = row_headers is not None
        has_col_head = col_headers is not None

        if has_row_head and self.has_totals:
            row_headers = list(row_headers) + ['Totals']

        if has_col_head:
            data = np.vstack((col_headers, data))

            # NOTE:  when both are given, the 0,0 table position is ambiguously both column and row header
            if has_row_head and (len(row_headers) == data.shape[0] - 1):
                row_headers = [''] + list(row_headers)

        if has_row_head:
            row_head_col = np.atleast_2d(row_headers).T
            data = np.hstack((row_head_col, data))

        if number_rows:
            numbers = np.arange(1, data.shape[0] + 1).astype(str)
            if has_col_head:
                numbers = ['#'] + list(numbers[:-1])
            if self.has_totals:
                numbers[-1] = ''

            data = np.c_[numbers, data]

        return data

    def make_title(self, width, continued=False):
        """make title line"""
        text = self.title + (' (continued)' if continued else '')
        return self.build_long_line(text, width,
                                    self.title_align, self.title_props)

    def build_long_line(self, text, width, align='<', props=None):

        if self.frame:
            b = self._default_border
            width -= len(b)
        else:
            b = ''
        borders = b, b

        if props is None:
            props = []
        _under = ('underline' in props)
        if _under:
            props = list(props)
            props.pop(props.index('underline'))

        lines = []
        for line in text.split(os.linesep):
            line = self.format_cell(line, width, align, *borders)
            line = codes.apply(line, props)  # self.apply_props(line, properties)
            lines.append(line)

        if _under:
            lines[-1] = _underline(lines[-1])  # codes.apply(lines[-1], 'underline')
        return '\n'.join(lines)

    def format_cell(self, text, width, align, border=_default_border, lhs=''):
        # this is needed because the alignment formatting gets screwed up by the ANSI
        # characters (which have length, but are not displayed)
        pad_width = ansi.len_codes(text) + width
        return self.cell_fmt.format(text, pad_width, align, border, lhs)

    def gen_multiline_rows(self, cells, colix=..., underline=False):
        """apply properties each item in the list of columns create a single string"""

        # convert to ansi array so we can measure component lengths
        # columns = as_ansi(columns, ndmin=1)

        # handle multi-line cell elements
        multilines = [col.split('\n') for col in cells]
        # NOTE: using str.splitlines here creates empty sequences for cells with empty strings
        # as contents.  This is undesired since this generator will then yield nothing instead
        # of a formatted row
        nlines = max(map(len, multilines))

        for i, row_items in enumerate(itt.zip_longest(*multilines, fillvalue='')):
            # print(row_items)
            row = self.make_row_single(row_items, colix)
            if (i + 1 == nlines) and underline:
                row = _underline(row)  # as_ansi(row, 'underline')
            yield row

    def make_row_single(self, cells, colix=...):
        # TODO: handle various column alignment...

        # format cells
        align = itt.repeat(self.align)
        cw = self.col_widths[colix]
        cb = self.borders[colix]
        cells = list(map(self.format_cell, cells, cw, align, cb))
        # cells = list(map(cell_fmt, cells, col_padwidths, self.borders))

        # Apply properties to whitespace filled row headers (including column borders)
        if self.frame:
            cells[0] = self._default_border + cells[0]
        if self.has_row_head:
            cells[0] = codes.apply(cells[0], self.row_head_props)

        # stick cells together
        row = ''.join(cells)
        self.rows.append(row)

        return row

    def make_table(self):
        """Construct the table and return it as as one long str"""

        table_width = sum(self.col_widths) + self.lcb.sum()

        # TODO: truncation
        # TODO: here data should be an array of str objects.  To do the truncation, we first need to strip
        # TODO: the control characters, truncate, then re-apply control....
        # TODO: ??? OR is there a better way??

        if table_width > self.max_width:  # if self.handle_too_wide == 'split':
            self.title += '\n'  # to indicate continuation under title line
            split_tables = self.split()
            if self.show_colourbar:
                split_tables[-1] = self.add_colourbar(split_tables[-1])
            table = '\n\n'.join(split_tables)
            return table
        # else:
        #     raise NotImplementedError
        else:
            table = self._build()
            return '\n'.join(table)

    def split(self, max_width=None):
        # TODO: return Table objects??

        max_width = max_width or self.max_width
        split_tables = []
        widths = self.col_widths + self.lcb
        # n_head_col = self.has_row_head + self.has_row_nrs
        rhw = widths[:self.n_head_col].sum()  # row header width

        splix = 0  # FIXME: adjust to use pre_table indices!!!???                    #location of current split
        while True:
            if splix == self.n_data_col:
                break

            ctcw = np.cumsum(widths[splix:])  # cumulative total column width
            ix, = np.where(ctcw + rhw > max_width)  # indices of columns beyond max width
            if len(ix):  # need to split
                endix = splix + max(ix[0], 1)  # need at least one column to build table
                if ix[0] == 0:  # first column +row headers too wide to display
                    'TODO: truncation_policy'
            else:
                endix = None

            # make a table using selection of columns
            tbl = self._build(splix, endix, bool(splix))
            tblstr = '\n'.join(map(str, tbl))
            split_tables.append(tblstr)

            if endix is None:
                break
            splix = endix
        return split_tables

    # def _build(self, c0=0, c1=None, continued=False):

    def _build(self, c0=0, c1=None, continued=False):
        """
        Build partial or full table.

        Parameters
        ----------
        c0 : int, optional
            starting column (data)
        c1 : int, optional
           ending column (data)
        continued: bool, optional
            whether or not continuation of split table

        Returns
        -------
        list of str (table rows)
        """
        table = []
        # make a list of column indices from which table will be built
        segm = slice(c0, c1)
        n_head_col = self.has_row_head + self.has_row_nrs
        headix = np.arange(n_head_col)  # always print header columns
        colix = np.arange(self.n_data_col)[segm] + n_head_col
        colix = np.hstack([headix, colix])
        part_table = self.pre_table[:, colix]
        table_width = self.col_widths[colix].sum() + self.lcb[colix].sum()

        if self.frame:
            # top line
            # NOTE: ANSI overline not supported (linux terminal) use underlined whitespace
            lcb = len(self._default_border)
            top_line = ' ' * (table_width + lcb)
            top_line = _underline(top_line)  # as_ansi(top_line, 'underline')
            table.append(top_line)

        # title
        if self.title is not None:
            title = self.make_title(table_width, continued)
            table.append(title)

        # FIXME; case if title wider than table!
        # FIXME: problems with too-wide column

        # compacted columns
        if np.size(self.compacted):
            # display compacted columns in single row
            names, values = self.compacted
            compact = Table(values, row_headers=names,
                            row_head_props=self.col_head_props,
                            col_borders='= ', frame=False)
            compact_rows = self.build_long_line(str(compact), table_width)
            table.append(compact_rows)

        # make rows
        for i, row_cells in enumerate(part_table):
            underline = (i in self.where_row_borders)
            for row in self.gen_multiline_rows(row_cells, colix, underline):
                if i == 0 and self.has_col_head:
                    row = codes.apply(row, self.col_head_props)
                table.append(row)
        return table

    # def expand_dtype(self, data):
    #     # enlarge the data type if needed to fit escape codes
    #     _, type_, size = re.split('([^0-9]+)', data.dtype.str)
    #     if int(size) < self.col_widths.max() + 20:
    #         dtype = type_ + str(int(size) + 20)
    #         data = data.astype(dtype)
    #     return data

    def colourise(self, states, *colours, **kws):
        """

        Parameters
        ----------
        states
        colours
        kws : dict
            eg: {'bg': 'rbg'}

        Returns
        -------

        """
        # if less colours than number of states are specified = states.astype(int)
        # if len(colours) < states.max() + 1:
        #     colours = ('default',) + colours  # i.e. index zero corresponds to default colour
        #
        # while len(colours) < states.max() + 1:
        #     colours += colours[-1:]  # all remaining higher states will be assigned the same colour
        #

        propList = ansi.get_state_dicts(states, *colours, **kws)

        # propIter = ansi._prop_dict_gen(*colours, **kws)
        # propList = list(propIter)
        # nstates = len(propList)
        # istart = states.max() + 1 - nstates

        for i, props in enumerate(propList):
            where = (states == i)
            if np.any(where):
                self.data[where] = as_ansi(self.data[where], **props)
            self.state_props.append(props)

        # plonk data into pre_table
        # r0 = int(self.has_col_head)
        # c0 = int(self.has_row_head + self.has_row_nrs)
        # self.pre_table[r0:, c0:] = self.data

        self.states = np.unique(states)
        self.show_colourbar = True

        return self.data

    # alias
    colorize = colourise

    def flag_headers(self, states, *colours, **kws):

        states = np.asarray(states, int)
        propList = ansi.get_state_dicts(states, *colours, **kws)

        # apply colours implied by maximal states sequentially to headers
        for i, s in enumerate(('col', 'row')):
            h = getattr(self, '%s_headers' % s)
            if h is not None:
                flags = np.take(propList, states.max(i))  # operator.itemgetter(*states.max(0))(propList)
                h = ansi.rainbow(h.ravel(), flags)
                setattr(self, '%s_headers' % s, h)

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
            cbar += codes.apply(str(lbl), **props)

        # cbar = ''.join(map(as_ansi, self.states[start:], self.colours[start:]))
        return '\n'.join((table, cbar))

    def hstack(self, other):
        """plonk two tables together horizontally"""

        # FIXME: better to alter data and return Table

        lines1 = str(self).splitlines(True)
        lines2 = str(other).splitlines(True)
        nl = '\n' * max(len(lines1), len(lines2))

        print(''.join((map(str.replace, lines1, nl, lines2))))

    def to_latex(self, longtable=True):
        """Convert to latex tabular"""
        raise NotImplementedError
        # TODO

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


if __name__ == '__main__':
    # do Tests
    from collections import OrderedDict

    # from dict
    Ncpus = 8
    nproc = OrderedDict(('find', Ncpus),
                        ('fit', 2 * Ncpus),
                        ('phot', 2 * Ncpus),
                        ('bg', 2 * Ncpus),
                        ('defer', 2))
    table = Table(title='Load balance', data=nproc, order='r')
    print(table)

    # TODO: print pretty things:
    # http://misc.flogisoft.com/bash/tip_colors_and_formatting
    # http://askubuntu.com/questions/512525/how-to-enable-24bit-true-color-support-in-gnome-terminal
    # https://github.com/robertknight/konsole/blob/master/tests/color-spaces.pl
