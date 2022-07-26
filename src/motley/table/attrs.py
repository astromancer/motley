
# std
import functools as ftl
import itertools as itt
from collections import abc
from _string import formatter_parser

# third-party
import numpy as np

# local
from pyxides.grouping import Groups
from pyxides.vectorize import AttrTabulate
from recipes.iter import cofilter
from recipes.dicts import AttrDict
from recipes.sets import OrderedSet
from recipes.string.brackets import BracketParser

# relative
from ..utils import make_group_title, resolve_alignment
from .table import Table
from .column import Column
from .xlsx import XlsxWriter


# ---------------------------------------------------------------------------- #

CONVERTERS = {  # TODO: MOVE TO formatter
    's': str,
    'r': repr,
    'a': ascii,
    'o': ord,
    'c': chr,
    't': str.title,
    'q': lambda _: repr(str(_))
}

SENTINEL = object()
# ---------------------------------------------------------------------------- #


class AttrColumn(Column):
    def __init__(self, title=None, unit=None, convert=None, fmt=None, align='<',
                 total=False):

        # TODO: fmt = '. 14.5?f|gBi_/teal'
        self.title = title
        # self.data = np.atleast_1d(np.asanyarray(data, 'O').squeeze())
        # assert self.data.ndim == 1
        # self.dtypes = set(map(type, np.ma.compressed(self.data)))
        self.unit = unit
        self.align = resolve_alignment(align)
        # self.width = width
        self.total = bool(total)  # self.data.sum() if total else None

        # if fmt is None:
        #     fmt = self.get_default_formatter()
        # assert callable(fmt)
        self.convert = convert
        self.fmt = fmt


