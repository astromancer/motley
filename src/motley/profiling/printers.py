"""
Printers for displaying profiled source code
"""

# builtin libs
# std
import re
import ast
import sys
import inspect
import textwrap
import functools as ftl
from io import StringIO

# third-party
import numpy as np
import more_itertools as mit

# local
from recipes import pprint
from recipes.lists import where
from recipes.introspect import get_defining_class

# relative
from .. import codes
from ..table import Table
from ..codes.utils import length


# FIXME: line stripping still buggy

# TODO: print std if more than one hit per line  σ =
# TODO: make all tables same width for consistency for multi print
# TODO: Heatmap256

cdot = u'\u00B7'  # '·'


def func2str(func):

    if (cls := get_defining_class(func)) is not None:
        return '.'.join((cls.__name__, func.__name__))

    if isinstance(func, ftl.partial):
        func = func.func
        argstr = str(func.args).strip(')') + f', {cdot})'
        return f'partial({func2str(func.func)}{argstr})'

    return func.__name__


def truncate_block_gen(block, width, dots='...'):
    """
    Truncate a block of text at given *width* adding ellipsis to indicate missing
    text
    """
    le = length(dots)
    for line in block:
        if len(line) > width:  # need to truncate
            yield line[:(width - le)] + dots
        else:  # fill to width with whitespace
            yield '{0:<{1:d}}'.format(line, width)


def truncate_block(block, width, dots='...'):
    return list(truncate_block_gen(block, width, dots))


def make_bar(line, fraction, line_width, colour):
    if l := int(np.round(fraction * line_width)):
        bar = codes.apply(line[:l], bg=colour)
        return bar + line[l:]
    return line


def _ast_func_index(source):
    """
    Parse the function definition. Return line indices for the definition head
    (including docstring).  Here the docstring is taken to be the first
    expression in the function body if that is a str.

    Parameters
    ----------
    source: str
        raw source code str

    Returns
    -------
    line_nr_def: int
        line number for start of function definition
    line_nr_doc, line_nr_doc_end: int
        The start and end line numbers for the docstring if any
    line_nr_body: int
        line number for start of function body
    """
    # adapted from: https://stackoverflow.com/a/11609209/1098683

    tree = ast.parse(source)
    doc_raw = line_nr_doc = line_nr_doc_end = line_nr_def = line_nr_body = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            # now at start of function / class def
            line_nr_def = node.lineno - 1
            if (node.body and isinstance(node.body[0], ast.Expr) and
                    isinstance(node.body[0].value, ast.Str)):
                # now at first str expression ==> docstring
                doc_raw = node.body[0].value.s
            # get line number of first non-docstring statement
            if len(node.body) > 1:  # function has content
                line_nr_body = node.body[1].lineno - 1
            else:  # function has no content besides docstring
                line_nr_body = node.body[0].lineno - 1
            # and we're done
            break

    assert line_nr_def is not None, 'No class or function definition found!'
    # this should never happen

    if line_nr_def == line_nr_body:
        # one liner like `class Foo: ""` or `def foo(): pass`
        if doc_raw is not None:  # no docstring
            line_nr_doc = line_nr_doc_end = line_nr_def
        return line_nr_def, line_nr_doc, line_nr_doc_end, line_nr_body

    # now that we have the function definition head, find the docstring
    if doc_raw is not None:
        sourceLines = source.splitlines()
        head = '\n'.join(sourceLines[line_nr_def:line_nr_body + 1])
        # escape regex characters in docstring
        matcher = re.compile(
            '[^"\']*?(["\']{1,3})(%s)(\\1)' % re.escape(doc_raw))
        for m in matcher.finditer(head):
            pass  # go to last match

        # docstring including single/triple quotes
        # doc_repr = source[m.start(1):m.end(3)]

        # line index of dostring
        line_nr_doc = source[:m.start(1)].count('\n')
        line_nr_doc_end = source[:m.end(3)].count('\n')

    return line_nr_def, line_nr_doc, line_nr_doc_end, line_nr_body


