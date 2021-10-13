"""
Image rendering in the console!
"""

# std
import itertools as itt
import functools as ftl

# third-party
import numpy as np
from loguru import logger
from matplotlib.pyplot import get_cmap
from matplotlib.colors import Normalize

# local
from scrawl.imagine import get_clim
from recipes.string import vstack
from recipes.functionals import echo0

# relative
from .. import ansi, apply, codes, format, hstack, length, underline
from ..textbox import TickedGridFrame, textbox
from .trace import trace_boundary


RIGHT_BORDER = '\N{RIGHT ONE EIGHTH BLOCK}'
LEFT_BORDER = '\N{LEFT ONE EIGHTH BLOCK}'

# WARNING: Some terminal emulators like Konsole do not render underlined
# RIGHT ONE EIGHTH BLOCK properly. Underline disappears.

# BORDER = '⎪'    # U+23aa Sm CURLY BRACKET EXTENSION ⎪  # '|'
# LBORDER = '⎸'  # LEFT VERTICAL BOX LINE
# RBORDER = '⎹'  # RIGHT VERTICAL BOX LINE
BLOCKS = tuple(' ▄▀█')
# '▀'   UPPER HALF BLOCK    U+2580
# '▄'   LOWER HALF BLOCK    U+2584
# '█'   FULL BLOCK          U+2588


def _add_edge(pixel, left, char, color):
    #
    csi, nrs, fin, text, end = next(ansi.parse(pixel))
    # order = -int(left or -1)
    new = ''.join((text[left], char)[::-int(left or -1)])
    fg = codes.get_code_str(color)
    # Apply color if this pixel doesn't already has an edge on the opposite side
    # with a fg color!
    if fg not in nrs.split(';'):
        nrs = fg + nrs
    return ''.join((csi, nrs, fin, new, end))


def add_right_edge(pixel, color=None):
    # RIGHT_BORDER = '［'
    return _add_edge(pixel, 0, RIGHT_BORDER, color)


def add_left_edge(pixel, color):
    # LEFT_BORDER = '］'
    return _add_edge(pixel, 1, LEFT_BORDER, color)


def _get_edge_drawing_funcs(color):
    left = ftl.partial(add_left_edge, color=color)
    right = ftl.partial(add_right_edge, color=color)
    top = bottom = ftl.partial(apply, fg=('_', color))
    return [(left,   echo0, right),
            (bottom, echo0, top)]


def overlay(mask, pixels, color=None):
    """
    Overlay the contours from `mask` on the image `pixels`.

    Parameters
    ----------
    mask : array-like
        Boolean array of region to overlay the outline of.
    pixels : array-like
        Image pixels (strings).
    color : str or None, optional
        Colour of the contours, by default None.


    Returns
    -------
    np.ndarray(dtype=str)
        Pixels with edge characters added. NOTE that an extra row is added to
        the top of the image to keep ansi underline codes.
    """
    mask = np.asarray(mask)
    assert mask.shape == pixels.shape

    # edge drawing functions
    edge_funcs = _get_edge_drawing_funcs(color)

    # get boundary line
    indices, boundary, _ = trace_boundary(mask)

    # underline top edge pixels requires extending the image size
    if 0 in indices[:, 0]:
        # The 0th row has a boundary pixel => we have to extend the image shape
        # upward by one row to hold the ansi underline for the upper edge of the
        # top row.
        out = np.full(np.add(pixels.shape, (1, 0)), '  ', 'O')
        out[:-1] = pixels
        # off = -1
    else:
        out = pixels.astype('O')
        # off = -1
    #
    # i = 0
    current = indices[0]
    for step in np.diff(boundary, axis=0):
        axis, = np.where(step)[0]
        add_edge = edge_funcs[axis][step[axis] + 1]

        # logger.debug(step, axis, step[axis])
        offset = (0, 0)
        if step[axis] < 0:
            offset = step
        elif axis == 0:
            offset = (0, -1)
        ix = tuple(current + offset)

        # add edge character
        out[ix] = add_edge(out[ix])
        logger.opt(lazy=True).trace('\n{}', lambda: stack(out[::-1]))
        # update current pixel position
        current += step

    return out.astype(str)

# FRAMES = {
#     '-':,
#     '+',
#     ''
# }


def frame_inpixel(pixels, color):
    # Add frame characters to pixels.
    pixels = np.row_stack((['  '] * pixels.shape[1], pixels)).astype('O')

    # add left right edges
    pixels[1:, 0] = np.vectorize(add_left_edge, 'O')(pixels[1:, 0], color)
    pixels[1:, -1] = np.vectorize(add_right_edge, 'O')(pixels[1:, -1], color)
    # pixels[0, 0] = pixels[0, -1] = '   '

    # underline top / bottom row
    for row in (0, -1):
        pixels[row] = list(map(underline, pixels[row]))

    return pixels


# def framed(pixels, add_top_row=True):


#     # "frame" represented by ANSI underline  (top, bottom)
#     # and "CURLY BRACKET EXTENSION" "⎪" for sides

#     # pixels = pixels.astype(str)
#     # add top row for underline to work as frame
#     if add_top_row:
#         pix = np.row_stack((['  '] * pixels.shape[1], pixels)).astype('O')
#     else:
#         pix = pixels.astype('O')

#     # add left right edges
#     pix[1:, 0] = np.char.add(BORDER, pix[1:, 0].astype(str))
#     pix[1:, -1] = np.char.add(pix[1:, -1].astype(str), BORDER)
#     pix[0, 0] = pix[0, -1] = '   '

