
# relative
from .. import codes

from recipes.pprint.formatters import (
    Array, Collection, Decimal, Masked, Measurement, Metric, Numeric,
    Percentage, Scientific
)


# ---------------------------------------------------------------------------- #

class Conditional:
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


# ---------------------------------------------------------------------------- #
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

ConditionalFormatter = Conditional
