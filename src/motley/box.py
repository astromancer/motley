
# std
import warnings as wrn

# local
from recipes.functionals import echo0

# relative
from . import underline
from .utils import wideness, resolve_width


def resolve_emph(char):
    if char is underline:
        return underline, ' '

    char = str(char) or ''
    assert len(char) < 2
    return echo0, char


class TextBox:  # TODO: AsciiBox, AnsiBox
    def __init__(self,  top='—', left='⎪', bottom=None, right=None):

        self.left = str(left)
        self.right = str(right or left)

        self.overline, self.top = resolve_emph(top)
        self.underline, self.bottom = resolve_emph(bottom or top)

    def __call__(self, text='', width=None, align='^'):
        width = resolve_width(width)
        text_width = wideness(text)
        if text_width > width:
            wrn.warn(f'Text too wide for box {text_width} > {width}.')
        
        *lines, last = self._iter(text, width, align)
        parts = (*lines, self.underline(last))
        if self.bottom:
            parts = (*parts, self.bottom * width)
            
        return '\n'.join(filter(None, parts))

    def _iter(self, text, width, align):
        if self.top:
            yield self.overline(self.top * width)
            
        width = width - len(self.left) - len(self.right)
        for line in text.split('\n'):
            yield f'{self.left}{line!s: {align}{width}}{self.right}'



clear_box = TextBox('', '')
box = TextBox('—', '⎪')
