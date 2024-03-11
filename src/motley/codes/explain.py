
# local
from recipes.containers.dicts import invert

# relative
from .utils import parse
from ._codes import BG_CODES, FG_COLORS, FG_EFFECTS


# ---------------------------------------------------------------------------- #

CODES = {**invert(FG_EFFECTS), **invert(FG_COLORS), **invert(BG_CODES)}
SPECIAL = {'38': 'fg',
           '48': 'bg'}
COMPOUND = {'5': (1, '8 bit {} color: {}'),
            '2': (3, '24 bit {} color: ({},{},{})')}


def explain(text):

    info = {}
    for csi, params, fb, text, end in parse(text):
        info[text] = dict(_explain(params))

    return info


def _explain(params):

    params = filter(None, params.split(';'))
    while (p := next(params, None)):
        if fg_or_bg := SPECIAL.get(p, None):
            n, fmt = COMPOUND[(bitcode := next(params))]
            bits = tuple(next(params) for _ in range(n))
            name = fmt.format(fg_or_bg, *bits)
            yield (';'.join((p, bitcode, *bits)), name)

        elif (ip := int(p)) in CODES:
            name = CODES[ip]
            for fmt, db in {'text effect: {}': FG_EFFECTS,
                            'text color: {}': FG_COLORS,
                            'background color: {}': BG_CODES}.items():
                if name in db:
                    yield (f'{p};', fmt.format(name))
                    break
        else:
            yield (f'{p};', 'invalid')
