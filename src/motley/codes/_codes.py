"""
Map names to numerical ANSI codes.

see:  https://en.wikipedia.org/wiki/ANSI_escape_code
      http://ascii-table.com/ansi-escape-sequences.php
"""


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ANSI Codes for Text effects and colours  FG_CODES BG_CODE
#
FG_CODES = {
    'bold':             1,
    'dim':              2,                   # faint
    'italic':           3,
    'underline':        4,
    'blink':            5,                 # blink slow
    # 'blink' :         6,              # blink fast
    'invert':           7,
    'hidden':           8,                # conceal
    'strike':           9,
    # ------------------
    # 10	Primary(default) font
    # 11–19	{\displaystyle n} n-th alternate font	Select the {\displaystyle n}
    # n-th alternate font (14 being the fourth alternate font, up to 19 being
    # the 9th alternate font).
    # 20	Fraktur	hardly ever supported
    # 21	Bold: off or Underline: Double	Bold off not widely supported;
    # double underline hardly ever supported.
    # 22	Normal color or intensity	Neither bold nor faint
    # 23	Not italic, not Fraktur
    # 24	Underline: None	Not singly or doubly underlined
    # 25	Blink: off
    # 26	Reserved
    # 27	Image: Positive
    # 28	Reveal  conceal off
    # 29	Not crossed out
    # ------------------
    'black':            30,
    'red':              31,
    'green':            32,
    'yellow':           33,
    'blue':             34,
    'magenta':          35,
    'cyan':             36,
    'bright gray':      37,
    # 38	Reserved for extended set foreground color typical supported next
    # arguments are 5;n where {\displaystyle n}￼ is color index (0..255) or
    # 2;r;g;b where {\displaystyle r,g,b}￼ are red, green and blue color
    # channels (out of 255)
    'default':          39,                  # Default text color (foreground)
    # ------------------
    'frame':            51,
    'circle':           52,
    'overline':         53,
    # 54	Not framed or encircled
    # 55	Not overlined
    # ------------------
    # 'dark gray':    90,
    'gray':             90,
    'bright red':       91,
    'bright green':     92,
    'bright yellow':    93,
    'bright blue':      94,
    'bright magenta':   95,
    'bright cyan':      96,
    'white':            97,
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Background Colours
BG_CODES = {
    'black':            40,
    'red':              41,
    'green':            42,
    'yellow':           43,
    'blue':             44,
    'magenta':          45,
    'cyan':             46,
    'bright gray':      47,
    # ------------------
    # 48	Reserved for extended set background color	typical supported next
    # arguments are 5;n where {\displaystyle n}￼ is color index (0..255) or
    # 2;r;g;b where {\displaystyle r,g,b}￼ are red, green and blue color
    # channels (out of 255)
    'default':          49,
    # 49	Default background color	implementation defined (according to
    # standard)
    # 50	Reserved
    # ------------------
    # 56–59	Reserved
    # 60	ideogram underline or right side line	hardly ever supported
    # 61	ideogram double underline or double line on the right side	hardly
    # ever supported
    # 62	ideogram overline or left side line	hardly ever supported
    # 63	ideogram double overline or double line on the left side
    # hardly ever supported
    # 64	ideogram stress marking	hardly ever supported
    # 65	ideogram attributes off	hardly ever supported, reset the effects of
    # all of 60–64
    # ------------------
    'dark gray':        100,
    'bright red':       101,
    'bright green':     102,
    'bright yellow':    103,
    'bright blue':      104,
    'bright magenta':   105,
    'bright cyan':      106,
    'white':            107,
}


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

effectAliasMap = {
    'B':                'bold',
    'I':                'italic',
    'i':                'italic',
    'U':                'underline',
    'u':                'underline',
    '_':                'underline',
    'ul':               'underline',
    'S':                'strike',
    's':                'strike',
    '-':                'strike',
    'strikethrough':    'strike',
    'unbold':           'dim',
    'blink':            'blink_slow',
    'hide':             'hidden',
    'faint':            'dim'
}
# volcab is translated before keyword mappings in Many2One, so the uppercase
# here works

# Short colour descriptions
colorAliasMap = {
    'r':                'red',
    'b':                'blue',
    'g':                'green',
    'c':                'cyan',
    'm':                'magenta',
    'y':                'yellow',
    'k':                'black',
    'w':                'white',
}
