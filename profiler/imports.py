"""
Functions that extract and time all import statements from python source code
"""

import ast
import sys
import math
import warnings
from io import StringIO

from recipes.io import read_file_slice
from motley.profiler.core import HLineProfiler
from motley.profiler.printers import ShowDynamicFunction


def get_block(filename, up_to_line):
    """"""
    # lines = read_file_slice(filename, None)
    lines = read_file_slice(filename, up_to_line)
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


def depends_on(filename, up_to_line=None):
    code = get_block(filename, up_to_line)
    tree = ast.parse(code)
    visitor = ModuleExtractor()
    visitor.visit(tree)
    return visitor.modules


def no_future(lines):
    # exclude from __future__ import since it will bork
    newlines = []
    for line in lines:
        if '__future__' in line:
            warnings.warn("Cannot profile 'from __future__' imports. Removing.")
        else:
            newlines.append(line)
    return newlines


def extractor(filename, up_to_line=None):
    """
    Tokenizer that extracts all the import statements from python source code file

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

    with open(filename) as fp:
        code = fp.read()

    # extract all import statements up to maxLines
    tree = ast.parse(code)
    iv = ImportFinder(up_to_line or math.inf)
    iv.visit(tree)

    if iv.line_nrs:
        importLines = code.splitlines()[:iv.line_nrs[-1]]
        # TODO: handle edge case - last found import statement in multi-line. this will bork

        # exclude from __future__ import since it will bork
        if iv.future:
            warnings.warn("Cannot profile 'from __future__' imports. Commenting"
                          " out line nrs %s during profiling." % iv.future)
        for ln in iv.future:
            importLines[ln - 1] = '# %s' % importLines[ln - 1]

        return importLines
    return []


def _construct_importer(filename, up_to_line, name='importer'):

    lines = extractor(filename, up_to_line)
    if lines:
        # create the function object from extracted source code str
        funcLines = ['def %s():' % name] + lines
        source = '\n\t'.join(funcLines).expandtabs()

        # build the importer function
        try:
            exec(source)
        except Exception as err:
            raise Exception(
                    'Could not build import function due to the following exception:'
                    '%s' % str(err))

        return eval(name), lines
    return None, None


class ImportFinder(ast.NodeVisitor):
    """
    Extract, re-construct and buffer import statements from parsed python source
    code.
    """
    def __init__(self, up_to_line=math.inf):
        # collect source code line numbers for *start* of import statements
        self.last_line = float(up_to_line)
        self.line_nrs = []
        self.future = []
        self.nr_alias = 1
        self.current_nr = 1

    def visit_Import(self, node):
        self.current_nr = 1
        self.nr_alias = 1

        ln = node.lineno
        if ln <= self.last_line:
            self.line_nrs.append(ln)
            self.generic_visit(node)

    def visit_ImportFrom(self, node):
        self.nr_alias = len(node.names)
        self.current_nr = 1

        ln = node.lineno
        if node.module == '__future__':
            self.future.append(ln)

        if ln <= self.last_line:
            self.line_nrs.append(ln)
            self.generic_visit(node)


class ImportExtractor(ast.NodeVisitor):
    """
    Extract, re-construct and buffer import statements from parsed python source
    code.
    """

    def __init__(self):  # , no_future=False
        self.buffer = StringIO()
        # source code line numbers for *start* of import statement
        self.line_nrs = []
        self.nr_alias = 1
        self.current_nr = 1

    def visit_Import(self, node):
        self.buffer.write('import ')
        self.line_nrs.append(node.lineno)
        self.current_nr = 1
        self.nr_alias = 1
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        line = 'from %s%s import ' % ('.' * node.level, node.module or '')

        self.buffer.write(line)
        self.nr_alias = len(node.names)
        self.current_nr = 1
        self.line_nrs.append(node.lineno)
        self.generic_visit(node)

    def visit_alias(self, node):
        self.buffer.write(node.name)
        if node.asname:
            self.buffer.write(' as %s' % node.asname)

        last = self.current_nr == self.nr_alias
        char = [', ', '\n'][last]
        self.buffer.write(char)
        self.current_nr += 1



class ModuleExtractor(ast.NodeVisitor):
    """
    Extract names of imported (external) modules
    """

    def __init__(self):
        self.modules = []
        self.accept = True

    def visit_Import(self, node):
        self.accept = True
        # print(ast.dump(node), self.accept)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        self.accept = not bool(node.level)
        # print(ast.dump(node), self.accept)
        self.generic_visit(node)

    def visit_alias(self, node):
        # print(ast.dump(node), self.accept)
        if self.accept:
            self.modules.append(node.name)
            # self.generic_visit(node)


class DynamicFunctionProfiler(HLineProfiler):
    printerClass = ShowDynamicFunction

    def __init__(self, *args, **kwargs):
        HLineProfiler.__init__(self, *args, **kwargs)
        self._source_lib = {}

    def print_stats(self, **kws):
        HLineProfiler.print_stats(self, contents=self._source_lib, **kws)

    def add_dynamic_function(self, func, source):
        self.add_function(func)
        self._source_lib[func] = source


if __name__ == '__main__':
    # Todo print some info so we know wtf is happening

    import argparse
    parser = argparse.ArgumentParser(
        prog='motley.profiler.imports',
        description='Profile your import statements with ease.')
    parser.add_argument('filename', type=str)
    parser.add_argument('up_to_line', type=int, nargs='?', default=100)
    args = parser.parse_args(sys.argv[1:])

    #
    importer, source_lines = _construct_importer(args.filename, args.up_to_line)
    if importer:
        # offset source lines due to `def` line
        source = '\n'.join([''] + source_lines)

        # setup profiler
        profiler = DynamicFunctionProfiler()
        profiler.add_dynamic_function(importer, source)
        profiler.enable_by_count()

        # run the dynamically generated function
        importer()

        # print the results
        profiler.print_stats(strip=('#', '', '<1e-5'))
    else:
        print('No import statements found.')