class AttrTable:
    """
    Helper class for tabulating attributes (or properties) of lists of objects.
    Attributes of the objects in the container are mapped to the columns of the
    table.
    """

    _unit_parser = BracketParser('[]')

    # @classmethod
    # def from_dict(cls, mapping=(), **kws):

    @classmethod
    def from_columns(cls, mapping=(), **kws):
        mapping = dict(mapping)
        option_names = ('headers', 'units', 'converters', 'formatters', 'alignment')
        options = [{}, {}, {}, {}]
        col_keys = 'title', 'unit', 'convert', 'fmt', 'align'
        totals = []
        for attr, col in mapping.items():
            if col in (..., ''):
                continue

            # assert isinstance(col, AttrColumn)

            # populate the headers, units, converters, formatters
            col_opts = cofilter(None, map(vars(col).get, col_keys), options)
            for val, opt in zip(*col_opts):
                opt[attr] = val

            if col.total:
                totals.append(attr)

        kws.update(zip(option_names, options))
        return cls(mapping.keys(), totals=totals, **kws)

    @classmethod
    def from_spec(cls, mapping=(), **kws):
        attrs, *opts = cls._resolve_opts(mapping)
        parsed_option_names = ('headers', 'units', 'converters', 'formatters')
        for key, opt in zip(parsed_option_names, opts):
            if key in kws:
                kws[key].update(opt)
            else:
                kws[key] = opt
        return cls(attrs, **kws)

    @classmethod
    def _resolve_opts(cls, mapping):
        # headers, units, converters, formatters
        info = {}, {}, {}, {}
        attrs = []
        for attr, *options in cls._iter_from_spec(dict(mapping)):
            # header, unit, converter, formatter
            for i, opt in enumerate(options):
                if opt:
                    info[i][attr] = opt

            attrs.append(attr)
        # attrs, headers, units, converters, formatters
        return attrs, *info

    @classmethod
    def _iter_from_spec(cls, mapping):
        for header, spec in mapping.items():
            # parse units
            if spec in (..., ''):
                #     attr, header, unit, converter, formatter
                yield header, None, None, None, None
                continue

            unit = cls._unit_parser.match(header)
            if unit:
                unit = unit.full
                header = header.replace(unit, '').strip()

            attr, converter, spec = cls._parse_spec(spec)
            yield (attr or header), header, unit, converter, spec

    @staticmethod
    def _parse_spec(spec):
        # literal_text, field_name, format_spec, conversion
        items = next(formatter_parser(f'{{{spec}}}'))
        _, attr, format_spec, conversion = items
        # if items is None:
        #     raise NotImplementedError()
        # formatter._parse_spec()
        converter = CONVERTERS.get(conversion.lower()) if conversion else None
        return attr, converter, format_spec

    # @classmethod
    # def from_spec(cls, name_spec_list):
    #     value, spec, effects = formatter._parse_spec('', name_spec_list)
    #     for key, col in columns.items():

    def __get__(self, instance, kls):
        if instance:  # lookup from instance
            self.parent = instance
        return self  # lookup from class

    def _ensure_dict(self, obj):
        if obj is None:
            return dict()

        if isinstance(obj, dict):
            return obj

        return dict(zip(self.attrs, obj))

    def __new__(cls, attrs, *args, **kws):
        if isinstance(attrs, dict):
            return cls.from_dict(attrs)
        return super().__new__(cls)

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
                 **kws):

        # set default options for table
        self.kws = {**dict(row_nrs=0,
                           precision=5,
                           minimalist=True,
                           compact=True),
                    **kws}

        self.title = self.kws.get('title')
        self.attrs = list(attrs)
        self.converters = self._ensure_dict(converters)
        self.formatters = self._ensure_dict(formatters)
        self.header_levels = self._ensure_dict(header_levels)
        # self.header_formatter = header_formatter
        self.headers = self._ensure_dict(headers)
        self.units = self._ensure_dict(units)
        totals = [totals] if isinstance(totals, str) else list(totals)
        self.totals = [self.get_header(attr) for attr in totals]
        self.align = alignment
        self.show_groups = bool(show_groups)

        # self.headers = dict(zip(attrs, self.get_headers(attrs)))
        # self._heads = {a: self.get_header_parts(a) for a in self.attrs}
        self.parent = None

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

        container = container or self.parent
        if isinstance(self.parent, AttrTabulate):
            return self.get_table(self.parent, attrs, **kws)

        if isinstance(self.parent, Groups):
            return self.get_tables(self.parent, attrs, **kws)

        raise TypeError(f'Cannot tabulate object of type {type(self.parent)}.')

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
        # obj = self.parent[0]
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
            container = self.parent

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

    def to_xlsx(self, path, widths={}, **kws):

        data = np.array(self.get_data(self.parent.sort_by('t.t0')))

        # FIXME: better to use get_table here, but then we need to keep
        # table.data as objects not convert to str prematurely!
        # PLEASE FIX THIS UNGODLY HACK

        col_headers = self.get_headers()
        tmp = AttrDict(
            data=data,
            col_groups=self.get_groups(),
            col_headers=col_headers,
            _col_headers=col_headers,
            units=self.get_units(),
            formatters={self.attrs.index(k): v for k, v in self.formatters.items()},
            totals=[col_headers.index(t) for t in self.totals],
            title=self.title,
            shape=(len(data), len(self.attrs))
        )

        # may need to set widths manually eg. for cells that contain formulae
        # tmp.col_widths = get_col_widths(tmp) if widths is None else widths
        # table = tmp()
        tmp.resolve_input = ftl.partial(Table.resolve_input, tmp)
        #  self.align,
        return XlsxWriter(tmp, widths, **kws).write(path)

    def get_table(self, container, attrs=None, **kws):
        """
        Keyword arguments passed directly to the `motley.table.Table`
        constructor.

        Returns
        -------
        motley.table.Table
        """

        if not isinstance(container, AttrTabulate):
            raise TypeError(f'Object of type {type(container)} does not '
                            f'support vectorized attribute lookup on items.')

        if len(container) == 0:
            return Table(['Empty'])

        if attrs is None:
            attrs = self.attrs

        return Table(container.attrs(*attrs),
                     **{**self.kws,  # defaults
                        **{**dict(title=container.__class__.__name__,
                                  col_headers=self.get_headers(attrs),
                                  col_groups=self.get_groups(attrs),
                                  totals=self.totals),
                           **{key: self.get_defaults(attrs, key)
                              for key in ('units', 'formatters')},
                           **kws},  # keywords from user input
                        })

    def prepare(self, groups, **kws):
        # class GroupedTables:

        attrs = OrderedSet(self.attrs)
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
        Get a dictionary of tables for the containers in `groups`. This method
        assists working with groups of tables.
        """

        title = kws.pop('title', self.__class__.__name__)
        ncc = kws.pop('compact', False)  # number of columns in compact part
        kws['compact'] = False

        if titled is True:
            titled = make_group_title

        attrs, compactable, headers, units, totals = self.prepare(groups)
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
                # title = titled(i, gid, kws.get('title_props'))

            tables[gid] = tbl = self.get_table(group, attrs,
                                               title=title,
                                               totals=totals,
                                               units=units,
                                               # compact=False,
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
            grand = np.ma.sum([_.totals for _ in tables.values()
                               if _.totals is not None], 0)

            tables['totals'] = tbl = Table(grand,
                                           title='Totals:',
                                           title_align='<',
                                           formatters=tbl.formatters,
                                           row_headers='',
                                           masked='')

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

        # HACK compact repr
        if ncc and first.is_compactable():
            first.compact = ncc
            first.compact_items = dict(zip(
                list(compactable),
                self.get_table(first[:1], compactable,
                               chead=None, cgroups=None,
                               row_nrs=False, **kws).pre_table[0]
            ))
            first._compact_table = first._get_compact_table()

        # put empty tables at the end
        # tables.update(empty)
        return tables
