
# std
import warnings
import unicodedata
from collections.abc import Collection

# third-party
import more_itertools as mit
from .codes import utils as ansi

# local
from recipes import api
from recipes.functionals import echo0
from recipes.dicts import AttrReadItem
from recipes.oo import iter_subclasses
from recipes.utils import duplicate_if_scalar
from recipes.string import backspaced, justify

# relative
from . import apply, format, underline
from .utils import get_width, resolve_width


# TODO
# class Paragraph(str):
# def  get_width, justify, frame etc


# '⎿'

# see: https://en.wikipedia.org/wiki/Box-drawing_character
# '─'	U+2500	BOX DRAWINGS LIGHT HORIZONTAL
# '━'	U+2501	BOX DRAWINGS HEAVY HORIZONTAL
# '│'	U+2502	BOX DRAWINGS LIGHT VERTICAL
# '┃'	U+2503	BOX DRAWINGS HEAVY VERTICAL
# '╌'	U+254C	BOX DRAWINGS LIGHT DOUBLE DASH HORIZONTAL
# '╍'	U+254D	BOX DRAWINGS HEAVY DOUBLE DASH HORIZONTAL
# '╎'	U+254E	BOX DRAWINGS LIGHT DOUBLE DASH VERTICAL
# '╏'	U+254F	BOX DRAWINGS HEAVY DOUBLE DASH VERTICAL
# '┄'	U+2504	BOX DRAWINGS LIGHT TRIPLE DASH HORIZONTAL
# '┅'	U+2505	BOX DRAWINGS HEAVY TRIPLE DASH HORIZONTAL
# '┆'	U+2506	BOX DRAWINGS LIGHT TRIPLE DASH VERTICAL
# '┇'	U+2507	BOX DRAWINGS HEAVY TRIPLE DASH VERTICAL
# '┈'	U+2508	BOX DRAWINGS LIGHT QUADRUPLE DASH HORIZONTAL
# '┉'	U+2509	BOX DRAWINGS HEAVY QUADRUPLE DASH HORIZONTAL
# '┊'	U+250A	BOX DRAWINGS LIGHT QUADRUPLE DASH VERTICAL
# '┋'	U+250B	BOX DRAWINGS HEAVY QUADRUPLE DASH VERTICAL
# '╵'   U+2575  BOX DRAWINGS LIGHT UP
# '╷'   U+2577  BOX DRAWINGS LIGHT DOWN
# '┌'	U+250C	BOX DRAWINGS LIGHT DOWN AND RIGHT
# '┍'	U+250D	BOX DRAWINGS DOWN LIGHT AND RIGHT HEAVY
# '┎'	U+250E	BOX DRAWINGS DOWN HEAVY AND RIGHT LIGHT
# '┏'	U+250F	BOX DRAWINGS HEAVY DOWN AND RIGHT
# '┐'	U+2510	BOX DRAWINGS LIGHT DOWN AND LEFT
# '┑'	U+2511	BOX DRAWINGS DOWN LIGHT AND LEFT HEAVY
# '┒'	U+2512	BOX DRAWINGS DOWN HEAVY AND LEFT LIGHT
# '┓'	U+2513	BOX DRAWINGS HEAVY DOWN AND LEFT
# '└'	U+2514	BOX DRAWINGS LIGHT UP AND RIGHT
# '┕'	U+2515	BOX DRAWINGS UP LIGHT AND RIGHT HEAVY
# '┖'	U+2516	BOX DRAWINGS UP HEAVY AND RIGHT LIGHT
# '┗'	U+2517	BOX DRAWINGS HEAVY UP AND RIGHT
# '┘'	U+2518	BOX DRAWINGS LIGHT UP AND LEFT
# '┙'	U+2519	BOX DRAWINGS UP LIGHT AND LEFT HEAVY
# '┚'	U+251A	BOX DRAWINGS UP HEAVY AND LEFT LIGHT
# '┛'	U+251B	BOX DRAWINGS HEAVY UP AND LEFT
# '├'	U+251C	BOX DRAWINGS LIGHT VERTICAL AND RIGHT
# '┝'	U+251D	BOX DRAWINGS VERTICAL LIGHT AND RIGHT HEAVY
# '┞'	U+251E	BOX DRAWINGS UP HEAVY AND RIGHT DOWN LIGHT
# '┟'	U+251F	BOX DRAWINGS DOWN HEAVY AND RIGHT UP LIGHT
# '┠'	U+2520	BOX DRAWINGS VERTICAL HEAVY AND RIGHT LIGHT
# '┡'	U+2521	BOX DRAWINGS DOWN LIGHT AND RIGHT UP HEAVY
# '┢'	U+2522	BOX DRAWINGS UP LIGHT AND RIGHT DOWN HEAVY
# '┣'	U+2523	BOX DRAWINGS HEAVY VERTICAL AND RIGHT
# '┤'	U+2524	BOX DRAWINGS LIGHT VERTICAL AND LEFT
# '┥'	U+2525	BOX DRAWINGS VERTICAL LIGHT AND LEFT HEAVY
# '┦'	U+2526	BOX DRAWINGS UP HEAVY AND LEFT DOWN LIGHT
# '┧'	U+2527	BOX DRAWINGS DOWN HEAVY AND LEFT UP LIGHT
# '┨'	U+2528	BOX DRAWINGS VERTICAL HEAVY AND LEFT LIGHT
# '┩'	U+2529	BOX DRAWINGS DOWN LIGHT AND LEFT UP HEAVY
# '┪'	U+252A	BOX DRAWINGS UP LIGHT AND LEFT DOWN HEAVY
# '┫'	U+252B	BOX DRAWINGS HEAVY VERTICAL AND LEFT
# '┬'	U+252C	BOX DRAWINGS LIGHT DOWN AND HORIZONTAL
# '┭'	U+252D	BOX DRAWINGS LEFT HEAVY AND RIGHT DOWN LIGHT
# '┮'	U+252E	BOX DRAWINGS RIGHT HEAVY AND LEFT DOWN LIGHT
# '┯'	U+252F	BOX DRAWINGS DOWN LIGHT AND HORIZONTAL HEAVY
# '┰'	U+2530	BOX DRAWINGS DOWN HEAVY AND HORIZONTAL LIGHT
# '┱'	U+2531	BOX DRAWINGS RIGHT LIGHT AND LEFT DOWN HEAVY
# '┲'	U+2532	BOX DRAWINGS LEFT LIGHT AND RIGHT DOWN HEAVY
# '┳'	U+2533	BOX DRAWINGS HEAVY DOWN AND HORIZONTAL
# '┴'	U+2534	BOX DRAWINGS LIGHT UP AND HORIZONTAL
# '┵'	U+2535	BOX DRAWINGS LEFT HEAVY AND RIGHT UP LIGHT
# '┶'	U+2536	BOX DRAWINGS RIGHT HEAVY AND LEFT UP LIGHT
# '┷'	U+2537	BOX DRAWINGS UP LIGHT AND HORIZONTAL HEAVY
# '┸'	U+2538	BOX DRAWINGS UP HEAVY AND HORIZONTAL LIGHT
# '┹'	U+2539	BOX DRAWINGS RIGHT LIGHT AND LEFT UP HEAVY
# '┺'	U+253A	BOX DRAWINGS LEFT LIGHT AND RIGHT UP HEAVY
# '┻'	U+253B	BOX DRAWINGS HEAVY UP AND HORIZONTAL
# '┼'	U+253C	BOX DRAWINGS LIGHT VERTICAL AND HORIZONTAL
# '┽'	U+253D	BOX DRAWINGS LEFT HEAVY AND RIGHT VERTICAL LIGHT
# '┾'	U+253E	BOX DRAWINGS RIGHT HEAVY AND LEFT VERTICAL LIGHT
# '┿'	U+253F	BOX DRAWINGS VERTICAL LIGHT AND HORIZONTAL HEAVY
# '╀'	U+2540	BOX DRAWINGS UP HEAVY AND DOWN HORIZONTAL LIGHT
# '╁'	U+2541	BOX DRAWINGS DOWN HEAVY AND UP HORIZONTAL LIGHT
# '╂'	U+2542	BOX DRAWINGS VERTICAL HEAVY AND HORIZONTAL LIGHT
# '╃'	U+2543	BOX DRAWINGS LEFT UP HEAVY AND RIGHT DOWN LIGHT
# '╄'	U+2544	BOX DRAWINGS RIGHT UP HEAVY AND LEFT DOWN LIGHT
# '╅'	U+2545	BOX DRAWINGS LEFT DOWN HEAVY AND RIGHT UP LIGHT
# '╆'	U+2546	BOX DRAWINGS RIGHT DOWN HEAVY AND LEFT UP LIGHT
# '╇'	U+2547	BOX DRAWINGS DOWN LIGHT AND UP HORIZONTAL HEAVY
# '╈'	U+2548	BOX DRAWINGS UP LIGHT AND DOWN HORIZONTAL HEAVY
# '╉'	U+2549	BOX DRAWINGS RIGHT LIGHT AND LEFT VERTICAL HEAVY
# '╊'	U+254A	BOX DRAWINGS LEFT LIGHT AND RIGHT VERTICAL HEAVY
# '╋'	U+254B	BOX DRAWINGS HEAVY VERTICAL AND HORIZONTAL

