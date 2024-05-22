"""
Construct tables from sequences of objects and lists of attributes.
"""

# std
import functools as ftl
import itertools as itt
from collections import abc, defaultdict

# third-party
import numpy as np

# local
from recipes.containers.sets import OrderedSet
from pyxides.grouping import Grouped
from pyxides.vectorize import AttrTableMixin

# relative
from ..utils import make_group_title, resolve_alignment
from .table import Table
from .column import Column


# ---------------------------------------------------------------------------- #
SENTINEL = object()

# ---------------------------------------------------------------------------- #


class AttrColumn(Column):
    def __init__(self, title=None, unit=None, convert=None, fmt=None, align=None,
                 total=False, group=None, formatter=None, flags=None, flag_info=None):
        """
        _summary_

        Parameters
        ----------
        title : _type_, optional
            _description_, by default None
        unit : _type_, optional
            _description_, by default None
        convert : _type_, optional
            _description_, by default None
        fmt : _type_, optional
            _description_, by default None
        align : str, optional
            _description_, by default '<'
        total : bool, optional
            _description_, by default False
        group : _type_, optional
            _description_, by default None
        formatter : _type_, optional
            _description_, by default None
        flags : list or callable, optional
            A function that recives the target object for attribute lookup and
            returns a symbol (str) to append to the formatted value (returned by
            formatter).
        flag_info: dict
            Info describing any possible flags. This is used to automatically
            construct footnotes for the table.

        Examples
        --------
        >>> 
        """

        # TODO: fmt = '. 14.5?f|gBi_/teal'
        self.title = title
        # self.data = np.atleast_1d(np.asanyarray(data, 'O').squeeze())
        # assert self.data.ndim == 1
        # self.dtypes = set(map(type, np.ma.compressed(self.data)))
        self.unit = unit
        self.align = resolve_alignment(align) if align else None
        # self.width = width
        self.total = bool(total)  # self.data.sum() if total else None

        # if fmt is None:
        #     fmt = self.get_default_formatter()
        # assert callable(fmt)
        self.convert = convert
        self.fmt = fmt
        self.flags = flags
        self.flag_info = flag_info


