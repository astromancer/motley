# std
from collections import UserString

# relative
from . import codes
from .formatter import formatter


# f"{String('Hello world'):rBI_/k}"
# f"{String('Hello world'):red,B,I,_/k}"
# String.format("{'Hello world':aquamarine,I/lightgrey}")
# String("{'Hello world':[122,0,0],B,I,_/k}")


class String(UserString):

    # def parse(cls, s):

    def __init__(self, text, *effects, **kws):
        super().__init__(codes.apply(text, *effects, **kws))

    def __format__(self, spec):
        return formatter.format_field(self.data, spec)

    def format(self, *args, **kws):
        return self.__class__(format(self.data, *args, **kws))


Str = String
