# third-party
import numpy as np
from scipy.stats import multivariate_normal

# local
from motley.image import AnsiImage


# r = np.random.randint(0, 256, (10, 10))
# # im = AnsiImage(r, frame=True).render()


# im = BinaryImage(r >= 128).render()


def test_display():
    
    # 2D Gaussian
    mu = (0, 0)
    covm = np.array([[0.5,  1.2],
                     [0.6,  1.2]])
    rv = multivariate_normal(mu, covm)
    Y, X = np.mgrid[-3:3:10j, -3:3:10j]
    grid = np.array([X, Y])
    Zg = rv.pdf(grid.transpose(1, 2, 0)).T
    ai = AnsiImage(Zg)
    # ai.render(frame=True)

    ai.overlay(Zg > 0.01, 'red')

    #ai.pixels = overlay(Zg > 0.01, ai.pixels[::-1])[::-1].astype(str)
    ai.render(frame=True)


# if __name__ == "__main__":

#     test_display()
