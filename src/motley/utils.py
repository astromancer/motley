"""
Utility functions and classes
"""

# std libs
import os
import numbers
import functools as ftl
import itertools as itt

# third-party libs
import numpy as np

# local libs
from recipes.misc import get_terminal_size

# relative libs
from . import codes, ansi


ALIGNMENT_MAP = {'r': '>',
                 'l': '<',
                 'c': '^'}


def get_alignment(align):
    align = ALIGNMENT_MAP.get(align.lower()[0], align)
    if align not in '<^>':
        raise ValueError('Unrecognised alignment {!r}'.format(align))
    return align


def hstack(tables, spacing=0, offset=()):
    """
    Stick two or more tables (or multi-line strings) together horizontally

    Parameters
    ----------
    tables
    spacing
    offset

    Returns
    -------

    """

    assert len(tables), 'tables must be non-empty sequence'

    from motley.table import Table

    #
    if isinstance(offset, numbers.Integral):
        offset = [0] + [offset] * (len(tables) - 1)

    #
    widths = []
    lines_list = []
    max_length = 0
    for i, (tbl, off) in enumerate(
            itt.zip_longest(tables, offset, fillvalue=None)):
        if off is None:
            nl = tbl.n_head_lines if isinstance(tbl, Table) else 0
            if i == 0:
                nl0 = nl
            off = nl0 - nl

        lines = ([''] * off) + str(tbl).splitlines()
        lines_list.append(lines)
        max_length = max(len(lines), max_length)
        widths.append(ansi.length_seen(lines[0]))
        if spacing:
            lines_list.append([])
            widths.append(spacing)

    #
    for i, lines in enumerate(lines_list):
        fill = ' ' * (widths[i])
        m = max_length - len(lines)
        lines_list[i].extend([fill] * m)

    return '\n'.join(map(''.join, zip(*lines_list)))


def vstack(tables, strip_titles=True, strip_headers=True, spacing=1):
    """
    Vertically stack tables while aligning column widths

    Parameters
    ----------
    tables: list of motley.table.Table
        Tables to stack
    strip_titles: bool
        Strip titles from all but the first table in the sequence
    strip_headers: bool
        Strip column group headings and column headings from all but the first
        table in the sequence

    Returns
    -------
    str
    """
    # check that all tables have same number of columns
    ncols = [tbl.shape[1] for tbl in tables]
    if len(set(ncols)) != 1:
        raise ValueError(
            f'Cannot stack tables with unequal number of columns: {ncols}')

    w = np.max([tbl.col_widths for tbl in tables], 0)
    vspace = '\n' * (spacing + 1)
    s = ''
    nnl = 0
    for i, tbl in enumerate(tables):
        tbl.col_widths = w  # set all column widths equal
        if i and strip_headers:
            nnl = (tbl.frame + tbl.has_title + tbl.n_head_rows)
        *head, r = str(tbl).split('\n', nnl)
        keep = []
        if head:
            if not strip_titles:
                keep += head[tbl.frame:(-tbl.n_head_rows or None)]
            if not strip_headers:
                keep += head[(tbl.frame + tbl.has_title):]

        s += '\n'.join((vspace, *keep, r))

    return s.lstrip('\n')


def vstack_compact(tables):
    # figure out which columns can be compactified
    # note. the same thing can probs be accomplished with table groups ...
    assert len(tables)
    varies = set()
    ok_size = tables[0].data.shape[1]
    for i, tbl in enumerate(tables):
        size = tbl.data.shape[1]
        if size != ok_size:
            raise ValueError('Table %d has %d columns while the preceding %d '
                             'tables have %d columns.'
                             % (i, size, i - 1, ok_size))
        # check compactable
        varies |= set(tbl.compactable())

    return varies


def overlay(text, background='', align='^', width=None):
    """overlay text on background using given alignment."""

    if not (background or width):  # nothing to align on
        return text

    if not background:
        background = ' ' * width  # align on clear background
    elif not width:
        width = ansi.length_seen(background)

    if ansi.length_seen(background) < ansi.length_seen(text):
        # alignment is pointless
        return text

    # do alignment
    align = get_alignment(align)
    if ansi.has_ansi(background):
        raise NotImplementedError(
            '# fixme: will not work if background has coded strings')

    if align == '<':  # left aligned
        overlaid = text + background[ansi.length_seen(text):]

    elif align == '>':  # right aligned
        overlaid = background[:-ansi.length_seen(text)] + text

    elif align == '^':  # center aligned
        div, mod = divmod(ansi.length_seen(text), 2)
        half_width = width // 2
        # start and end indices of the text in the center of the background
        idx = half_width - div, half_width + (div + mod)
        # center text on background
        overlaid = background[:idx[0]] + text + background[idx[1]:]

    return overlaid


def wideness(s, raw=False):  # rename width ??
    """
    For multi-line string `s` get the character width of the widest line.

    Parameters
    ----------
    s
    raw

    Returns
    -------

    """
    length = ftl.partial(ansi.length, raw=raw)
    # deal with cell elements that contain newlines
    return max(map(length, s.split(os.linesep)))


def banner(obj, width=None, swoosh='=', align='<', **props):
    """print pretty banner"""
    if width is None:
        width = get_terminal_size()[0]

    swoosh = swoosh * width
    # s = pprint.pformat(obj, width=width)
    s = str(obj)
    # fill whitespace (so background props reflect for entire block of banner)
    s = '{0:{2}{1:d}}'.format(s, width, align)
    info = '\n'.join([swoosh, s, swoosh])
    info = codes.apply(info, **props)
    return info


