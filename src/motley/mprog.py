import multiprocessing as mp

from lll import SynchedCounter

from ansi.progress import ProgressBar

import time
        
#====================================================================================================
def init(counter):
    ''' initialize shared objects '''
    global progress
    progress = counter

def work(i):
    time.sleep(0.001)
    progress.inc()
    bar.progress(progress.value())
    #if not (progress % 100):
        #print(progress)

N = 5000

bar = ProgressBar(symbol='=', properties={'bg':'green'})
bar.create(N)

pool = mp.Pool(initializer=init,
               initargs=(SynchedCounter(0),))

pool.map(work, range(N), chunksize=100)
pool.close()
pool.join()
