from motley.image import AnsiImage, UnicodeBinaryImage
import numpy as np


r = np.random.randint(0, 256, (10, 10))
# im = AnsiImage(r, frame=True).render()


im = UnicodeBinaryImage(r >= 128).render()