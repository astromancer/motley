"""
Output tables to Excel spreadsheet
"""


# std
import itertools as itt
import numpy as np

# third-party
import more_itertools as mit
from openpyxl import Workbook
from openpyxl.cell import Cell
from openpyxl.styles import Alignment, Border, Font, Side

# local
from recipes import op
from recipes.string import sub
from recipes.lists import where_duplicate
from recipes.string.brackets import BracketParser


ALIGNMENT_MAP = {'>': 'right',
                 '<': 'left',
                 '^': 'center'}
square_brackets = BracketParser('[]')
_xl_fmt_nondisplay = {'"': '', '@': ''}

# def stack_cell_attributes(cell, kws):
#     keys = ('alignment', 'font', 'border', 'fill')
#     props = op.AttrDict(*keys)(cell)
#     try:
#         # TypeError: unhashable type: 'StyleProxy'
#         op.AttrSetter(*keys)(cell, {**kws, **props})
#     except Exception as err:
#         import sys, textwrap
#         from IPython import embed
#         from better_exceptions import format_exception
#         embed(header=textwrap.dedent(
#                 f"""\
#                 Caught the following {type(err).__name__} at 'xlsx.py':25:
#                 %s
#                 Exception will be re-raised upon exiting this embedded interpreter.
#                 """) % '\n'.join(format_exception(*sys.exc_info()))
#         )
#         raise


def set_style(cell, kws):
    op.AttrSetter(*kws.keys())(cell, kws.values())


def set_block_attrs(cells, **kws):
    itr = [cells] if isinstance(cells, Cell) else mit.flatten(cells)
    for cell in itr:
        # stack_cell_attributes(cell, kws)
        set_style(cell, kws)
        # for key, val in kws.items():
        #     setattr(cell, key, val)

# def get_col_width():


def get_col_widths(table, requested=(), fallback=4, minimum=3):

    # headers = table.col_headers
    width = fallback
    requested = mit.padded(requested, 0)
    for i, (reqw, col) in enumerate(zip(requested, zip(*table.data))):
        if reqw:
            yield reqw
            continue

        if (fmt := table.formatters.get(i)) and isinstance(fmt, str):
            # sub non-display characters in excel format string
            width = max((len(sub(square_brackets.remove(f), _xl_fmt_nondisplay))
                         for f in fmt.split(';')))
        else:
            # width = table.col_width[i]
            try:
                width = max(map(len, col))
            except TypeError:
                pass

        header = table.col_headers[i]
        repeats = list(table.col_headers).count(header)
        hwidth = (len(header) * 1.2 / repeats)   # fudge factor for font
        # logger.debug(i, header, hwidth, fwidth, width, minimum)
        yield max(hwidth, width, minimum)


