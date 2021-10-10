
# std
import itertools as itt
import more_itertools as mit
import contextlib as ctx
from recipes.misc import duplicate_if_scalar
import warnings as wrn

# local
from recipes.functionals import echo0

# relative
from . import underline
from .utils import get_width, resolve_width
from . import apply, format, codes, format_partial


# TODO
# class Paragraph(str):
# def  get_width, justify, frame etc


# ' 𝇁'  U+1D100  Musical symbol longa perfecta rest

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
    # '+':    ''
}
HLINES_BOLD = {
    '':     ' ',
    ' ':    ' ',
    '-':    '━',
    '--':   '╍',
    '.':    '┅',
    ':':    '┉',
}

VLINES = {
    '':     '',
    '-':    '│',
    '|':    '│',
    '=':    '║',
    '||':   '║',
    '--':   '╎',
    '.':    '┆',
    ':':    '┊'
}
VLINES_BOLD = {
    '':     '',
    ' ':    '',
    '-':    '┃',
    '|':    '┃',
    '--':   '╏',
    '.':    '┇',
    ':':    '┋'
}

CORNERS = {
    '':         [''] * 4,
    ' ':        '    ',
    'round':    '╭╮╰╯',
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
CORNERS_BOLD = {
    # 'round': '',
    'square': '┏┓┗┛',
    # 'double': ''
}


def resolve_line(char):
    if char is underline:
        return underline, ' '

    char = str(char) or ''
    assert len(char) < 2
    return echo0, char


# @tag_defaults
def _get_corners(corners, bold):
    if corners is not None:
        return CORNERS[corners]

    if bold:
        return CORNERS_BOLD['square']

    return CORNERS['round']
    # corners = str(corners)
    # assert len(corners) == 4


def textbox(text,
            style='_',
            bold=False,
            color=None,
            **kws):
    """
    High level function that wraps multi-line strings in a text box. The
    parameters `top`, `bottom`, `left` and `right` are mapped to unicode
    box drawing symbols.

    Parameters
    ----------
    text : [type]
        [description]
    style : str
        frame style
    bold : bool, optional
        [description], by default False
    color : [type], optional
        [description], by default None

    Examples
    --------
    >>> 

    Returns
    -------
    [type]
        [description]
    """
    # textbox(style='')
    # textbox(style='-')
    # textbox(style='=')
    # textbox(style='.')

    hlines = (HLINES, HLINES_BOLD)[bold]
    vlines = (VLINES, VLINES_BOLD)[bold]
    # corners_ = (CORNERS, CORNERS_BOLD)[bold]

    # kws.pop('sides', None)
    if style is None:
        return text

    if style == '_':
        return AnsiBox(**kws)(text)

    if style == '+':
        return GridFrameBox(**kws)(text)

    # top = bottom = left = right = style
    top = bottom = hlines[style]
    # bottom = hlines[bottom] if bottom is not None else top
    left = right = vlines[style]
    # right = vlines[right] if right is not None else left
    # corners = corners_[corners]
    corners = CORNERS.get(style, None)

    if 'sides' in kws:
        sides = kws.pop('sides') or ''
        left, right = duplicate_if_scalar(sides)
        corners = corners or sides

    if corners is None:
        corners = _get_corners(corners, bold)

    return TextBox(top, bottom, left, right, corners, color)(text, **kws)

#  TODO: AsciiTextBox


# null singleton for default identification
NULL = object()


class TextBox:
    """
    Flexible box drawing.
    """

    def __init__(self,
                 #  fmt='{text: {align}{width}|{fg}/{bg}}'
                 top='\N{BOX DRAWINGS LIGHT HORIZONTAL}',
                 bottom=NULL,
                 left='\N{BOX DRAWINGS LIGHT VERTICAL}',
                 right=NULL,
                 corners='╭╮╰╯',
                 colors=(),
                 **kws):
        """
        Initialize the TextBox. This object works at a lower level than the
        `textbox` function. The parameters `top`, `bottom`, `left` and `right`
        are used directly as characters for the frame, repeating until the space
        is filled.
        """

        # TODO: parse stylized input for sides

        self.left = str(left)
        self.right = str(left if right is NULL else right or '')
        self.top = top
        self.bottom = top if bottom is NULL else bottom
        self.corners = corners

        self.colors = duplicate_if_scalar(kws.get('color', colors) or '', 4)

    def __call__(self, text='', width=None, height=None, align='^'):
        text = str(text)
        text_width = get_width(text)
        if width is None:
            width = text_width + len(self.left) + len(self.right)
        else:
            width = resolve_width(width)
            if text_width > width:
                wrn.warn(f'Text too wide for box {text_width} > {width}.')

        return '\n'.join(self._iter_lines(text, width, align))

    # line_formats = {
    #     'top': '{{corners[0]}{{top}:{top}^{width}}{corners[1]}:|{colors[0]}}',
    #     'bot': '{{corners[2]}{{bot}:{bot}^{width}}{corners[3]}:|{colors[1]}}',
    #     'mid': '{left:|{colors[2]}}{line: {align}{width}}{right:|{colors[3]}}'
    # }
    line_fmt = '{left:|{colors[2]}}{line: {align}{width}}{right:|{colors[3]}}'

    def _iter_lines(self, text, width, align, **kws):
        width = width - len(self.left) - len(self.right)
        kws = {**locals(), **vars(self), **kws}
        kws.pop('self')
        yield make_hline(self.top, self.corners[:2], width, self.colors[0])

        line_fmt = format_partial(self.line_fmt, **kws)
        for line in text.splitlines():
            yield format(line_fmt, **kws, line=line)

        if self.bottom:
            yield make_hline(self.bottom, self.corners[2:], width, self.colors[1])


def make_hline(characters, corners, width, color):
    n = len(characters)
    line = (characters * (width // n) + characters[:(width % n)]).join(corners)
    return apply(line, color)


class AnsiBox(TextBox):
    def __init__(self, **kws):
        super().__init__(**{**dict(top=' ',
                                   corners=CORNERS[' '],
                                   colors=('_', '', '', '')),
                            **kws})

    def _iter_lines(self, text, width, align, **kws):
        # from IPython import embed
        # embed(header="Embedded interpreter at 'src/motley/textbox.py':386")
        itr = super()._iter_lines(text, width, align)
        itr = mit.islice_extended(itr)
        upto = text.count('\n') + bool(self.top) - bool(self.bottom) #- 1
        yield from itr[:upto]
        yield underline(next(itr))


class GridFrameBox(AnsiBox):
    def __init__(self, **kws):
        super().__init__(**{**dict(top='𝇁 ',  # ' ╷',
                                   bottom=' 𝇁',  # ' ╵',
                                   left='▕',
                                   right='▏',
                                   color='_',  # underline
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
        self.xticks = list(xticks)
        self.yticks = list(yticks)

    def _iter_lines(self, text, width, align):
        itr = super()._iter_lines(text, width, align)
        for tick, line in itt.zip_longest(self.yticks, itr, fill_value=None):
            yield tick + line

        if self.xticks:
            yield ''.join(self.xticks)