# '═'	U+2550	BOX DRAWINGS DOUBLE HORIZONTAL
# '║'	U+2551	BOX DRAWINGS DOUBLE VERTICAL
# '╒'	U+2552	BOX DRAWINGS DOWN SINGLE AND RIGHT DOUBLE
# '╓'	U+2553	BOX DRAWINGS DOWN DOUBLE AND RIGHT SINGLE
# '╔'	U+2554	BOX DRAWINGS DOUBLE DOWN AND RIGHT
# '╕'	U+2555	BOX DRAWINGS DOWN SINGLE AND LEFT DOUBLE
# '╖'	U+2556	BOX DRAWINGS DOWN DOUBLE AND LEFT SINGLE
# '╗'	U+2557	BOX DRAWINGS DOUBLE DOWN AND LEFT
# '╘'	U+2558	BOX DRAWINGS UP SINGLE AND RIGHT DOUBLE
# '╙'	U+2559	BOX DRAWINGS UP DOUBLE AND RIGHT SINGLE
# '╚'	U+255A	BOX DRAWINGS DOUBLE UP AND RIGHT
# '╛'	U+255B	BOX DRAWINGS UP SINGLE AND LEFT DOUBLE
# '╜'	U+255C	BOX DRAWINGS UP DOUBLE AND LEFT SINGLE
# '╝'	U+255D	BOX DRAWINGS DOUBLE UP AND LEFT
# '╞'	U+255E	BOX DRAWINGS VERTICAL SINGLE AND RIGHT DOUBLE
# '╟'	U+255F	BOX DRAWINGS VERTICAL DOUBLE AND RIGHT SINGLE
# '╠'	U+2560	BOX DRAWINGS DOUBLE VERTICAL AND RIGHT
# '╡'	U+2561	BOX DRAWINGS VERTICAL SINGLE AND LEFT DOUBLE
# '╢'	U+2562	BOX DRAWINGS VERTICAL DOUBLE AND LEFT SINGLE
# '╣'	U+2563	BOX DRAWINGS DOUBLE VERTICAL AND LEFT
# '╤'	U+2564	BOX DRAWINGS DOWN SINGLE AND HORIZONTAL DOUBLE
# '╥'	U+2565	BOX DRAWINGS DOWN DOUBLE AND HORIZONTAL SINGLE
# '╦'	U+2566	BOX DRAWINGS DOUBLE DOWN AND HORIZONTAL
# '╧'	U+2567	BOX DRAWINGS UP SINGLE AND HORIZONTAL DOUBLE
# '╨'	U+2568	BOX DRAWINGS UP DOUBLE AND HORIZONTAL SINGLE
# '╩'	U+2569	BOX DRAWINGS DOUBLE UP AND HORIZONTAL
# '╪'	U+256A	BOX DRAWINGS VERTICAL SINGLE AND HORIZONTAL DOUBLE
# '╫'	U+256B	BOX DRAWINGS VERTICAL DOUBLE AND HORIZONTAL SINGLE
# '╬'	U+256C	BOX DRAWINGS DOUBLE VERTICAL AND HORIZONTAL
# '╭'	U+256D	BOX DRAWINGS LIGHT ARC DOWN AND RIGHT
# '╮'	U+256E	BOX DRAWINGS LIGHT ARC DOWN AND LEFT
# '╯'	U+256F	BOX DRAWINGS LIGHT ARC UP AND LEFT
# '╰'	U+2570	BOX DRAWINGS LIGHT ARC UP AND RIGHT
#
# \N{EM DASH}
# \N{CURLY BRACKET EXTENSION}


