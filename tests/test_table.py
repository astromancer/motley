from motley.table import Table


def test_formatters_mixed():
    Table([['foo', 1.44],
           ['bar', 3.14]],
          col_headers=['one', 'two'],
          formatters={0: str, 'two': '{:.3f}'.format})
