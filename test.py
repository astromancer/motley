import sys


#
# ESC = '\033'
# CSI = ESC + '['
#
# sys.stdout.write('-'*80)
# sys.stdout.write(CSI + 's')
# sys.stdout.write('\n'*5)
# sys.stdout.write(CSI + 'u')
# sys.stdout.write('hello')


if __name__ == '__main__':
    import numpy as np
    from ansi import rainbow

    #
    # print(rainbow('joe', 'rgb'))
    # print(rainbow('joe', bg='rgb'))

    h = np.arange(19, dtype=int).astype(str)
    flags = np.array([{'bg': ' '}, {'bg': ' '}, {'bg': ' '}, {'bg': 'r'}, {'bg': ' '},
       {'bg': ' '}, {'bg': ' '}, {'bg': 'y'}, {'bg': ' '}, {'bg': ' '},
       {'bg': ' '}, {'bg': ' '}, {'bg': ' '}, {'bg': ' '}, {'bg': ' '},
       {'bg': ' '}, {'bg': ' '}, {'bg': 'y'}, {'bg': 'y'}], dtype=object)
    print(rainbow(h, flags))