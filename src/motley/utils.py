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
from wcwidth import wcswidth

# local
from recipes import op, string
from recipes.shell import terminal
from recipes.oo.singleton import Singleton
from recipes.containers.dicts import invert

# relative
from . import codes, formatter
from .codes import utils as ansi


ALIGNMENT_MAP = {'r': '>',
                 'l': '<',
                 'c': '^'}
ALIGNMENT_MAP_INV = invert(ALIGNMENT_MAP)


def resolve_alignment(align):
    # resolve_align  # alignment.resolve() # alignment[align]
    align = ALIGNMENT_MAP.get(align.lower()[0], align)
    if align not in '<^>.':
        raise ValueError(f'Unrecognised alignment {align!r}.')
    return align


@ftl.lru_cache()
def resolve_width(width):
    return terminal.get_size()[0] if width is None else int(width)


# @ftl.lru_cache()
def get_width(text, raw=False):
    """
    For string `text` get the maximal line width (number of characters in
    longest line).

    Parameters
    ----------
    text: str
        String, possibly multi-line, possibly containing non-display characters
        such as ANSI colour codes.
    raw: bool
        Whether to count the "hidden" non-display characters such as ANSI escape
        codes.  If True, this function returns the same result as you would get
        from `len(text)`. If False, the length of the string as it would appear
        on screen when printed is returned.

    Returns
    -------
    int
    """
    # length = ftl.partial(ansi.length, raw=count_hidden)
    # length = ansi.length_raw if raw else ansi.length_seen
    # length = ftl.partial(, length_func=length)
    text = str(text)
    if raw:
        return max(map(len,  text.split(os.linesep)))

    # get longest line for cell elements that contain newlines
    # deal with unicode combining, double width, emoji's etc..
    return max(map(wcswidth, ansi.strip(text).split(os.linesep)))


# alias
get_text_width = get_width


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

    if offsets == ():
        n0, *n_header_lines = op.AttrVector('n_head_lines', default=0)(tables)
        offsets = [n0, *np.subtract(n0, n_header_lines)]

    if isinstance(offsets, numbers.Integral):
        offsets = [0] + [offsets] * (len(tables) - 1)
    else:
        offsets = list(offsets)

    return string.hstack(tables, spacing, offsets, _width_first)


def _width_first(lines):
    return ansi.length(lines[0])


