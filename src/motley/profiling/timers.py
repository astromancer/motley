import time
import math
import functools
import traceback
import inspect
from collections import defaultdict  # , OrderedDict
from recipes.dicts import DefaultOrderedDict
from recipes import pprint

from .. import codes


class Chrono():
    # TODO: Singleton so it can be used across multiple modules
    fmt = '{: <50s}{:s}'

    def __init__(self, title=None):
        # print(inspect.getmodule(self))
        frame = inspect.stack()[1]
        module = inspect.getmodule(frame[0])
        if title is not None:
            title = str(module)

        self.title = title or ''
        self._start = self._mark = time.time()
        self.deltas = []
        self.labels = []

        self.funcs = DefaultOrderedDict(int)  # OrderedDict()
        self.hits = defaultdict(int)

    def mark(self, label=None):
        elapsed = time.time() - self._mark
        self._mark = time.time()
        if label:
            self.deltas.append(elapsed)
            self.labels.append(label)

    def report(self):

        # TODO: multiline text block better?
        # TODO: spacing for timing values based on magnitude
        # FIXME: time format does not always pad zeros correctly

        total = time.time() - self._start
        border = '=' * 80
        hline = '-' * 80
        print()
        print(border)
        print('%s Report: %s' % (self.__class__.__name__, self.title))
        print(hline)
        for t, lbl in zip(self.deltas, self.labels):
            txt = self.fmt.format(lbl, pprint.hms(t))
            print(txt)

        for f, t in self.funcs.items():
            txt = self.fmt.format('Function: %s' % f.__name__, pprint.hms(t))
            print(txt)

        print(hline)
        print(self.fmt.format('Total:', pprint.hms(total)))
        print(border)

    # def add_function(self):
    #     'TODO'
    #
    # # def register(self):
    #     """decorator to be used as
    #     @chrono.register
    #     def foo():
    #         pass
    #     """

    def timer(self, func):

        @functools.wraps(func)
        def wrapper(*args, **kw):
            ts = time.time()
            result = func(*args, **kw)
            te = time.time()

            self.hits[func] += 1
            self.funcs[func] += (te - ts)
            return result

        return wrapper


#


def timer(f):
    @functools.wraps(f)
    def wrapper(*args, **kw):
        ts = time.time()
        result = f(*args, **kw)
        te = time.time()

        # TODO: use generic formatter as in expose.args
        # (OR pass formatter as argument)
        # TRIM items with big str reps

        # print('func:%s(%r, %r) took: %2.4f sec'
        # % (f.__name__, args, kw, te-ts))

        msg = 'func: %s took:\t%2.4f sec' % (f.__name__, te - ts)
        print(msg)
        return result

    return wrapper


def timer_extra(postscript, *psargs):
    def timer(f):
        @functools.wraps(f)
        def wrapper(*args, **kw):
            ts = time.time()
            result = f(*args, **kw)
            te = time.time()
            td = te - ts

            print('func: %s\ttook: %2.4f sec'
                  % (f.__name__, td))

            try:
                postscript(td, *psargs)
            except Exception as err:
                print('WHOOPS!')
                traceback.print_exc()

                # pass

            return result

        return wrapper

    return timer


def first_non_zero(a):
    for i, e in enumerate(a):
        if e:
            return i


def metric_unit(x):
    prefixes = {-6: 'μ', -3: 'm', 0: ' '}
    s = ['', '-'][x < 0]
    xus = abs(x)
    lx = math.log10(xus)
    lx3 = math.floor(lx / 3)
    pwr = int(lx3 * 3)
    if pwr in prefixes:
        xun = xus / 10 ** pwr
        u = prefixes[pwr]
        return s, xun, u

    return s, xus, ''  # sign, val, unit


# def fmt_hms(t, sep='hms'):
#     raise DeprecationWarning('use obstools.utils.fmt_hms')
#
#     if len(sep) == 1:
#         sep *= 3
#     assert len(sep) == 3, 'bad seperator'
#
#     sexa = hms(t)
#     start = first_non_zero(sexa)
#
#     if start == 2:
#         return '%s%.1f %ss' % metric_unit(sexa[2])
#
#     parts = list(map('{:g}{:}'.format, sexa, sep))
#     return ''.join(parts[start:])


def timer_highlight(f):
    from decor.expose import get_func_repr

    @functools.wraps(f)
    def wrapper(*args, **kw):
        ts = time.time()
        result = f(*args, **kw)
        te = time.time()

        r = get_func_repr(f, args, kw, verbosity=1)
        # r = f.__name__
        print(codes.apply('Timer', txt='underline', bg='c'))
        print(codes.apply(r, bg='c'))
        print(codes.apply(pprint.hms(te - ts), bg='y'))

        return result

    return wrapper


def timer_dev(f):
    from motley.table import Table
    from decor.expose import get_func_repr

    # TODO: methods similar to profiler: add func / print report / etc

    @functools.wraps(f)
    def wrapper(*args, **kw):
        ts = time.time()
        result = f(*args, **kw)
        te = time.time()

        r = get_func_repr(f, args, kw, verbosity=1)
        tstr = codes.apply(pprint.hms(te - ts), bg='y')
        tbl = Table([r, tstr],
                    title='Timer',
                    title_props=dict(c='bold', bg='g'),
                    row_headers=['func', 'Time'],
                    where_row_borders=[0, -1])
        print(tbl)
        return result

    return wrapper

# def timer(codicil, *psargs):
# def timer(f):
# @functools.wraps(f)
# def wrapper(*args, **kw):
# ts = time.time()
# result = f(*args, **kw)
# te = time.time()
# td = te-ts

# try:
# codicil(td, *psargs)
# except Exception as err:
# import traceback
# traceback.print_exc()

# return result
# return wrapper
# return timer


# from ..expose import get_func_repr

# ====================================================================================================
# class timer(OptArgDecor):
#     """Print function execution time upon return"""
#
#     def make_wrapper(self, func):
#         @functools.wraps(func)
#         def wrapper(*args, **kws):
#             ts = time.time()
#             result = func(*args, **kws)
#             te = time.time()
#             self._t = te - ts
#             self._print_info(args, kws)
#             return result
#
#         return wrapper
#
#     def __call__(self, *args, **kws):
#         ts = time.time()
#         result = self.func(*args, **kws)
#         te = time.time()
#         self._t = te - ts
#         self._print_info(args, kws)
#         return result
#
#     def _print_info(self, args, kws):
#         # print timing info
#         # FIXME: may not always want such verbose output...
#         repr_ = self.get_func_repr(args, kws)
#         size = len(repr_.split('\n', 1)[0])
#         swoosh = '-' * size
#         pre = overlay('Timer', swoosh)
#         post = '\n'.join((swoosh, 'took:\t%2.4f sec' % self._t, swoosh))
#         str_ = '\n'.join((pre, repr_, post))
#         print(str_)
#         sys.stdout.flush()