# '𝇁'   U+1D100     Musical symbol longa perfecta rest
# '𝄅'   U+1D105      Musical symbol short barline
# '𝆠'   U+1D1A0     Musical symbol ornament stroke-6
# '𝇃' 1D1C3   Musical symbol brevis rest

# '⏐' Vertical line extension

# ' ᑊ' Canadian syllabics west-cree p
# ' ᴵ' Modifier letter capital i

# '⌙'    2319        Turned not sign
# '⌜'   '\u231C'      Top left corner
# '⌝'   '\u231D'
# '⌞'   '\u231E'
# '⌟'   '\u231F'
# '⎾'    23be       Dentistry symbol light vertical and top right
# '⎿'   23bF        Dentistry symbol light vertical and bottom right

# '―'   2015        Horizontal bar
#       23D7  Metrical triseme


# '⁅' Left Square Bracket with Quill
# '⁆'

# '｢'   Halfwidth Left Corner Bracket
# '｣'

# '⎹' RIGHT VERTICAL BOX LINE
# '⎸' LEFT VERTICAL BOX LINE
# '⎺' HORIZONTAL SCAN LINE-1
# '⎽' HORIZONTAL SCAN LINE-9
# '⎥' RIGHT SQUARE BRACKET EXTENSION
# '▏' LEFT ONE EIGHTH BLOCK
# '▕' RIGHT ONE EIGHTH BLOCK
# '▔' UPPER ONE EIGHTH BLOCK
# '▁' LOWER ONE EIGHTH BLOCK

