"""
Image rendering in the terminal.
"""

# third-party
import numpy as np
from matplotlib.pyplot import get_cmap
from matplotlib.colors import Normalize

from scrawl.imagine import get_clim


BORDER = '⎪'    # U+23aa Sm CURLY BRACKET EXTENSION ⎪  # '|'
# LBORDER = '⎸'  # LEFT VERTICAL BOX LINE
# RBORDER = '⎹'  # RIGHT VERTICAL BOX LINE
BLOCKS = tuple(' ▄▀█')
# '▀'   UPPER HALF BLOCK    U+2580
# '▄'   LOWER HALF BLOCK    U+2584
# '█'   FULL BLOCK          U+2588


def stack(pixels):
    return ''.join(''.join(row) + '\n' for row in pixels)


def framed(pixels, add_top_row=True):
    from . import underline

    # "frame" represented by ANSI underline  (top, bottom)
    # and "CURLY BRACKET EXTENSION" "⎪" for sides

    # pixels = pixels.astype(str)
    # add top row for underline to work as frame
    if add_top_row:
        pix = np.row_stack((['  '] * pixels.shape[1], pixels)).astype('O')
    else:
        pix = pixels.astype('O')

    # add left right edges
    pix[1:, 0] = np.char.add(BORDER, pix[1:, 0].astype(str))
    pix[1:, -1] = np.char.add(pix[1:, -1].astype(str), BORDER)
    pix[0, 0] = pix[0, -1] = '   '

    # underline top / bottom row
    for row in (0, -1):
        pix[row] = list(map(underline, pix[row]))

    return pix


class TextImage:
    """
    Base class for text-based image rendering.
    """

    # characters per pixel
    _pixel_size = 2
    frame = False

    def __init__(self, data, origin=0, *args, **kws):
        self.pixels = self.get_pixels(data, origin)
        self.shape = self.pixels.shape

    def get_pixels(self, data, origin=0):
        data = np.array(data)
        assert data.ndim == 2, 'Only 2D arrays can be imaged.'
        # assert (data.dtype.kind in 'ib'), 'Only integer arrays can be imaged.'

        # re-orient data
        origin = int(origin)
        assert origin in {0, 1}
        o = (-1, 1)[origin]
        return data[::o]

    def __str__(self):
        return stack(self.pixels)

    def __repr__(self):
        # format here for ineractive use
        return self.format()

    def format(self, frame=frame):
        if not frame:
            return str(self)

        return stack(framed(self.pixels))

        # # underline first and last row
        # top = underline(' ' * self._pixel_size * (self.shape[1] + 1))
        # mid, bot, _ = stack(framed(self.pixels)).rsplit('\n', 2)
        # bot = underline(bot)
        # return '\n'.join((top, mid, bot, ''))

    def render(self, frame=frame):
        print(self.format(frame))
        return self

    # def _framed(self):
    #     # "frame" represented by ANSI underline  (top, bottom)
    #     # and "CURLY BRACKET EXTENSION" "⎪" for sides
    #     # have to expand dtype to add character
    #     dt = self.pixels.dtype
    #     pix = self.pixels.astype(f'{dt.kind}{dt.itemsize // 4 + len(BORDER)}')
    #     pix[:, 0] = np.char.add(BORDER, pix[:, 0])
    #     pix[:, -1] = np.char.add(pix[:, -1], BORDER)
    #     return pix


class AnsiImage(TextImage):
    """
    Super fast image rendering in the terminal!

    ... for tiny images ...
    """

    def __init__(self, data, cmap=None, origin=0):
        # colour map
        self.cmap = get_cmap(cmap)
        #
        TextImage.__init__(self, data, origin)

    def get_pixels(self, data, origin):
        from . import codes
        data = super().get_pixels(data, origin)

        # normalize
        data = data.astype(float)
        data = Normalize(*get_clim(data))(data)

        # get the 24 bit colours
        shape = data.shape
        data = self.cmap(data.ravel(), bytes=True)[..., :3]

        # create "pixels"
        # a single pixels represented by 2 ansi coded whitespaces.
        data = [codes.apply('  ', bg=_) for _ in data]
        return np.reshape(data, shape)


class BinaryImage(TextImage):
    def __init__(self, data, origin=0):
        assert data.dtype.kind == 'b'

        super().__init__(data, origin)


class UnicodeBinaryImage(BinaryImage):
    """
    Pixels are represented by unicode block elements:
        U+2580     '▀'       Upper half block
        U+2584     '▄'       Lower half block
        U+2588     '█'       Full block
        and space  ' '
    Each representing 2 (row) pixels. In this way, a binary Image can be represented
    4 times more compactly than with 'AnsiImage':

    Compare:


    Parameters
    ----------
    TextImage : [type]
        [description]

    Examples
    --------
    >>> 
    """

    # characters per pixel
    _pixel_size = 1

    def __init__(self, data):
        super().__init__(data)
        nr, nc = self.shape
        if nr % 2:
            data = np.vstack([data, np.zeros(nc)])

        encoded = np.packbits(data.reshape(-1, 2, nc), 1) // 64
        self.pixels = np.array(BLOCKS)[encoded.squeeze()]


def show(self,  frame=True, origin=0, cmap=None):

    origin = int(origin)
    assert origin in {0, 1}

    # re-orient data
    o = (-1, 1)[origin]
    data = self.data[::o]

    #
    return AnsiImage(data, cmap).render(frame)
