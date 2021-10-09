"""
Utility functions and classes.
"""


# std
import os
import numbers
import functools as ftl
from collections import abc

# third-party
import numpy as np

# local
from recipes.misc import get_terminal_size
from recipes.string import hstack as string_hstack

# relative
from . import codes, ansi


ALIGNMENT_MAP = {'r': '>',
                 'l': '<',
                 'c': '^'}


def get_alignment(align):
    # resolve_align  # alignment.resolve() # alignment[align]
    align = ALIGNMENT_MAP.get(align.lower()[0], align)
    if align not in '<^>':
        raise ValueError('Unrecognised alignment {!r}'.format(align))
    return align


def hstack(tables, spacing=0, offsets=0):
    """
    Stick two or more tables (or multi-line strings) together horizontally.

    Parameters
    ----------
    tables
    spacing : int
        Number of horizontal spaces to be added as a column between the string
        blocks.
    offset : Sequence of int
        Vertical offsets in number of rows between string blocks.


    Returns
    -------
    str
        Horizontally stacked string
    """
    tables = list(filter(None, tables))
    assert tables, '`tables` must be non-empty sequence'

    if len(tables) == 1:
        return str(tables[0])

    #

    if offsets == ():
        n0, *n_header_lines = op.AttrVector('n_head_lines', default=0)(tables)
        offsets = [n0, *np.subtract(n0, n_header_lines)]

    if isinstance(offsets, numbers.Integral):
        offsets = [0] + [offsets] * (len(tables) - 1)
    else:
        offsets = list(offsets)

    return string_hstack(tables, spacing, offsets, _width_first)


def _width_first(lines):
    return ansi.length_seen(lines[0])


def vstack(tables, strip_titles=True, strip_headers=True, spacing=1):
    """
    Vertically stack tables while aligning column widths.

    Parameters
    ----------
    tables: list of motley.table.Table
        Tables to stack vertically.
    strip_titles: bool
        Strip titles from all but the first table in the sequence.
    strip_headers: bool
        Strip column group headings and column headings from all but the first
        table in the sequence.

    Returns
    -------
    str
    """
    # check that all tables have same number of columns
    ncols = [tbl.shape[1] for tbl in tables]
    if len(set(ncols)) != 1:
        raise ValueError(
            f'Cannot stack tables with unequal number of columns: {ncols}.'
        )

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
    assert tables
    varies = set()
    ok_size = tables[0].data.shape[1]
    for i, tbl in enumerate(tables):
        size = tbl.data.shape[1]
        if size != ok_size:
            raise ValueError(
                'Table %d has %d columns while the preceding %d tables have %d '
                'columns.' % (i, size, i - 1, ok_size)
            )
        # check compactable
        varies |= set(tbl.compactable())

    return varies


def make_group_title(keys):
    if isinstance(keys, str):
        return keys

    try:
        return "; ".join(map(str, keys))
    except:
        return str(keys)


def vstack_groups(groups, strip_titles, braces=False, vspace=1, **kws):
    """
    Pretty print dict of table objects.

    Parameters
    ----------
    groups : dict
        Keys are `motley.table.Tables`.
    strip_titles : bool
        Whether to strip table titles.
    braces : bool, optional
        Whether to use curly braces to mark the groups by their keys, by default
        False
    vspace : int, optional
        Vertical space between tables in number of newlines, by default 1

    Returns
    -------
    str
        The formatted stack of tables.
    """

    # ΤΟDO: could accomplish the same effect by colour coding...
    groups = dict(groups)
    ordered_keys = list(groups.keys())  # key=sort
    stack = [groups[key] for key in ordered_keys]

    if not braces:
        return vstack(stack, strip_titles, True, vspace)

    braces = ''
    for i, gid in enumerate(ordered_keys):
        tbl = groups[gid]
        braces += ('\n' * bool(i) +
                   hbrace(tbl.data.shape[0], gid) +
                   '\n' * (tbl.has_totals + vspace))

    # vertical offset
    offsets = stack[0].n_head_lines
    return string_hstack([vstack(stack, True, vspace), braces],
                         spacing=1, offsets=offsets)


