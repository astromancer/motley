import os
import sys
import math
import time
import functools

from recipes.misc import getTerminalSize
from recipes.string import overlay
# from recipes.progressbar import ProgressBarBase
from . import codes


def move_cursor(val):
    """move cursor up or down"""
    AB = 'AB'[val > 0]  # move up (A) or down (B)
    mover = '\033[{}{}'.format(abs(val), AB)
    sys.stdout.write(mover)


class ProgressBar(object):
    # TODO: convert to base class
    # TODO: Timing estimate!?
    # TODO: Get it to work in qtconsole  (cursor movements not working!)  NOTE: This is probably impossible with text progressbar
    # TODO: capture sys.stdout ????  optional stream
    """
    A basic progress bar intended to be used inside a function or for-loop which
    executes 'end' times

    Note: print (sys.stdout.write) statements inside the for loop will screw up
    the progress bar.
    """

    def __init__(self, **kws):
        """ """
        self.sigfig = kws.get('sigfig', 2)
        self.width = kws.get('width', getTerminalSize()[0])
        self.symbol = kws.get('symbol', '*')
        self.sides = kws.get('sides', '|')
        self.nbars = kws.get('nbars', 1)
        self.alignment = kws.get('align', ('^', '<'))  # centering for percentage, info
        self.infoloc = kws.get('infoloc', 'above').lower()
        self.infospace = kws.get('infospace', 0)
        self.props = kws.get('properties')
        self.show_eta = kws.get('eta', False)

        wraps, empty = ['{1}{0}{1}'.format(sym * (self.width - 2), self.sides)
                        for sym in (self.symbol, ' ')]
        self.bar_wrapper = '{0}\n{1}{0}'.format(wraps, (empty + '\n') * self.nbars)

        self.t0 = time.time()
        self.progress = self.timer(self.progress)

        # space needed for percentage string (5 for xxx.pp% and one more for good measure)
        # self.space              = (self.sigfig + 6)

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
        self.every = math.ceil((10 ** -(self.sigfig + 2)) * self.end)  # only have to updat text every so often

        infospacer = '\n' * self.infospace

        if self.infoloc in ('above', 'top'):
            whole = infospacer + self.bar_wrapper
            move = -self.nbars  # how much should the cursor move up again to center in bar wrapper

        if self.infoloc in ('below', 'bottom'):
            whole = self.bar_wrapper + infospacer
            move = -self.nbars - self.infospace

        if self.infoloc in ('center', 'bar'):
            whole = self.bar_wrapper
            move = -self.nbars

        stream.write(
            codes.apply(whole, self.props) + '\r')
        move_cursor(move)  # center cursor in bar

    def update(self, state):
        """Make progress/percentage indicator strings."""

        frac = state / self.end if self.end > 1 else 1  # ???
        ifb = int(round(frac * (self.width - 2)))  # integer fraction of completeness of for loop

        progress = (self.symbol * ifb).ljust(self.width - 2)  # filled up to 'width' in whitespaces
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

            # if nn > self.infospace:
            # print(nn, self.infospace, '!!')
            # raise ValueError
            # print( info )

            if self.infoloc in ('above', 'top'):
                move_cursor(-self.infospace)
                sys.stdout.write(info)
                move_cursor(self.infospace - nn - 1)

                # bar = self.overlay(info, progress, ali)
                # sys.stdout.write( self.move_down )            #cursor down
                # sys.stdout.write( '\r' + bar )
                # sys.stdout.write( self.move_up )            #cursor up

        sys.stdout.flush()

    def close(self):
        sys.stdout.write('\n' * 4)  # move the cursor down 4 lines
        sys.stdout.flush()
