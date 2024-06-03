
# std
from pathlib import Path
from string import Template

# third-party
import numpy as np

# local
from recipes import string

# relative
from ..utils import ALIGNMENT_MAP_INV
from . import Table


# ---------------------------------------------------------------------------- #
#

class LatexTable(Table):

    MID_BORDER = ' & '
    RIGHT_BORDER = R' \\'
    LEFT_BORDER = ''
    # latex symbol nrs header
    NRS_HEADER = R'\#'

    booktabs = True

    def _toprule(self, _):
        if self.frame:
            yield rf"\{'toprule' if self.booktabs else 'hline'}"

    def _midrule(self, text):
        yield text
        yield rf"\{'midrule' if self.booktabs else 'hline'}"

    # def _bottomrule(self, _):
    #     return
    #     yield

# ---------------------------------------------------------------------------- #


class LatexWriter:

    def __init__(self, table):
        self.table = table

    def __call__(self, path=None, style='table', tabsize=2, overwrite=False, **kws):
        text = self.to_text(style, tabsize, **kws)
        if path:
            path = Path(path).resolve()
            if not path.exists() or overwrite:
                path.write_text(text)

        return text

    def to_text(self, style, tabsize=2, **kws):
        fname = f'_to_{style}'
        worker = getattr(self, fname, None)
        if worker is None:
            raise NotImplementedError(
                f'Latex table style {style!r} not supported.'
            )

        # reindent
        table = worker(**kws, tabsize=tabsize)
        return '\n'.join(map(str.rstrip,  table.splitlines()))

    def _tabular_body(self,
                      booktabs=True, indent=2,
                      flag_fmt=R'$\:^{{{flag}}}$',
                      foot_fmt=R'\hspace{{1eM}}$^{{{flag}}}$\ {info}\\',
                      summary_fmt=R'\hspace{{1eM}}{{{key[-1]} = {val}<? [{unit}]?>}}\\',
                      **kws):

        # setup for latex
        LatexTable.booktabs = booktabs

        tbl = LatexTable.from_table(
            self.table,
            title=False,
            col_headers=self.table.col_headers[1:],
            col_head_style=None,
            row_nrs=1,
            whitespace=0,
            too_wide=False,
            col_borders=LatexTable.MID_BORDER,
            summary=dict(footer=True, n_cols=1, bullets='', align='<',
                         ignore=['t0'], fmt=summary_fmt),
            flag_fmt=flag_fmt,
            foot_fmt=foot_fmt,
            **kws
        )
        tbl.borders[-1] = LatexTable.RIGHT_BORDER

        # Hack out the footnotes for formatting downstream
        footnotes = tbl.footnotes[:]
        tbl.footnotes = []
        return tbl, footnotes

    def _tabular_colspec(self, tbl):
        col_spec = list(map(ALIGNMENT_MAP_INV.get, tbl.align[tbl._idx_shown]))
        # letters = list(map(chr, range(65, 65 + len(col_spec))))
        letters = [f'{i:c}' for i in range(65, 65 + len(col_spec))]
        letters[0] = f'% {letters[0]}'
        col_spec = LatexTable(
            [letters, col_spec],
            col_borders=[*[LatexTable.MID_BORDER] * (len(letters) - 1), ''],
            frame=False, too_wide=False
        )
        # col_spec._idx_shown = tbl._idx_shown
        widths = tbl.col_widths[tbl._idx_shown]
        col_spec.max_width = 1000  # HACK since split is happening here... FIXME
        # widths[widths  spec_widths] =
        col_spec.col_widths = widths = np.max([[*map(len, letters)], widths], 0)
        col_spec.truncate_cells(widths)
        letters, spec = map(str.rstrip, str(col_spec).splitlines())

        return '\n'.join((letters, spec.replace('&', ' ')))

    def _to_table(self, star='*', pos='ht!',
                  options=R'\centering',
                  caption=None, cap=None,
                  label=None, env='tabular',
                  booktabs=True, tabsize=2):

        # options
        star = '*' if star else ''
        cap = f'[{{{cap!s}}}]' if cap else ''
        caption = fR'\caption{cap}{{{caption}}}' if caption else ''
        label = fR'\\label{{{label}}}' if label else ''

        #
        tbl, footnotes = self._tabular_body(booktabs, tabsize)
        if footnotes:
            footnotes = f'\n{" " * tabsize}'.join(np.char.strip(footnotes))

        # get column spec
        template = Template(
            string.reindent(R'''
                \begin{table$star}[$pos]
                    $options
                    $caption
                    $label
                    %
                    \begin{$env}{%
                        $colspec
                        }
                        $body
                    \end{$env}

                    \footnotesize
                    \raggedright
                    $footnotes
                \end{table$star}
                ''', tabsize)
        )

        colspec = string.indent(self._tabular_colspec(tbl), tabsize * 2)
        body = string.indent(str(tbl), tabsize * 2)
        if booktabs:
            body = string.replace_suffix(body, R'\midrule', R'\bottomrule')

        return template.substitute(locals())

    def _to_ctable(self, options='star, nosuper', pos='ht!',
                   caption=None, cap=None, label=None,
                   hspace_body='-1.5cm', hspace_footer='-1.2cm',
                   booktabs=True, tabsize=2):

        options = f',\n{" " * tabsize}'.join(
            filter(None, (f'{options}',
                          f'{pos     = !s}',
                          f'caption = {{{caption!s}}}' if caption else '',
                          f'cap     = {{{cap!s}}}' if cap else '',
                          f'{label   = !s}' if label else ''))
        )

        tbl, footnotes = self._tabular_body(
            booktabs, tabsize,
            flag_fmt=R'\tmark[$\:{{{flag}}}$]',
            foot_fmt=R'\tnote[$^{{{flag}}}\:$]{{{info}}}',
            summary_fmt=R'\tnote[{{}}]{{{key} = {val}<? {unit}?>}}'
        )

        hack = '% ' if (len(tbl._idx_shown) < 7) else ''
        template = Template(string.reindent(R'''
            \ctable[
                $options,
                % hack to move table into left margin
                ${hack}doinside= {\hspace*{$hspace_body}}
            ]{
                % column spec
                $colspec
            }{
                % footnotes
                % also move footnotes to keep alignment consistent
                $hack\hspace*{$hspace_footer}
                $footnotes
            }{
                % tabular body
                $body
            }
            '''), tabsize)
        return template.substitute(
            locals(),
            body=string.indent(tbl, tabsize),
            colspec=self._tabular_colspec(tbl),
            footnotes=f'\n{" " * tabsize}'.join(footnotes)
        )

    def _to_tabularray(self, options='',  # pos='ht!',
                       caption=None, cap=None, label=None,
                       hspace_body='-1.5cm', hspace_footer='-1.2cm',
                       booktabs=True, tabsize=2):

        options = f',\n{" " * tabsize}'.join(
            filter(None, (f'{options}',
                          #   f'{pos     = !s}',
                          f'caption = {{{caption!s}}}' if caption else '',
                          f'entry   = {{{cap!s}}}' if cap else '',
                          f'{label   = !s},' if label else ''))
        )

        tbl, footnotes = self._tabular_body(
            booktabs, tabsize,
            flag_fmt=R'\TblrNote{{{flag}}}',
            foot_fmt=R'note{{${{{flag}}}$}} = {{{info}}},',
            summary_fmt=R'remark{{{key}}} = {{{val}{unit}}},'
        )

        template = Template(string.reindent(R'''
            \begin{tblr}[
                % outer spec
                $options
                % footnotes
                % \hspace*{$hspace_footer}
                $footnotes
            ]{% inner spec
                % Column headers (to appear on every page for page-split tables)
                row{1-2} = {c, m, font=\bfseries},
                rowhead = 2,
                % rowfoot = 1,
                colspec={
                $colspec
                },
            }
            $body
            \end{tblr}
            ''', tabsize))
        return template.substitute(
            locals(),
            colspec=self._tabular_colspec(tbl, tabsize),
            body=string.indent(tbl, tabsize),
            footnotes=f'\n{" " * tabsize}'.join(footnotes)
        )
