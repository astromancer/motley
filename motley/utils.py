"""
Utility functions and classes
"""

import os
from recipes.misc import get_terminal_size
from . import codes
from . import ansi

import itertools as itt
import functools as ftl

ALIGNMENT_MAP = {'r': '>',
                 'l': '<',
                 'c': '^'}


def get_alignment(align):
    align = ALIGNMENT_MAP.get(align.lower()[0], align)
    if align not in '<^>':
        raise ValueError('Unrecognised alignment {!r}'.format(align))
    return align


def overlay(text, background='', align='^', width=None):
    """overlay text on background using given alignment."""

    if not (background or width):  # nothing to align on
        return text

    if not background:
        background = ' ' * width  # align on clear background
    elif not width:
        width = ansi.length_seen(background)

    if ansi.length_seen(background) < ansi.length_seen(text):
        # alignment is pointless
        return text

    # do alignment
    align = get_alignment(align)
    if ansi.has_ansi(background):
        raise NotImplementedError(
                '# fixme: will not work if background has coded strings')

    if align == '<':  # left aligned
        overlaid = text + background[ansi.length_seen(text):]

    elif align == '>':  # right aligned
        overlaid = background[:-ansi.length_seen(text)] + text

    elif align == '^':  # center aligned
        div, mod = divmod(ansi.length_seen(text), 2)
        half_width = width // 2
        # start and end indices of the text in the center of the background
        idx = half_width - div, half_width + (div + mod)
        # center text on background
        overlaid = background[:idx[0]] + text + background[idx[1]:]

    return overlaid


def wideness(s, raw=False):  # rename width ??
    """
    For multi-line string `s` get the character width of the widest line.

    Parameters
    ----------
    s
    raw

    Returns
    -------

    """
    length = ftl.partial(ansi.length, raw=raw)
    # deal with cell elements that contain newlines
    return max(map(length, s.split(os.linesep)))


def banner(obj, width=None, swoosh='=', align='<', **props):
    """print pretty banner"""
    if width is None:
        width = get_terminal_size()[0]

    swoosh = swoosh * width
    # s = pprint.pformat(obj, width=width)
    s = str(obj)
    # fill whitespace (so background props reflect for entire block of banner)
    s = '{0:{2}{1:d}}'.format(s, width, align)
    info = '\n'.join([swoosh, s, swoosh])
    info = codes.apply(info, **props)
    return info


def rainbow(words, effects=(), **kws):
    # try:
    # embed()

    propIter = _prop_dict_gen(*effects, **kws)
    propList = list(propIter)
    nprops = len(propList)

    if len(words) < nprops:
        pairIter = itt.zip_longest(words, propList, fillvalue='default')
    else:
        pairIter = zip(words, propList)

    try:
        out = list(itt.starmap(codes.apply, pairIter))
    except:
        print('rainbow_' * 25)
        from IPython import embed
        embed()
    #     raise SystemExit
    # out = []
    # for i, (word, props) in enumerate(pairIter):
    #     word = codes.apply(word, **props)
    #     out.append(word)

    if isinstance(words, str):
        return ''.join(out)

    return out


class ConditionalFormatter(object):
    def __init__(self, properties, test, test_args, formatter=str, **kws):
        self.test = test
        if not isinstance(test_args, tuple):
            test_args = test_args,
        self.args = test_args
        self.properties = properties
        self._kws = kws
        self.formatter = formatter

    def __call__(self, val):
        out = self.formatter(val)
        if self.test(val, *self.args):
            return codes.apply(out, self.properties, **self._kws)
        return out

# def _prop_dict_gen(*effects, **kws):
#     # if isinstance()
#
#     # from IPython import embed
#     # embed()
#
#     # deal with `effects' being list of dicts
#     props = defaultdict(list)
#     for effect in effects:
#         print('effect', effect)
#         if isinstance(effect, dict):
#             for k in ('txt', 'bg'):
#                 v = effect.get(k, None)
#                 props[k].append(v)
#         else:
#             props['txt'].append(effect)
#             props['bg'].append('default')
#
#     # deal with kws having iterable values
#     for k, v in kws.items():
#         if len(props[k]):
#             warnings.warning('Ambiguous: keyword %r. ignoring' % k)
#         else:
#             props[k].extend(v)
#
#     # generate prop dicts
#     propIter = itt.zip_longest(*props.values(), fillvalue='default')
#     for p in propIter:
#         d = dict(zip(props.keys(), p))
#         yield d
#
#
# def get_state_dicts(states, *effects, **kws):
#     propIter = _prop_dict_gen(*effects, **kws)
#     propList = list(propIter)
#     nprops = len(propList)
#     nstates = states.max()  # ptp??
#     istart = int(nstates - nprops + 1)
#     return ([{}] * istart) + propList


# def iter_props(colours, background):
#     for txt, bg in itt.zip_longest(colours, background, fillvalue='default'):
# codes.get_code_str(txt, bg=bg)
# yield tuple(codes._gen_codes(txt, bg=bg))
