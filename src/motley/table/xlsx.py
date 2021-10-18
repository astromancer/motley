"""
Output tables to Excel spreadsheet
"""


# std
import itertools as itt

# third-party
import more_itertools as mit
from openpyxl import Workbook
from openpyxl.cell import Cell
from openpyxl.styles import Alignment, Border, Font, Side

# local
from recipes.lists import tally


def set_block_attrs(cells, **kws):
    itr = [cells] if isinstance(cells, Cell) else mit.flatten(cells)
    for cell in itr:
        for key, val in kws.items():
            setattr(cell, key, val)


class XlsxWriter:

    def __init__(self,
                 font=dict(name='Ubuntu Mono', size=10),
                 font_header=dict(name='Libertinus Sans', size=12, bold=True)):

        self.workbook = Workbook()
        self.worksheet = self.workbook.active
        # worksheet.title = ""
        self.font_header = Font(**font_header)
        self.font_data = Font(**font)
        self.font_totals = Font(**font, bold=True)
        self.align_center_top = Alignment(horizontal='center', vertical='top')
        self.align_center_wrap = Alignment(horizontal='center', vertical='top',
                                           wrap_text=True)
        self.header_border = Border(bottom=Side('double'))

    def write(self, table, path, widths=None, show_singular_groups=False):

        self.col_widths = table.col_widths if widths is None else widths

        ncols = table.shape[1]

        # title
        self.make_header_row(itt.repeat(table.title, ncols))

        # col group headers
        self.make_header_row(table.col_groups, show_singular_groups)

        # row headers

        j = ncols + 65

        # headers
        # headers = table.get_headers()
        self.make_header_row(table.col_headers, 0)

        # units
        self.append(table.units,
                    font=self.font_data,
                    alignment=self.align_center_top,
                    border=Border(bottom=Side('double')))

        # populate data
        ws = self.worksheet
        r0 = ws._current_row + 1  # first data row

        for r, row in enumerate(table.data, r0):
            self.append(row)
        r = ws._current_row

        # Totals
        if table.totals:
            totals = [f'=SUM({c:c}{r0}:{c:c}{r})'
                      if attr in table.totals else ''
                      for c, attr in enumerate(table.col_headers, 65)]
            self.append(totals,
                        # style for totals line
                        border=Border(bottom=Side('thin'), top=Side('thin')),
                        font=self.font_totals)
            r += 1

        # ---------------------------------------------------------------------------- #
        # Set number formats
        for idx, fmt in table.formatters.items():
            if isinstance(fmt, str):
                col = chr(idx + 65)
                # print(col, fmt)
                set_block_attrs(ws[f'{col}{r0}:{col}{r}'],
                                number_format=fmt)

        # set font for all other cells
        set_block_attrs(ws[f'A{r0}:{j-1:c}{r}'], font=self.font_data)

        # set col widths
        # double_rows = defaultdict(bool)
        # z = bool(table.title) + 1
        for idx, width in enumerate(self.col_widths):
            # print(idx, table.col_headers[idx], width)
            # print(idx, table.col_headers[idx], width)

            ws.column_dimensions[chr(idx + 65)].width = width
            # double_rows[z] |= ('\n' in table.col_headers[idx])
            # double_rows[z + 1] |= ('\n' in table.col_groups[idx])

        # for r, tf in double_rows.items():
        #     if tf:
        #         ws.row_dimensions[r].height = 10 * 3

        self.workbook.save(path)

    def append(self, row, **style):
        if row is None:
            return

        sheet = self.worksheet
        sheet.append(list(row))
        r = sheet._current_row
        set_block_attrs(sheet[f'A{r}:{len(row) + 64:c}{r}'], **style)
        return r

    def should_double_height(self, row):
        for content, width in zip(row, self.col_widths):
            if (isinstance(content, str) and
                    (('\n' in content) or len(content) > width)):
                return True

    def make_header_row(self, row, trigger=2, **style):
        if row is None:
            return

        i = 65
        sheet = self.worksheet
        r = sheet._current_row + 1  # next(row_nr)
        for header, count in tally(row).items():
            j = i + count
            cell = f'{i:c}{r}'
            if header and count >= trigger:
                print(header, f'{cell}:{j:c}1')
                sheet[cell] = header#.title()
                sheet.merge_cells(f'{cell}:{j - 1:c}{r}')
            i = j

        #
        # print(row, self.should_double_height(row))
        if self.should_double_height(row):
            style.setdefault('alignment', self.align_center_wrap)
            ws = self.worksheet
            ws.row_dimensions[ws._current_row].height = 10 * 3

        set_block_attrs(sheet[f'A{r}:{j - 1:c}{r}'],
                        **{**dict(font=self.font_header,
                                  alignment=self.align_center_top,
                                  border=self.header_border),
                           **style})

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
    #                 alignment=self.align_center_top,
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
