from .str import SuperString, overlay
from recipes.misc import getTerminalSize
from sys import stdout

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def move_cursor(val):
    '''move cursor up or down'''
    AB = 'AB'[val>0]               #move up (A) or down (B)
    mover = '\033[{}{}'.format(abs(val), AB)
    stdout.write(mover)


#****************************************************************************************************
class ProgressBar(object):
    #TODO: Timing estimate!?
    #TODO: Get it to work in qtconsole  (cursor movements not working!)  NOTE: This is probably impossible with text progressbar
    #TODO: capture sys.stdout ????
    '''
    A basic progress bar intended to be used inside a function or for-loop which
    executes 'end' times
    
    Note: print (stdout.write) statements inside the for loop will screw up
    the progress bar.
    '''
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __init__(self, **kw):
        ''' '''
        self.sigfig             = kw.get('sigfig',     3 )
        self.width              = kw.get('width',      getTerminalSize()[0] )
        self.symbol             = kw.get('symbol',     '*' )
        self.nbars              = kw.get('nbars',      1 )
        self.alignment          = kw.get('align',      ('^','<') )      #centering for percentage, info
        self.infoloc            = kw.get('infoloc',    'above' ).lower()
        self.infospace          = kw.get('infospace',  0 )
        self.props              = kw.get('properties' )
        
        self.bar_wrapper        = '{0}\n{1}{0}'.format( self.symbol*self.width, '\n'*self.nbars )
        
        self.space              = (self.sigfig + 6)                             #space needed for percentage string (5 for xxx.pp% and one more for good measure)
        #self.move_up            = '\033[{}A'.format( self.nbars-1 )             #how much should the cursor move up again
        #self.move_down          = '\033[{}B'.format( self.nbars-1 )
        
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def create(self, end):
        '''create the bar and move cursor to it's center'''
        
        self.end = end
        infospacer = '\n' * self.infospace
        
        if self.infoloc in ('above','top'):
            whole = infospacer + self.bar_wrapper
            move = -self.nbars                           #how much should the cursor move up again to center in bar wrapper
        
        if self.infoloc in ('below','bottom'):
            whole = self.bar_wrapper +  infospacer
            move =  -self.nbars - self.infospace
        
        if self.infoloc in ('center', 'bar'):
            whole = self.bar_wrapper
            move = -self.nbars
        
        stdout.write( self.apply_props(whole) + '\r' )
        move_cursor(move)                        #center cursor in bar
        
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def apply_props(self, string):
        if isinstance(self.props, dict):
            string = SuperString(string).set_property(**self.props)
        else:
            string = SuperString(string).set_property(self.props)
        return string
        
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def update(self, state):
        '''Make progress/percentage indicator strings.'''
        
        frac = state/self.end   if self.end>1   else 1 #???
        ifb = int( round(frac*self.width) )                                     #integer fraction of completeness of for loop
        progress = (self.symbol*ifb).ljust( self.width )                        #filled up to 'width' in whitespaces
        percentage = '{0:>{1}.{2}%}'.format(frac, self.space, self.sigfig)                      #percentage completeness displayed to sigfig decimals
        
        return progress, percentage
    
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def overlay(self, text, bgtext='', alignment='^', width=None):
        
        layer = ft.partial( overlay, alignment=alignment, width=width )
        args = itt.zip_longest(text.split('\n'), bgtext.split('\n'), fillvalue='')
        #TODO: truncate if longer than available space????
        ov = '\n'.join( itt.starmap(layer, args) )
        return ov

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def progress(self, state, info=None):
        
        if state < self.end:
            progress, percentage = self.update( state+1 )
            alp, ali = self.alignment
            bar = overlay(percentage, progress, alp)
                
            stdout.write( '\r' + self.apply_props(bar) )
            
            if info:
                info = self.overlay(info, '', ali or '<', self.width)
                nn = info.count( '\n' )
                
                #if nn > self.infospace:
                    #print(nn, self.infospace, '!!')
                    #raise ValueError
                #print( info )
                
                if self.infoloc in ('above','top'):
                    
                    move_cursor( -self.infospace )
                    stdout.write( info )
                    move_cursor( self.infospace-nn-1 )
                    
                #bar = self.overlay(info, progress, ali)
                #stdout.write( self.move_down )            #cursor down
                #stdout.write( '\r' + bar )
                #stdout.write( self.move_up )            #cursor up
            
            stdout.flush()
        
        if state == self.end-1:
            progress, percentage = self.update( self.end )
            alp, ali = self.alignment
            bar = overlay(percentage, progress, alp)
                
            stdout.write( '\r' + self.apply_props(bar) )
            
            self.close()
        
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def close(self):
        stdout.write('\n'*4)                # move the cursor down 4 lines
        stdout.flush()