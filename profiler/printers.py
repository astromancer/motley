"""
Printers displaying profiled source code
"""

import ast
import inspect
import re
import sys
import textwrap
import functools
from io import StringIO

import numpy as np
from recipes.iter import where_true, where_false, pairwise
from recipes.list import flatten

from .. import codes, length
from ..table import Table


# FIXME: line stripping still buggy

# TODO: print std if more than one hit per line
# TODO: make all tables same width for consistency
# TODO: Heatmap256

cdot = u'\u00B7'

def func2str(func):
    cls = get_class_that_defined_method(func)
    if cls is None:
        if isinstance(func, functools.partial):
            func = func.func
            argstr = str(func.args).strip(')') + ', %s)' % cdot
            return 'partial(%s%s)' % (func2str(func.func), argstr)
        return func.__name__
    else:
        return '.'.join((cls.__name__, func.__name__))


def get_class_that_defined_method(meth):
    # source: https://stackoverflow.com/questions/3589311/get-defining-class-of-unbound-method-object-in-python-3/25959545#25959545

    # handle bound methods
    if inspect.ismethod(meth):
        for cls in inspect.getmro(meth.__self__.__class__):
            if cls.__dict__.get(meth.__name__) is meth:
                return cls
        meth = meth.__func__  # fallback to __qualname__ parsing

    # handle unbound methods
    if inspect.isfunction(meth):
        cls = getattr(inspect.getmodule(meth),
                      meth.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0])
        if isinstance(cls, type):
            return cls

    # handle special descriptor objects
    return getattr(meth, '__objclass__', None)


# ====================================================================================================
def truncateBlockGen(block, width, dots='...'):
    """
    Truncate a block of text at given *width* adding ellipsis to indicate missing
    text
    """
    le = length(dots, raw=False)
    for line in block:
        if len(line) > width:  # need to truncate
            yield line[:(width - le)] + dots
        else:  # fill to width with whitespace
            yield '{0:<{1:d}}'.format(line, width)


def truncateBlock(block, width, dots='...'):
    return list(truncateBlockGen(block, width, dots))


def make_bar(line, fraction, line_width, colour):
    l = int(np.round(fraction * line_width))
    if l:
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
                line_nr_body = node.body[0].lineno
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
        matcher = re.compile('[^"\']*?(["\']{1,3})(%s)(\\1)' % re.escape(doc_raw))
        for m in matcher.finditer(head):
            pass  # go to last match

        # docstring including single/triple quotes
        # doc_repr = source[m.start(1):m.end(3)]

        # line index of dostring
        line_nr_doc = source[:m.start(1)].count('\n')
        line_nr_doc_end = source[:m.end(3)].count('\n')

    return line_nr_def, line_nr_doc, line_nr_doc_end, line_nr_body


