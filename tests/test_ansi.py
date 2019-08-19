import motley
from motley import ansi


def test_split():
    ansi.split('\033[32m green \033[0m')
    (['\033[32m', ' green ', '\033[0m'])

def test_apply():
    ''

def test_stack_effects():
    motley.red(motley.bold('hi'))

def test_parse():
    '\033\[[\d;]*[a-zA-Z]'