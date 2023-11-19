# third-party
import more_itertools as mit

# relative
from . import codes


# # Demo 256 colours
#       0 - 7:      standard colors (as in ESC [ 30–37 m)
#       8 - 15:     high intensity colors (as in ESC [ 90–97 m)
#       16-231:     6 × 6 × 6 cube (216 colors):
#                       16 + 36 × r + 6 × g + b (0 ≤ r, g, b ≤ 5)
#       232-255:    grayscale from black to white in 24 steps
#

def make_line(start, stop, width=10):
    fmt = '{0:^%i}' % width
    return ''.join(codes.apply(fmt.format(i),
                               fg='wb'[((i - 16) % 36) > 17],
                               bg=i)
                   for i in range(start, stop))


def demo_8bit():
    w = 10
    print('\t', '{0:^{1}}'.format('Standard', w * 7),
          '\t' * 2, '{0:^{1}}'.format('High Intensity', w * 7), '\n',
          '\t', make_line(0, 7, w),
          '\t' * 2, make_line(8, 15, w))

    print('{0:^{1}}'.format('216 Colours', 5 * 36))
    for start, stop in mit.pairwise(range(16, 256, 36)):
        print(make_line(start, stop, 5))

    print('{0:^{1}}'.format('Grayscale colors', 5 * 36))
    print(make_line(232, 255, 7))