# ****************************************************************************************************
class PrintStats(object):
    """
    Helper class that prints profiler results for a single function when called.
    This base class is essentially an OO (and therefore extensible) version of
    the native `LineProfiler.print_stats` with better handling of interactively
    defined functions.
    """

    column_headers = '#', 'Hits', 'Time', 'Per Hit', '% Func', '% Total', 'Line Contents'
    header_template = '{:6} {:9} {:12} {:8} {:8} {:8} {}'
    template = '{:<6} {:>9} {:>12} {:>8} {:>6.2%}, {:>6.2%} {}'

    # TODO: Don't strip lines that are part of multiline statement
    # TODO: Optionally keep lines that determine statement nesting (eg if, for while etc)
    # TODO: option to reset after multiple calls.  may sometimes be desired

    # def __init__(self, **kws):
    #     pass

    # TODO: optionally sort most expensive first?
    #     self.timings = lstats.timings
    #     self.unit = lstats.unit
    # self.stream = stream or sys.stdout

    def print_stats(self, lstats):

        not_run = []
        timings = lstats.timings
        ran = map(bool, map(len, timings.values()))
        many_ran = sum(ran) > 1  # we have results for more than one func

        for (filename, start_line_no, func), (stats, total) in timings.items():
            if len(stats):
                self.show_func(func, stats, lstats.unit, total, many_ran)
            else:  # No timings ==> function not executed
                # print these at the end
                not_run.append(func2str(func))

        if not_run:
            print('\nThe following functions where not executed:\n\t%s'
                  % '\n\t'.join(not_run))

    def show_func(self, func, stats, unit, total, show_fot=True, stream=None):
        """
        Show profiler results for a single function.

        Note that this method takes the actual function object as its third
        argument and not just the function name as is the case with the
        `line_profiler.show_func`.  This offers several advantages, the foremost
        being that we can retreive the function source code for functions
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

    # def table(self, stats, source, ignore):
    def table(self, stats, show_fot, stream=None):
        """print stats table"""
        stream = stream or sys.stdout
        empty = ('', ) * 5
        for lineNo, line in self.enumerate():
            nhits, time, per_hit, fof, fot = stats.get(lineNo, empty)
            txt = self.template.format(
                    lineNo, nhits, time, per_hit, fof, fot, line)
            stream.write(txt)
            stream.write("\n")

    def closing(self, stream=None):
        """print closing remarks"""
        stream = stream or sys.stdout
        stream.write("\n")


# ****************************************************************************************************
class ShowHistogram(PrintStats):
    """
    Extend the standard profile display with multiple options for how to format
    the returned source code body based on the profiling statistics.
    """

    comment = r'\s*#'  # match only whitespace followed by comment #
    commentMatcher = re.compile(comment)

    dots = codes.apply(cdot * 3, 'r', 'bold')
    histogram_color = 'g'

    def __init__(self, **kws):
        # PrintStats.__init__(self, **kws)

        # TODO option to show outside table / overlapping with source

        # default is to strip comment lines, blank lines, docstrings and zero-time lines
        strip = set(kws.get('strip', ('#', '', '"""', '<1e-5')))
        docInd = ('"""', "'''", 'doc', 'docstring')  # any of these can be passed to strip docstring
        commentInd = ('#', 'comment', 'comments')
        blankInd = ('', ' ', 'blank')
        zeroInd = (0, '0', 'zero', 'zeros')

        self.strip_docstring = set(docInd) & strip
        self.strip_comments = set(commentInd) & strip
        self.strip_blanks = set(blankInd) & strip
        self.strip_zeros = set(zeroInd) & strip
        # self.strip_decor = # '@'

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
            raise ValueError('Unknown option(s) for strip keyword: %s'
                             % tuple(unhandled))

        self.gap_borders = kws.get('gap_borders', False)
        self.max_line_width = kws.get('max_line_width')  # maxLineWidth
        self.where_gaps = []

    # def show_func(self, filename, start_line_no, func, timings,
    #               unit, output_unit=None, stream=None):
    #     # call the base printer
    #     PrintStats.show_func(self, filename, start_line_no, func, timings, unit,
    #                          output_unit, stream)

    def preprocess(self, stats, start_line_nr, end_line_nr):
        """pre-process the raw source code lines for display"""
        ignore = []
        source_lines = self.sourceCodeLines
        source = '\n'.join(source_lines)
        start, end = start_line_nr, end_line_nr

        # FIXME: not stripping correct lines......

        if self.strip_docstring:
            # identify various parts of the function in the source code
            line_nr_def, line_nr_doc, line_nr_doc_end, line_nr_body \
                = _ast_func_index(source)

            if (line_nr_doc is not None) and (line_nr_doc != line_nr_def):
                # source code relative line numbers
                line_nrs_doc = np.arange(line_nr_doc, line_nr_doc_end + 1) + start
                ignore.extend(line_nrs_doc)

        if self.strip_comments:
            line_nrs_comment = where_true(source_lines, self.commentMatcher.match)
            ignore.extend(np.add(line_nrs_comment, start))

        if self.strip_blanks:
            line_nrs_blank = where_true(source_lines, str.isspace)  # only whitespace
            ignore.extend(np.add(line_nrs_blank, start))
            line_nrs_empty = where_false(source_lines)  # empty lines
            ignore.extend(np.add(line_nrs_empty, start))

        if self.strip_zeros:
            # no timing stats available for these lines (i.e. they where not executed)
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
            singleSkip = np.diff(ignore) == 1  # isolated ignore lines.
            wms, = np.where(~singleSkip)
            splitBlockIx = np.split(ignore, wms + 1)
            skipBlockSize = np.array(list(map(len, splitBlockIx)))  #
            ix = np.take(splitBlockIx, np.where(skipBlockSize == 1))
            ignore = list(set(ignore) - set(flatten(ix)))
            # ignore now contains only indices of continuous multiline code blocks to skip when printing

            # figure out where the gaps are in the displayed code so we can indicate gaps with ellipsis
            lineIxShow = sorted(set(range(start, end)) - set(ignore))
            nrpairs = np.array(list(pairwise(lineIxShow)))
            gaps = np.subtract(*zip(*nrpairs))
            self.where_gaps = nrpairs[gaps < -1][:, 0]  # relative to source code line numbers
        else:
            ignore = []

        self.ignoreLines = ignore
        # truncate and fill lines with whitespace to create block text
        if self.max_line_width:
            self.sourceCodeLines = truncateBlock(source_lines,
                                                 self.max_line_width,
                                                 self.dots)

    def preamble(self, filename, func_name, start_line_nr, total_time, stream=None):
        # intercept the preamble text so we can use it as a table header
        self._preamble = StringIO()
        filename = codes.apply(filename, 'y')
        name = codes.apply(func_name, 'b')
        PrintStats.preamble(self, filename, name, start_line_nr, total_time,
                            self._preamble)

    def header(self, stream=None):
        # for the table we need tuple of headers not formatted str, so pass
        pass

    def table(self, stats, show_fot=True, stream=None):
        """make the time table and write to stream"""
        stream = stream or sys.stdout

        empty = ('',) * 5
        n = len(self.sourceCodeLines) - len(self.ignoreLines) + len(self.where_gaps)
        table = np.empty((n, 7), 'O')

        # at this point all lines are the same length
        lineLength = len(self.sourceCodeLines[0])
        where_row_borders = [0]  # first border after column headers
        i = 0
        for lineNo, line in self.enumerate():
            nhits, time, per_hit, fof, fot = stats.get(lineNo, empty)
            # Convert fraction to percentage
            pof, pot = fof * 100, fot * 100
            # make time indicator bar
            if time:  # might be empty str
                line = make_bar(line, fof, lineLength, self.histogram_color)
            # populate table
            table[i] = lineNo, nhits, time, per_hit, fof, fot, line
            i += 1

            # print separator lines to segment code blocks
            if lineNo in self.where_gaps:
                if self.gap_borders:
                    where_row_borders.append(i + 1)
                # insert blank line to indicate gap!
                table[i] = self.dots, *empty, self.dots
                i += 1
        where_row_borders.append(i)

        # add timing unit to header
        colhead = list(self.column_headers)
        tu = {1e-6: 'μs'}[self.unit]
        colhead[2] = '%s (%s)' % (colhead[2], tu)

        # right align numbered columns
        align = list('>>>>>><')

        # Remove column with percentage of total
        if not show_fot:
            colhead.pop(-2)
            table = np.delete(table, -2, 1)
            align = np.delete(align, -2)


        # title
        self._preamble.seek(0)
        title = self._preamble.read()
        # create table
        self._table = Table(table,
                            title=title,
                            title_align='left',
                            title_props=dict(text='bold', bg='dark gray'),
                            col_headers=colhead,
                            col_head_props=dict(text=('bold', 'w'), bg='b'),
                            where_row_borders=where_row_borders,
                            align=align,
                            precision=3, minimalist=True,
                            width=range(1000))  # large max width so table doesn't split
        stream.write(str(self._table))


