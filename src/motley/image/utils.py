
# std
from collections import abc

# third-party
import numpy as np
import matplotlib.transforms
from matplotlib import patheffects
from loguru import logger



def not_none(*args):
    for t in is_none(*args):
        yield not t


def percentile(data, p, axis=None):
    """
    Get percentile value on (possibly masked) `data`. Negative values for
    `p` are interpreted as percentile distance below minimum.  Similarly for
    values of `p` greater than 100. Useful for scaling the axes of plots.

    Parameters
    ----------
    data : array-like
        Data to compute percentile values for.
    p : array-like
        Percentile value(s) in the interval (-100, 100)
    axis : int or tuple, optional
        Axis along which to do the computation, by default None, which uses all
        data

    Examples
    --------
    >>> 

    Returns
    -------
    [type]
        [description]

    Raises
    ------
    NotImplementedError
        [description]
    """

    data = np.asanyarray(data)
    signum = np.array([-1, 1])

    p = np.array(p, ndmin=1) / 100
    # p = np.divide(p, 100)
    a = np.abs(p)
    s = signum[(p > 0).astype(int)]
    # _, q = np.divmod(a, 1)
    c = np.abs((p > 1).astype(float) - s * (a % 1)) * 100

    # remove masked points
    if np.ma.isMA(data):
        if axis is not None:
            raise NotImplementedError

        data = np.ma.compressed(data)

    # create output array
    d = np.zeros((len(p),
                  *(np.take(data.shape, np.delete(np.arange(data.ndim), axis))
                    if axis else ())))
    d[c > 0] = np.percentile(data, c[c > 0], axis)

    # sourcery skip: flip-comparison
    mn, mx, = data.min(axis, keepdims=True), data.max(axis, keepdims=True)
    p1 = (p > 1).astype(int)
    s2 = np.array(signum[((0 < p) & (p < 1)).astype(int)], ndmin=d.ndim).T
    u = np.array(p1 - s * np.ceil(a) + 1, ndmin=d.ndim).T
    v = np.array(p1 + s * np.floor(a), ndmin=d.ndim).T
    return np.squeeze(u * mn + v * mx + s2 * d)


def get_percentiles(data, plims=(-5, 105), errorbars=(), axis=None):
    """
    Return suggested axis limits based on the extrema of `data` and optional
    1 sigma standard deviation `errorbars`.

    data : array-like
        data on display
    plims : 2-tuple
        Data limits expressed as percentiles of the data distribution.
        0 corresponds to the 0th percentile, 100 to the 100th percentile.
        numbers outside range (0, 100) are allowed, in which case they will be
        interpreted as distances from the 0th and 100th percentile
        respectively and the unit distance is a 100th of the data peak-to-peak
        distance.
    e : uncertainty (stddev, measurement errors)
        can be either single array of same shape as x, or 2 arrays (δx+, δx-)
    axis :  int, tuple
        axis along which to compute percentile
    """
    if np.ma.ptp(plims) == 0:
        raise ValueError('Percentile values for colour limits must differ. '
                         f'Received: {plims}.')

    x = get_data_pm_1sigma(data, errorbars)
    lims = np.empty(2, data.dtype)
    for i, (x, p) in enumerate(zip(x, plims)):
        lims[i] = percentile(x, p, axis)

    return lims


def get_data_pm_1sigma(x, e=()):
    """
    Compute the 68.27% confidence interval given the 1-sigma measurement
    uncertainties `e` are given, else return a 2-tuple with data duplicated.

    Parameters
    ----------
    x: array-like
    e: optional, array-like or 2-tuple of array-like
        If array like, assume this is the 1-sigma measurement uncertainties
        If 2-tuple, assume these are the upper and lower confidence distance
        from the mean

    Returns
    -------

    """
    if e is None:
        return x, x

    n = len(e)
    if n == 0:
        return x, x

    # sourcery skip: assign-if-exp, reintroduce-else
    if n == 2:
        return x - e[0], x + e[1]

    return x - e, x + e


def _get_percentile_clim(data, plim):
    # need data to compute percentiles
    assert data is not None

    data = _sanitize_data(data)

    # no data / all masked / nans
    if not np.size(data) or np.all(np.ma.getmask(data)) or np.isnan(data).all():
        return None, None

    # compute percentiles
    clim = get_percentiles(data, plim)

    # check bad clims
    if clim[0] == clim[1]:
        logger.warning('Ignoring bad colour interval: ({:.1f}, {:.1f}) '
                       'computed from percentiles ({:.1f}, {:.1f}).',
                       *clim, *plim)
        return None, None

    return clim


def resolve_clim(data=None, vmin=None, vmax=None, clim=None, plim=None, **_ignored):
    """
    Get colour scale limits for data.
    """
    if any(not_none(vmin, vmax)):
        return vmin, vmax

    if plim is not None:
        return _get_percentile_clim(data, plim)

    if (clim is False) or (clim is None):
        return (None, None)

    if isinstance(clim, abc.Sized) and len(clim) == 2:
        return clim

    raise ValueError(f'Invalid value for {clim=!r}.')