# '⎢' Left square bracket extension 023A2
# '⎥' Right square bracket extension 023A5
# '⎜' Left parenthesis extension 0239C
# '⎟' Right parenthesis extension  0239F


# '＿' Fullwidth Low Line (U+FF3F)
# '￣' Fullwidth Macron U+FFE3
# '｜' Fullwidth Vertical Line (U+FF5C)
# '［' Fullwidth Left Square Bracket(U+FF3B)
# '］' Fullwidth Right Square Bracket (U+FF3D)
# '⎴' Top square bracket 023B4
# '⎵' Bottom square bracket 023B5


MAJOR_TICK_TOP = '\N{COMBINING SHORT VERTICAL LINE OVERLAY}'
MINOR_TICK_TOP = '\N{MUSICAL SYMBOL BREVIS REST}'
MAJOR_TICK_BOTTOM = '\N{MUSICAL SYMBOL LONGA PERFECTA REST}'
MINOR_TICK_BOTTOM = '\N{CANADIAN SYLLABICS WEST-CREE P}'

HLINES = {
    '':     ' ',
    ' ':    ' ',
    '-':    '─',
    '=':    '═',
    '--':   '╌',
    '.':    '┄',
    ':':    '┈',
    '_':    ' ',
    underline: ' ',
    '[':    (f'{MAJOR_TICK_TOP}  ', f' {MINOR_TICK_BOTTOM}'),
    '+':    (f'  {MAJOR_TICK_TOP}', f' {MINOR_TICK_BOTTOM}'),
    'E':    (f' {MAJOR_TICK_TOP}{MINOR_TICK_TOP}',
             f'{MAJOR_TICK_BOTTOM}{MINOR_TICK_BOTTOM}'),
    # '+':    ''
}
HLINES_HEAVY = {
    '-':    '━',
    '--':   '╍',
    '.':    '┅',
    ':':    '┉'
}