# def rainbow(words, effects=(), **kws):
#     # try:
#     # embed()

#     propIter = _prop_dict_gen(*effects, **kws)
#     propList = list(propIter)
#     nprops = len(propList)

#     if len(words) < nprops:
#         pairIter = itt.zip_longest(words, propList, fillvalue='default')
#     else:
#         pairIter = zip(words, propList)

#     out = list(itt.starmap(codes.apply, pairIter))
    
#     #     raise SystemExit
#     # out = []
#     # for i, (word, props) in enumerate(pairIter):
#     #     word = codes.apply(word, **props)
#     #     out.append(word)

#     if isinstance(words, str):
#         return ''.join(out)

#     return out


# def _echo(_):
#     return _
#
#  NOTE: single dispatch not a good option here due to formatting subtleties
#   might be useful at some point tho...
# @ftl.singledispatch
# def formatter(obj, precision=None, short=False, **kws):
#     """default multiple dispatch func for formatting"""
#     if hasattr(obj, 'pprint'):
#         return obj.pprint()
#     return pprint.PrettyPrinter(precision=precision,
#                                 minimalist=short,
#                                 **kws).pformat
#
#
# @formatter.register(str)
# @formatter.register(np.str_)
# def _(obj, **kws):
#     return _echo
#
#
# # numbers.Integral
# @formatter.register(int)
# @formatter.register(np.int_)
# def _(obj, precision=0, short=True, **kws):
#     # FIXME: this code path is sub optimal for ints
#     # if any(precision, right_pad, left_pad):
#     return ftl.partial(pprint.decimal,
#                        precision=precision,
#                        short=short,
#                        **kws)
#
#
# # numbers.Real
# @formatter.register(float)
# @formatter.register(np.float_)
# def _(obj, precision=None, short=False, **kws):
#     return ftl.partial(pprint.decimal,
#                        precision=precision,
#                        short=short,
#                        **kws)
#
#
# def format(obj, precision=None, minimalist=False, align='<', **kws):
#     """
#     Dispatch formatter based on type of object and then format to str by
#     calling  formatter on object.
#     """
#     return formatter(obj, precision, minimalist, align, **kws)(obj)


class ConditionalFormatter(object):
    """
    A str formatter that applies ANSI codes conditionally
    """

    def __init__(self, properties, test, test_args, formatter=None, **kws):
        """

        Parameters
        ----------
        properties: str, tuple

        test: callable
            If True, apply `properties` after formatting with `formatter`
        test_args: tuple, object
            Arguments passed to the test function
        formatter: callable, optional
            The formatter to use to format the object before applying properties
        kws:
            Keywords passed to formatter
        """
        self.test = test
        if not isinstance(test_args, tuple):
            test_args = test_args,
        self.args = test_args
        self.properties = properties
        self._kws = kws
        self.formatter = formatter or format

    def __call__(self, obj):
        """
        Format the object and apply the colour / properties

        Parameters
        ----------
        obj: object
            The object to be formatted

        Returns
        -------

        """
        out = self.formatter(obj, **self._kws)
        if self.test(obj, *self.args):
            return codes.apply(out, self.properties)
        return out

# def _prop_dict_gen(*effects, **kws):
#     # if isinstance()
#
#     # from IPython import embed
#     # embed()
#
#     # deal with `effects' being list of dicts
#     props = defaultdict(list)
#     for effect in effects:
#         print('effect', effect)
#         if isinstance(effect, dict):
#             for k in ('txt', 'bg'):
#                 v = effect.get(k, None)
#                 props[k].append(v)
#         else:
#             props['txt'].append(effect)
#             props['bg'].append('default')
#
#     # deal with kws having iterable values
#     for k, v in kws.items():
#         if len(props[k]):
#             warnings.warning('Ambiguous: keyword %r. ignoring' % k)
#         else:
#             props[k].extend(v)
#
#     # generate prop dicts
#     propIter = itt.zip_longest(*props.values(), fillvalue='default')
#     for p in propIter:
#         d = dict(zip(props.keys(), p))
#         yield d
#
#
# def get_state_dicts(states, *effects, **kws):
#     propIter = _prop_dict_gen(*effects, **kws)
#     propList = list(propIter)
#     nprops = len(propList)
#     nstates = states.max()  # ptp??
#     istart = int(nstates - nprops + 1)
#     return ([{}] * istart) + propList


# def iter_props(colours, background):
#     for txt, bg in itt.zip_longest(colours, background, fillvalue='default'):
# codes.get_code_str(txt, bg=bg)
# yield tuple(codes._gen_codes(txt, bg=bg))


class Filler:
    text = 'NO MATCH'
    table = None

    def __init__(self, style):
        self.style = style

    def __str__(self):
        self.table.pre_table[0, 0] = codes.apply(self.text, self.style)
        return str(self.table)

    @classmethod
    def make(cls, table):
        cls.table = table.empty_like(1, frame=False)


class GroupTitle:
    width = None
    # formater = 'group {}'

    def __init__(self, i, keys, props):
        self.g = f'group {i}:'
        self.s = self.format_key(keys)
        # self.s = "; ".join(map('{:s} = {:s}'.format, *zip(*info.items())))
        self.props = props

    # @staticmethod
    def format_key(self, keys):
        if isinstance(keys, str):
            return keys
        return "; ".join(map(str, keys))

    def __str__(self):
        return '\n' + overlay(codes.apply(self.s, self.props),
                              self.g.ljust(self.width))
