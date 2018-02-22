"""
Convenient coloured strings
"""

import re
import pprint
import warnings
import itertools as itt
from collections import defaultdict

from recipes.iter import pairwise
from recipes.misc import get_terminal_size

from . import codes


pattern = '\033\[[\d;]*[a-zA-Z]'
matcher = re.compile(pattern)


# TODO: convenience methods:
# bold
# dim
# underline
# blink
# invert
# hide
# reset / clear
# etc...


def has_ansi(s):
    return not matcher.search(s) is None


def strip(s):
    """strip motley codes from str"""
    return matcher.sub('', s)


def pull(s):
    """extract motley codes from str"""
    return matcher.findall(s)


def split(s):
    """split str at motley code locations"""
    idxs = []
    for i, match in enumerate(s.matcher.finditer(s)):
        idxs += [match.start(), match.end()]

    if not len(idxs):
        return [s]

    if idxs[0] != 0:
        idxs = [0] + idxs
    if idxs[-1] != len(s):
        idxs += [len(s)]

    parsed = [s[i0:i1] for i0, i1 in pairwise(idxs)]
    return parsed


def length(s, raw=True):
    """ """
    if raw:
        return len(s)
    return length_bare(s)


def length_codes(s):
    """length of the ansi escape sequences in the str"""
    return sum(map(len, pull(s)))


def length_bare(s):
    """
    length of the string as it would be displayed on screen
    i.e. all ansi codes resolved / removed
    """
    return len(strip(s))


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

    # except:
    #     print('rainbow_' * 25)
    #     embed()
    #     raise SystemExit


def banner(obj, width=None, swoosh='=', **props):
    """print pretty banner"""
    if width is None:
        width = get_terminal_size()[0]

    swoosh = swoosh * width
    s = pprint.pformat(obj, width=width)
    # fill whitespace (so background props reflect for entire block of banner)
    s = '{0:<{1:d}}'.format(s, width)
    info = '\n'.join([swoosh, s, swoosh])
    info = codes.apply(info, **props)
    return info


def _prop_dict_gen(*effects, **kws):
    # if isinstance()

    # deal with `effects' being list of dicts
    props = defaultdict(list)
    for effect in effects:
        if isinstance(effect, dict):
            for k in ('fg', 'bg'):
                v = effect.get(k, None)
                props[k].append(v)
        else:
            props['fg'].append(effect)

    # deal with kws having itearble values
    for k, v in kws.items():
        if len(props[k]):
            warnings.warning('Ambiguous: keyword %r. ignoring' % k)
        else:
            props[k].extend(v)

    # generate prop dicts
    propIter = itt.zip_longest(*props.values(), fillvalue='default')
    for p in propIter:
        d = dict(zip(props.keys(), p))
        yield d


def get_state_dicts(states, *effects, **kws):
    propIter = _prop_dict_gen(*effects, **kws)
    propList = list(propIter)
    nprops = len(propList)
    nstates = states.max()  # ptp??
    istart = int(nstates - nprops + 1)
    return ([{}] * istart) + propList



