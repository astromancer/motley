"""
Convenience methods that contains various decorators for profiling functions
with line_profiler and pretty-printing the results.

Examples
--------
from motley.profiling import profile

@profile()  # The default `line_profiler` report format
# FIXME: this probs doesn't  work!
def foo():
    ...


@profile(report='bars')
def foo():
    ...


@profile(report='heatmap')
def foo():
    ...


"""

from .core import *




# profile = ReportStats
# bars = DisplayStatsWithBars
# all = profileAll

# TODO
# @profiler.all()
# class Foo:
#     def methodA():
#         'do things'
#     def methodB():
#         'do other things'
#
# Foo().methodA()
# profiler.print_stats()



# ****************************************************************************************************
# class profiler(DisplayStatsBase):
#     """
#     convenience class that contains various decorators for profiling functions with line_profiler
#
#     example
#     -------
#     @profile        # FIXME: this doesn't actually work yet!
#     def foo():
#         ...
#
#     @profile.bars      # FIXME: this doesn't actually work yet!
#     def foo():
#         ...
#     """
#
#     # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#     # bars = DisplayStatsWithBars
#     all = profileAll
#
#     @property
#     def bars(self):
#         return DisplayStatsWithBars

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # TODO
        # def heatmap(self, func):
        #     """Creates a ANSI 256 colour heatmap to indicate line excecution time"""
        #     return DisplayStatsWithBars(self.follow)(func)

        # TODO:
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # def all(self, cls):
        #     # profile all methods in the class
        #     if not inspect.isclass(cls):
        #         raise ValueError('Class please')
        #
        #     from decor.profiler import HLineProfiler
        #     profiler = HLineProfiler()
        #
        #     for name, method in inspect.getmembers(DragMachinery, predicate=inspect.isfunction):
        #         profiler.add_function(method)
        #     profiler.enable_by_count()