VLINES = {
    '':     '',
    ' ':    '',
    '_':    '│',
    '-':    '│',
    '|':    '│',
    '=':    '║',
    '||':   '║',
    '--':   '╎',
    '.':    '┆',
    ':':    '┊',
    '[':    ('▕', '▏'),
    '+':    ('┤', '├'),
    'E':     ('┤', '├')
}
VLINES_HEAVY = {
    '-':    '┃',
    '|':    '┃',
    '--':   '╏',
    '.':    '┇',
    ':':    '┋'
}

CORNERS = {
    '':         [''] * 4,
    '_':        [' ', ' ', '', ''],
    ' ':        '    ',

    '[':        ('  ', f'{MAJOR_TICK_TOP}', '', ''),
    '+':        (' ', ' ', ' ', '\b'),
    'E':        (' ', f' {MAJOR_TICK_TOP}', ' ', '\b'),

    'round':    '╭╮╰╯',
    '-':        '╭╮╰╯',

    'square':   '┌┐└┘',
    'L':        '┌┐└┘',
    'double':   '╔╗╚╝',
    '=':        '╔╗╚╝',
    # ◜◝ ◟◞
    'o':        '◶◵◷◴',
    'circle':   '◶◵◷◴',
    'triangle': '◤◥◣◢',
    'block':    '◲◱◳◰',
    # ◆ 	BLACK DIAMOND
    # ◇ 	WHITE DIAMOND
    # ■ 	BLACK SQUARE
    # □ 	WHITE SQUARE
}
CORNERS_HEAVY = '┏┓┗┛'


LINESTYLE_TO_EDGESTYLES = {
    # top, bottom, left, right
    '_': ('_', '_', '', ''),
    '[': '_',
    '+': ('_', '_', '', ''),
    'E': '_'
}


BOLD_OK = {'heavy', 'thick', 'bold', 'b', '*'}


def resolve_line(char):
    if char is underline:
        return underline, ' '

    char = str(char) or ''
    assert len(char) < 2
    return echo0, char


# @tag_defaults
# def _get_corners(corners, heavy):
#     if corners is not None:
#         return CORNERS[corners]

#     if heavy:
#         return CORNERS_HEAVY['square']

#     return CORNERS['round']

    # corners = str(corners)
    # assert len(corners) == 4

def resolve_linestyle(linestyle):
    if (linestyle is None) or isinstance(linestyle, str):
        return linestyle, False

    if not isinstance(linestyle, Collection):
        raise TypeError(f'Parameter `linestyle` should be of a str or '
                        f'Collection, not {type(linestyle)}.')

    linestyle, *heavy = linestyle
    heavy = (heavy[0].lower() in BOLD_OK) if heavy else False

    if heavy and (linestyle not in HLINES_HEAVY):
        warnings.warn(f'Bold line not available for style: {linestyle!r}.')
        heavy = False

    return linestyle, heavy


EMPTY = object()


