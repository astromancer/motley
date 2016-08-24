import sys

ESC = '\033'
CSI = ESC + '['

sys.stdout.write('-'*80)
sys.stdout.write(CSI + 's')
sys.stdout.write('\n'*5)
sys.stdout.write(CSI + 'u')
sys.stdout.write('hello')