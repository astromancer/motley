# std
import itertools as itt

# local
from motley.textbox import textbox
from recipes.testing import Expected, mock


# texts = [  # 'Hello world!',
#     'Hello\nworld!']
# linestyles = ('', '-', '--', '.', ':', '=', '+', '[', 'E')
# # ('E', ):   #'_', '-', '=', '+', '['):
# boldness = '', 'Bold'
# for text, linestyle, bold in itt.product(texts, linestyles, boldness):
#     # try:
#     if bold:
#         linestyle = (linestyle, bold)
#     print(f'{linestyle=}\n{bold=}')
#     print(str(textbox(text, linestyle=linestyle)))
#     # except Exception as err:
#     #     print(str(err))


# # ◆──────◆
# │Hello │
# │world!│
# ◆──────◆
test_textbox = Expected(textbox, text='Hello\nworld!',
                        right_transform='\n'.join)(
    {
        mock(linestyle=''):
        (
            '      ',
            'Hello ',
            'world!',
            '      '
        ),
        mock(linestyle=('', 'bold')):
        (
            '      ',
            'Hello ',
            'world!',
            '      '
        ),
        mock(linestyle='-'):
        (
            '╭──────╮',
            '│Hello │',
            '│world!│',
            '╰──────╯'
        ),
        mock(linestyle=('-', 'bold')):
        (
            '┏━━━━━━┓',
            '┃Hello ┃',
            '┃world!┃',
            '┗━━━━━━┛'
        ),
        mock(linestyle='--'):
        (
            '╭╌╌╌╌╌╌╮',
            '╎Hello ╎',
            '╎world!╎',
            '╰╌╌╌╌╌╌╯'
        ),
        mock(linestyle=('--', 'bold')):
        (
            '┏╍╍╍╍╍╍┓',
            '╏Hello ╏',
            '╏world!╏',
            '┗╍╍╍╍╍╍┛'
        ),
        mock(linestyle='.'):
        (
            '╭┄┄┄┄┄┄╮',
            '┆Hello ┆',
            '┆world!┆',
            '╰┄┄┄┄┄┄╯'
        ),
        mock(linestyle=('.', 'bold')):
        (
            '┏┅┅┅┅┅┅┓',
            '┇Hello ┇',
            '┇world!┇',
            '┗┅┅┅┅┅┅┛'
        ),
        mock(linestyle=':'):
        (
            '╭┈┈┈┈┈┈╮',
            '┊Hello ┊',
            '┊world!┊',
            '╰┈┈┈┈┈┈╯'
        ),
        mock(linestyle=(':', 'bold')):
        (
            '┏┉┉┉┉┉┉┓',
            '┋Hello ┋',
            '┋world!┋',
            '┗┉┉┉┉┉┉┛'
        ),
        mock(linestyle='='):
        (
            '╔══════╗',
            '║Hello ║',
            '║world!║',
            '╚══════╝'
        ),
        # mock(linestyle=('=', 'bold')):
        #     '╔══════╗',
        #     '║Hello ║',
        #     '║world!║',
        #     '╚══════╝'

        mock(linestyle='+'):
        (
            '\x1b[;4m   ⃓  ⃓  ⃓ \x1b[0m',
            '┤Hello ├',
            '\x1b[;4m┤world!├\x1b[0m',
            '  ᑊ ᑊ ᑊ'
        ),
        # mock(linestyle=('+', 'bold')):
        #     '\x1b[;4m   ⃓  ⃓  ⃓ \x1b[0m',
        #     '┤Hello ├',
        #     '\x1b[;4m┤world!├\x1b[0m',
        #     '  ᑊ ᑊ ᑊ'

        mock(linestyle='['):
        (
            '\x1b[;4m  ⃓  ⃓  ⃓  ⃓\x1b[0m',
            '\x1b[;4m▕\x1b[0mHello \x1b[;4m▏\x1b[0m',
            '\x1b[;4;4m▕\x1b[0m\x1b[;4mworld!\x1b[0m\x1b[;4;4m▏\x1b[0m',
            ' ᑊ ᑊ ᑊ ᑊ'
        ),
        # mock(linestyle=('[', 'bold')):
        #     '\x1b[;4m  ⃓  ⃓  ⃓  ⃓\x1b[0m',
        #     '\x1b[;4m▕\x1b[0mHello \x1b[;4m▏\x1b[0m',
        #     '\x1b[;4;4m▕\x1b[0m\x1b[;4mworld!\x1b[0m\x1b[;4;4m▏\x1b[0m',
        #     ' ᑊ ᑊ ᑊ ᑊ'

        mock(linestyle='E'):
        (
            '\x1b[;4m  ⃓𝇃 ⃓𝇃 ⃓𝇃 ⃓\x1b[0m',
            '\x1b[;4m┤\x1b[0mHello \x1b[;4m├\x1b[0m',
            '\x1b[;4;4m┤\x1b[0m\x1b[;4mworld!\x1b[0m\x1b[;4;4m├\x1b[0m',
            ' 𝇁ᑊ𝇁ᑊ𝇁ᑊ𝇁'
        ),
        # mock(linestyle=('E', 'bold')):
        #     '\x1b[;4m  ⃓𝇃 ⃓𝇃 ⃓𝇃 ⃓\x1b[0m',
        #     '\x1b[;4m┤\x1b[0mHello \x1b[;4m├\x1b[0m',
        #     '\x1b[;4;4m┤\x1b[0m\x1b[;4mworld!\x1b[0m\x1b[;4;4m├\x1b[0m',
        #     ' 𝇁ᑊ𝇁ᑊ𝇁ᑊ𝇁',
    })
