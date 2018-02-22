"""
Convenience methods that contains various decorators for profiling functions
with line_profiler and pretty-printing the results.

Example
-------
from motley import profiler

@profiler.profile()
def foo():
    ...


@profiler.histogram()
def foo():
    ...

"""

from .core import *


profile = PrintStats
histogram = HistogramDisplay
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
# class profiler(ProfileStatsDisplay):
#     """
#     convenience class that contains various decorators for profiling functions with line_profiler
#
#     example
#     -------
#     @profile        # FIXME: this doesn't actually work yet!
#     def foo():
#         ...
#
#     @profile.histogram      # FIXME: this doesn't actually work yet!
#     def foo():
#         ...
#     """
#
#     # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#     # histogram = HistogramDisplay
#     all = profileAll
#
#     @property
#     def histogram(self):
#         return HistogramDisplay

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # TODO
        # def heatmap(self, func):
        #     """Creates a ANSI 256 colour heatmap to indicate line excecution time"""
        #     return HistogramDisplay(self.follow)(func)

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
