# std
from curses.ascii import isspace
import numbers
import operator as op
from warnings import warn
from collections import abc
from typing import MutableMapping

# third-party
import numpy as np

# local
from recipes import api
from recipes.logging import LoggingMixin
from recipes.string.brackets import BracketParser, braces

# relative
from .. import ansi
from ..formatter import format
from .utils import align_at, apportion

# from .utils import justified_delta
# ---------------------------------------------------------------------------- #

BULLET = '⦁'  # '·'  # '\N{MIDDLE DOT}'
# — '\N{EM DASH}'

PILLAR_COLUMN_KEYS = {'pillars', 'except', 'not', 'ignore', 'keep'}
KNOWN_SUMMARY_STRINGS = {'header', 'footer', 'drop'}
# *PILLAR_COLUMN_KEYS,
#'ncols', 'n_cols',
# 'borders'

parse_fmt_opt = BracketParser('¿?')

null = object()

# defines vectorized length
# lengths = np.vectorize(len, [int])

# ---------------------------------------------------------------------------- #


def resolve(summary, table):
    # resolve: User spec for summary table:

    if not table.allow_summary():
        if summary:
            warn(f'Ignoring request to summarize with {summary!r}, since '
                 'table has no column headers, or insufficient data.')

        return -1, 0, (), {}

    # logger.debug(f'{pos = } {summary = } {keep = }')
    # logger.debug('`summary` resolved as {}. Not removing columns: {}',
    #              summary, keep)
    return _resolve(summary)  # pos, summary, kee


def _resolve(summary):
    #   loc, n_cols, pillar columns to never remove from main table, kws
    # pillars = ()
    if isinstance(summary, numbers.Integral):
        # backwards comp shortcut, assume header loc
        # loc, n_cols, pillars, kws
        return 0, summary, (), {}

    if 'drop' in summary:  # handle dict, str
        # loc, n_cols, pillars, kws
        return -1, 0, (), {}

    if isinstance(summary, str):
        if summary not in KNOWN_SUMMARY_STRINGS:
            raise ValueError('Invalid string value for `summary` parameter: '
                             f'{summary!r}. Only The following are allowed: '
                             f'{KNOWN_SUMMARY_STRINGS}')
        # loc, n_cols, pillars, kws
        return summary.startswith('foot'), None, (), {}

    if not isinstance(summary, abc.MutableMapping):
        raise TypeError('Expected `summary` parameter to be one of types '
                        f'bool, int, str or dict. Got {summary!r}, which '
                        f'is {type(summary)}.')

    # if (nope := set(summary.keys()) - KNOWN_SUMMARY_KEYS):
    #     raise ValueError(f'Invalid keys: {nope} in `summary` dict.')

    ncols = summary.pop('ncols', summary.pop('n_cols', True))
    pillars = set().union(*(summary.pop(_, ()) for _ in PILLAR_COLUMN_KEYS))
    for i, key in enumerate(('header', 'footer')):
        if key not in summary:
            continue

        kws = summary.pop(key)
        if isinstance(kws, bool):  # eg: `footer=True`
            kws = {}
        elif isinstance(kws, int):  # eg: `footer=1`
            ncols = kws
            kws = {}
        elif isinstance(kws, str):  # eg: `footer='{key}={val}'`
            kws = {'fmt': kws}
        elif isinstance(kws, MutableMapping):
            ncols = kws.pop('ncols', kws.pop('n_cols', ncols))
        else:
            raise TypeError(
                f'Expected `{key}` parameter to be one of types bool, int, '
                f'str or dict. Got {kws!r}, which is {type(kws)}.'
            )

        if summary:
            kws.update(summary)
            #warn(f'Ignoring unresolved summary info: {summary}.')

        return i, ncols, pillars, kws


