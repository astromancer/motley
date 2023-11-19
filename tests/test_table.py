
# third-party
import numpy as np

# local
from motley.table import Table


def random_words(word_size, n_words, ord_range=(97, 122)):
    return list(map(''.join,
                    np.vectorize(chr)(
                            np.random.randint(*ord_range, (n_words, word_size))
                    )))

def test_formatters_mixed():
    Table([['foo', 1.44],
           ['bar', 3.14]],
          col_headers=['one', 'two'],
          formatters={0: str, 'two': '{:.3f}'.format})

# TODO: loads more basic tests to showcase functionality

# TODO: automated way of looping through all possible argument combinations
#  that make sense?? --> pytest.mark.parametrize!!


# test_simple
nr, nc = 5, 8
data = np.random.randn(nr, nc)
tp = (dict(txt=('bold', 'm'), bg='g'))

tables = [
    # test_simple
    Table(data),

    # test title
    Table(data,
          title='Random data',
          precision=3,
          title_style=tp),

    # test col_headers
    Table(data,
          title='Random data',
          precision=3,
          title_style=tp,
          total=True,
          row_nrs=True,
          col_headers=random_words(5, nc),
          col_head_style=('italic', 'y')),

    # test terse keywords
    Table(data,
          title='Random data',
          nrs=True,
          chead=random_words(5, nc),
          chead_prop=('italic', 'y')),

    # test minimalist
    Table.from_columns(*np.random.randn(3, nc),
                       *np.random.randint(0, 1000, (3, nc)),
                       title='Mixed float, int',
                       precision=3, minimalist=True, ),

    # test auto alignment
    # test summerize
    # test auto format
    # test highlight
    # test multiline cells
    # test ansi input

    Table(data,
          title='Random data',
          precision=3,
          title_style=(dict(txt=('bold', 'm'), bg='g')),
          totals=True,
          row_nrs=True,
          col_headers=random_words(5, nc),
          col_head_style=('italic', 'y')),

    Table.from_columns(*np.random.randn(3, nc),
                       *np.random.randint(0, 1000, (3, nc)),
                       title='Mixed float, int',
                       precision=3, minimalist=True, ),
    # title_style=(dict(txt=('bold', 'm'), bg='g')),
    # total=True,
    # row_nrs=True,
    # col_headers=random_words(5, 10),
    # col_head_style=('italic', 'y'))
]

for tbl in tables:
    print(tbl)

# # from dict
# Ncpus = 8
# nproc = OrderedDict(('find', Ncpus),
#                     ('fit', 2 * Ncpus),
#                     ('phot', 2 * Ncpus),
#                     ('bg', 2 * Ncpus),
#                     ('defer', 2))
# table = Table(title='Load balance', data=nproc, order='r')
# print(table)
