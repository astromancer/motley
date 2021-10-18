# std
import itertools as itt

# local
from motley.textbox import textbox
from recipes.testing import Expected, mock


texts = [  # 'Hello world!',
    'Hello\nworld!']
styles = ('', '-', '--', '.', ':', '=', '+', '[', 'E')
# ('E', ):   #'_', '-', '=', '+', '['):
boldness = False, True
for text, style, bold in itt.product(texts, styles, boldness):
    # try:
    print(f'{style=}\n{bold=}')
    print(str(textbox(text, style=style, bold=bold)))
    # except Exception as err:
    #     print(str(err))


# ◆──────◆
# │Hello │
# │world!│
# ◆──────◆
test_textbox = Expected(textbox)({
    mock(style='', bold=False):
        '      '
        'Hello '
        'world!'
        '      ',
    mock(style='', bold=True):
        '      '
        'Hello '
        'world!'
        '      ',
    mock(style='-', bold=False):
        '╭──────╮'
        '│Hello │'
        '│world!│'
        '╰──────╯',
    mock(style='-', bold=True):
        '┏━━━━━━┓'
        '┃Hello ┃'
        '┃world!┃'
        '┗━━━━━━┛',
    mock(style='--', bold=False):
        '╭╌╌╌╌╌╌╮'
        '╎Hello ╎'
        '╎world!╎'
        '╰╌╌╌╌╌╌╯',
    mock(style='--', bold=True):
        '┏╍╍╍╍╍╍┓'
        '╏Hello ╏'
        '╏world!╏'
        '┗╍╍╍╍╍╍┛',
    mock(style='.', bold=False):
        '╭┄┄┄┄┄┄╮'
        '┆Hello ┆'
        '┆world!┆'
        '╰┄┄┄┄┄┄╯',
    mock(style='.', bold=True):
        '┏┅┅┅┅┅┅┓'
        '┇Hello ┇'
        '┇world!┇'
        '┗┅┅┅┅┅┅┛',
    mock(style=':', bold=False):
        '╭┈┈┈┈┈┈╮'
        '┊Hello ┊'
        '┊world!┊'
        '╰┈┈┈┈┈┈╯',
    mock(style=':', bold=True):
        '┏┉┉┉┉┉┉┓'
        '┋Hello ┋'
        '┋world!┋'
        '┗┉┉┉┉┉┉┛',
    mock(style='=', bold=False):
        '╔══════╗'
        '║Hello ║'
        '║world!║'
        '╚══════╝',
    # mock(style='=', bold=True):
    #     '╔══════╗'
    #     '║Hello ║'
    #     '║world!║'
    #     '╚══════╝',
    mock(style='+', bold=False):
        '\x1b[;4m   ⃓  ⃓  ⃓ \x1b[0m'
        '┤Hello ├'
        '\x1b[;4m┤world!├\x1b[0m'
        '  ᑊ ᑊ ᑊ',
    # mock(style='+', bold=True):
    #     '\x1b[;4m   ⃓  ⃓  ⃓ \x1b[0m'
    #     '┤Hello ├'
    #     '\x1b[;4m┤world!├\x1b[0m'
    #     '  ᑊ ᑊ ᑊ',
    mock(style='[', bold=False):
        '\x1b[;4m  ⃓  ⃓  ⃓  ⃓\x1b[0m'
        '\x1b[;4m▕\x1b[0mHello \x1b[;4m▏\x1b[0m'
        '\x1b[;4;4m▕\x1b[0m\x1b[;4mworld!\x1b[0m\x1b[;4;4m▏\x1b[0m'
        ' ᑊ ᑊ ᑊ ᑊ',
    # mock(style='[', bold=True):
    #     '\x1b[;4m  ⃓  ⃓  ⃓  ⃓\x1b[0m'
    #     '\x1b[;4m▕\x1b[0mHello \x1b[;4m▏\x1b[0m'
    #     '\x1b[;4;4m▕\x1b[0m\x1b[;4mworld!\x1b[0m\x1b[;4;4m▏\x1b[0m'
    #     ' ᑊ ᑊ ᑊ ᑊ',
    mock(style='E', bold=False):
        '\x1b[;4m  ⃓𝇃 ⃓𝇃 ⃓𝇃 ⃓\x1b[0m'
        '\x1b[;4m┤\x1b[0mHello \x1b[;4m├\x1b[0m'
        '\x1b[;4;4m┤\x1b[0m\x1b[;4mworld!\x1b[0m\x1b[;4;4m├\x1b[0m'
        ' 𝇁ᑊ𝇁ᑊ𝇁ᑊ𝇁',
    # mock(style='E', bold=True):
    #     '\x1b[;4m  ⃓𝇃 ⃓𝇃 ⃓𝇃 ⃓\x1b[0m'
    #     '\x1b[;4m┤\x1b[0mHello \x1b[;4m├\x1b[0m'
    #     '\x1b[;4;4m┤\x1b[0m\x1b[;4mworld!\x1b[0m\x1b[;4;4m├\x1b[0m'
    #     ' 𝇁ᑊ𝇁ᑊ𝇁ᑊ𝇁',
})