def hbrace(size, name=''):
    #
    if size < 3:
        return '← ' + str(name) + '\n' * (int(size) // 2)

    d, r = divmod(int(size) - 3, 2)
    return '\n'.join(['⎫'] +
                     ['⎪'] * d +
                     ['⎬ {!s}'.format(name)] +
                     ['⎪'] * (d + r) +
                     ['⎭'])


def overlay(text, background='', align='^', width=None):
    """
    Overlay `text` on `background` string using given alignment at a given
    width.

    Parameters
    ----------
    text : [type]
        [description]
    background : str, optional
        [description], by default ''
    align : str, optional
        [description], by default '^'
    width : [type], optional
        [description], by default None

    Examples
    --------
    >>> 

    Returns
    -------
    [type]
        [description]

    Raises
    ------
    NotImplementedError
        [description]
    """

    # TODO: can you acheive this with some clever use of fstrings?
    # {line!s: {align}{width}}

    if not (background or width):
        # nothing to align on
        return text

    text_size = ansi.length_seen(text)
    bg_size = ansi.length_seen(background)
    if not background:
        # align on clear background
        background = ' ' * width
    elif not width:
        # keep width of background text
        width = bg_size

    if bg_size < text_size:
        # background will be clobbered. Alignment is pointless.
        return text

    if ansi.has_ansi(background):
        raise NotImplementedError(
            '# FIXME: will not work if background has coded strings')

    # resolve alignment character
    align = get_alignment(align)

    # center aligned
    if align == '^':
        div, mod = divmod(text_size, 2)
        half_width = width // 2
        # start and end indices of the text in the center of the background
        # center text on background
        return ''.join((background[:(half_width - div)],
                        text,
                        background[(half_width + div + mod):]))

    # left aligned
    if align == '<':
        return text + background[text_size:]

     # right aligned
    if align == '>':
        return background[:-text_size] + text


# @ftl.lru_cache()
def get_width(text, count_hidden=False):
    """
    For string `text` get the maximal line width in number of characters.

    Parameters
    ----------
    text: str
        String, possibly multi-line, possibly containing non-display characters
        such as ANSI colour codes.
    count_hidden: bool
        Whether to count the "hidden" non-display characters such as ANSI escape
        codes.  If True, this function returns the same result as you would get
        from `len(text)`. If False, the length of the string as it would appear
        on screen when printed is returned.

    Returns
    -------
    int
    """
    length = ftl.partial(ansi.length, raw=count_hidden)
    # deal with cell elements that contain newlines
    return max(map(length, text.split(os.linesep)))


def banner(text, width=None, align='^', color=None, **kws):
    """
    print pretty banner

    Parameters
    ----------
    obj : [type]
        [description]
    width : [type], optional
        [description], by default None
    swoosh : str, optional
        [description], by default '='
    middle : str, optional
        [description], by default ''
    align : str, optional
        [description], by default '<'

    Examples
    --------
    >>> 

    Returns
    -------
    [type]
        [description]
    """

    from .textbox import textbox

    if width is None:
        width = get_terminal_size()[0]
    width = int(width)

    # fill whitespace (so background props reflect for entire block of banner)
    # title = f'{text: {align}{width - 2 * len(side)}}'
    width = resolve_width(width)
    # TextBox()
    return textbox(text, sides=False, width=width, align=align, color=color,
                   **kws)
    # return codes.apply(banner,  **props)


@ftl.lru_cache()
def resolve_width(width):
    if width is None:
        return get_terminal_size()[0]
    return int(width)


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


class ConditionalFormatter:
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
    template = 'group {}: '

    def __init__(self, i, keys, props, align='^'):
        self.g = self.template.format(i)
        self.s = codes.apply(self.format_key(keys), props)
        # self.props = props

        self.align = get_alignment(align)

    @staticmethod
    def format_key(keys):
        if isinstance(keys, str):
            return keys
        if isinstance(keys, abc.Collection):
            return "; ".join(map(str, keys))
        return str(keys)

    def __str__(self):
        if self.align == '<':
            return (self.g + self.s).ljust(self.width)

        return '\n' + overlay(self.s,
                              self.g.ljust(self.width),
                              self.align)
