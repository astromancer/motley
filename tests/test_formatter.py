
# third-party
from loguru import logger

# local
from recipes.testing import Expected, mock
from motley.formatter import Formatter, formatter

logger.enable('motley')


# formatter = Formatter()
exp = Expected(formatter.format)
exp.is_method = False

test_std_fmt = exp({
    **{  # Basic
        ('{0}, {1}, {2}', 'a', 'b', 'c'):
            'a, b, c',
        ('{}, {}, {}', 'a', 'b', 'c'):  # 3.1+ only
            'a, b, c',
        ('{2}, {1}, {0}', 'a', 'b', 'c'):
            'c, b, a',
        ('{2}, {1}, {0}', *'abc'):      # unpacking argument sequence
            'c, b, a',
        ('{0}{1}{0}', 'abra', 'cad'):   # arguments' indices can be repeated
            'abracadabra',

        # Accessing arguments by name:
        mock('Coordinates: {latitude}, {longitude}',
             latitude='37.24N', longitude='-115.81W'):
            'Coordinates: 37.24N, -115.81W',
        mock('Coordinates: {latitude}, {longitude}',
             **{'latitude': '37.24N', 'longitude': '-115.81W'}):
            'Coordinates: 37.24N, -115.81W',

        # Accessing arguments’ attributes:
        ('The complex number {0} is formed from the real part {0.real} '
         'and the imaginary part {0.imag}.', 3-5j):
            'The complex number (3-5j) is formed from the real part 3.0 and the imaginary part -5.0.',

        # Accessing arguments’ items:
        ('X: {0[0]};  Y: {0[1]}', (3, 5)):
            'X: 3;  Y: 5',

        # Replacing %s and %r:
        ("repr() shows quotes: {!r}; str() doesn't: {!s}", 'test1', 'test2'):
            "repr() shows quotes: 'test1'; str() doesn't: test2",

        # Aligning the text and specifying a width:
        ('{:<30}', 'left aligned'):
            'left aligned                  ',
        ('{:>30}', 'right aligned'):
            '                 right aligned',
        ('{:^30}', 'centered'):
            '           centered           ',
        ('{:*^30}', 'centered'):  # use '*' as a fill char
            '***********centered***********',

        # Replacing %+f, %-f, and % f and specifying a sign:
        ('{:+f}; {:+f}', 3.14, -3.14):  # show it always
            '+3.140000; -3.140000',
        ('{: f}; {: f}', 3.14, -3.14):  # show a space for positive numbers
            ' 3.140000; -3.140000',
        ('{:-f}; {:-f}', 3.14, -3.14):  # show only the minus -- same as '{:f}; {:f}'
            '3.140000; -3.140000',

        # Replacing %x and %o and converting the value to different bases:
        # format also supports binary numbers
        ("int: {0:d};  hex: {0:x};  oct: {0:o};  bin: {0:b}", 42):
            'int: 42;  hex: 2a;  oct: 52;  bin: 101010',
        # with 0x, 0o, or 0b as prefix:
        ("int: {0:d};  hex: {0:#x};  oct: {0:#o};  bin: {0:#b}", 42):
            'int: 42;  hex: 0x2a;  oct: 0o52;  bin: 0b101010',

        # Using the comma as a thousands separator:
        ('{:,}', 1234567890):
        '1,234,567,890',

        # Expressing a percentage:
        ('Correct answers: {:.2%}', 19/22):
            'Correct answers: 86.36%',

        # Using type-specific formatting:

        # ('{:%Y-%m-%d %H:%M:%S}', datetime.datetime(2010, 7, 4, 12, 15, 58)):
        #     '2010-07-04 12:15:58'
    },

    # # Nesting arguments and more complex examples:
    **{mock('{0:{fill}{align}16}', text, fill=align, align=align): rhs
        for align, text, rhs in zip('<^>',
                                    ['left', 'center', 'right'],
                                    ('left<<<<<<<<<<<<',
                                     '^^^^^center^^^^^',
                                     '>>>>>>>>>>>right'))},

    **{('{:02X}{:02X}{:02X}{:02X}', *[192, 168, 0, 1]):
        'C0A80001'}
})

# width = 5
# for num in range(5, 12):
#      for base in 'dXob':
# (print('{0:{width}{base}}', num, base=base, width=width), end=' ')
#      print()

