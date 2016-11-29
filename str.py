import re
#import functools as ft
#from pprint import pformat

import numpy as np

from recipes.misc import getTerminalSize
from recipes.iter import as_sequence
from recipes.dict import SmartDict
from recipes.string import rformat as as_str

# from decor import expose
#from IPython import embed

#*******************************************************************************
class ANSICodes(object):
    #
    DESCRIPTORS = ['text', 'background']
    #TODO:  TransDict
    descriptorTranslationMap = {
        'text'          :       'text',
        'txt'           :       'text',
        'colour'        :       'text',
        'color'         :       'text',
        'c'             :       'text',
        'background'    :       'background',
        'bg'            :       'background',
        'bc'            :       'background',
        'bgc'           :       'background',
    }

    #Escape sequence
    ESC = '\033'
    CSI = ESC + '['

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #Text effects and colours
    TextCodes = {
        'bold'              :       1,
        'dim'               :       2,
        'italic'            :       3,
        'underline'         :       4,
        'blink'             :       5,
        'invert'            :       7,
        'hidden'            :       8,
        'strikethrough'     :       9,
        'default'           :       39,
        'black'             :       30,
        'red'               :       31,
        'green'             :       32,
        'yellow'            :       33,
        'blue'              :       34,
        'magenta'           :       35,
        'cyan'              :       36,
        'light gray'        :       37,
        'dark gray'         :       90,
        'light red'         :       91,
        'light green'       :       92,
        'light yellow'      :       93,
        'light blue'        :       94,
        'light magenta'     :       95,
        'light cyan'        :       96,
        'white'             :       97,
    }

    MplShortHands = {
        'b': 'blue',
        'g': 'green',
        'r': 'red',
        'c': 'cyan',
        'm': 'magenta',
        'y': 'yellow',
        'k': 'black',
        'w': 'white',
    }

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #Background Colours
    BackgroundCodes = {
        'default'           :       49,
        'black'             :       40,
        'red'               :       41,
        'green'             :       42,
        'yellow'            :       43,
        'blue'              :       44,
        'magenta'           :       45,
        'cyan'              :       46,
        'light gray'        :       47,
        'dark gray'         :       100,
        'light red'         :       101,
        'light green'       :       102,
        'light yellow'      :       103,
        'light blue'        :       104,
        'light magenta'     :       105,
        'light cyan'        :       106,
        'white'             :       107,
    }

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Movement = {}

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def factory(cD, shorthands):
        '''Create the code translation dict'''
        Codes = SmartDict(cD)
        Codes.add_vocab(shorthands)
        Codes.add_map(str.lower)
        return Codes

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    CodeDicts = {'text'         : factory(TextCodes, MplShortHands),
                 'background'   : factory(BackgroundCodes, MplShortHands), }

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #256 Colours
    Format256 = {'text'         : '38;5;{}',         #TextCodes256
                 'background'   : '48;5;{}' }        #BackgroundCodes256
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #24bit (3-byte) true color support
    #NOTE: Gnome Terminal 24bit support is enabled by default but gnome-terminal
    #has to be in version linked against libvte >= 0.36
    #see: http://askubuntu.com/questions/512525/how-to-enable-24bit-true-color-support-in-gnome-terminal
    #TODO

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #End
    END = CSI + '0m'

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @classmethod
    def get_prop_code(cls, prop, which='text' ):

        cdict = cls.CodeDicts[which]#.get(prop)
        if prop in cdict:
            return cdict[prop]

        elif str(prop).isdigit():
            if int(prop)<=256:
                return cls.Format256[which].format(prop)
            else:
                raise ValueError( 'Only 256 colours available.' )
        else:
            raise ValueError( 'Unknown property {}'.format(prop) )

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @classmethod
    def get_code(cls, *properties, **kw):
        '''Get ANSI code given the properties and kw descriptors.
        properties      - text colour or effects
        kw              - 'text_colour', 'text_effect', 'background_colour'
        '''
        noprops = properties in [(), None] or None in properties
        if noprops and not kw:
            return ''

        codes = []
        if properties:
            for prop in properties:
                codes.append(cls.get_prop_code(prop))

        if kw:
            for desc, properties in kw.items():
                if not desc in cls.descriptorTranslationMap:
                    raise KeyError("'{}' is not a valid property descriptor".format(desc))
                else:
                    desc = cls.descriptorTranslationMap[desc]       #translation
                    if isinstance(properties, (str,int)):
                        properties = properties,
                    for prop in properties:
                        codes.append(cls.get_prop_code(prop, desc))

        codes = ';'.join(map(str, codes))
        #format as ANSI escape sequence. NOTE: still missisg END at this point
        return '{}{}m'.format(cls.CSI, codes)


