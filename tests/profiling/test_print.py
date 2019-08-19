from motley.profiler.printers import _ast_func_index

from more_itertools import pairwise


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

# some source code snippets of barely legible source code for testing
sources = [
    'class F: ""',  # shortest class def with actual doc string

    'def foo(): pass',

    '''
    def foo(*zzz,
            **dork): "bad"
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
        'your doc'
    ''',

    '''
    @bla
    @foo
    def horrible(baz, *a, z='""""""', zz={'#'},
                        
                        zzz=...,
                        
                        **kws
                        
                        ) -> "??":    "this is the docstring?!?"; 1+1
    ''']
