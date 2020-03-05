import functools
import logging
import inspect

import numpy as np
import line_profiler as lp

from .. import codes
from .printers import ReportStats, ReportStatsTable


# def get_methods(cls_or_obj):
#     import inspect
#     names, methods = \
#         zip(*inspect.getmembers(cls_or_obj, predicate=inspect.ismethod))
#     return methods


class LineProfiler(lp.LineProfiler):
    """
    Extend `line_profiler.LineProfiler` to enable printing timing statistics
    """
    printerClass = ReportStats

    # TODO: option to reset after multiple calls.  may sometimes be desired

    def __init__(self, *args, **kws):
        lp.LineProfiler.__init__(self, *args, **kws)
        self.fmap = {}  # name - function mapping
        # add mapping from function names to actual function object. Useful for
        # retrieving source code from interactively defined functions

    # def print_stats(self, stream=None, output_unit=None, **kws):
    #     # report line timings for each profiled function
    #     self.printerClass(**kws)(self.get_stats())

    def add_function(self, func):
        # add function to name - function map
        # since function names may not be unique, use filename, funcname
        filename = inspect.getfile(func)
        key = (filename, func.__name__)
        self.fmap[key] = func
        lp.LineProfiler.add_function(self, func)

    def get_stats(self):
        """
        Calculate some extra stats. Also add function object in key to stats.
        """
        lstats = lp.LineProfiler.get_stats(self)
        # return lstats

        # replace func name in timing dict with actual func object
        timings = {}
        grand_total = sum(a for v in lstats.timings.values() for *_, a in v)

        for info, line_times in lstats.timings.items():
            filename, start_line_no, name = info
            if len(line_times):
                # function was executed
                lnr, hits, times = zip(*line_times)

                # calculate extras
                times = np.array(times)
                total = times.sum()
                total_time = total * lstats.unit
                per_hit = times / hits
                foft = times / total  # fraction of function total
                fogt = times / grand_total  # fraction of grand total

                # remake stats dict
                stats = dict(zip(lnr, zip(hits, times, per_hit, foft, fogt)))
            else:
                total_time = 0
                stats = {}

            newkey = (filename, start_line_no, self.fmap[(filename, name)])
            timings[newkey] = (stats, total_time)

        lstats.timings = timings
        lstats.grand_total = grand_total

        return lstats

    def add_all_methods(self, cls, exclude=None):
        """
        A decorator that profiles all methods in a class.

        Parameters
        ----------
        cls: object
            object to profile
        exclude: list of str, optional
            methods to exclude

        Returns
        -------

        """
        # FIXME: does not work interactively!!
        # import atexit

        if exclude is None:
            exclude = []

        for i, (name, method) in enumerate(
                inspect.getmembers(cls, predicate=inspect.ismethod)):
            # NOTE:  inspect.isfunction for some classes???
            if name not in exclude:
                self.add_function(method)
                logging.info('Added method: %s', name)

        logging.info('%i methods added to profiler %s', i, self)
        self.enable_by_count()

    def rank_functions(self):
        from shutil import get_terminal_size

        import numpy as np
        from recipes.containers.lists import sortmore

        from motley.table import Table
        # from recipes.misc import get_terminal_size

        lstats = self.get_stats()
        totals = {}
        for (filename, lineno, func), timings in lstats.timings.items():
            if len(timings):
                linenos, Nhits, times = zip(*timings)
                totals[func.__name__] = sum(times)

        # sort timings etc. descending
        totals, names = sortmore(totals.values(), totals.keys(), order=-1)

        # do histogram thing
        frac = np.divide(totals, max(totals))

        # format totals with space as thousands separator for readability
        fmtr = lambda s: '{:,}'.format(s).replace(',', ' ')
        # totals = list(map(fmtr, totals))
        col_headers = ('Function', u'Time (\u00B5s)')
        table = Table(list(zip(names, totals)),
                      col_headers=col_headers,
                      formatters={1: fmtr},
                      totals=[1])

        termwidth = get_terminal_size()[0]
        hwidth = termwidth - table.get_width() - 1
        frac = np.round(frac * hwidth).astype(int)
        sTable = str(table).split('\n')
        for i, f in enumerate(frac):
            hline = codes.apply(' ' * f, bg=ReportStatsTable.bar_color)
            sTable[i + 2] += hline
        htable = '\n'.join(sTable)
        print(htable)


# ****************************************************************************************************
# Decorator classes
# ****************************************************************************************************

class profile(object):
    """
    Decorator for printing results from multiple profiled functions in
    various output formats
    """

    # singleton profiler.  All functions will be added to this one.
    profiler = LineProfiler()

    def __init__(self, follow=(), report=None, **kws):
        # decorator for profiling

        logging.debug('__init__ %s: %s; %s', self, follow, kws)

        if report is None:
            # default report
            printer = ReportStats()

        elif report == 'bars':
            # displays a highlighted version of the source code in the
            # terminal to indicate execution times in a fashion that resembles
            # a bar chart.
            printer = ReportStatsTable(**kws)

        # elif report == 'heatmap':
        #     printer = ReportHeatMap(**kws)
        else:
            raise ValueError('Invalid report type %r requested' % report)

        self.printer = printer
        self.follow = follow

    def __call__(self, func):
        logging.debug('calling %s with %s', self, func.__name__)

        # ----------------------------------------------------------------------------------------------------
        @functools.wraps(func)
        def profiled_func(*args, **kwargs):
            # print(func, args, kwargs)
            try:
                self.profiler.add_function(func)
                for f in self.follow:
                    self.profiler.add_function(f)
                self.profiler.enable_by_count()
                return func(*args, **kwargs)
            finally:
                # report line timings for each profiled function
                self.printer(self.profiler.get_stats())

        # ----------------------------------------------------------------------------------------------------
        return profiled_func


