from motley.table import Table
import numpy as np


def test_formatters_mixed():
    Table([['foo', 1.44],
           ['bar', 3.14]],
          col_headers=['one', 'two'],
          formatters={0: str, 'two': '{:.3f}'.format})


def random_words(word_size, n_words, ord_range=(97, 122)):
    return list(map(''.join,
                    np.vectorize(chr)(
                            np.random.randint(*ord_range, (n_words, word_size))
                    )))


# TODO: loads more basic tests to showcase functionality

data = np.random.randn(10, 10)
tbl = Table(data)
print(tbl)

Table(data,
      title='Random data',
      precision=3,
      title_props=dict(txt=('bold', 'm'), bg='g'))

Table(data,
      title='Random data',
      precision=3,
      title_props=(dict(txt=('bold', 'm'), bg='g')),
      totals=True,
      row_nrs=True,
      col_headers=random_words(5, 10),
      col_head_props=('italic', 'y'))

Table.from_columns(*np.random.randn(3, 10),
                   *np.random.randint(0, 1000, (3, 10)),
                   title='Mixed float, int',
                   precision=3, minimalist=True,)
                   #title_props=(dict(txt=('bold', 'm'), bg='g')),
                   #total=True,
                   #row_nrs=True,
                   #col_headers=random_words(5, 10),
                   #col_head_props=('italic', 'y'))

# # from dict
# Ncpus = 8
# nproc = OrderedDict(('find', Ncpus),
#                     ('fit', 2 * Ncpus),
#                     ('phot', 2 * Ncpus),
#                     ('bg', 2 * Ncpus),
#                     ('defer', 2))
# table = Table(title='Load balance', data=nproc, order='r')
# print(table)

# test_simple
# test_alignment
# test auto alignment
# test compactify
# test auto format
# test highlight
# test multiline cells
# test ansi input
