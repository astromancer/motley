import numpy as np

# from myio import warn

from recipes.misc import getTerminalSize
from recipes.iter import as_sequence, pairwise
from decor import expose

from .str import AnsiStr, as_ansi

# from IPython import embed

#TODO: unit tests!!!!!!!!

##########################################################################################################################################
#from PyQt4.QtCore import pyqtRemoveInputHook, pyqtRestoreInputHook
#TODO:  Check out astropy.table ...........................
#TODO: HIGHLIGHT ROWS / COLUMNS
#TODO: OPTION for plain text row borders
class Table( object ):          #TODO: remane as ansi table??
    ALIGNMENT_MAP = { 'r' : '>', 'l' : '<', 'c' : '^' }     #map to alignment format characters
    ALLOWED_KWARGS = [] #TODO

    col_fmt = '{0:{2}{1}}'  # The column format specification. 0 - item; 1 - fill; 2 - alignment character
    #====================================================================================================
    def __init__(self, data,
                 title=None, title_props=(), title_alignment='center',
                 col_headers=None, col_head_props='bold', col_widths=None,
                 col_borders='|', col_sort=None,
                 #TODO: where_col_borders
                 row_headers=None, row_head_props='bold', where_row_borders=None,
                 row_sort=None,
                 align='left', precision=2, number_rows=False,
                 ignore_keys=None, order ='c',
                 max_col_width=None, max_table_width=None, truncation='split',
                ):
        #TODO: reformat docstring
        '''
        Class to create and optionally colourise tabular representation of data
        for terminal output.
        Parameters
        ----------
        data            :       array-like
            input data - must be 1D, 2D or dict
            if dict, keys will be used as row_headers, and values as data

        title           :       The table title
        title_props     :       str, tuple or dict with ANSICodes property descriptors
        title_alignment :       title alignment - ('left', 'right', or 'center')

        col_headers     :       column headers.
        col_head_props  :       str, tuple or dict with ANSICodes property descriptors
                                to use as global column header properties
                                TODO: OR a sequence of these, one for each column
        col_widths      :       numerical column width
        col_borders     :       character used as column seperator
        col_sort        :       TODO callable that operates on strings and returns column sorting order

        row_headers     :
        row_head_props  :       see col_head_props
        where_row_borders:      sequence with row numbers below which a solid border will be drawn.
                                Default is after column headers and after last line
        row_border_type :       TODO
        row_sort        :       TODO callable that operates on strings and returns row sorting order

        align           :       column alignment  {'left', 'right', or 'center'}
        precision        :      integer precision to use for number representation FIXME!!!!!!!!!!!!!
        number_rows     :       bool
            Will number the rows if True

        ignore_keys     :       if dictionary is passed as data, optionally specify the keys that will not be printed in table

        order           :       str - {'row', 'col'}
            whether to interpret data as row ordered or column ordered

        truncation:      (dict) what to do in case of tables that are too wide for display
        '''

        #self.datatypes = np.vectorize(type)(data)
        self.original_data = data

        if isinstance(data, dict):
            headers, data = self.convert_dict(data, ignore_keys)
            #h =  (row_headers, col_headers)
            if order.startswith('c'):
                #if row_headers is not None:
                   #warn( "Dictionary keys will be superceded by {}." )
                row_headers = headers
            elif order.startswith('r'):
                col_headers = headers

        # TODO: deal with multiline cell data

        #convert to array of AnsiStrs
        self.data = as_ansi(data, precision=precision, minimalist=False)


        #check data shape
        dim = np.ndim(self.data)
        if dim == 1:
            if order.startswith('c'):
                self.data = self.data[None].T               #default for 1D data is to display in a column with row_headers
        if dim > 2:
            raise ValueError('Only 2D data can be tabelised!  Data is {}D'.format(dim))

        # title
        self.title = title
        self.title_props =  title_props
        self.title_alignment = self.get_alignment(title_alignment)

        # misc
        self.number_rows = number_rows
        self.col_borders = col_borders
        self.align = self.get_alignment(align)
        self.precision = precision

        # Add row/column headers
        self.col_head_props = col_head_props
        self.row_head_props = row_head_props
        self.pre_table = self.add_headers(self.data, row_headers, col_headers)
        self.nrows, self.ncols = self.pre_table.shape # np.add(data.shape, (int(self.has_row_head), int(self.has_col_head))  #

        # Column specs
        if col_widths is None:
            self.col_widths = self.get_column_widths(self.pre_table) + 1    #add 1 for whitespace
            self.col_widths_no_ansi = self.get_column_widths(self.pre_table, as_displayed=True)
        else:
            self.col_widths = col_widths

        # Row specs
        self.rows = []
        # self.row_fmt = ('{}'+self.col_borders) * Ncols

        if not where_row_borders is None:
            wrb = np.array(where_row_borders)
            wrb[wrb < 0] += self.nrows
            self.where_row_borders = wrb
        else:
            if self.has_col_head:
                self.where_row_borders = [0, self.nrows-1]
            else:
                self.where_row_borders = [self.nrows-1]

        # table truncation / split stuff
        self.max_table_width = max_table_width or getTerminalSize()[0]

        # if truncation_policy.lower() != 'split':
        #     raise NotImplementedError
        self.truncation = truncation
        # self.max_column_width = self.truncation.get('columns')

        self.show_colourbar = False

    #====================================================================================================
    def get_column_widths(self, data, as_displayed=False, with_borders=True):
        '''data should be string type array'''
        lcb = len(self.col_borders) if with_borders else 0
        lenf = AnsiStr.len_no_ansi if as_displayed else len
        # max_column_width = self.truncation.get('columns')
        return np.vectorize(lenf)(data).max(axis=0) + lcb

    #====================================================================================================
    def __repr__(self):
        return str(self)            # useful in interactive sessions to immediately print the table

    #====================================================================================================
    def __str__(self):
        if len(self.original_data):
            return self.make_table()
        else:
            return '|Empty Table|'

    #====================================================================================================
    def get_alignment(self, char):
        if char.lower()[0] in self.ALIGNMENT_MAP:
            return self.ALIGNMENT_MAP[char.lower()[0]]
        else:
            raise ValueError('Unrecognised alignment {!r}'.format(char))

    #====================================================================================================
    @staticmethod
    def apply_props(obj, props=()):
        '''Convert to ansi array and apply given properties globally'''
        #TODO: options to apply globally, or sequentially??
        if isinstance(props, dict):
            return as_ansi(obj, **props)
        else:
            props = as_sequence(props, return_as=tuple)
            return as_ansi(obj, props)

    #====================================================================================================
    @staticmethod
    def convert_dict(dic, ignore_keys):
        _dic = dic.copy()
        if not ignore_keys is None:
            for key in ignore_keys:
                _dic.pop(key, None)

        keys = list(_dic.keys())
        vals = list(_dic.values())
        return keys, vals

    #====================================================================================================
    # @expose.args()
    def add_headers(self, data, row_headers=None, col_headers=None):
        '''Add row and column headers to table data'''

        # row and column headers     #TODO: error check for len of row/col_headers
        self.has_row_head = row_headers is not None
        self.has_col_head = col_headers is not None
        self.col_headers = col_headers  # May be None. will be re-written below if necessary
        self.row_headers = row_headers

        if self.has_col_head:
            # self.col_headers = self.apply_props(col_headers, col_head_props)
            data = np.vstack((self.col_headers, data))

            if self.has_row_head:
                # NOTE:  when both are given, the 0,0 table position is ambiguously both column and row header
                if len(row_headers) == self.data.shape[0]:
                    row_headers = [''] + list(row_headers)

        # from IPython import embed
        # embed()

        if self.has_row_head:
            # first pad whitespace
            # cw0 = max(map(len, map(str, row_headers))) + 1
            # row_headers = [self.col_fmt.format(rh, cw0, self.align) for rh in row_headers]
            # apply props and convert to column vector
            # self.row_headers = self.apply_props(row_headers, row_head_props)
            # FIXME: will apply props just to text and not to whitespace filled column...
            data = np.hstack((np.c_[row_headers], data))

        if self.number_rows:            #FIXME: may cause problems during colourise...
            numbers = np.arange(1, data.shape[0]+1).astype(str)
            if col_headers is not None:
                numbers = ['#'] + list(numbers[:-1])

            data = np.c_[numbers, data]

        # TODO:   implement truncation here
        # TODO: here data should be an array of AnsiStr objects.  To do the truncation, we first need to strip
        # TODO: the control characters, truncate, then re-apply control....
        # TODO: ??? OR is there a better way??

        return as_ansi(data)    #as_ansi necessary because numpy sometimes implicitly converts AnsiStr to str

    #====================================================================================================
    def make_row(self, columns):
        '''apply properties each item in the list of columns create a single string'''
        cb = self.col_borders
        columns = as_ansi(columns)  # convert to ansi array so we can measure component lengths
        col_padwidths = [w + col.ansi_len() if col.has_ansi() else w
                            for col, w in zip(columns, self.col_widths_no_ansi)]
        # format columns (and add rhs border)
        col_fmt = self.col_fmt + cb
        columns = [col_fmt.format(col, cw, self.align)#[:self.max_column_width]
                        for col, cw in zip(columns, col_padwidths)]
        # this is needed because the alignment formatting gets screwed up by the ANSI characters that
        # have length, but are not displayed

        # Apply header properties to whitespace filled row headers (including column borders)
        if self.has_row_head:
            columns[0] = self.apply_props(cb + columns[0], self.row_head_props)
        else:
            columns[0] = cb + columns[0]

        # stick columns together
        row = ''.join(columns)
        self.rows.append(row)

        return row

    #====================================================================================================
    def make_table(self, truncate=False):
        #Express data table as AnsiStr
        # from copy import copy

        lcb = len(self.col_borders)
        tcw = self.col_widths_no_ansi + lcb     # total column width
        # ctcw = np.cumsum(tcw)                   # cumulative total column width
        table_width = sum(tcw) + lcb

        # print('MX', table_width, self.max_table_width)

        if table_width > self.max_table_width:     # if self.truncation == 'split':
            split_tables = self.split()
            if self.show_colourbar:
                split_tables[-1] = self.add_colourbar(split_tables[-1])
            table = '\n\n'.join(split_tables)
            return table
        # else:
        #     raise NotImplementedError
        else:
            table = self._build_partial(0, None)
            return '\n'.join(table)

    #====================================================================================================
    def split(self, max_width=None):
        max_width = max_width or self.max_table_width
        split_tables = []

        no_rh = self.pre_table[:, int(self.has_row_head):]          # excude row headers
        tcw = self.get_column_widths(no_rh, as_displayed=True) + 1  # total column width #NOTE: add 1 to compensate whitespace
        rhw = tcw[0] if self.has_row_head else 0
        splix = 0
        while True:
            if splix == no_rh.shape[1]:
                break
            ctcw = np.cumsum(tcw[splix:])    # cumulative total column width
            w = np.where(ctcw + rhw > max_width)[0]

            if len(w):
                endix = splix + max(w[0], 1)
                if w[0] == 0: #first column +row headers too wide to display
                    'TODO: truncation_policy'
            else:
                endix = None

            last = endix is None
            tbl = self._build_partial(splix, endix, bool(splix))      # make a table using selection of columns
            tblstr = '\n'.join(tbl)
            split_tables.append(tblstr)

            if last:
                break
            splix = endix
        return split_tables

    #====================================================================================================
    def _build_partial(self, c0, c1, continued=False):

        table = []
        slice_ = slice(c0, c1)
        lcb = len(self.col_borders)

        #add headers
        col_headers = self.col_headers[slice_] if self.has_col_head else None
        #FIXME: use pre_table?
        part_table = self.add_headers(self.data[:, slice_], self.row_headers, col_headers)

        #NOTE: add 1 below to compensate whitespace
        table_width = sum(self.get_column_widths(part_table, as_displayed=True) + 1)

        # FIXME: problems with too-wide columns

        # top line
        # FIXME: topline too short with tables with title
        top_line = self.col_fmt.format('', table_width + lcb, '^')
        top_line = as_ansi(top_line, 'underline')
        table.append(top_line)

        if not self.title is None:
            title = self.make_title(table_width + lcb, continued)
            table.append(title)

        # FIXME; case if title wider than table!

        # make rows
        for i, col_items in enumerate(part_table):
            row = self.make_row(col_items)
            if i == 0 and self.has_col_head:
                row = as_ansi(row, self.col_head_props)  # HACK

            if i in self.where_row_borders:
                row = as_ansi(row, 'underline')

            # row = trunc(row)
            table.append(row)
        return table

    #====================================================================================================
    def make_title(self, width, continued=False):
        '''make title line'''
        self.title_fmt = self.col_borders + self.col_fmt + self.col_borders
        title_lines = []
        title = self.title + (' (continued)' if continued else '')
        for title_line in title.splitlines():
            title_line = self.title_fmt.format(title_line, width, self.title_alignment)
            title_line = self.apply_props(title_line, self.title_props)
            title_lines.append(title_line)

        title_lines[-1] = title_lines[-1].set_property('underline')

        return '\n'.join(title_lines)

    # ====================================================================================================
    def colourise(self, states, *colours, **kws):
        # if less colours than number of states are specified
        states = states.astype(int)
        if len(colours) < states.max() + 1:
            colours = ('default',) + colours  # i.e. index zero corresponds to default colour

        while len(colours) < states.max() + 1:
            colours += colours[-1:]  # all remaining higher states will be assigned the same colour

        for i, c in enumerate(colours):
            where = (states == i)
            if np.any(where):
                cdata = as_ansi(self.data[where], c)
                self.data[where] = cdata

        # row_headers = self.row_headers
        # col_headers = self.col_headers

        if kws.get('flag_headers', False):
            #apply colours implied by states sequentially to headers
            if self.has_row_head:
                self.row_headers = [AnsiStr(rh).set_property(c)
                    for rh, c in zip(self.row_headers, np.take(colours, states.max(0)))]
            if self.has_col_head:
                self.col_headers = [AnsiStr(ch).set_property(c)
                     for ch, c in zip(self.col_headers, np.take(colours, states.max(1)))]

        #FIXME: OR JUST PLONK data into pre_table instead of re-adding headers??
        #self.pre_table = self.add_headers(self.data, row_headers, col_headers)
        self.pre_table[int(self.has_col_head):, int(self.has_row_head):] = self.data

        self.states = np.unique(states)
        self.colours = colours
        self.show_colourbar = True

        return self.data

    # alias
    colorize = colourise

    # ====================================================================================================
    # def

    # ====================================================================================================
    def add_colourbar(self, table):

        # ignore default state in colourbar
        start = int('default' in self.colours)
        cbar = ''.join(map(as_ansi, self.states[start:], self.colours[start:]))
        return '\n'.join((table, cbar))

    #====================================================================================================
    #def truncate(self, table ):
        #w,h = getTerminalSize()
        #if len(table[0]) > w:   #all rows have equal length... #np.any( np.array(list(map(len, table))) > w ):

    # use_width = copy(table_width)
    # trunc = lambda row : row
    #
    # if truncate:
            #     #FIXME!
            #     termW,termH = getTerminalSize()
            #
            #     if table_width > termW:
            #         use_width = termW
            #
            #         cs = np.cumsum(self.col_widths_no_ansi)
            #         iq = first_true_index( cs > termW - self.col_widths[-1] )
            #         lidx = cs[iq-1] + termW - cs[iq] - 5
            #         uidx = table_width - self.col_widths[-1]
            #         trunc = lambda row : row[:lidx] + '<...>' + row[uidx:]
            #     #FIXME!


            # return table



if __name__ == '__main__':
    #do Tests
    from collections import OrderedDict
    Ncpus = 8
    default_nproc = OrderedDict(('find'   , Ncpus),
                                ('fit'    , 2*Ncpus),
                                ('phot'   , 2*Ncpus),
                                ('bg'     , 2*Ncpus),
                                ('defer'  , 2))
    table = Table(title='Load balance', data=Nproc, order='r')
    print(table)
    table = Table(title='Load balance', data=Nproc, order='r')
    print(table)