# ****************************************************************************************************
class ReportStats:
    """
    Helper class that prints profiling results for a single function when called.
    This base class is essentially an OO (and therefore extensible) version of
    the native `LineProfiler.print_stats` with better handling of interactively
    defined functions.
    """

    column_headers = '#', 'Hits', 'Time', 'Per Hit', '% Func', '% Total', 'Line Contents'
    header_template = '{:6} {:9} {:12} {:8} {:8} {:8} {}'
    template = '{:<6} {:>9} {:>12} {:>8} {:>6.2%}, {:>6.2%} {}'

    def __call__(self, line_stats):

        not_run = []
        timings = line_stats.timings
        ran = map(bool, map(len, timings.values()))
        many_ran = sum(ran) > 1  # we have results for more than one func

        for (filename, start_line_no, func), (stats, total) in timings.items():
            if len(stats):
                self.show_func(func, stats, line_stats.unit, total, many_ran)
            else:  # No timings ==> function not executed
                # print these at the end
                not_run.append(func2str(func))

        if not_run:
            print('\nThe following functions where not executed:\n\t%s'
                  % '\n\t'.join(not_run))

    def show_func(self, func, stats, unit, total, show_fot=True, stream=None):
        """
        Show profiling results for a single function.

        Note that this method takes the actual function object as its 1st
        argument and not just the function name as is the case with the
        `line_profiler.show_func`.  This offers several advantages, the foremost
        being that we can retrieve the source code for functions
        defined in interactive sessions with minimal effort.
        """

        # get function source
        filename, start_line_nr, lines = self.get_block(func)
        end_line_nr = start_line_nr + len(lines)

        self.start = start_line_nr
        self.ignoreLines = []
        self.sourceCodeLines = lines
        self.unit = unit

        # process lines
        self.preprocess(stats, start_line_nr, end_line_nr)

        # funcName = func.__name__
        name = func2str(func)
        self.preamble(filename, name, start_line_nr, total, stream)
        self.header(stream)
        self.table(stats, show_fot, stream)
        self.closing(stream)

    def get_block(self, func):
        # get function source
        filename = inspect.getfile(func)
        source_code_lines, start_line_nr = inspect.getsourcelines(func)

        # strip newlines from source and unindent
        source = ''.join(source_code_lines)
        source_code_lines = textwrap.dedent(source).splitlines()
        # source_code_lines = [line.strip('\n') for line in source_code_lines]

        return filename, start_line_nr, source_code_lines

    def preprocess(self, *args, **kws):
        """
        Optionally implemented in subclass to pre-process the raw source code
        lines for display
        """
        pass

    def enumerate(self):  # source_code, ignore
        """
        Generator that enumerates code lines filtering those in `ignoreLines`
        """
        i = self.start
        for line in self.sourceCodeLines:
            if i not in self.ignoreLines:
                yield i, line
            i += 1

    def preamble(self, filename, func_name, start_line_nr, total_time,
                 stream=None):
        """print preamble"""
        stream = stream or sys.stdout
        stream.write(textwrap.dedent(
            """
                File: %s
                Function: %s at line %s
                Total time: %g s""".lstrip('\n')
            % (filename, func_name, start_line_nr, total_time)))

    def header(self, stream=None):
        """print header"""
        stream = stream or sys.stdout
        # TODO: add time unit (ms)??
        header = self.header_template.format(self.column_headers)
        underline = '=' * len(header)
        stream.write("\n%s\n%s\n" % (header, underline))

    def table(self, stats, show_fot, stream=None):
        """print stats table"""
        stream = stream or sys.stdout
        empty = ('',) * 5
        for lineNo, line in self.enumerate():
            nhits, time, per_hit, fof, fot = stats.get(lineNo, empty)
            txt = self.template.format(
                lineNo, nhits, time, per_hit, fof, fot, line)
            stream.write(txt)
            stream.write("\n")

    def closing(self, stream=None):
        """print any closing remarks"""
        stream = stream or sys.stdout
        stream.write("\n")


