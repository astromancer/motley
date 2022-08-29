# std
import re
import numbers
import operator as op
import warnings as wrn
import itertools as itt
from collections import abc

# third-party
import numpy as np
import more_itertools as mit

# local
from recipes.logging import LoggingMixin
from recipes.string.brackets import BracketParser, braces

# relative
from ..formatter import format, RGX_FMT_SPEC_BASE
from .. import ansi
# from .utils import justified_delta

STICKY_COLUMN_KEYS = {'except', 'not'}
KNOWN_SUMMARY_KEYS = {'header', 'footer', 'drop'} | STICKY_COLUMN_KEYS

RGX_FMT_SPEC = re.compile(RGX_FMT_SPEC_BASE.replace('(?x)', '(?x):'))

parse_fmt_opt = BracketParser('¿?')

# defines vectorized length
# lengths = np.vectorize(len, [int])


def resolve(summary, table):
    # resolve: User spec for summary table:
    #   ncols, loc, columns to keep/ignore, kws
    if not table.allow_summary():
        if summary:
            wrn.warn(f'Ignoring request to summarize with {summary!r}, since '
                     'table has no column headers, or insufficient data.')

        return -1, 0, (), {}

    # logger.debug(f'{pos = } {summary = } {keep = }')
    # logger.debug('`summary` resolved as {}. Not removing columns: {}',
    #              summary, keep)
    return _resolve(summary)  # pos, summary, kee


def _resolve(summary):

    keep = ()
    if isinstance(summary, numbers.Integral):
        # backwards comp shortcut, assume header loc
        return 0, summary, keep, {}

    if 'drop' in summary:  # handle dict, str
        return -1, 0, keep, {}

    if isinstance(summary, abc.MutableMapping):
        if (nope := set(summary.keys()) - KNOWN_SUMMARY_KEYS):
            raise ValueError(f'Invalid keys: {nope} in `summary` dict.')

        ncols = summary.pop('n_cols', True)
        keep = set().union(*(summary.pop(_, ()) for _ in STICKY_COLUMN_KEYS))
        for i, key in enumerate(('header', 'footer')):
            if key in summary:
                kws = summary.pop(key)
                if summary:
                    wrn.warn(f'Ignoring unresolved summary info: {summary}.')
                return i, ncols, keep, kws

    if isinstance(summary, str):
        if summary not in (KNOWN_SUMMARY_KEYS - STICKY_COLUMN_KEYS):
            raise ValueError('Invalid string value for `summary` parameter: '
                             f'{summary!r}')

        return summary.startswith('foot'), None, keep, {}

    raise ValueError('Expected `summary` parameter to be one of types '
                     f'bool, int, str or dict. Got {summary!r}, which '
                     f'is {type(summary)}.')


def format_special(fmt, *args, **kws):
    for opt in parse_fmt_opt.iterate(fmt):
        key = braces.match(opt.enclosed).enclosed
        if kws.pop(key, '') == '':
            fmt = fmt.replace(opt.full, '')

    return format(fmt, *args, **kws)


