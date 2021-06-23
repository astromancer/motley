from decor.profile import profile
import time

profiler = profile()

@profiler.histogram
def func(i): 
    j = i * i
    j= i ** 3
    time.sleep(1)
    time.sleep(1.3)
    time.sleep(1.5)
    time.sleep(1.8)
    time.sleep(0.9)
    #do other useful stuff
    return

func(100)