#     # underline top / bottom row
#     for row in (0, -1):
#         pix[row] = list(map(underline, pix[row]))

#     return pix


def stack(pixels):
    return ''.join(''.join(row) + '\n' for row in pixels)


def show(self,  frame=True, origin=0, cmap=None):

    origin = int(origin)
    assert origin in {0, 1}

    # re-orient data
    o = (-1, 1)[origin]
    data = self.data[::o]

    return AnsiImage(data, cmap).render(frame)


def thumbnails(images, masks=(),
               cmap='cmr.voltage_r', contour_color='r',
               title=None,
               labels=(),
               label_fmt='{{label:d|B_}: ^{width}}'):
    """
    Cutout image thumbnails displayed as a grid in terminal. Optional binary
    contours overlaid.

    Parameters
    ----------
    image : np.ndarray
        Image array with sources to display.
    seg : obstools.image.segmentation.SegmentedImage
        The segmented image of detected sources
    top : int
        Number of brightest sources to display images for.
    image_cmap : str, optional
        Colour map, by default 'cmr.voltage_r'.
    contour_color : str, optional
        Colour for the overlaid contour, by default 'r'.
    label_fmt : str, optional
        Format string for the image titles, by default
        '{{label:d|Bu}: ^{width}}'. This will produce centre justified lables in
        bold, underlined text above each image.

    """
    #    contour_cmap='hot'):
    # contours_cmap = seg.get_cmap(contour_cmap)
    #line_colours  = cmap(np.linspace(0, 1, top))
    # format(label_fmt, label=lbl, width=2 * biggest[1])

    for label, image, mask in itt.zip_longest(labels, images, masks):
        img = AnsiImage(image, cmap)
        img.overlay(mask, contour_color)
        # contours_cmap(i / top)[:-1]
        yield '\n'.join((format(label_fmt, label=label, width=2*len(image[0])),
                         str(img)))

    #
    text = hstack(images, 2)

    if title:
        width = length(text[:text.index('\n')], raw=False)
        return vstack((title, text), '^', width)

    return text


class TextImage:
    """
    Base class for text-based image rendering.
    """

    # characters per pixel
    _pixel_size = 2
    # frame = False

    def __init__(self, data, origin=0, frame=False, *args, **kws):
        self.pixels = self.get_pixels(data, origin)
        self.shape = self.pixels.shape
        self.frame = bool(frame)

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
        return self.format()

    def __repr__(self):
        # format here for ineractive use
        return self.format()

    def format(self, frame=None, xticks=(), yticks=()):
        if frame is None:
            frame = self.frame

        if not frame:
            return stack(self.pixels)

        if xticks or yticks:
            return TickedGridFrame(xticks, yticks)(stack(self.pixels))
        
        # if frame in ('_', underline, True):
        #     return AnsiBox()(stack(self.pixels))
            # return stack(frame_inpixel(self.pixels, None))

        return textbox(stack(self.pixels), style=frame)

        # # underline first and last row
        # top = underline(' ' * self._pixel_size * (self.shape[1] + 1))
        # mid, bot, _ = stack(framed(self.pixels)).rsplit('\n', 2)
        # bot = underline(bot)
        # return '\n'.join((top, mid, bot, ''))

    def render(self, frame=None):
        print(self.format(frame))
        return self

    # def add_frame(self, **kws):
    #     # Add frame characters to pixels.

    #     # "frame" represented by ANSI underline  (top, bottom)
    #     # and "CURLY BRACKET EXTENSION" "⎪" for sides

    #     if self.has_frame:
    #         raise ValueError()

    #     pixels = self.pixels
    #     # add top row for underline to work as frame
    #     self._frame_top_row = ['  '] * pixels.shape[1]

    #     # add left right edges
    #     pix[1:, 0] = np.char.add(BORDER, pix[1:, 0].astype(str))
    #     pix[1:, -1] = np.char.add(pix[1:, -1].astype(str), BORDER)
    #     pix[0, 0] = pix[0, -1] = '   '

    #     # underline top / bottom row
    #     for row in (0, -1):
    #         pix[row] = list(map(underline, pix[row]))

    #     self.has_frame = True
    #     return pix

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
    Fast image rendering in the terminal!

    ... for tiny images ...

    Pixels are represented as two spaces coloured using ansi codes.
    """

    _top_row_added = False

    def __init__(self, data, cmap=None, origin=0, frame=True):
        # colour map
        self.cmap = get_cmap(cmap)
        #
        TextImage.__init__(self, data, origin, frame)

        self._frame_top_row = None
        self.has_frame = False

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
        return np.reshape([codes.apply('  ', bg=_) for _ in data], shape)

    def overlay(self, mask, color=None):
        self.pixels = overlay(mask, self.pixels[::-1], color)[::-1].astype(str)
        self._top_row_added = True

    # def format(self, frame=None):
    #     if frame is None:
    #         frame = self.frame

    #     if not frame:
    #         return str(self)

    #     if frame in ('_', underline):
    #         return stack(frame_inpixel(self.pixels, None))

    #     return textbox(stack(self.pixels), style=frame)

        # if frame:
        #     pixels = framed(self.pixels, not self._top_row_added)

        # return stack(pixels)


class BinaryImage(TextImage):
    def __init__(self, data, origin=0):
        assert data.dtype.kind == 'b'

        super().__init__(data, origin)


class BinaryImageUnicodeBlocks(BinaryImage):
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


class SegmentedImageUnicodeBlocks(BinaryImageUnicodeBlocks):
    pass