class ReportStatsTable(ReportStats):
    """
    Extend the standard profile display with multiple options for how to format
    the returned source code body based on the profiling statistics.

    Optionally show timing stats visually as a "bar chart" (using ANSI
    background highlight) behind the source code lines that are most
    expensive. Allows one to see at a glance which code lines are more expensive
    """
    # TODO option to show outside table so not overlapping with source

    comment = r'\s*#'  # match only whitespace followed by comment #
    commentMatcher = re.compile(comment)

    # any of these can be passed to strip docstring
    docIds = {'"""', "'''", 'doc', 'docstring'}
    commentIds = {'#', 'comment', 'comments'}
    blankIds = {'', ' ', 'blank'}
    zeroIds = {0, '0', 'zero', 'zeros'}

    # printing
    dots = codes.apply(cdot * 3, 'r', 'bold')
    bar_color = 'g'

    # TODO: Don't strip lines that are part of multi-line statement
    # TODO: Optionally keep lines that determine statement nesting
    #  (eg if, for while etc)

    # def __init__(self, **kws):
    #     pass

    # TODO: optionally sort most expensive first?
    #     self.timings = lstats.timings
    #     self.unit = lstats.unit
    # self.stream = stream or sys.stdout

    def __init__(self, **kws):
        # ReportStats.__init__(self, **kws)

        # FIXME: blank lines not being stripped correctly
        # FIXME: keep scope lines when stripping

        # default is to strip comment lines, blank lines, docstrings.
        # lines that are fast running can be removed from the report by
        # passing strip = ('<0.001', ) where the number represents the
        # fraction of total execution time. In the example above lines that
        # took less than 1000th of total execution time of the function will
        # not be shown in the report
        strip = set(kws.get('strip', ('#', '', '"""')))

        # To keep source verbatim in report use strip=False or strip=None
        if strip in (None, False):
            strip = set()

        self.strip_docstring = self.docIds & strip
        self.strip_comments = self.commentIds & strip
        self.strip_blanks = self.blankIds & strip
        self.strip_zeros = self.zeroIds & strip

        handled = (self.strip_docstring | self.strip_comments |
                   self.strip_blanks | self.strip_zeros)
        unhandled = (strip - handled)

        self.smallest = 0
        for s in unhandled.copy():
            if s.startswith('<'):
                # strip lines with smaller fractional execution time
                self.smallest = float(s.strip('<'))
                unhandled.remove(s)
        if len(unhandled):
            raise ValueError(f'Unknown option(s) for strip keyword: {tuple(unhandled)}')

        self.max_line_width = kws.get('max_line_width')  # maxLineWidth
        self.where_gaps = []

    # def show_func(self, filename, start_line_no, func, timings,
    #               unit, output_unit=None, stream=None):
    #     # call the base printer
    #     ReportStats.show_func(self, filename, start_line_no, func, timings, unit,
    #                          output_unit, stream)

    def preprocess(self, stats, start_line_nr, end_line_nr):
        """pre-process the raw source code lines for display"""
        ignore = []
        source_lines = self.sourceCodeLines
        start, end = start_line_nr, end_line_nr

        # FIXME: not stripping correct lines......

        if self.strip_docstring:
            source = '\n'.join(source_lines)
            # identify various parts of the function in the source code
            line_nr_def, line_nr_doc, line_nr_doc_end, line_nr_body \
                = _ast_func_index(source)

            if (line_nr_doc is not None) and (line_nr_doc != line_nr_def):
                # source code relative line numbers
                line_nrs_doc = np.arange(line_nr_doc,
                                         line_nr_doc_end + 1) + start
                ignore.extend(line_nrs_doc)

        if self.strip_comments:
            line_nrs_comment = where(source_lines, self.commentMatcher.match)
            ignore.extend(np.add(line_nrs_comment, start))

        if self.strip_blanks:
            line_nrs_blank = where(source_lines, str.isspace)  # only whitespace
            ignore.extend(np.add(line_nrs_blank, start))
            line_nrs_empty = where(source_lines, '')  # empty lines
            ignore.extend(np.add(line_nrs_empty, start))

        if self.strip_zeros:
            # no timing stats available for these lines (i.e. they where not
            # executed)
            # Make sure we do not ignore the function `def` line and preceding
            # decorators
            line_nrs = set(range(line_nr_body + start, end + 1))
            line_nrs_no_stats = line_nrs - set(stats.keys())
            ignore.extend(line_nrs_no_stats)

        if self.smallest:
            # strip any line times smaller than smallest
            line_nrs_stats, data = zip(*stats.items())
            *stuff, fractions = zip(*data)
            small = np.less(fractions, self.smallest)
            line_nrs_small = np.array(line_nrs_stats)[small]
            ignore.extend(line_nrs_small)

        # FIXME: not showing ellipses for first skipped block

        # remove isolated lines from ignore list
        # If we are inserting ellipsis to indicate missing blocks, it's defies
        # the purpose to do so for a single skipped line
        ignore = sorted(set(ignore))
        if len(ignore) > 1:
            singleSkip = (np.diff(ignore) == 1)  # isolated ignore lines.
            wms, = np.where(~singleSkip)
            splitBlockIx = np.split(ignore, wms + 1)
            skipBlockSize = np.array(list(map(len, splitBlockIx)))  #

            ix = [splitBlockIx[i] for i in np.where(skipBlockSize == 1)[0]]
            ignore = list(set(ignore) - set(mit.collapse(ix)))

            # ignore now contains only indices of continuous multi-line code
            # blocks to skip when printing

            # figure out where the gaps are in the displayed code so we can
            # indicate gaps with ellipsis
            lineIxShow = sorted(set(range(start, end)) - set(ignore))
            nrpairs = np.array(list(mit.pairwise(lineIxShow + [end])))
            gaps = nrpairs.ptp(1)  # np.subtract(*zip(*nrpairs))
            self.where_gaps = nrpairs[gaps > 1][:, 0]
            # relative to source code line numbers
        else:
            ignore = []

        #
        self.ignoreLines = ignore
        # truncate and fill lines with whitespace to create block text
        if self.max_line_width:
            self.sourceCodeLines = truncate_block(source_lines,
                                                  self.max_line_width,
                                                  self.dots)

    def preamble(self, filename, func_name, start_line_nr, total_time,
                 stream=None):
        # intercept the preamble text so we can use it as a table header
        self._preamble = StringIO()
        filename = codes.apply(filename, 'y')
        name = codes.apply(func_name, 'b')
        ReportStats.preamble(
            self, filename, name, start_line_nr, total_time, self._preamble)

    def header(self, stream=None):
        # for the table we need tuple of headers not formatted str, so pass
        pass

    def table(self, stats, show_fot=True, show_hits=None, stream=None):
        """
        make the time table and write to stream
        """
        stream = stream or sys.stdout

        empty = ('',) * 5
        n = len(self.sourceCodeLines) - len(self.ignoreLines) + \
            len(self.where_gaps)
        table = np.empty((n, 7), 'O')

        lineLength = min(max(map(len, self.sourceCodeLines)), 80)
        # at this point all lines are the same length (NOT ALWAYS~!!)
        # lineLength = len(self.sourceCodeLines[0])
        where_row_borders = [0]  # first border after column headers
        i = 0

        for lineNo, line in self.enumerate():
            nhits, time, per_hit, fof, fot = stats.get(lineNo, empty)
            # Convert fraction to percentage
            # pof, pot = fof * 100, fot * 100
            # make time indicator bar
            if time:  # might be empty str
                line = make_bar(line, fof, lineLength, self.bar_color)
            # populate table
            table[i] = lineNo, nhits, time, per_hit, fof, fot, line
            i += 1

            # print separator lines to segment code blocks
            if lineNo in self.where_gaps:
                # insert blank line to indicate gap!
                table[i] = self.dots, *empty, self.dots
                i += 1
        where_row_borders.append(i)

        # add timing unit to header
        colhead = list(self.column_headers)
        tu = {1e-6: 'μs',
              1e-9: 'ns'}[self.unit]
        colhead[2] = '%s (%s)' % (colhead[2], tu)

        # right align numbered columns
        align = list('>>>>>><')

        # assign column formatters
        #    = '#', 'Hits', 'Time', 'Per Hit', '% Func', '% Total', 'Source'
        pformat = '{:.1%}'.format
        formatters = {'#': str,
                      colhead[2]: ftl.partial(pprint.decimal, precision=0,
                                              thousands=' '),
                      '% Func': pformat,
                      '% Total': pformat}

        # Remove column with percentage of total
        remove_col = []
        if not show_fot:
            remove_col.append(5)
            formatters.pop('% Total')

        # if hits all 1, doesn't make sense to print Hits and Per Hit
        if show_hits is None:
            col = table[:, 1]
            show_hits = np.all(col[col != ''] == 1)

        if show_hits:
            remove_col.extend([1, 3])

        if len(remove_col):
            keep_cols = np.setdiff1d(np.arange(table.shape[1]), remove_col)
            colhead = np.take(colhead, keep_cols)
            align = np.take(align, keep_cols)
            table = table[:, keep_cols]
            # formatters = list(np.take(formatters, keep_cols))

        table = np.ma.MaskedArray(table, table == '')

        # title
        self._preamble.seek(0)
        title = self._preamble.read()
        # create table
        self._table = Table(table,
                            title=title,
                            title_align='left',
                            title_style=dict(text='bold', bg='dark gray'),
                            col_headers=colhead,
                            col_head_style=dict(text=('bold', 'w'), bg='b'),
                            hlines=where_row_borders,
                            align=align,
                            # width=range(1000),
                            formatters=formatters,
                            masked='')

        # large max width so table doesn't split
        stream.write(str(self._table))

        # from IPython import embed
        # embed()


# class ReportHeatMap(ReportStatsTable):
    # TODO


class ReportDynamicFunction(ReportStatsTable):
    """
    Pretty printer for dynamically generated functions
    """

    def __init__(self, **kws):
        self._source_lib = kws.pop('contents')
        ReportStatsTable.__init__(self, **kws)

    def get_block(self, func):
        source_code_lines = self._source_lib[func].splitlines()
        return '__main__', 1, source_code_lines