def _stack_keyval_pairs(items, n_cols):
    n_items = len(items)
    # n items per column
    n_per_col = (n_items // n_cols) + bool(n_items % n_cols)
    # pad
    items.extend([('', '')] * (n_per_col * n_cols - n_items))
    data = np.hstack(np.reshape(items, (n_cols, n_per_col, 2)))
    return np.atleast_2d(data.squeeze())


class SummaryTable(LoggingMixin):

    LOCATIONS = dict(enumerate(('drop', 'header', 'footer'), -1))
    # LOCATIONS[False] = 'ignore'

    @classmethod
    def from_table_api(cls, table, summary):
        if summary and (len(table.data) <= 1) or not table.has_col_head:
            cls.logger.warning(
                'Requested `summary` representation, but no column headers '
                'provided. Ignoring.'
            )
            return cls(table, False)

        *args, kws = _resolve(summary)
        return cls(table, *args, **kws)

    def __init__(self, table, loc=0, ncols=None, ignore=(),
                 fmt=' {key: >|B} = {{val}¿ [{unit}]?: <}', **kws):
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
        self.fmt, self.kws = fmt, kws
        # columns for which all data identical
        # end = -1 if self.has_totals else None
        data = table.data
        if loc is False:
            self.items = {}
            self.index_shown = np.arange(table.n_cols + table.has_row_head + table.has_row_nrs)
            self.loc = -1
            return

        # if a total is asked for on a column, make sure we don't suppress it
        idx_squash = np.setdiff1d(self.possible(ignore), np.nonzero(table.totals)[0])
        val_squash = data[0, idx_squash]
        idx_show = np.setdiff1d(range(data.shape[1]), idx_squash)
        idx_show = np.r_[np.arange(table.n_head_col), idx_show + table.n_head_col]
        # check if any data left to display
        if idx_show.size == 0:
            self.logger.warning('No data left in table after summarizing '
                                'singular value columns.')

        # get summarized items
        headers, units = zip(*op.itemgetter(*idx_squash)(
            list(zip(table.col_headers, table.units))
        ))

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

    def __call__(self, fmt=None, justify=True, borders=None):

        from motley.table import Table

        # summary_items = list(self.items.items())
        fmt = fmt or self.fmt
        km, vm = (braces.match(fmt, condition=lambda m: (_ in m.enclosed),
                               inside_out=True) for _ in ('key', 'val'))
        assert km and vm
        fmt_key, fmt_val = km.full, vm.full
        equal = fmt[km.end + 1:vm.start]

        summary_items = [(format(fmt_key, key=key),
                          format_special(fmt_val, val=val, unit=unit))
                         for key, (val, unit) in self.items.items()]

        _2widths = np.vectorize(ansi.length_seen, [int])(summary_items)
        widths = (_2widths.sum(1) + ansi.length_seen(equal)
                  + self.table.lcb[self.index_inset] + self.table.cell_white)

        n_cols = self._auto_ncols(widths) if self.auto_ncols else int(self.n_cols)
        rows = _stack_keyval_pairs(summary_items, n_cols)

        # add borders to width
        borders = borders or self.table.borders[self.index_inset]
        borders = list(mit.interleave(itt.repeat(equal), borders))
        #

        left_alight = mo['align'] if (mo := RGX_FMT_SPEC.search(fmt_key)) else '>'
        right_alight = mo['align'] if (mo := RGX_FMT_SPEC.search(fmt_val)) else '<'

        # , '<'

        # # justified spacing
        # if justify:
        #     _2widths.reshape((-1, n_cols, 2)).max(0).reshape(-1, n_cols * 2)

        #     deltas = justified_delta(widths.reshape(-1, n_cols).max(0),
        #                              self.table.get_width())
        #     if np.any(widths[1::2] <= -deltas):
        #         wrn.warn('Column justification lead to zero/negative column '
        #                  'widths. Ignoring!')
        #     else:
        #         widths[1::2] += deltas

        # print(data.shape)

        # TODO row_head_props=self.col_head_props,
        # col_borders = [equal, self._default_border] * n_cols
        borders[-1] = ''

        return Table(rows, frame=False, col_borders=borders,
                     align=[left_alight, right_alight] * n_cols,
                     width=self.table.get_width(), too_wide=False, **self.kws)

    def _auto_ncols(self, widths):
        # decide how many columns the inset table will have
        # n_cols chosen to be as large as possible given table width
        # this leads to most summary repr
        self.logger.debug('Computing optimal number of columns for summary table.')

        # format: width=0 for narrowest width possible
        # data = [format(fmt, key=key, val=val, unit=unit, width=0)
        #             for key, (val, unit) in self.items.items()]
        # widths = np.vectorize(ansi.length_seen, int)(data)

        # number of summary columns
        n_items = len(self.items)
        table_width = self.table.get_width()  # excludes lhs border
        # extra = self.table.lcb[self.index_inset] + self.table.cell_white
        if max(widths) >= table_width:
            return 1

        # extra = 3  # len(self._default_border) + self.cell_white
        trials = range(table_width // max(widths), round(n_items / 2) + 1)
        trials = [*trials, n_items]
        for i, n_cols in enumerate(trials):
            nc, lo = divmod(n_items, n_cols)
            pad = (nc + bool(lo)) * n_cols - n_items
            ccw = np.hstack([widths, [0] * pad]
                            ).reshape(n_cols, -1).max(1)

            # + extra for column border + cell_white
            if sum(ccw) > table_width:
                if np.any(ccw == 0):
                    continue

                n_cols = trials[i - 1]
                break

        return n_cols