# class TestExt:

# TODO: test_stylize with cases below!
test_extended_format = exp({
    **{  # Basic
        ('{0:|r}, {1:|g}, {2:|b}', 'a', 'b', 'c'):
            '\x1b[;31ma\x1b[0m, \x1b[;32mb\x1b[0m, \x1b[;34mc\x1b[0m',
        ('{:|r}, {:|g}, {:|b}', 'a', 'b', 'c'):  # 3.1+ only
            '\x1b[;31ma\x1b[0m, \x1b[;32mb\x1b[0m, \x1b[;34mc\x1b[0m',
        ('{2}, {1}, {0}', 'a', 'b', 'c'):
            'c, b, a',
        ('{2}, {1}, {0}', *'abc'):      # unpacking argument sequence
            'c, b, a',
        ('{0:|r}{1:|g}{0:|b}', 'abra', 'cad'):   # arguments' indices can be repeated
        '\x1b[;31mabra\x1b[0m\x1b[;32mcad\x1b[0m\x1b[;34mabra\x1b[0m',

        # Accessing arguments by name:
        mock('Coordinates: {latitude:|w/k}, {longitude:|k/w}',
             latitude='37.24N', longitude='-115.81W'):
            'Coordinates: \x1b[;97;40m37.24N\x1b[0m, \x1b[;30;107m-115.81W\x1b[0m',
        mock('Coordinates: {latitude:/k}, {longitude:/black}',
             **{'latitude': '37.24N', 'longitude': '-115.81W'}):
            'Coordinates: \x1b[;40m37.24N\x1b[0m, \x1b[;40m-115.81W\x1b[0m',

        # Accessing arguments’ attributes:
        ('The complex number {0} is formed from the real part {0.real:|BIr} '
         'and the imaginary part {0.imag:|BIb}.', 3-5j):
            'The complex number (3-5j) is formed from the real part '
            '\x1b[;1;3;31m3.0\x1b[0m and the imaginary part '
            '\x1b[;1;3;34m-5.0\x1b[0m.',

        # Accessing arguments’ items:
        ('X: {0[0]};  Y: {0[1]}', (3, 5)):
            'X: 3;  Y: 5',

        # Replacing %s and %r:
        ("repr() shows quotes: {!r:|darksalmon}; str() doesn't: {!s:|pink}",
         'test1', 'test2'):
            "repr() shows quotes: \x1b[;38;2;233;150;122m'test1'\x1b[0m; str() "
            "doesn't: \x1b[;38;2;255;192;203mtest2\x1b[0m",

        # Aligning the text and specifying a width:
        ('{:<30|g/c}', 'left aligned'):
            '\x1b[;32;46mleft aligned                  \x1b[0m',
        ('{:>30|g/c}', 'right aligned'):
            '\x1b[;32;46m                 right aligned\x1b[0m',
        ('{:^30|g/c}', 'centered'):
            '\x1b[;32;46m           centered           \x1b[0m',
        ('{:*^30|g/c}', 'centered'):  # use '*' as a fill char
            '\x1b[;32;46m***********centered***********\x1b[0m',

        # Replacing %+f, %-f, and % f and specifying a sign:
        ('{:+f}; {:+f}', 3.14, -3.14):  # show it always
            '+3.140000; -3.140000',
        ('{: f}; {: f}', 3.14, -3.14):  # show a space for positive numbers
            ' 3.140000; -3.140000',
        ('{:-f}; {:-f}', 3.14, -3.14):  # show only the minus -- same as '{:f}; {:f}'
            '3.140000; -3.140000',

        # Replacing %x and %o and converting the value to different bases:
        # format also supports binary numbers
        ("int: {0:d};  hex: {0:x};  oct: {0:o};  bin: {0:b}", 42):
            'int: 42;  hex: 2a;  oct: 52;  bin: 101010',
        # with 0x, 0o, or 0b as prefix:
        ("int: {0:d};  hex: {0:#x};  oct: {0:#o};  bin: {0:#b}", 42):
            'int: 42;  hex: 0x2a;  oct: 0o52;  bin: 0b101010',

        # Using the comma as a thousands separator:
        ('{:,}', 1234567890):
        '1,234,567,890',

        # Expressing a percentage:
        ('Correct answers: {:.2%}', 19/22):
            'Correct answers: 86.36%',

        # Using type-specific formatting:

        # ('{:%Y-%m-%d %H:%M:%S}', datetime.datetime(2010, 7, 4, 12, 15, 58)):
        #     '2010-07-04 12:15:58'
    },

    # Nesting arguments and more complex examples:
    **{mock('{0:{fill}{align}16}', text, fill=align, align=align): rhs
        for align, text, rhs in zip('<^>',
                                    ['left', 'center', 'right'],
                                    ('left<<<<<<<<<<<<',
                                     '^^^^^center^^^^^',
                                     '>>>>>>>>>>>right'))},

    **{('{:02X}{:02X}{:02X}{:02X}', *[192, 168, 0, 1]):
       'C0A80001'},

    # Parsing multiple stacked effects
    **{mock('|{:*^100|B,r,_/teal}|', 'Hello world!'):
        '|\x1b[;1;31;4;48;2;0;128;128m'
        '********************************************'
        'Hello world!'
        '********************************************'
        '\x1b[0m|',

        mock('{:|rBI_/k}', 'Hello world!'):
        '\x1b[;31;1;3;4;40mHello world!\x1b[0m',

        mock('{:|red,B,I,_/k}', 'Hello world!'):
        '\x1b[;31;1;3;4;40mHello world!\x1b[0m',

        mock('{:|aquamarine,I/lightgrey}', 'Hello world!'):
        '\x1b[;38;2;127;255;212;3;48;2;211;211;211mHello world!\x1b[0m',

        mock('{:|[122,0,0],B,I,_/k}', 'Hello world!'):
        '\x1b[;38;2;122;0;0;1;3;4;40mHello world!\x1b[0m',

        # Nested with alignment spec
        mock('{{name:s|g}:{line:d|orange}: <21}', name='xyz', line=666):
            '\x1b[;32mxyz\x1b[0m:\x1b[;38;2;255;165;0m666\x1b[0m              ',

        # abstracted effects
        mock('{{level}: {message}:|{effects}}',
             level='WARNING', message='Dragons!', effects='Br'):
        '\x1b[;1;31mWARNING: Dragons!\x1b[0m',

        # Nested field names
        mock('{{{name}.{function}:|green}:{line:d|orange}: <25}|'
             '{{level}: {message}:|rB_}',
             name='test', function='func', line=1, level='INFO', message='hi!'):
        '\x1b[;32mtest.func\x1b[0m:\x1b[;38;2;255;165;0m1\x1b[0m              |'
        '\x1b[;31;1;4mINFO: hi!\x1b[0m',

        # Format a stylized string
        mock('\x1b[;1;34m{elapsed:s}\x1b[0m|{\x1b[;32m{name}.{function}\x1b[0m:'
             '\x1b[;38;2;255;165;0m{line:d}\x1b[0m: <78}|\x1b[;34;1m{level}: '
             '{message}\x1b[0m\n',
             elapsed='12.1', name='obstools.campaign',
             function='shocCampaign.load_files', line=122, level='INFO',
             message='x'):
             '\x1b[;1;34m12.1\x1b[0m|'
             '\x1b[;32mobstools.campaign.shocCampaign.load_files\x1b[0m:'
             '\x1b[;38;2;255;165;0m122\x1b[0m                                 |'
             '\x1b[;34;1mINFO: x\x1b[0m\n'
       }
})

# Partial resolution
exp = Expected(Formatter().format_partial)
exp.is_method = False
test_partial_format = exp({
    mock('{elapsed:s|Bb}|'
         '{{{name}.{function}:|green}:{line:d|orange}: <52}|'
         '{{level}: {message}:|{style}}',
         style='crimson'
         ): '\x1b[;1;34m{elapsed:s}\x1b[0m|{\x1b[;32m{name}.{function}\x1b[0m:'
            '\x1b[;38;2;255;165;0m{line:d}\x1b[0m: <84}|'
            '\x1b[;38;2;220;20;60m{level}: {message}\x1b[0m'

})


# f"{String('Hello world'):rBI_/k}"
# f"{String('Hello world'):red,B,I,_/k}"
# String.format("{'Hello world':aquamarine,I/lightgrey}")
# String("{'Hello world':[122,0,0],B,I,_/k}")