class XlsxWriter:

    def __init__(self):

        self.workbook = Workbook()
        self.worksheet = self.workbook.active
        # worksheet.title = ""

        # styling defaults
        font = dict(name='Ubuntu Mono',
                         size=10)
        font_data = Font(**font)
        rule = Side('thin')
        rule2 = Side('double')
        self.header_style = dict(
            font=Font(name='Libertinus Sans',
                      size=12,
                      bold=True),
            alignment=Alignment(horizontal='center',
                                vertical='center',
                                wrap_text=True),
            border=Border(bottom=rule2)
        )
        self.style_units = dict(
            font=font_data,
            alignment=Alignment(horizontal='center',
                                vertical='top'),
            border=Border(bottom=rule2)
        )
        self.style_data = dict(
            font=font_data,
            alignment=Alignment(horizontal='center',
                                vertical='center')
        )
        self.style_totals = dict(
            font=Font(**font, bold=True),
            border=Border(bottom=rule, top=rule)
        )

    def write(self, table, path, widths=None, merge_unduplicate=()):
        # ('rows', 'cells')

        self.col_widths = np.array(list(get_col_widths(table, widths)))
        self.alignments = [Alignment(ALIGNMENT_MAP[_]) for _ in table.align]

        ncols = table.shape[1]
        j = ncols + 65  # column index: ord(65) == 'A'

        # title
        self.make_header_row([table.title] * ncols)

        # col group headers
        for groups in table.col_groups:
            self.make_header_row(groups, 'cells' in merge_unduplicate)

        # headers
        # headers = table.get_headers()
        self.make_header_row(table.col_headers, 0)

        # units
        self.append(table.units, **self.style_units)

        # -------------------------------------------------------------------- #
        # data
        ws = self.worksheet
        r0 = ws._current_row + 1  # first data row

        for r, row in enumerate(table.data, r0):
            self.append(row)
        r = ws._current_row

        # -------------------------------------------------------------------- #
        # Totals
        if table.totals:
            totals = [''] * ncols
            for i in table.totals:
                totals[i] = f'=SUM({(c:=i+65):c}{r0}:{c:c}{r})'

            #           data    row style
            self.append(totals, **self.style_totals)

            r += 1

        # -------------------------------------------------------------------- #
        # Set number formats
        for idx, fmt in table.formatters.items():
            if isinstance(fmt, str):
                col = chr(idx + 65)
                # logger.debug(col, fmt)
                set_block_attrs(ws[f'{col}{r0}:{col}{r}'],
                                number_format=fmt)

        # style for "data" cells
        set_block_attrs(ws[f'A{r0}:{j-1:c}{r}'], **self.style_data)

        # set col widths
        # double_rows = defaultdict(bool)
        # z = bool(table.title) + 1
        for idx, width in enumerate(self.col_widths):
            # logger.debug(idx, table.col_headers[idx], width)
            
            ws.column_dimensions[chr(idx + 65)].width = width
            # double_rows[z] |= ('\n' in table.col_headers[idx])
            # double_rows[z + 1] |= ('\n' in table.col_groups[idx])

        # for r, tf in double_rows.items():
        #     if tf:
        #         ws.row_dimensions[r].height = 10 * 3

        if 'rows' in merge_unduplicate:
            self.merge_duplicate_rows(table.data, r0,
                                      )

        self.workbook.save(path)
        return self.workbook

    def append(self, data, **style):
        if data is None:
            return

        sheet = self.worksheet
        sheet.append(list(data))
        r = sheet._current_row
        cells = sheet[f'A{r}:{len(data) + 64:c}{r}'][0]
        if self.alignments:
            for i, cell in enumerate(cells):
                style.update(alignment=self.alignments[i])
                set_style(cell, style)
        else:
            set_block_attrs(cells, **style)
        return r

    def should_double_height(self, row, merged):
        unmerged = zip(set(range(len(row))) - set(sum(merged, [])))

        for i in (*merged, *unmerged):
            content, width = row[i[0]], self.col_widths[i].sum()
            if (isinstance(content, str) and
                    (('\n' in content) or len(content) > width)):

                return True

    def make_header_row(self, row, merge_duplicate_cells=2, **style):
        if row is None:
            return

        j = len(row) + 65
        sheet = self.worksheet
        r = sheet._current_row + 1  # next(row_nr)

        # logger.debug(row)
        self.append(row)
        merged = self.merge_duplicate_cells(r, row, merge_duplicate_cells)

        # logger.debug(row, self.should_double_height(row, merged))
        if self.should_double_height(row, merged):
            # style.setdefault('alignment', self.align_center_wrap)
            ws = self.worksheet
            ws.row_dimensions[ws._current_row].height = 10 * 3

        set_block_attrs(sheet[f'A{r}:{j - 1:c}{r}'],
                        **{**self.header_style, **style})

    def merge_duplicate_rows(self, data, r0, **style):
        for i, col in enumerate(data.T, 65):
            for idx in where_duplicate(col):
                j, *_, k = idx
                # logger.debug(idx, j, k + 1)
                if idx != list(range(j, k + 1)):
                    continue

                # logger.debug(i, j, k, r0)
                # logger.debug(f'merging {i:c}{j + r0}:{i:c}{k + r0}')
                set_style(self.worksheet[f'{i:c}{j + r0}'], style)
                self.worksheet.merge_cells(f'{i:c}{j + r0}:{i:c}{k + r0}')

    def merge_duplicate_cells(self, row_index, data, trigger=2):
        merged = where_duplicate(data)
        for j, *_, k in merged:
            val = data[j]
            if val and (k - j >= trigger):
                cell = f'{j + 65:c}{row_index}'
                # logger.debug(f'Merging:{cell}:{k + 65:c}{row_index}')
                self.worksheet.merge_cells(f'{cell}:{k + 65:c}{row_index}')

        return merged

    # def _write_attr_table(self, table, data, path):

    #     ncols = len(table.attrs)

    #     # title
    #     self.make_header_row(itt.repeat(table.title, ncols),
    #                          border=Border(bottom=Side('double')))

    #     # col group headers
    #     self.make_header_row(table.get_groups())

    #     # row headers

    #     j = ncols + 65

    #     # headers
    #     headers = table.get_headers()
    #     self.make_header_row(headers, 0)

    #     # units
    #     self.append(table.get_units(),
    #                 font=self.font_data,
    #                 alignment=self.align_center,
    #                 border=Border(bottom=Side('double')))

    #     # populate data
    #     ws = self.worksheet
    #     r0 = ws._current_row
    #     for r, row in enumerate(data, r0):
    #         self.append(row)
    #     r = ws._current_row

    #     # Totals
    #     if table.totals:
    #         totals = [f'=SUM({c:c}{r0}:{c:c}{r})'
    #                   if attr in table.totals else '' for c,
    #                   attr in enumerate(table.attrs, 65)]
    #         self.append(totals,
    #                     # style for totals line
    #                     border=Border(bottom=Side('thin'), top=Side('thin')),
    #                     font=self.font_totals)
    #         r += 1

    #     # ---------------------------------------------------------------------------- #
    #     # Set number formats
    #     for attr, fmt in table.formatters.items():
    #         col = chr(table.attrs.index(attr) + 65)
    #         # print(col, fmt)
    #         set_block_attrs(ws[f'{col}{r0}:{col}{r}'], number_format=fmt)

    #     # set font for all other cells
    #     set_block_attrs(ws[f'A{r0}:{j-1:c}{r-1}'], font=self.font_data)

    #     # set col widths
    #     # double_row = False
    #     itr = zip(table.attrs, zip(*data))
    #     for col, (attr, data) in enumerate(itr, 65):

    #         width = get_col_width(table, attr)
    #         # print(hdr, width)
    #         ws.column_dimensions[chr(col)].width = width
    #         # double_row |= ('\n' in hdr)

    #     # if double_row:
    #     #     ws.row_dimensions[2].height = font_normal_size * 3

    #     self.workbook.save(path)