#*******************************************************************************
class AnsiStr(str):
    ansi_pattern = '\033\[[\d;]*[a-zA-Z]'
    ansi_matcher = re.compile(ansi_pattern)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __getitem__(self, key):
        return AnsiStr(str.__getitem__(self, key))

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #def __len__(self):
        #return len( self.ansi_strip() )

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __add__(self, other):
        return AnsiStr(str(self) + other)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __radd__(self, other):
        return AnsiStr(other + str(self))

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def join(self, iterable):
        return AnsiStr(super().join(iterable))

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def ansi_strip(self):
        return AnsiStr.ansi_matcher.sub('', self)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def ansi_pull(self):
        return AnsiStr.ansi_matcher.findall(self)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def ansi_split(self):
        parsed = []
        idxs = []
        for match in AnsiStr.ansi_matcher.finditer(self):
            idxs += [match.start(), match.end()]
        if not len(idxs):
            return [self]
        for i in range(len(idxs)):
            try:
                parsed.append( self[ idxs[i]:idxs[i+1] ] )
            except IndexError:
                pass
        return parsed

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def ansi_len(self):
        if self.has_ansi():
            return sum(map(len, self.ansi_pull()))
        else:
            return 0

    def len_ansi(self):
        return self.ansi_len()

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def len_no_ansi(self):
        return len( self.ansi_strip() )

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def has_ansi(self):
        return not AnsiStr.ansi_matcher.search(self) is None

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def set_property(self, *properties, **kw):
        '''set the ANSI codes for a string given the properties and kw descriptors'''
        noprops = properties in [(), None] or None in properties
        if noprops and not kw:
            return self

        code = ANSICodes.get_code( *properties, **kw )

        #elliminate unnecesary END codes. (self may already have previous END code)
        end = ANSICodes.END
        if end in self:         #FIXME: unnecessary if??
            endcount = self.count(end)
            string = self.replace(end, end+code, endcount)
        else:
            string = self

        return AnsiStr('{}{}{}'.format(code, string, end))

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def stripNonAscii(s):
        return ''.join([x for x in s if ord(x)<128])

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #def center(self, width, fill=' ' ):

        #div, mod = divmod( len(self), 2 )
        #if mod: #i.e. odd window length
            #pl, ph = div, div+1
        #else:  #even window len
            #pl = ph = div

        #idx = width//2-pl, width//2+ph                    #start and end indeces of the text in the center of the progress indicator
        #s = fill*width
        #return s[:idx[0]] + self + s[idx[1]:]                #center text

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def rreplace(self, subs, repl):
        return rreplace( str(self), subs, repl )

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def wrap(self, wrappers):
        if isinstance(wrappers, str):
            return wrappers + self + wrappers
        elif np.iterable(wrappers):
            return self.join( wrappers )

SuperString = AnsiStr

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#from decor import expose
# @expose.args()
def as_ansi(obj, props=(), **propkw):   #as_ansi_array???
    '''
    Convert the obj to an array of AnsiStr objects, applying the properties.
    Parameters
    ----------
    obj         :       If input is unsized - return its AnsiStr representation
                        If input is 0 size - return empty AnsiStr object
                        Else return array of AnsiStr objects
    '''
    precision   = propkw.pop('precision', 2)
    ndmin       = propkw.pop('ndmin', 0)
    pretty      = propkw.pop('pretty', True)

    obja = np.array(as_sequence(obj), dtype=object)
    #try:
        #obja = np.atleast_1d(obj)
    #except Exception as err:
        #print(err)
        #from IPython import embed
        #embed()

    #print()

    #reshape complex dtype arrays to object arrays
    if obja.dtype.kind == 'V':  #complex dtype as in record array
        #check if all the dtypes are the same.  If so we can change view
        dtypes = next(zip(*obja.dtype.fields.values()))
        dtype0 = dtypes[0]
        if np.equal(dtypes, dtype0).all():
            obja = obja.view(dtype0).reshape(len(obja), -1)
    #else:

    #view as object array
    #obja = obja.astype(object)

    if isinstance(props, dict):
        propkw.update(props)
        props = ()
    else:
        props = np.atleast_1d(props)    #as_sequence( props, return_as=tuple)

    #deal with empty arrays     #???????
    if not len(obja): #???????
        return AnsiStr(str(obj))

    fun = lambda s: AnsiStr(as_str(s, precision, pretty)).set_property(*props, **propkw)
    out = np.vectorize(fun, (AnsiStr,))(obja)

    if len(out)==1 and out.ndim==1 and ndmin==0:
        out = out[0] #collapse arrays of shape (1,) to item itself if ndmin=0 asked for

    return out

as_superstrings = as_ansi

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def banner(*args, **props):
    '''print pretty banner'''
    swoosh      = props.pop('swoosh', '=',)
    width       = props.pop('width', getTerminalSize()[0])
    pretty      = props.pop('pretty', True)
    _print      = props.pop('_print', True)

    swoosh = swoosh * width
    #TODO: fill whitespace to width?
    #try:
    msg = '\n'.join(as_ansi(args, ndmin=1, pretty=pretty))
    #except:
        #embed()

    #.center( width )
    info = '\n'.join( [swoosh, msg, swoosh] )

    info = as_ansi(info).set_property(**props)

    if _print:
        print(info)

    return info



if __name__ == '__main__':
    #FIXME:  this breaks the numpy import!! ---> rename this script to fix the issue
    for i in range(256):
        print(AnsiStr(' '*16).set_property(i))

        #TODO: print stuff like this:
        #http://askubuntu.com/questions/512525/how-to-enable-24bit-true-color-support-in-gnome-terminal
        #https://github.com/robertknight/konsole/blob/master/tests/color-spaces.pl