@api.synonyms({'((line|edge)_?)?colou?rs?': 'linestyle'})
def textbox(text, fg=None, bg=None,
            linestyle='_',
            linecolor=None,
            **kws):
    """
    High level function that wraps multi-line strings in a text box. The
    parameters `top`, `bottom`, `left` and `right` are mapped to unicode
    box drawing symbols.


    Parameters
    ----------
    text : str
        Text to enclose in box.
    fg : _type_, optional
        Foreground style for text, by default None
    bg : _type_, optional
        Background style for text, by default None
    linestyle : str, optional
        Linestyle of frame, by default '_'
    linecolor : _type_, optional
        Colour of frame lines, by default None

    Examples
    --------
    >>> 

    Returns
    -------
    _type_
        _description_
    """

    linestyle, heavy = resolve_linestyle(linestyle)

    if linestyle is None:
        return justify(text, kws.get('align', '^'), kws.get('width'))

    # top = bottom = left = right = style
    hlines = (HLINES, HLINES_HEAVY)[heavy]
    vlines = (VLINES, VLINES_HEAVY)[heavy]
    top, bottom = duplicate_if_scalar(hlines[linestyle])
    # also allow user override
    top = kws.pop('top', top)
    bottom = kws.pop('bottom', bottom)

    # sides can be separately specified or toggled
    sides = kws.pop('sides', EMPTY) or ''
    corners = kws.pop('corners', EMPTY)
    if sides in {EMPTY, True}:
        sides = vlines[linestyle]

    left, right = duplicate_if_scalar(sides)
    # also allow user override
    left = kws.pop('left', left)
    right = kws.pop('right', right)

    if corners in {EMPTY, True}:
        # default corners to match linestyle
        if sides:
            corners = (CORNERS_HEAVY if heavy else
                       CORNERS.get(linestyle, CORNERS['round']))
        else:
            corners = CORNERS['']
    else:
        # corners explicitly given
        corners = CORNERS.get(corners, corners)

    return TextBox.for_style(linestyle)(
        fg=fg, bg=bg,
        left=left, top=top,
        right=right, bottom=bottom,
        corners=corners,
        linecolor=LINESTYLE_TO_EDGESTYLES.get(linestyle, linecolor)
    )(text, **kws)

    # return (TextBox.for_style(linestyle), init_kws)
    # return TextBox.for_style(linestyle)(**init_kws)(text, **kws)

#  TODO: AsciiTextBox
# def effect_as_string(effects):
  #


# null singleton for default identification
TOP = LEFT = object()


