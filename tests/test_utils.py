
# third-party
import numpy as np

# local
import motley


# ---------------------------------------------------------------------------- #

def test_split():
    motley.codes.split('\033[32m green \033[0m')
    (['\033[32m', ' green ', '\033[0m'])


def test_stack_effects():
    motley.red(motley.bold('hi'))


def test_parse():
    '\033\[[\d;]*[a-zA-Z]'


def test_resolve():
    motley.codes.get(None)
    motley.codes.get('')
    motley.codes.get(0)
    motley.codes.get(txt='r')
    motley.codes.get(fg='r')
    motley.codes.get(fg=('w', 'bold'), bg='r')
    motley.codes.get(dict(fg=('w', 'bold'), bg='r'))
    motley.codes.get('blue', 'italic')
    motley.codes.get(31, 'italic', bg='y')
    motley.codes.get((55, 55, 55), 'italic', bg=(255, 1, 1))
    motley.codes.get(text=('magenta',), bg='gray')
    motley.codes.get(dict(fg=((55, 55, 55), 'bold', 'italic'), bg='r'))


def test_apply():
    test_str = '\tTHIS IS A TEST\t'
    print(motley.apply(test_str, None))
    print(motley.apply(test_str, ''))
    print(motley.apply(test_str, 0))
    print(motley.apply(test_str, txt='r'))
    print(motley.apply(test_str, fg='r'))
    print(motley.apply(test_str, fg=('w', 'bold'), bg='r'))
    print(motley.apply(test_str, dict(fg=('w', 'bold'), bg='r')))
    print(motley.apply(test_str, dict(fg=('w', 'bold')), bg=(55, 100, 1)))
    print(motley.apply(test_str, 'blue', 'italic'))
    print(motley.apply(test_str, 31, 'italic', bg='y'))
    print(motley.apply(test_str, (55, 55, 55), 'italic', bg=(255, 1, 1)))
    print(motley.apply(test_str, text=('magenta',), bg='gray'))
    print(motley.apply(test_str, dict(fg=((55, 55, 55), 'bold', 'italic'), bg='r')))


# def test_rainbow():
#     #
#     # print(rainbow('joe', 'rgb'))
#     # print(rainbow('joe', bg='rgb'))

#     h = np.arange(19, dtype=int).astype(str)
#     flags = np.array(
#         [{'bg': ' '}, {'bg': ' '}, {'bg': ' '}, {'bg': 'r'}, {'bg': ' '},
#          {'bg': ' '}, {'bg': ' '}, {'bg': 'y'}, {'bg': ' '}, {'bg': ' '},
#          {'bg': ' '}, {'bg': ' '}, {'bg': ' '}, {'bg': ' '}, {'bg': ' '},
#          {'bg': ' '}, {'bg': ' '}, {'bg': 'y'}, {'bg': 'y'}],
#         dtype=object)
#     print(motley.utils.rainbow(h, flags))


test_apply()

# print('\033[38;2;255;1;55mHELLOO!!!\033[0m')

# TODO: print pretty things:
# http://misc.flogisoft.com/bash/tip_colors_and_formatting
# http://askubuntu.com/questions/512525/how-to-enable-24bit-true-color-support-in-gnome-terminal
# https://github.com/robertknight/konsole/blob/master/tests/color-spaces.pl
