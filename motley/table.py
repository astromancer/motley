"""
Pretty printed tables for small data sets
"""

import itertools as itt
import os, logging
import warnings
from shutil import get_terminal_size

import numpy as np

# from recipes.pprint import PrettyPrinter
from recipes.logging import LoggingMixin
from . import ansi
from . import codes
from . import wideness, get_alignment

import numbers, functools as ftl
from recipes import pprint
from recipes.introspection.utils import get_module_name

# from .utils import formatter

# TODO: unit tests!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# TODO: GIST
# TODO: possibly integrate with astropy.table ...........................
# TODO: HIGHLIGHT COLUMNS
# TODO: OPTION for plain text row borders?

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

# module level logger
logger = logging.getLogger(get_module_name(__file__))

#
TRUNC_CHR = '…'  # single character ellipsis u"\u2026" to indicate truncation
BORDER = '⎪'  # U+23aa Sm CURLY BRACKET EXTENSION ⎪  # '|'

# defines vectorized length
lengths = np.vectorize(len, [int])


def _echo(_):
    return _


def str2tup(keys):
    if isinstance(keys, str):
        keys = keys,  # a tuple
    return keys


def apportion(w, n):
    # divide space as equally as possible between `n` columns
    space = np.array([w // n] * n)
    space[:(w % n)] += 1
    return space


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
        raise ValueError('Cannot interpret width %r for data of shape %s'
                         % (width, data.shape))


def resolve_input(obj, data, col_headers, what, converter=None,
                  default_factory=None, args=(), raises=True,
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

    if raises:
        def action(msg):
            raise ValueError(msg)
    else:
        action = logger.warning

    keys = list(obj.keys())
    if (str in set(map(type, keys))) and col_headers is None:
        # only really a problem if formatter is not None
        action('Could not assign %r due to missing `column_headers`' % what)

    # convert all keys in format dict to int
    if col_headers is not None:
        col_headers = list(col_headers)
        for key, val in obj.items():
            if isinstance(key, str):
                if key not in col_headers:
                    action('Could not assign %s. Key %r not in `column_headers`'
                           % (what, key))
                    continue
                #
                new_key = col_headers.index(key)
                # at this point key should be int
                obj[new_key] = obj.pop(key)

            elif not isinstance(key, numbers.Integral):
                action('Key %r invalid type for mapping to column' % key)

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


# def get_format_dict(data, formatters, col_headers, what, default_factory,
#                     args, **kws):
#     n_cols = data.shape[1]
#     if formatters is None:
#         formatters = {}
#
#     # convert formatters to dict
#     if not isinstance(formatters, dict):
#         if len(formatters) != n_cols:
#             raise ValueError('Incorrect number of specifiers (%i) for column %r'
#                              ' in table with %i columns' %
#                              (len(formatters), what, n_cols))
#         formatters = dict(enumerate(formatters))
#
#     keys = list(formatters.keys())
#     if (str in set(map(type, keys))) and col_headers is None:
#         raise ValueError('Could not assign %r due to missing `column_headers`'
#                          % what)
#
#     # convert all keys in format dict to int
#     if col_headers is not None:
#         col_headers = list(col_headers)
#         for key in keys:
#             if isinstance(key, str):
#                 if key not in col_headers:
#                     raise ValueError('Could not assign formatter %r. Key '
#                                      'not in `column_headers`' % key)
#                 #
#                 new_key = col_headers.index(key)
#                 # at this point key should be int
#                 formatters[new_key] = formatters.pop(key)
#
#             elif not isinstance(key, numbers.Integral):
#                 raise ValueError('Key %r invalid type for mapping to '
#                                  'column' % key)
#
#     # get default formatters
#     idx_no_fmt = set(range(n_cols)) - set(formatters.keys())
#     for i in idx_no_fmt:
#         formatters[i] = default_factory(i, *args, **kws)
#
#     return formatters


#
# def get_default_alignment(col):
#     use = ~col.mask if np.ma.is_masked(col) else ...
#     ts = set(map(type, col[use]))


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
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=np.ComplexWarning)
            wcb = wcb.astype(int)

    if col_borders is not None:
        borders[wcb] = col_borders

    # final column border
    borders[-1] = BORDER if frame else ''

    return borders


def dict_to_list(dic, ignore_keys, order):
    """
    Convert input dict to list of values with keys as column / row_headers
    (depending on `order`)

    Parameters
    ----------
    dic
    ignore_keys
    order

    Returns
    -------

    """
    _dic = dic.copy()
    if ignore_keys is not None:
        for key in ignore_keys:
            _dic.pop(key, None)

    headers = list(_dic.keys())
    data = list(_dic.values())

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


def highlight(array, condition, props, formatter=pprint.numeric, **kws):
    out = np.vectorize(formatter, (str,))(array, **kws)
    if condition in (all, ...):
        condition = np.ones_like(array, bool)

    if condition.any():
        tmp = np.vectorize(codes.apply, (str,))(out[condition], props)
        dtype = 'U%i' % (max(tmp.itemsize, out.itemsize) / 4)
        out = out.astype(dtype)
        out[condition] = tmp
    return out


def truncate(item, width):
    # TODO: if TRUNC_CHR more than 1 chr long
    cw = 0  # cumulative width
    s = ''
    for parts in ansi.parse(str(item), named=True):
        cw += len(parts.s)
        if cw > width:
            s += ''.join(parts[:3] + (parts.s[:width - 1], TRUNC_CHR) +
                         parts[-1:])
            break
        else:
            s += ''.join(parts)
    return s


# TODO: check out wcwidth lib


from recipes.string import match_brackets

import re


class TerseKws(object):
    """

    """

    def __init__(self, pattern, answer=None):
        """

        Parameters
        ----------
        pattern
        answer
        """
        regex = ''
        self.answer = ''
        self.pattern = pattern
        sub = pattern
        while 1:
            s, (i0, i1) = match_brackets(sub, '[]', return_index=True)
            # print(s, i0, i1)
            if s is None:
                regex += sub
                break

            regex += f'{sub[:i0]}[{s}]{{0,{len(s)}}}'
            self.answer += sub[:i0]
            sub = sub[i1 + 1:]

            # print(sub, regex)
            # i += 1
        self.regex = re.compile(regex)

        if answer:
            self.answer = str(answer)

    def __call__(self, s):
        if self.regex.match(s):
            return self.answer

    def __repr__(self):
        return f'{self.pattern} --> {self.answer}'


import types


# from recipes.containers.dicts import Many2OneMap
class KeywordResolver(object):
    """Helper class for resolving terse keywords"""

    def __init__(self, mappings):
        self.mappings = []
        for k, v in mappings.items():
            self.mappings.append(TerseKws(k, v))

    def __repr__(self):
        return repr(self.mappings)

    def resolve(self, func, kws, namespace):

        # get arg names and defaults
        code = func.__code__
        defaults = func.__defaults__
        arg_names = code.co_varnames[1:code.co_argcount]

        # load the defaults / passed args
        n_req_args = len(arg_names) - len(defaults)
        # opt_arg_names = arg_names[n_req_args:]
        # now get non-default arguments (those passed by user)
        args_dict = {}
        for i, o in enumerate(arg_names[n_req_args:]):
            v = namespace[o]
            if v is not defaults[i]:
                args_dict[o] = v

        # resolve terse kws and add to dict
        for k, v in kws.items():
            if k not in arg_names:
                for m in self.mappings:
                    if m(k) in arg_names:
                        args_dict[m(k)] = v
                        break
                else:
                    # get name
                    name = func.__name__
                    if isinstance(func, types.MethodType):
                        name = '.'.join((func.__self__.__class__.__name__,
                                         name))
                    raise KeyError(
                            f'{k!r} is not a valid keyword for {name!r}')

        return args_dict


class Table(LoggingMixin):
    """
    An ascii table formatter. Good for displaying data, definitely not for data
    manipulation.  Plays nicely with ANSI colours and multi-line cell elements.
    """

    # mappings for terse kws
    _mappings = {'unit[s]': 'units',
                 'footnote[s]': 'footnotes',
                 'formatter[s]': 'formatters',
                 'cell_white[space]': 'cell_whitespace',
                 'minimal[ist]': ' minimalist',
                 '[column_]width[s]': '',
                 'c[olumn_]groups': 'col_groups',
                 '[row_]nrs': 'row_nrs',
                 'total[s]': ''}
    for rc, p in {'row': 'r[ow_]', 'col': 'c[olumn_]'}.items():
        _mappings.update({f'{p}head[ers]': f'{rc}_headers',
                          f'{p}head[er]_prop[erties]': f'{rc}_head_props',
                          f'{p}borders': 'col_borders'})
    #
    _kw_map = KeywordResolver(_mappings)

    #
    _default_border = BORDER

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

    # @classmethod
    # def from_dict(cls, *columns, **kws):

    def __init__(self, data,
                 title=None, title_align='center', title_props=('underline',),
                 col_headers=None, col_head_props='bold',
                 units=None,
                 col_borders=_default_border, vlines=None,
                 col_groups=None,
                 row_headers=None, row_head_props='bold',
                 row_nrs=False,
                 hlines=None,
                 frame=True,
                 align=None,
                 precision=2, minimalist=False,
                 compact=False,
                 ignore_keys=None, order='c',
                 width=None, too_wide='split',
                 cell_whitespace=1,
                 totals=None,
                 formatters=None,
                 masked='--',
                 flags=None,
                 insert=None,
                 highlight=None,
                 footnotes='', **kws):

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
        align, title_align : {'left', 'right', 'center', '<', '>', '^', None}
            column / title alignment
            if None (default)- right align for numerical type data, left align
            for everything else

        col_headers, row_headers  : array_like
            column -, row headers as sequence of str objects.
        col_head_props, row_head_props : str or dict or array_like
            Column header properties.  If `row_nrs` is True,
            the row_head_props will be applied to the number column as well
            TODO: OR a sequence of these, one for each column
        TODO: column head align


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
            rows or columns. Defualt is to interpret 1D data as a column with
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
                  `pprint.PrettyPrinter` subclass is used which respects the
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

        #TODO: list attributes here
        """

        # FIXME: precision etc ignored when init from dict
        # FIXME: hlines with cell elements that have ansi ... effects don't
        #  stack...

        # resolve kws
        if kws:
            kws_ = self._kw_map.resolve(self.__init__, kws, locals())
            self.__init__(data, **kws_)
            return

        # save a backup of the original data
        # self.original_data = data
        self._col_headers = col_headers

        # check arguments valid
        assert order in 'rc', 'Invalid order: %s' % order

        # convert dict
        if isinstance(data, dict):
            row_headers, col_headers, data = dict_to_list(data, ignore_keys,
                                                          order)

        # convert to object array
        data = np.asanyarray(data, 'O')

        # check data shape / dimensions
        dim = data.ndim
        if dim == 1:
            # default for 1D data is to display in a column with row_headers
            if order.startswith('c'):
                data = data[None].T
        # TODO: deprecate order='c' / order='r' in favour o
        # elif dim == 2 and order.startswith('r'):
        #     data = data.T

        if dim > 2:
            raise ValueError('Only 2D data can be tabled! Data is %iD' % dim)

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
        self.has_col_head = hch = (col_headers is not None)
        self.n_head_col = nhc = hrh + hrn

        # FIXME: column headers should be left aligned even when column values
        #  are right aligned.
        align = resolve_input(align, data, col_headers, 'alignment',
                              get_alignment,
                              self.get_default_align)
        # make align an array with same size as nr of columns in table
        n_cols = data.shape[1] + self.n_head_col
        self.align = np.empty(n_cols, 'U1')
        self.align[:self.n_head_col] = '<'  # row headers are left aligned
        self.align[self.n_head_col:] = list(align.values())

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
        data = self._apply_format(data, self.formatters, str(masked), flags)

        # add totals row
        if self.has_totals:
            totals = self._apply_format(self.totals, self.formatters, '')
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

        # add the (row/column) headers / row numbers / totals
        self.pre_table = self.add_headers(
                data, row_headers, col_headers, row_nrs)
        # note `pre_table` is dtype='O'

        self.cell_white = int(cell_whitespace)

        # handle group headers
        if col_groups is not None:
            assert len(col_groups) == self.data.shape[1]
            col_groups = ([''] * self.n_head_col) + list(col_groups)

        self.col_groups = col_groups
        # FIXME: too wide col_groups should truncate

        # compactify
        self.compact = compact
        self.compacted = []
        self._idx_shown = np.arange(self.shape[1])
        if compact:
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
        has_compact = compact and np.size(self.compacted)
        if has_compact:
            # this is an instance of `Table`!!
            self._compact_table = self._get_compact_table()

        # check for too-wide title or compacted lines, and amend column widths
        # to match
        tw = 0
        if self.has_title or has_compact:
            if has_compact:
                tw = self._compact_table.get_width()

            # use explicit split('\n') below instead of splitlines since the
            # former yields a non-empty sequence for title=''
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

        # insert lines
        self.insert = dict(insert or {})
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
        return sum(((self.col_groups is not None),
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
            m = len(self.compacted[0]) if len(self.compacted) else 0
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

    def get_default_formatter(self, col_idx, precision, minimalist, data):
        """

        Parameters
        ----------
        col_idx
        precision
        minimalist

        Returns
        -------

        """
        types_ = self.col_data_types[col_idx]

        if len(types_) == 1:
            type_, = types_  # nb since it's a set, don't try types_[0]
            # all data in this column is of the same type
            if issubclass(type_, str):  # this includes np.str_!
                return _echo

            if not issubclass(type_, numbers.Real):
                return str

            #
            right_pad = 0
            sign = ''
            if issubclass(type_, numbers.Integral):
                if minimalist:
                    precision = 0

            else:  # real numbers
                if minimalist and self.align[col_idx] == '>':
                    right_pad = precision
                sign = (' ' * np.any(data[:, col_idx] < 0))

            # print(col_idx,type_, precision, minimalist, sign, right_pad)

            return ftl.partial(pprint.decimal,
                               precision=precision,
                               compact=minimalist,
                               sign=sign,
                               right_pad=right_pad)

            #  NOTE: single dispatch not a good option here due to formatting
            #   subtleties
            # return formatter.registry[type_](None, precision=precision,
            #                                  compact=minimalist,
            #                                  sign=sign,
            #                                  right_pad=right_pad)

        return pprint.PrettyPrinter(precision=precision,
                                    minimalist=minimalist).pformat

    def _apply_format(self, data, formatters, masked_str='--', flags=None):
        """convert to array of str"""

        # if self.
        flags = flags or {}

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
            else:
                use = ...

            # wrap the formatting in try, except since it's usually not
            # critical and getting some info is better than none
            try:
                data[use, i] = np.vectorize(fmt, (str,))(col[use])
            except Exception as err:
                logger.warning('Could not format column %i with %r due to '
                               'the following exception:\n%s', i, fmt, err)
                data[use, i] = np.vectorize(str, (str,))(col[use])

            # concatenate data with flags
            # flags = flags.get(i)
            if i in flags:
                try:
                    data[use, i] = np.char.add(data[use, i].astype(str),
                                               flags[i])
                except Exception as err:
                    logger.warning(
                            'Could not append flags to formatted data for '
                            'column %i due to the following  exception:\n%s',
                            i, err)

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
            if issubclass(typ, (numbers.Integral, numbers.Real)):
                return '>'

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

    def compactable(self, ignore=()):
        # todo: no column headers raise
        idx_same, = np.where(np.all(self.data == self.data[0], 0))
        _, idx_ign = np.where(self.col_headers == np.atleast_2d(ignore).T)
        idx_same = np.setdiff1d(idx_same, idx_ign)
        return idx_same

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
        if len(data) <= 1:
            return ...

        if not self.has_col_head:
            self.logger.warning('Requested `compact` representation, but no '
                                'column headers provided. Ignoring.')
            return ...

        nhc = self.n_head_col
        idx_same, = np.where(np.all(data == data[0], 0))
        _, idx_ign = np.where(self.col_headers == np.atleast_2d(ignore).T)
        idx_same = np.setdiff1d(idx_same, idx_ign) + nhc
        #

        # if a total is asked for on a column, make sure we don't suppress it
        totals = None
        if self.has_totals:
            totals = self.pre_table[-1]

        idx_squash = np.setdiff1d(idx_same, np.nonzero(totals)[0])
        val_squash = self.pre_table[self.n_head_rows - 1, idx_squash]
        idx_show = np.setdiff1d(range(self.shape[1]), idx_squash)
        # check if any data left to display
        if idx_show.size == 0:
            self.logger.warning('No data left in table after compacting '
                                'singular value columns.')

        # remove columns
        # self.col_data_types = np.take(self.col_data_types, idx_show[nhc:] - nhc)
        self._idx_shown = idx_show
        self.compacted = [np.take(self.col_headers, idx_squash), val_squash]

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
                item = self.pre_table[i, j]
                self.pre_table[i, j] = truncate(item, w)

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

    def get_totals(self, data, col_indices):

        # suppress totals for tables with single row
        if data.shape[0] <= 1:
            if col_indices is not None:
                self.logger.info('Suppressing totals line since table has only '
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
    def add_headers(self, data, row_headers=None, col_headers=None,
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

    def format_cell(self, text, width, align, border=_default_border, lhs=''):
        # this is needed because the alignment formatting gets screwed up by the
        # ANSI characters (which have length, but are not displayed)
        pad_width = ansi.length_codes(text) + width
        return self.cell_fmt.format(text, pad_width, align, border, lhs)

    def gen_multiline_rows(self, cells, indices=..., underline=False):
        """
        handle multi-line cell elements, apply properties to each item in the
        list of columns create a single string

        Parameters
        ----------
        cells
        indices
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
            row = self.make_row(row_items, indices)
            if (i + 1 == n_lines) and underline:
                row = _underline(row)
            yield row

    def make_row(self, cells, indices=...):

        # format cells
        cells = list(map(self.format_cell, cells, self.col_widths[indices],
                         self.align[indices], self.borders[indices]))

        # Apply properties to whitespace filled row headers
        if self.has_row_head:
            cells[0] = codes.apply(cells[0], self.row_head_props)

        if self.frame:
            cells[0] = self._default_border + cells[0]

        # stick cells together
        row = ''.join(cells)
        self.rows.append(row)
        return row

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
            props.pop(props.index('underline'))

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
            if self.title:
                self.title += '\n'  # to indicate continuation under title line
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
            tbl = self._build(idx_show, bool(splix))
            tblstr = '\n'.join(map(str, tbl))
            split_tables.append(tblstr)

            if endix is None:
                break
            splix = endix
        return split_tables

    # def _build(self, c0=0, c1=None, continued=False):

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

        part_table = self.pre_table[:, column_indices]
        table_width = self.get_width(column_indices)
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

        # FIXME; case if title wider than table!
        # FIXME: problems with too-wide column

        # compacted columns
        if np.size(self.compacted):
            # display compacted columns in single row
            compact_rows = self.build_long_line(str(self._compact_table),
                                                table_width,
                                                props=['underline'])
            table.append(compact_rows)

        # column groups
        if self.col_groups is not None:
            line = self._default_border
            lbl = self.col_groups[column_indices[0]]  # name of current group
            gw = 0  # width of current column group header

            # FIXME: this code below in `format cell??`
            for i, j in enumerate(column_indices):
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
                # line += '{: ^{:}s}{:}'.format(lbl, gw - 1, self.borders[j])

            # table.append(_underline(self.borders[0] +
            #                         ' ' * (table_width - lcb) +
            #                         self.borders[-1]))

            table.append(_underline(line))

        # make rows
        start = -(self.has_col_head + self.has_units)
        used = set()
        for i, row_cells in enumerate(part_table, start):
            underline = (i in self.hlines)
            row_props = self.highlight.get(i)
            insert = self.insert.get(i, None)
            if insert is not None:
                table.extend(self.insert_lines(insert, table_width))
                used.add(i)

            for row in self.gen_multiline_rows(row_cells, column_indices,
                                               underline):
                # if i == 0 and self.has_col_head:
                #     row = codes.apply(row, self.col_head_props)
                # fixme: maybe don't apply to border symbols
                table.append(codes.apply(row, row_props))

        # check if all insert lines have been consumed
        unused = set(self.insert.keys()) - used
        for i in unused:
            # underline = (i in self.hlines)
            table.extend(self.insert_lines(self.insert[i], table_width))

        # finally add any footnotes present
        if len(self.footnotes):
            table.extend(self.footnotes)

        return table

    def _get_compact_table(self, n_cols=None, justify=False):

        if isinstance(self.compact, numbers.Integral) and n_cols is None:
            n_cols = self.compact

        n_cols = int(n_cols)
        n_comp = len(self.compacted[0])
        table_width = self.get_width()  # excludes lhs border
        if n_cols is None:
            # find optimal shape for table                  # +3 for ' = '
            widths = np.vectorize(len)(self.compacted)
            _2widths = widths.sum(0) + 3
            for n_cols in range(1, 5):
                pad = (n_comp // n_cols + (n_comp % n_cols)) * n_cols - n_comp
                ccw = np.hstack([_2widths, [0] * pad]).reshape(n_cols, -1).max(
                        1)
                # +3 for column spacing
                if sum(ccw + 3) > table_width:
                    if np.any(ccw == 0):
                        continue
                    n_cols -= 1
                    break

        # n items per column
        n_pc = (n_comp // n_cols) + (n_comp % n_cols)
        pad = n_pc * n_cols - n_comp
        data = np.hstack([self.compacted, [[''] * pad] * 2])
        data = np.hstack(data.T.reshape(n_cols, n_pc, 2))
        data = np.atleast_2d(data.squeeze())

        # todo row_head_props=self.col_head_props,
        # self._default_border #  u"\u22EE" VERTICAL ELLIPSIS
        col_borders = ['= ', self._default_border + ' '] * n_cols
        col_borders[-1] = ''

        # justified spacing
        w = apportion(table_width, n_cols)
        widths = np.vectorize(len)(data).max(0)
        widths[0::2] += 1
        extra = sum(w - widths.reshape(2, -1).sum(0) - 3)  # '= ' borders
        if justify:
            widths[1::2] += apportion(extra, n_cols)
        return Table(data, col_borders=col_borders, frame=False,
                     width=widths)

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
