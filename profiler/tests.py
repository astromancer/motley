import time
import logging

from motley import profiler

logging.basicConfig(level=logging.DEBUG)

@profiler.histogram()
def foo():
    """
    Sample docstring
    """
    time.sleep(0.1)
    time.sleep(0.2)
    time.sleep(0.3)
    time.sleep(0.5)
    time.sleep(0.3)
    time.sleep(0.2)
    time.sleep(0.1)

    # comment
    time.sleep(1e-5)
    time.sleep(0)


foo()