class TextBox:
    """
    Flexible box drawing.
    """

    # line_fmt_template = ('{left:|{linecolor[2]}}'
    #                      '{line: {align}{width}|{style.fg}/{style.bg}}'
    #                      '{right:|{linecolor[3]}}')

    @classmethod
    def for_style(cls, style):
        return next((kls for kls in iter_subclasses(cls)
                     if style in kls._supported_linestyles),
                    TextBox)

    def __init__(self,
                 #  fmt='{text: {align}{width}|{fg}/{bg}}'
                 left='\N{BOX DRAWINGS LIGHT VERTICAL}',
                 top='\N{BOX DRAWINGS LIGHT HORIZONTAL}',
                 right=LEFT,
                 bottom=TOP,
                 corners='╭╮╰╯',
                 linestyles=(),
                 fg=None,
                 bg=None,
                 **kws):
        """
        Initialize the TextBox. This object works at a lower level than the
        `textbox` function. The parameters `top`, `bottom`, `left` and `right`
        are used directly as characters for the frame, repeating until the space
        is filled.
        """

        # TODO: parse stylized input for sides
        self.left = (left or '')
        self.right = self.left if (right is LEFT) else (right or '')
        assert isinstance(self.left, str) and isinstance(self.right, str)

        self.top = top
        self.bottom = top if bottom is TOP else bottom
        self.corners = corners
        self.style = AttrReadItem(fg=(fg or ''),
                                  bg=(bg or ''))
        # get line colors for edges
        linestyles = kws.get('color', linestyles) or ''
        self.linestyles = list(duplicate_if_scalar(linestyles, 4))

        # stylize(line_fmt_template,
        self.line_fmt = (apply(left, self.linestyles[2]) +
                         apply('{line: {align}{width}}', **self.style) +
                         apply(right, self.linestyles[3]))

    def __call__(self, text='', width=None, height=None, align='^'):
        text = str(text)
        text_width = get_width(text)
        if width is None:
            width = text_width + len(self.left) + len(self.right)
        else:
            width = resolve_width(width)
            if text_width > width:
                warnings.warn(f'Text too wide for box {text_width} > {width}.')

        return '\n'.join(self._iter_lines(text, width, align))

    # line_formats = {
    #     'top': '{{corners[0]}{{top}:{top}^{width}}{corners[1]}:|{linestyles[0]}}',
    #     'bot': '{{corners[2]}{{bot}:{bot}^{width}}{corners[3]}:|{linestyles[1]}}',
    #     'mid': '{left:|{linestyles[2]}}{line: {align}{width}}{right:|{linestyles[3]}}'
    # }

    def _iter_lines(self, text, width, align, **kws):
        width = width - len(self.left) - len(self.right)
        kws = {**locals(), **vars(self), **kws}
        kws.pop('self')
        # lc0, lc1 = self.linestyles
        yield make_hline(self.top, self.corners[:2], width, self.linestyles[0])

        for line in text.splitlines():
            yield format(self.line_fmt, **kws, line=line)

        if self.bottom:
            yield make_hline(self.bottom, self.corners[2:], width, self.linestyles[1])


def make_hline(characters, corners, width, color):
    # draw horizontal frame edge
    n = sum((len(s) - unicodedata.combining(s) for s in characters))
    line = (characters * (width // n) + characters[:(width % n)]).join(corners)
    return apply(backspaced(line), color)


class AnsiBox(TextBox):
    _supported_linestyles = {'_', underline}

    def __init__(self, **kws):
        super().__init__(**{**dict(top=' ',
                                   corners=CORNERS[' '],
                                   linestyles=('_', '_', '', '')),
                            **kws})
        self.linestyles[0] = (self.linestyles[0], self.style.fg)

    def _iter_lines(self, text, width, align, **kws):
        itr = super()._iter_lines(text, width, align)
        itr = mit.islice_extended(itr)
        upto = text.count('\n') + bool(self.top) - bool(self.bottom)  # - 1
        yield from itr[:upto]
        yield underline(next(itr))


class GridFrameBox(AnsiBox):
    _supported_linestyles = {'[', '+', 'E'}

    def __init__(self, **kws):
        super().__init__(**{**dict(top='𝇁 ',        # ' ╷',
                                   bottom=' 𝇁',     # ' ╵',
                                   left='▕',
                                   right='▏',
                                   linestyles='_',       # underline
                                   corners=(' ', '𝇁', '', '')),
                            **kws})

    def _iter_lines(self, text, width, align, **kws):
        bottom = self.bottom
        self.bottom = ' '
        yield from super()._iter_lines(text, width, align)
        self.bottom = bottom
        yield make_hline(bottom, self.corners[2:], width, '')


class TickedGridFrame(GridFrameBox):
    def __init__(self, xticks=(), yticks=(), **kws):
        super().__init__(**kws)

        for xy, ticks in zip('xy', (xticks, yticks)):
            # ticks = [str(subscripts.get(t, t)) for t in ticks]
            w = max(map(ansi.length, ticks)) if ticks else 0
            setattr(self, f'{xy}ticks',
                    list(map(f'{{: >{w}}}'.format, ('', *ticks)))
                    )

    def _iter_lines(self, text, width, align):
        yield from super()._iter_lines(text, width, align)
        # for tick, line in itt.zip_longest(self.yticks, itr, fillvalue=' '):
        #     yield tick + line

        # if self.xticks:
        #     yield ''.join(self.xticks)