class ShowDynamicFunction(ShowHistogram):
    """
    Pretty printer for dynamically generated functions
    """
    # FIXME: show the file name in header
    # FIXME: show the actual source line numbers
    # FIXME: remove def line for print

    def __init__(self, **kws):
        self._source_lib = kws.pop('contents')
        ShowHistogram.__init__(self, **kws)

    def get_block(self, func):
        source_code_lines = self._source_lib[func].splitlines()
        return '__main__', 0, source_code_lines




if __name__ == '__main__':
    from recipes.iter import pairwise


    def show_func_parts(source):
        exec(source)  # make sure source code has valid syntax
        indices = _ast_func_index(source)
        sourceLines = source.splitlines()
        for i0, i1 in pairwise((0,) + indices + (None,)):
            if i0 is not None:
                print('\n'.join(sourceLines[i0:i1]))
                print('-' * 50)


    def bla(f):  # do nothing decorator for testing
        return f


    foo = bla

    # some source code snippets
    source = [
        'class Foo: ""',

        'def foo(): pass',

        '''
        def foo(*zzz,
                **gork): "bad"
        ''',

        r'''
        @bla
        class Foo:
            """
            lol
            """
            'yo'
        ''',

        r'''
    
    
        @bla
        @foo
        def find_def(source_code_lines
    
    
                        ) -> 'hi':
    
    
            """
            lol
            """
    
    
            # some comment
            pass
        ''',

        r'''
        @bla
        class Foo:
            """
            lol
            """
            'your mamma'
        ''',

        '''
        @bla
        @foo
        def horrible(baz, *a, z='""""""', zz={'#'},
                            **kws
                            ) -> "valid syntax":    "bad style docstring"; 1+1
        ''']
