from recipes.dict import SmartDict

# https://en.wikipedia.org/wiki/ANSI_escape_code

# Escape sequence
ESC = '\033'            # All sequences start with this character
CSI = ESC + '['         # Control Sequence Initiator
END = CSI + '0m'
# '{}{}m'.format(CSI, cs)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Text effects and colours
textCodes = {

    'bold': 1,
    'dim': 2,               # faint
    'italic': 3,
    'underline': 4,
    'blink': 5,             # blink slow
    #'blink' : 6,           # blink fast
    'invert': 7,
    'hidden': 8,            # conceal
    'strikethrough': 9,
    #------------------
    # 10	Primary(default) font
    # 11–19	{\displaystyle n} n-th alternate font	Select the {\displaystyle n} n-th alternate font (14 being the fourth alternate font, up to 19 being the 9th alternate font).
    # 20	Fraktur	hardly ever supported
    # 21	Bold: off or Underline: Double	Bold off not widely supported; double underline hardly ever supported.
    # 22	Normal color or intensity	Neither bold nor faint
    # 23	Not italic, not Fraktur
    # 24	Underline: None	Not singly or doubly underlined
    # 25	Blink: off
    # 26	Reserved
    # 27	Image: Positive
    # 28	Reveal  conceal off
    # 29	Not crossed out
    #------------------
    'black': 30,
    'red': 31,
    'green': 32,
    'yellow': 33,
    'blue': 34,
    'magenta': 35,
    'cyan': 36,
    'light gray': 37,
    # 38	Reserved for extended set foreground color	typical supported next arguments are 5;n where {\displaystyle n}￼ is color index (0..255) or 2;r;g;b where {\displaystyle r,g,b}￼ are red, green and blue color channels (out of 255)
    'default': 39,          # Default text color (foreground)
    # ------------------
    'frame': 51,
    'circle': 52,
    'overline': 53,                     # does not seem to work - TODO: maybe possible with unicode: https://en.wikipedia.org/wiki/Overline#Unicode
    # 54	Not framed or encircled
    # 55	Not overlined
    # ------------------
    'dark gray': 90,
    'light red': 91,
    'light green': 92,
    'light yellow': 93,
    'light blue': 94,
    'light magenta': 95,
    'light cyan': 96,
    'white': 97,
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Background Colours
backgroundCodes = {
    'default': 49,
    'black': 40,
    'red': 41,
    'green': 42,
    'yellow': 43,
    'blue': 44,
    'magenta': 45,
    'cyan': 46,
    'light gray': 47,
    #------------------
    # 48	Reserved for extended set background color	typical supported next arguments are 5;n where {\displaystyle n}￼ is color index (0..255) or 2;r;g;b where {\displaystyle r,g,b}￼ are red, green and blue color channels (out of 255)
    # 49	Default background color	implementation defined (according to standard)
    # 50	Reserved
    #------------------
    # 56–59	Reserved
    # 60	ideogram underline or right side line	hardly ever supported
    # 61	ideogram double underline or double line on the right side	hardly ever supported
    # 62	ideogram overline or left side line	hardly ever supported
    # 63	ideogram double overline or double line on the left side	hardly ever supported
    # 64	ideogram stress marking	hardly ever supported
    # 65	ideogram attributes off	hardly ever supported, reset the effects of all of 60–64
    #------------------
    'dark gray': 100,
    'light red': 101,
    'light green': 102,
    'light yellow': 103,
    'light blue': 104,
    'light magenta': 105,
    'light cyan': 106,
    'white': 107,
}


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Convenient short colour descriptions a la matplotlib
mplShorthands = {
    'b': 'blue',
    'g': 'green',
    'r': 'red',
    'c': 'cyan',
    'm': 'magenta',
    'y': 'yellow',
    'k': 'black',
    'w': 'white',
}


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# alias map for allowed keywords for functions
aliasMap = {
    'text': 'text',
    'txt': 'text',
    'colour': 'text',
    'color': 'text',
    'c': 'text',
    'fg': 'text',
    'foreground': 'text',
    'background': 'background',
    'bg': 'background',
    'bc': 'background',
    'bgc': 'background',
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Movement = {} # TODO


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _aliasFactory(codes, aliases):
    """Create the code translation dict"""
    Codes = SmartDict(codes)
    Codes.add_vocab(aliases)
    Codes.add_map(str.lower)
    return Codes


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class KeyResolver(SmartDict):
    def __init__(self, dic=None, **kwsargs):
        super().__init__(dic, **kwsargs)
        self.add_vocab(aliasMap)                # translation

    def __missing__(self, key):
        try:
            return super().__missing__(key)
        except KeyError as err:
            pass
        raise KeyError('%r is not a valid property description' %key)


class CodeTranslator(SmartDict):
    def __init__(self, dic=None, **kwsargs):
        super().__init__(dic, **kwsargs)
        self.add_vocab(mplShorthands)
        self.add_map(str.lower)

    def __missing__(self, key):
        try:
            return super().__missing__(key)
        except KeyError as err:
            ValueError('Unknown property %r' % key)

            # if str(key).isdigit():
            #     if int(key) <= 256:
            #         return format256[which].format(key)
            #     else:
            #         raise ValueError('Only 256 colours available.')


resolver = KeyResolver(text=CodeTranslator(textCodes),
                       background= CodeTranslator(backgroundCodes))
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# 256 Colours
format256 = KeyResolver(text='38;5;{}',
                        background='48;5;{}')

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# 24bit (3-byte) true color support
# TODO
# NOTE:  Gnome Terminal 24bit support is enabled by default but gnome-terminal
#       has to be in version linked against libvte >= 0.36
#       see: http://askubuntu.com/questions/512525/how-to-enable-24bit-true-color-support-in-gnome-terminal
# TODO


def get_prop_code(prop, which='text'):
    """Retrieve the ansi number"""
    cdict = resolver[which]  # .get(prop)
    if prop in cdict:
        return cdict[prop]

    elif str(prop).isdigit():
        if int(prop) <= 256:
            return format256[which].format(prop)
        else:
            raise ValueError('Only 256 colours available.')
    else:
        raise ValueError('Unknown property %r' %prop)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def _gen_codes(*properties, **kws):
    """
    Get ANSI code given the properties and kws descriptors.
    properties      - text colour or effects
    kws              - 'text_colour', 'text_effect', 'background_colour'
    """
    properties = tuple(filter(None, properties))
    noprops = (len(properties) == 0)
    if noprops and not kws:
        return

    yield from map(get_prop_code, properties)

    for desc, properties in kws.items():
        if properties is None:
            continue

        if isinstance(properties, str):
            if len(properties.strip()) == 0:
                continue
            properties = properties,

        if isinstance(properties, int):
            properties = properties,

        for prop in filter(None, properties):
            yield get_prop_code(prop, desc)


# def _get_codes_tuple(*properties, **kws):
#     return tuple(_gen_codes(*properties, **kws))


def get_code_str(*properties, **kws):
    codes = _gen_codes(*properties, **kws)
    cs = ';'.join(map(str, codes))
    return '{}{}m'.format(CSI, cs)


def apply(s, *properties, **kws):
    """set the ANSI codes for a string given the properties and kws descriptors"""
    # s = str(s) #TODO: warn if converting?
    properties = tuple(filter(None, properties))
    noprops = (len(properties) == 0) #(None in properties) or (
    if noprops and not kws:
        return s

    if len(properties) == 1:
        if isinstance(properties[0], dict):
            kws.update(properties[0])
            properties = ()

    code = get_code_str(*properties, **kws)      #NOTE: still missisg END at this point

    # eliminate unnecessary END codes. (self may already have previous END code)
    string = s.replace(END, END + code, s.count(END))

    # TODO: if whitespace and fg code will give blank uncoloured str.  convert to bg code?
    return code + string + END


if __name__ == '__main__':
    for i in range(256):
        print(
            apply(' ' * 16, i)
        )

        # TODO: print pretty things:
        # http://misc.flogisoft.com/bash/tip_colors_and_formatting
        # http://askubuntu.com/questions/512525/how-to-enable-24bit-true-color-support-in-gnome-terminal
        # https://github.com/robertknight/konsole/blob/master/tests/color-spaces.pl
