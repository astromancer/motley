"""
Functions that extract and time all import statements from python source code
"""

# std
import ast
import sys
import math
import warnings

# local
from recipes.io import read_lines

# relative
from .core import LineProfiler
from .printers import ReportDynamicFunction


def get_block(filename, up_to_line):
    """"""
    # lines = read_file_slice(filename, None)
    lines = read_lines(filename, up_to_line)
    # NOTE: partial code blocks lead to `SyntaxError: unexpected EOF while parsing`
    # might be better to advance until the next

    # if len(lines) and lines[-1].startswith('' * 4):
    #     # only go up to nearest un-indented line above `up_to_line`
    #     lines = lines[:-lines[::-1].index('\n') - 1]
    # could also try: `inspect.getblock(lines)` though this would limit us to imports from first
    # code block only
    # lines = inspect.getblock(lines) # FIXME: sometimes only returns first line of module docstring
    content = '\n'.join(lines)
    return content


def no_future(lines):
    # exclude from __future__ import since it will bork
    newlines = []
    for line in lines:
        if '__future__' in line:
            warnings.warn('Cannot profile "from __future__" imports. Removing.')
        else:
            newlines.append(line)
    return newlines


def extractor(filename, up_to_line=None):
    """
    Tokenizer that extracts all the import statements from python source code
    file.

    Parameters
    ----------
    filename: str
        The source code file - example.py
    up_to_line: int
        Maximal search depth (line nr) in source code file

    Returns
    -------
    imports: str
        code block containing extracted import statements

    """
    from recipes.introspect.imports import ImportCapture, rewrite

    with open(filename) as fp:
        source = fp.read()

    # extract all import statements up to maxLines
    net = ImportCapture(up_to_line or math.inf, filter_unused=False)
    tree = net.visit(ast.parse(source))

    lines = []
    for lnr, stm in zip(net.line_nrs, tree.body):
        line = rewrite(stm)

        # exclude from __future__ import since it will bork
        if 'from __future__' in line:
            warnings.warn("Cannot profile 'from __future__' imports. "
                          "Commenting out line nrs %s during profiling."
                          % lnr)
            line = '# %s' % line

        if line.startswith('from .'):
            warnings.warn("Cannot profile relative imports. "
                          "Commenting out line nrs %s during profiling."
                          % lnr)
            line = '# %s' % line

        lines.append(line)
    return lines


def _construct_importer(filename, up_to_line, name='importer'):
    lines = extractor(filename, up_to_line)
    if lines:
        # create the function object from extracted source code str
        lines = ['def %s():' % name] + lines
        source = '\n\t'.join(lines).expandtabs()

        # build the importer function
        try:
            exec(source)
        except Exception as err:
            raise Exception(
                    'Could not build import function due to the following  '
                    'exception: %s' % str(err))

        return eval(name), source
    return None, None


class DynamicFunctionProfiler(LineProfiler):

    def __init__(self, *args, **kws):
        LineProfiler.__init__(self, *args, **kws)
        self._source_lib = {}

    def print_stats(self, **kws):
        printer = ReportDynamicFunction(contents=self._source_lib, **kws)
        printer(self.get_stats())

    def add_dynamic_function(self, func, source):
        self.add_function(func)
        self._source_lib[func] = source


# def main():


if __name__ == '__main__':
    # Todo print some info so we know wtf is happening

    import argparse

    parser = argparse.ArgumentParser(
            prog='motley.profiling.imports',
            description="Profile your modules import statements easily")
    parser.add_argument('filename', type=str)
    parser.add_argument('up_to_line', type=int, nargs='?', default=math.inf)
    args = parser.parse_args(sys.argv[1:])

    #
    importer, source = _construct_importer(args.filename, args.up_to_line)
    if importer:
        # setup profiling
        profiler = DynamicFunctionProfiler()
        profiler.add_dynamic_function(importer, source)
        profiler.enable_by_count()

        # run the dynamically generated function
        importer()

        # print the results
        profiler.print_stats(strip=False)   # ('#', '', '<1e-5')
    else:
        print('No import statements found.')
