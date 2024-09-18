
# local
from collections import defaultdict
from recipes.containers.dicts import invert

# relative
from .utils import parse, pull
from ..colors import CSS_TO_RGB
from ._codes import BG_CODES, FG_COLORS, FG_EFFECTS
import math

# ---------------------------------------------------------------------------- #

NAMES = {**invert(FG_EFFECTS), **invert(FG_COLORS), **invert(BG_CODES)}
GROUPS = {'fg': [*FG_EFFECTS, *FG_COLORS],
          'bg': BG_CODES}
SPECIAL = {'38': 'fg',
           '48': 'bg'}
COMPOUND_CODE_BITS = {'5': 8,
                      '2': 24}
# COMPOUND = {'5': (1, '8 bit {} color: {}'),
#             '2': (3, '24 bit {} color: ({},{},{})')}
# EXPLAIN_FMT = {'text effect: {}': FG_EFFECTS,
#                'text color: {}': FG_COLORS,
#                'background color: {}': BG_CODES}

RGB_TO_CSS = invert(CSS_TO_RGB)

# ---------------------------------------------------------------------------- #


def codes(text):
    for pars in pull(text, 'params'):
        yield params(pars)


def params(params):
    style = defaultdict(list)
    for part, fg_or_bg, name in _explain(params):
        style[fg_or_bg].append(name)

    return dict(style)


def text(text):
    for csi, pars, _, text, end in parse(text):
        # name = fmt.format(fg_or_bg, *bits)
        yield text, params(pars)


def _explain(params):

    params = filter(None, params.split(';'))
    while (p := next(params, None)):
        if fg_or_bg := SPECIAL.get(p):
            bitcode = next(params)
            nbit = COMPOUND_CODE_BITS[bitcode]
            rgb = tuple(next(params) for _ in range(int(math.log2(nbit))))
            part = ';'.join((p, bitcode, *rgb))
            yield (part, fg_or_bg, RGB_TO_CSS.get(rgb, rgb))

        elif (ip := int(p)) in NAMES:
            name = NAMES[ip]
            for fg_or_bg, db in GROUPS.items():
                if name in db:
                    yield (f'{p};', fg_or_bg, name)
                    break
        else:
            yield (f'{p};', None, 'invalid')
