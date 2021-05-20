import os
import sys
import math
import time
import functools

from recipes.misc import get_terminal_size
from recipes.string import overlay
# from recipes.progressbar import ProgressBarBase
from . import codes


def move_cursor(val):
    """move cursor up or down"""
    AB = 'AB'[val > 0]  # move up (A) or down (B)
    mover = '\033[{}{}'.format(abs(val), AB)
    sys.stdout.write(mover)


class ProgressBar(object):  # TODO use tqdm instead ......
    # TODO: convert to base class
    # TODO: Timing estimate!?
    # TODO: Get it to work in qtconsole  (cursor movements not working!)
    #  NOTE: This is probably impossible with text progressbar
    # TODO: capture sys.stdout ????  optional stream
    """
    A basic progress bar intended to be used inside a function or for-loop which
    executes 'end' times

    Note: print (sys.stdout.write) statements inside the for loop will screw up
    the progress bar.
    """

    def __init__(self, precision=2, width=None, symbol='*', sides='|', n_bars=1,
                 align=('^', '<'), info_loc='above', info_space=0, eta=False,
                 **kws):
        """ """
        # TODO: make wrap optinal
        self.sigfig = int(precision)
        self.width = width or get_terminal_size()[0]
        self.symbol = str(symbol)
        self.sides = str(sides)
        self.n_bars = int(n_bars)
        # centering for percentage, info
        self.alignment = align
        self.info_loc = info_loc
        self.info_space = int(info_space)
        self.props = kws
        self.show_eta = bool(eta)

        fmt = '{3}{0:{1}<{2}}{3}'
        w = self.width - 2 * len(self.sides)
        wraps = fmt.format('', self.symbol, w, self.sides)
        empty = fmt.format('', '', w, self.sides)
        empty = os.linesep.join(((empty,) * self.n_bars))
        self.bar_wrapper = '{0}\n{1}\n{0}'.format(wraps, empty)

        self.t0 = time.time()
        self.progress = self.timer(self.progress)

        # space needed for percentage string (5 for xxx.pp% and one more for
        # good measure)
        # self.space              = (self.sigfig + 6)

    def __enter__(self):
        print('HI!')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print('BYE!')
        self.close()

    def timer(self, f):

        @functools.wraps(f)
        def wrapper(*args, **kw):
            ts = time.time()
            result = f(*args, **kw)
            te = time.time()
            self.deltat = te - ts

        return wrapper

    def create(self, end, stream=sys.stdout):
        """create the bar and move cursor to it's center"""

        self.end = end
        self.every = math.ceil((10 ** -(self.sigfig + 2)) * self.end)
        # only have to update text every so often

        info_spacer = '\n' * self.info_space

        if self.info_loc in ('above', 'top'):
            whole = info_spacer + self.bar_wrapper
            move = -self.n_bars
            # how much should the cursor move up again to center in bar wrapper

        if self.info_loc in ('below', 'bottom'):
            whole = self.bar_wrapper + info_spacer
            move = -self.n_bars - self.info_space

        if self.info_loc in ('center', 'bar'):
            whole = self.bar_wrapper
            move = -self.n_bars

        stream.write(
                codes.apply(whole, self.props) + '\r')
        move_cursor(move)  # center cursor in bar

    def update(self, state):
        """Make progress/percentage indicator strings."""

        frac = state / self.end if self.end > 1 else 1  # ???
        ifb = int(round(frac * (self.width - 2)))
        # integer fraction of completeness of for loop

        progress = (self.symbol * ifb).ljust(self.width - 2)
        # filled up to 'width' in whitespaces
        progress = self.sides + progress + self.sides
        # percentage completeness displayed to sigfig decimals
        percentage = '{0:.{1}%}'.format(frac, self.sigfig)

        return progress, percentage

    def needs_update(self, state):
        return (state == self.end - 1) or (not bool(state % self.every))

    def get_bar(self, state):
        progress, percentage = self.update(state + 1)
        alp, ali = self.alignment
        bar = overlay(percentage, progress, alp)

        if self.show_eta:
            eta = (self.end - state) * self.deltat
            eta_str = 'ETA: {:.1f} s'.format(eta)
            bar = overlay(eta_str, bar, '<')

        return bar

    def progress(self, state, info=None):  # TODO: make state optional

        if state >= self.end:
            return

        if not self.needs_update(state):
            return  # The state is not significantly different yet

        bar = self.get_bar(state)
        sys.stdout.write('\r' + codes.apply(bar, self.props))

        if state == self.end - 1:
            self.close()
            return

        if info:
            info = self.overlay(info, '', ali or '<', self.width)
            nn = info.count('\n')

            # if nn > self.info_space:
            # print(nn, self.info_space, '!!')
            # raise ValueError
            # print( info )

            if self.info_loc in ('above', 'top'):
                move_cursor(-self.info_space)
                sys.stdout.write(info)
                move_cursor(self.info_space - nn - 1)

                # bar = self.overlay(info, progress, ali)
                # sys.stdout.write( self.move_down )            #cursor down
                # sys.stdout.write( '\r' + bar )
                # sys.stdout.write( self.move_up )            #cursor up

        sys.stdout.flush()

    def close(self):
        sys.stdout.write('\n' * 4)  # move the cursor down 4 lines
        sys.stdout.flush()


if __name__ == '__main__':
    with ProgressBar() as prg:
        prg.create(1000)
        for i in range(1000):
            time.sleep(0.003)
            prg.progress(i)