class AttrTable:
    """
    Helper class for tabulating attributes (or properties) of lists of objects.
    Attributes of the objects in the container are mapped to the columns of the
    table.
    """

    @classmethod
    def from_columns(cls, mapping=(), **kws):
        mapping = dict(mapping)

        column_to_table = {
            'title':     'headers',
            'unit':      'units',
            'convert':   'converters',
            'fmt':       'formatters',
            'align':     'alignment',
            'flags':     'flags',
            # 'flag_info': 'footnotes'
        }
        options = defaultdict(dict)
        totals = []
        for attr, col in mapping.items():
            if col in (..., ''):
                continue

            # assert isinstance(col, AttrColumn)

            # populate the headers, units, converters, formatters
            for key, opt in column_to_table.items():
                if (val := getattr(col, key)):
                    options[opt][attr] = val

            # col_opts = map(vars(col).get, column_to_table.keys())
            # for val, key in zip(*cofilter(col_opts, column_to_table.values())):
            #     options[key][attr] = val

            if col.total:
                totals.append(attr)

        obj = cls(mapping.keys(), totals=totals, **options, **kws)
        obj._columns = mapping
        return obj

    def _ensure_dict(self, obj):
        if obj is None:
            return {}

        if isinstance(obj, dict):
            return obj

        return dict(zip(self.attrs, obj))

    def __new__(cls, attrs, *args, **kws):

        if isinstance(attrs, dict):
            return cls.from_dict(attrs)

        return super().__new__(cls)

    def __get__(self, instance, kls):
        if instance:  # lookup from instance
            self.target = instance
        return self  # lookup from class

    def __init__(self,
                 attrs,
                 headers=None,
                 converters=None,
                 formatters=None,
                 alignment=(),
                 units=None,
                 header_levels=None,
                 #  header_formatter=str, # NOPE. breaks column alias resolution
                 show_groups=True,
                 totals=(),
                 flags=(),
                 footnotes=(),
                 **kws):

        # set default options for table
        self.kws = {**dict(precision=5,
                           minimalist=True,
                           summary=True),
                    **kws}

        self.title = self.kws.get('title')
        self.attrs = list(attrs)
        # FIXME: better to have a list of columns here.
        self.converters = self._ensure_dict(converters)
        self.formatters = self._ensure_dict(formatters)
        self.header_levels = self._ensure_dict(header_levels)
        # TODO: remove `header_levels` in favour of ..timing.t0 / timing.t0..  ?
        # self.header_formatter = header_formatter
        self.headers = self._ensure_dict(headers)
        self.units = self._ensure_dict(units)
        totals = [totals] if isinstance(totals, str) else list(totals)
        self.totals = [self.get_header(attr) for attr in totals]
        self.align = {self.get_header(attr): val
                      for attr, val in self._ensure_dict(alignment).items()}
        self.show_groups = bool(show_groups)
        self.flags = {self.get_header(attr): flag
                      for attr, flag in self._ensure_dict(flags).items()}
        if isinstance(footnotes, dict):
            footnotes = {self.get_header(attr): val
                         for attr, val in footnotes.items()}

        self.footnotes = footnotes

        # self.headers = dict(zip(attrs, self.get_headers(attrs)))
        # self._heads = {a: self.get_header_parts(a) for a in self.attrs}
        self.target = None

    def __call__(self, attrs=None, container=None, **kws):
        """
        Print the table of attributes for this container as a table.

        Parameters
        ----------
        attrs: array_like, optional
            Attributes of the instance that will be printed in the table.
            defaults to the list given upon initialization of the class.
        **kws:
            Keyword arguments passed directly to the `motley.table.Table`
            constructor.

        Returns
        -------

        """

        container = container or self.target

        if isinstance(container, Grouped):
            return self.get_tables(container, attrs, **kws)

        if isinstance(container, AttrTableMixin):
            return self.get_table(container, attrs, **kws)

        raise TypeError(f'Cannot tabulate object of type {type(container)}.')

    def get_defaults(self, attrs, which):
        defaults = getattr(self, which)
        out = {}
        for attr in attrs:
            header = self.get_header(attr)
            use = defaults.get(attr, defaults.get(header, SENTINEL))
            if use is not SENTINEL:
                out[header] = use
        return out

    @ftl.lru_cache()
    def _get_header_parts(self, attr):
        base, *rest = attr.split('.')
        group = base if rest else ''
        if attr in self.headers:
            header = self.headers[attr]
        else:
            header = rest[-1] if group else base

        #
        unit = self.units.get(attr, '')

        # shift levels if needed
        if level := self.header_levels.get(base, 0):
            group, header, unit = [''] * level + [group, header, unit][:-level]
            return group, header, f'[{unit}]'

        return group, header, unit

    def get_group(self, attr):
        return self._get_header_parts(attr)[0]

    def get_header(self, attr):
        return self._get_header_parts(attr)[1]

    def get_unit(self, attr):
        return self._get_header_parts(attr)[-1]

    def get_groups(self, attrs=None):
        if self.show_groups:
            return [self.get_group(_) for _ in (attrs or self.attrs)]
        return []

    def get_headers(self, obj=None):
        # ok = set(map(self.headers.get, kws)) - {None}
        if obj is None:
            obj = self.attrs

        if isinstance(obj, dict):
            return {self.get_header(k): v for k, v in obj.items()}

        elif isinstance(obj, abc.Collection):
            return list(map(self.get_header, obj))

        raise TypeError(f'Cannot get headers from object type: {type(obj)}.'
                        ' Expected a Collection.')

    def get_units(self, attrs=None):
        return [self.get_unit(_) for _ in (attrs or self.attrs)]

    def add_attr(self, attr, column_header=None, formatter=None):

        if not isinstance(attr, str):
            raise ValueError('Attribute must be a str')

        # block below will bork with empty containers
        # obj = self.target[0]
        # if not hasattr(obj, attr):
        #     raise ValueError('%r is not a valid attribute of object of '
        #                      'type %r' % (attr, obj.__class__.__name__))

        # avoid duplication
        if attr not in self.attrs:
            self.attrs.append(attr)

        if column_header is not None:
            self.headers[attr] = column_header

        if formatter is not None:
            self.formatters[column_header] = formatter

    def get_data(self, container=None, attrs=None, converters=None):
        if container is None:
            container = self.target

        if len(container) == 0:
            return []

        if attrs is None:
            attrs = self.attrs

        values = container.attrs(*attrs)
        converters = converters or self.converters
        if not converters:
            return values

        tmp = dict(zip(attrs, zip(*values)))
        for key, convert in converters.items():
            if key in tmp:
                tmp[key] = list(map(convert, tmp[key]))

        return list(zip(*tmp.values()))

    def get_table(self, container, attrs=None, **kws):
        """
        Keyword arguments passed directly to the `motley.table.Table`
        constructor.

        Returns
        -------
        motley.table.Table
        """

        if not isinstance(container, AttrTableMixin):
            raise TypeError(f'Object of type {type(container)} does not '
                            f'support vectorized attribute lookup on items.')

        if len(container) == 0:
            return Table(['Empty'])

        if attrs is None:
            attrs = self.attrs
        # elif isinstance(MutableMapping)

        # get data
        data = self.get_data(container, attrs)

        # get column headers
        config = self._get_config(attrs, **kws)
        (*_, colnames) = zip(*config['col_headers'])
        flags = {colname: list(map(flag, container) if callable(flag) else flag)
                 for colname, flag in self.flags.items() if colname in colnames}

        return Table(data,
                     # keywords from user input
                     **{**config, 'flags': flags, **kws})

    def summarize(self, summary, **kws):
        """
        Keyword arguments passed directly to the `motley.table.Table`
        constructor.

        Returns
        -------
        motley.table.Table
        """

        groups = self.target
        if not isinstance(groups, Grouped):
            raise TypeError(f'Object of type {type(groups).__name__} does not '
                            f'support vectorized attribute lookup on items.')

        # get data
        data = groups.attrs.summarize(summary)
        attrs = tuple(summary.keys())
        # nfiles = list(map(len, groups.values()))

        config = self._get_config(attrs,
                                  **{'title': f'{self.target.__class__.__name__} summary',
                                     **kws})
        return Table(data, **config)

    def _get_config(self, attrs, **kws):
        # get column headers
        headers = [self.get_groups(attrs), self.get_headers(attrs)]
        headers = (*_, colnames) = list(filter(None, headers))
        # flags = {colname: list(map(flag, container) if callable(flag) else flag)
        #          for colname, flag in self.flags.items() if colname in colnames}
        align = {k: v for k, v in self.align.items() if k in headers}

        return {**self.kws,  # defaults
                **{**dict(title=f'{self.target.__class__.__name__}',
                          align=align,
                          col_headers=headers,
                          totals=self.totals,
                          #   flags=flags,
                          footnotes=self.footnotes),
                   **{key: self.get_defaults(attrs, key)
                      for key in ('units', 'formatters')},
                   **kws},  # keywords from user input
                }

    def to_xlsx(self, path, sheet=None, formats=(), widths=None, align=None,
                overwrite=False, **kws):

        if widths is None:
            widths = {}

        # may need to set widths manually eg. for cells that contain formulae
        # tmp.col_widths = get_col_widths(tmp) if widths is None else widths

        table = self.get_table(self.target)
        align = {**self.align, **(align or {})}
        formats = dict(formats)
        table.to_xlsx(path, sheet, overwrite=overwrite, formats=formats,
                    widths=widths, align=align, **kws)

    def to_latex(self, style='table', indent=2, **kws):
        # self.tabulate.parent = self.parent
        tbl = self.get_table(self.target, title=False, col_groups=None, **kws)
        tbl.to_latex(style='table', indent=2, **kws)

    def prepare(self, groups, attrs, **kws):
        # class GroupedTables:

        attrs = OrderedSet(attrs or self.attrs)
        attrs_grouped_by = ()
        compactable = set()
        # multiple = (len(self) > 1)
        if len(groups) > 1:
            if groups.group_id != ((), {}):
                keys, _ = groups.group_id
                key_types = {gid: list(grp)
                             for gid, grp in itt.groupby(keys, type)}
                attrs_grouped_by = key_types.get(str, ())
                attrs -= set(attrs_grouped_by)

            # check which columns are compactable
            attrs_varies = {key for key in attrs if groups.varies_by(key)}
            compactable = attrs - attrs_varies
            attrs -= compactable

        # column headers
        headers = self.get_headers(attrs)

        # handle column totals
        totals = self.totals  # kws.pop('totals', self.kws['totals'])
        if totals:
            # don't print totals for columns used for grouping since they will
            # not be displayed
            totals = list(set(totals) - set(attrs_grouped_by) - compactable)
            # convert totals to numeric since we remove column headers for
            # lower tables
            totals = list(map(headers.index, self.get_headers(totals)))

        units = self.units  # kws.pop('units', self.units)
        if units:
            want_units = set(units.keys())
            nope = set(units.keys()) - set(headers)
            units = {k: units[k] for k in (want_units - nope - compactable)}

        return attrs, compactable, headers, units, totals

    def get_tables(self, groups, attrs=None, titled=True, filler_text='EMPTY',
                   grand_total=None, **kws):
        """
        Get a dictionary of tables (`motley.table.Table` objects) for the
        containers in `groups`. This method assists working with groups of
        tables.
        """

        title = kws.pop('title', self.__class__.__name__)
        ncc = kws.pop('summary', False)  # number of columns in summary part
        kws['summary'] = False

        if titled is True:
            titled = make_group_title

        attrs, compactable, headers, units, totals = self.prepare(groups, attrs)
        grand_total = grand_total or totals

        tables = {}
        empty = []
        footnotes = OrderedSet()
        for gid, group in groups.items():
            if group is None:
                empty.append(gid)
                continue

            # get table
            if titled:
                # FIXME: problem with dynamically formatted group title.
                # Table wants to know width at runtime....
                title = titled(gid)
                # title = titled(i, gid, kws.get('title_style'))

            tables[gid] = tbl = self.get_table(group, attrs,
                                               title=title,
                                               totals=totals,
                                               units=units,
                                               # summary=False,
                                               **kws)

            # only first table gets title / headers
            if not titled:
                kws['title'] = None
            if not headers:
                kws['col_headers'] = kws['col_groups'] = None

            # only last table gets footnote
            footnotes |= set(tbl.footnotes)
            tbl.footnotes = []

        # grand total
        if grand_total:
            # gt = np.ma.sum(op.AttrVector('totals').filter(tables.values()), 0)
            totals = [_.totals if _.nrows > 1 else _.data[0] for _ in tables.values()]
            totals = np.ma.array(totals)
            totals.mask[:] = totals.mask.any(0)

            tables['totals'] = tbl = Table(totals.sum(0),
                                           title='Totals:',
                                           formatters=tbl.formatters,
                                           row_headers=[' '],
                                           masked='',
                                           **kws)

        #
        tbl.footnotes = list(footnotes)

        # deal with null matches
        first = next(iter(tables.values()))
        if len(empty):
            filler = [''] * first.shape[1]
            filler[1] = filler_text
            filler = Table([filler])
            for gid in empty:
                tables[gid] = filler

        # HACK summary repr
        if ncc and first.summary.allow():
            first.summarize = ncc
            first.summary.items = dict(zip(
                list(compactable),
                self.get_table(first[:1], compactable,
                               chead=None, cgroups=None,
                               row_nrs=False, **kws)._formatted[0]
            ))
            first.inset = first.summary()

        # put empty tables at the end
        # tables.update(empty)
        return tables