def format_special(fmt, *args, **kws):
    for opt in parse_fmt_opt.iterate(fmt):
        key = braces.match(opt.enclosed).enclosed
        if kws.pop(key, '') != '':
            fmt = fmt.replace(opt.full, '')

    return format(fmt, *args, **kws)


def _stack_keyval_pairs(items, ncols):
    n_items = len(items)
    # n items per column
    n_per_col = (n_items // ncols) + bool(n_items % ncols)
    # pad
    items.extend([('', '')] * (n_per_col * ncols - n_items))
    data = np.hstack(np.reshape(items, (ncols, n_per_col, 2)))
    return np.atleast_2d(data.squeeze())


def bulleted(string, bullet, space):
    return string if string.isspace() else f'{bullet}{" " * int(space)}{string}'


class SummaryTable(LoggingMixin):

    LOCATIONS = dict(enumerate(('drop', 'header', 'footer'), -1))
    # LOCATIONS[False] = 'ignore'

    @classmethod
    def from_table_api(cls, table, summary):
        if summary and (len(table.data) <= 1 or not table.has_col_head):
            msg = ("no column headers provided",
                   "table contains only a single row of data")[table.has_col_head] 
            cls.logger.warning(f'Requested `summary` representation, but {msg}.'
                               ' Ignoring.')
            return cls(table, False)

        *args, kws = _resolve(summary)
        return cls(table, *args, **kws)

    @api.synonyms(
        {'n_?cols?': 'ncols',
         'bullets?': 'bullet'},
        action=None
    )
    def __init__(self, table, loc=0, ncols=None, ignore=(), bullet=BULLET,
                 fmt='{key: <|B} = {{val}¿ [{unit}]?: <}', whitespace=2, **kws):
        """
        Check which columns contain single unique value duplicated. These data
        are represented as a sub-header in the table.  This makes for a more
        summary representation of the same data.

        Parameters
        ----------
        data
        col_headers`

        Returns
        -------

        """
        # logger.debug('{}')
        self.table = table
        self.ncols = ncols
        self.fmt = fmt
        self.bullet = str(bullet or '')
        self.whitespace = int(whitespace)
        self.kws = kws
        if 'borders' in kws:
            raise NotImplementedError

        data = table.data
        if loc is False or ncols is False:
            self.items = {}
            self.index_shown = np.arange(table.ncols + table.n_head_col)
            self.loc = -1
            return

        # if a total is asked for on a column, make sure we don't suppress it
        has_total = [] if table.totals is None else np.nonzero(table.totals)[0]
        idx_squash = np.setdiff1d(self.possible(ignore), has_total)
        val_squash = data[0, idx_squash]

        idx_show = np.setdiff1d(range(data.shape[1]), idx_squash)
        idx_show = np.r_[np.arange(table.n_head_col), idx_show + table.n_head_col]
        # check if any data left to display
        if idx_show.size == 0:
            self.logger.warning('No data left in table after summarizing '
                                'singular value columns.')

        # get summarized items. columns for which all data identical
        items = op.itemgetter(*idx_squash)(
            list(zip(table.col_headers, table.units))
        )
        if len(idx_squash) == 1:
            items = [items]

        headers, units = zip(*items)
        self.items = dict(zip(headers, zip(val_squash, units)))
        self.index_shown = idx_show
        self.loc = int(loc)

        # n_items = len(self.items)  # number of summary columns
        # table_width = self.get_width()  # excludes lhs border

        self.auto_ncols = (
            # number of compact columns unspecified
            ((ncols is None) or (ncols is True)) or
            # user specified too many compact columns
            ((ncols is not None) and (ncols > len(self.items)))
        )

    def __bool__(self):
        return bool((self.loc != -1) and self.items)

    @property
    def index_inset(self):
        tbl = self.table
        n = tbl.data.shape[1] + tbl.n_head_col
        return np.setdiff1d(np.arange(n), self.index_shown)

    def allowed(self):
        return self.table.allow_summary()

    def possible(self, ignore=()):
        if not self.allowed():
            return ()

        data = self.table.data
        idx_same, = np.where(np.all(data == data[0], 0))
        idx_ign = []
        if any(ignore):
            *_, idx_ign = np.where(self.table.col_headers == np.atleast_2d(ignore).T)

        # idx_same = np.setdiff1d(idx_same, idx_ign)  # + self.n_head_col
        return np.setdiff1d(idx_same, idx_ign)

    # def _default_format(self, key, val, unit):
    #     return format('{key: <{width}|B} = {val}' + (' [{unit}]' * bool(unit)),
    #                   **locals())

    def __call__(self, fmt=None, align_equal=True):
        # justify=True, bullet=BULLET,

        from motley.table import Table

        fmt = fmt or self.fmt
        kws = {**dict(frame=False,
                      align='^'),
               **self.kws}

        # summary_items
        cells = [format_special(fmt, key=key, val=val, unit=unit)
                 for key, (val, unit) in self.items.items()]
        widths = np.vectorize(ansi.length, [int])(cells) + self.whitespace
        # NOTE widths without cell borders

        ncols = self._auto_ncols(widths) if self.auto_ncols else int(self.ncols)

        lb = ansi.length(self.bullet)

        # handle single row summary
        if ncols == (n_items := len(cells)):
            borders = ['', *([self.bullet] * (ncols - 1)), '']
            # justify: Add space to columns. Passing column widths to Table API
            # assumes borders not included
            avail_space = self.table.get_width(frame=False) - sum(widths) - lb * ncols
            delta = apportion(avail_space, ncols)
            return Table(cells, borders=borders, width=np.add(widths, delta),
                         **kws)

        # If we are here, there are multiple rows in the summary table
        if leftover := (n_items % ncols):
            cells.extend([''] * leftover)
            widths = np.r_[widths, np.zeros(leftover, int)]

        rows = np.reshape(cells, (-1, ncols))
        widths = widths.reshape((-1, ncols)).max(0)

        # align equal
        if align_equal:
            rows = np.transpose([align_at(col, '=') for col in rows.T])

        # justify
        avail_space = self.table.get_width(frame=False) - sum(widths) - lb * ncols
        delta = apportion(avail_space, ncols)
        space = 2
        if self.bullet and all(delta > space):
            rows = np.vectorize(bulleted, [str])(rows, self.bullet, space)
            # borders = [*([f'{self.bullet}  '] * ncols), '']
            widths -= 2

        return Table(rows, borders='', width=np.add(widths, delta), **kws)

    def _auto_ncols(self, widths):
        # decide how many columns the inset table will have
        # ncols chosen to be as large as possible given table width
        # this leads to most summary repr
        self.logger.debug('Computing optimal number of columns for summary table.')

        # format: width=0 for narrowest width possible
        # data = [format(fmt, key=key, val=val, unit=unit, width=0)
        #             for key, (val, unit) in self.items.items()]
        # widths = np.vectorize(ansi.length, int)(data)

        # number of summary columns
        n_items = len(self.items)
        table_width = self.table.get_width()  # excludes lhs border
        max_column_width = max(widths)
        # extra = self.table.lcb[self.index_inset] + self.table.cell_white
        if max_column_width >= table_width:
            return 1

        #
        lb = ansi.length(self.bullet)
        start = min(max(n_items // 2, 1), table_width // max_column_width)
        end = max(round(n_items / 2), start) + 1
        trials = [*range(start, end), n_items]
        for i, ncols in enumerate(trials):
            nc, lo = divmod(n_items, ncols)
            pad = (nc + bool(lo)) * ncols - n_items
            ccw = np.hstack([widths, [0] * pad]).reshape(ncols, -1).max(1) + lb

            # + extra for column border + cell_white
            if sum(ccw) > table_width:
                if np.any(ccw == 0):
                    continue

                ncols = trials[i - 1]
                break

        return ncols