class _vstack(Singleton):  # NOTE this could just be a module...
    """
    Singleton helper class for vertical text stacking.
    """

    def __call__(self, tables, strip_titles=True, strip_headers=True, spacing=1,
                 **kws):
        """
        Vertically stack tables while aligning column widths.

        Parameters
        ----------
        tables: list of motley.table.Table
            Tables to stack vertically.
        strip_titles: bool
            Strip titles from all but the first table in the sequence.
        strip_headers: bool
            Strip column group headings and column headings from all but the
            first table in the sequence.

        Returns
        -------
        str
        """
        return self.stack(tables, strip_titles, strip_headers, spacing)

    def stack(self, tables, strip_titles=True, strip_headers=True, spacing=1, **kws):

        # check that all tables have same number of columns
        ncols = [tbl.n_cols + tbl.n_head_col for tbl in tables]
        if len(set(ncols)) != 1:
            raise ValueError(f'Cannot stack tables with unequal number of '
                             f'columns: {ncols}.')

        col_widths = np.max([tbl.col_widths for tbl in tables], 0)
        return ('\n' * (spacing + 1)).join(
            self._istack(tables, col_widths, strip_headers, strip_titles)
        ).lstrip('\n')

    def _istack(self, tables, col_widths, strip_headers, strip_titles):
        for i, table in enumerate(tables):
            yield '\n'.join(
                self.__istack(i, table, col_widths, strip_headers, strip_titles)
            )

    def __istack(self, i, table, col_widths, strip_headers, strip_titles):
        table.col_widths = col_widths  # set all column widths equal
        nnl = table.n_head_lines * bool(i and strip_headers)

        *head, r = str(table).split('\n', nnl)
        if head:
            if not strip_titles:
                yield from head[table.frame:(-table.n_head_rows or None)]
            if not strip_headers:
                yield from head[(table.frame + table.has_title):]

        yield r

    @staticmethod
    def compact(tables):
        # figure out which columns can be compactified
        # note. the same thing can probs be accomplished with table groups ...
        assert tables
        varies = set()
        ok_size = tables[0].data.shape[1]
        for i, tbl in enumerate(tables):
            if (size := tbl.data.shape[1]) != ok_size:
                raise ValueError(f'Table {i:d} has {size:d} columns while the '
                                 f'preceding {i-1:d} tables have {ok_size:d} '
                                 f'columns.')
            # check compactable
            varies |= set(tbl.compactable())

        return varies

    def from_dict(self, groups, strip_titles=False, strip_headers=True,
                  braces=False, vspace=1):
        """
        Pretty print dict of table objects.

        Parameters
        ----------
        groups : dict
            Values are `motley.table.Table`. Keys will be used to make the
            title.
        strip_titles : bool
            Whether to strip each table's title.
        braces : bool, optional
            Whether to use curly braces to mark the groups by their keys, by
            default False.
        vspace : int, optional
            Vertical space between tables in number of newlines, by default 1.

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
            return self.stack(stack, strip_titles, strip_headers, vspace)

        braces = ''
        for i, gid in enumerate(ordered_keys):
            tbl = groups[gid]
            braces += ('\n' * bool(i) +
                       vbrace(tbl.data.shape[0], gid) +
                       '\n' * (tbl.has_totals + vspace))

        # vertical offset
        offsets = stack[0].n_head_lines
        return string.hstack([self.stack(stack, strip_titles, strip_headers, vspace),
                              braces],
                             spacing=1, offsets=offsets)


# singleton
vstack = _vstack()


def justify(text, align='<', width=None):
    return string.justify(text, align, width, ansi.length, formatter.format)


def make_group_title(keys):
    if isinstance(keys, str):
        return keys

    try:
        return "; ".join(map(str, keys))
    except Exception:
        return str(keys)


def vbrace(size, name=''):
    """
    Create a multi-line right brace.

    Parameters
    ----------
    size : int
        Number of lines to span.
    name : str, optional
        Text to place on the right and vertically in center, by default ''.

    Examples
    --------
    >>> vbrace(5, 'Text!')
    '⎫\n'
    '⎪\n'
    '⎬ Text!\n'
    '⎪\n'
    '⎭\n'

    Returns
    -------
    str
        [description]


    """
    # TODO: recipes.strings.unicode.long_brace ???
    # Various other brace styles

    if size == 1:
        return '} ' + str(name)

    if size == 2:
        return ('⎱\n'       # Upper right or lower left curly bracket section
                '⎰')        # Upper left or lower right curly bracket section

    d, r = divmod(int(size) - 3, 2)
    return '\n'.join((r'⎫',             # 23AB: Right curly bracket upper hook
                      *'⎪' * d,         # 23AA Curly bracket extension
                      f'⎬ {name}',      # 23AC Right curly bracket middle piece
                      *'⎪' * (d + r),
                      r'⎭'))            # 23AD Right curly bracket lower hook


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

    Returns
    -------
    [type]
        [description]

    Raises
    ------
    NotImplementedError
        [description]
    """

    if ansi.has_ansi(background):
        raise NotImplementedError(
            '# FIXME: will not work if background has coded strings')

    align = resolve_alignment(align)

    return string.overlay(text, background, align, width)


def banner(text, width=None, align='^', fg=None, bg=None, **kws):
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
        width = terminal.get_size()[0]
    width = int(width)

    # fill whitespace (so background props reflect for entire block of banner)
    # title = f'{text: {align}{width - 2 * len(side)}}'
    width = resolve_width(width)
    # TextBox()
    return textbox(text, fg, bg, width=width, align=align,
                   **{**dict(linestyle='_', sides=False),
                      **kws})
    # return codes.apply(banner,  **props)


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

        self.align = resolve_alignment(align)

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
