import numpy as np

from myio import warn

from recipes.misc import getTerminalSize
from recipes.iter import as_sequence, first_true_index

from .str import SuperString, as_superstrings

#from IPython import embed

#TODO: unit tests!!!!!!!!

##########################################################################################################################################   
#from PyQt4.QtCore import pyqtRemoveInputHook, pyqtRestoreInputHook
#TODO:  Check out astropy.table ...........................
#TODO: HIGHLIGHT ROWS / COLUMNS
#TODO: OPTION for plain text row borders
class Table( object ):          #TODO: remane as ansi table??
    ALIGNMENT_MAP = { 'r' : '>', 'l' : '<', 'c' : '^' }     #map to alignment format characters
    ALLOWED_KWARGS = [] #TODO
    #====================================================================================================
    def __init__(self, data, 
                 title=None, title_props=(), title_alignment='center',
                 col_headers=None, col_head_props='bold', col_widths=None, 
                 col_borders='|', col_sort=None,
                 #TODO: where_col_borders
                 row_headers=None, row_head_props='bold', where_row_borders=None, 
                 row_sort=None,
                 align='left', num_prec=2, number_rows=False,
                 ignore_keys=None, order ='c'
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
        num_prec        :       integer precision to use for number representation FIXME!!!!!!!!!!!!!
        number_rows     :       bool
            Will number the rows if True
        
        ignore_keys     :       if dictionary is passed as data, optionally specify the keys that will not be printed in table 
        
        order           :       str - {'row', 'col'}
            whether to interpret data as row ordered or column ordered
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
        
        #convert to array of SuperStrings
        self.data = as_superstrings(data)
        
        #check data shape
        dim = np.ndim(self.data)
        if dim == 1:
            if order.startswith('c'):
                self.data = self.data[None].T               #default for 1D data is to display in a column with row_headers
        if dim > 2:
            raise ValueError( 'Only 2D data can be tabelised!  Data is {}D'.format(dim) )
        
        #title
        self.title = title
        self.title_props =  title_props
        self.title_alignment = self.get_alignment(title_alignment)
        
        self.number_rows = number_rows
        
        #row and column headers
        self.has_row_head = row_headers is not None
        self.has_col_head = col_headers is not None
        
        if self.has_col_head:
            self.col_head_props = col_head_props
            self.col_headers = self.apply_props(col_headers, 'bold')    #HACK: see 
        if self.has_col_head and self.has_row_head:
            #TODO:  when both are given, the 0,0 table position is ambiguously both column and row header
            #TODO:  allow user to specify either
            if len(row_headers) == self.data.shape[0]:
                row_headers = [''] + list(row_headers)
        if self.has_row_head:
            Nrows = len(row_headers)
            self.row_headers = self.apply_props(row_headers, 
                                                row_head_props).reshape(Nrows,1)
            #FIXME: will apply props just to text and not to whitespace filled column...
            
        self.pre_table = self.add_headers()
        Nrows, Ncols = self.pre_table.shape
        
        #Column specs
        if col_widths is None:
            self.col_widths = np.vectorize(len)(self.pre_table).max(axis=0) + 1
            pure_len = np.vectorize(SuperString.len_no_ansi)
            self.col_widths_no_ansi = pure_len(self.pre_table).max(axis=0) + 1
        else:
            self.col_widths = col_widths
        
        self.col_borders = col_borders
        
        #column alignment
        self.align = self.get_alignment(align)
        
        #The column format specification. 0 - item; 1 - fill; 2 - alignment character
        self.col_fmt = '{0:{2}{1}}'
        self.num_prec = num_prec
        
        #Row specs
        self.rows = []
        self.row_fmt = ('{}'+self.col_borders) * Ncols
        
        if not where_row_borders is None:
            self.where_row_borders = where_row_borders
        else:
            if self.has_col_head:
                self.where_row_borders = [0, Nrows-1]
            else:
                self.where_row_borders = [Nrows-1]
    
    #====================================================================================================
    def __repr__( self ):
        if len(self.original_data):
            self.make_table( )  
            return '\n'.join( self.table )
        else:
            return '|Empty Table|'
        
    #====================================================================================================    
    def __str__( self ):
        return repr(self)
    
    #====================================================================================================    
    def get_alignment(self, char):
        if char.lower()[0] in self.ALIGNMENT_MAP:
            return self.ALIGNMENT_MAP[char.lower()[0]]
        else:
            raise ValueError('Unrecognised alignment {!r}'.format(align))
    
    #====================================================================================================    
    @staticmethod
    def apply_props(obj, props=()):
        if isinstance(props, dict):
            return as_superstrings(obj, **props)
        else:
            props = as_sequence(props, return_as=tuple)
            return as_superstrings(obj, props)
    
    #====================================================================================================    
    @staticmethod
    def convert_dict(dic, ignore_keys):
        _dic = dic.copy()
        if not ignore_keys is None:
            ignore = [_dic.pop(key) for key in ignore_keys if key in _dic]
        
        keys = list(_dic.keys())
        vals = list(_dic.values())
        return keys, vals
    
    #====================================================================================================    
    def add_headers(self):
        
        data = self.data[...]

        if self.has_col_head:
            data = np.vstack((self.col_headers, data))

        if self.has_row_head:
            data = np.hstack((self.row_headers, data))
            
        if self.number_rows:
            numbers = np.arange(1, data.shape[0]+1).astype(str)
            if self.has_col_head:
                numbers = ['#'] + list(numbers[:-1])
            
            data = np.c_[numbers, data]
        
        return as_superstrings(data)    #as_superstrings necessary because numpy sometimes implicitly converts SuperStrings to str
    
    #====================================================================================================
    def create_row(self, columns):
        '''apply properties each item in the list of columns create a single string'''
        al = self.align
        columns = as_superstrings( columns )
        col_padwidths =  [w+col.ansi_len() if col.has_ansi() else w 
                            for col,w in zip(columns, self.col_widths_no_ansi)]
        columns = [self.col_fmt.format(col, cw, al) for col,cw in zip(columns, col_padwidths)]     #this is needed because the alignment formatting gets screwed up by the ANSI characters that have length, but are not displayed
        row = self.col_borders + self.row_fmt.format(*columns)
        row = SuperString(row)
        self.rows.append( row )
        
        return row
    
    #====================================================================================================
    def colourise(self, states, *colours):
        
        #if less colours than number of states are specified
        if len(colours) < states.max()+1:
            colours = ('default',) + colours            #i.e. index zero corresponds to default colour
        
        while len(colours) < states.max()+1:
            colours += colours[-1:]                     #all remaining higher states will be assigned the same colour
        
        #embed()
        for i,c in enumerate(colours):
            where = states==i
            if np.any(where):
                cdata = as_superstrings( self.data[where], c )
                self.data[where] = cdata
        
        self.pre_table = self.add_headers()
        return self.data
    
    #alias
    colorize = colourise
    
    #====================================================================================================
    def make_table(self, truncate=False):
        #Express data table as SuperString
        from copy import copy
        table = []
        lcb = len(self.col_borders)
        table_width = sum(self.col_widths_no_ansi+lcb) + lcb
        use_width = copy(table_width)
        trunc = lambda row : row
        
        if truncate:
            #FIXME!
            termW,termH = getTerminalSize()
        
            if table_width > termW:
                use_width = termW
            
                cs = np.cumsum(self.col_widths_no_ansi)
                iq = first_true_index( cs > termW - self.col_widths[-1] )
                lidx = cs[iq-1] + termW - cs[iq] - 5
                uidx = table_width - self.col_widths[-1]
                trunc = lambda row : row[:lidx] + '<...>' + row[uidx:]
            #FIXME!

        #top line
        top_line = self.col_fmt.format( '', use_width, '^' )
        top_line = as_superstrings(top_line, 'underline')
        table.append(top_line)
        
        if not self.title is None:
            title = self.make_title(use_width - lcb)
            table.append(title)
        
        #make rows
        for i, col_items in enumerate( self.pre_table ):
            row = self.create_row( col_items )
            if i==0 and self.has_col_head:
                row = as_superstrings(row, self.col_head_props)         #HACK
                
            if i in self.where_row_borders:
                row = as_superstrings(row, 'underline', 
                                      precision=self.num_prec )         #FIXME!!!!!!!!!!!!!
            

            row = trunc(row)
            table.append( row )
            
        self.table = table
        
        return table
    
    #====================================================================================================
    def make_title(self, width):
        '''make title line'''
        self.title_fmt = self.col_fmt + self.col_borders
        title_lines = []
        for title_line in self.title.splitlines():
            title_line = self.title_fmt.format(title_line, 
                                                width, 
                                                self.title_alignment)
            title_line = self.apply_props(title_line, self.title_props) 
            title_lines.append(title_line)
        
        title_lines[-1] = title_lines[-1].set_property('underline')
        
        return '\n'.join(title_lines)
    
    #====================================================================================================
    #def truncate(self, table ):
        #w,h = getTerminalSize()
        #if len(table[0]) > w:   #all rows have equal length... #np.any( np.array(list(map(len, table))) > w ):



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
    