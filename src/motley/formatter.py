"""
Stylizing strings with extended format directives.

Examples
--------
Drop in replacement for built in formatter
>>> motley.format('{}', 'Hello world!')
'Hello world!'


With additional colour specs: "|" marks the start of foreground colours or 
effects, "/" for the background. You'll want to print these in a console to see
the colours. The common rgbcymwk colour names are supported (eg "r" for red), as
is "B" for bold, "I" for italic, "_" for underline etc...
>>> motley.format('{hello:s|rBI_/k}', hello='Hello world')
'\x1b[;31;1;3;4;40mHello world\x1b[0m'


To resolve only the colour codes and leave behind something the builtin
formatter can understand, use the `stylize` function:
>>> motley.stylize('{hello!r:s|red,B,I,_/k}')
'\x1b[;31;1;3;4;40m{hello!r:s}\x1b[0m'


Field widths inside nested contexts are adjusted to compensate for hidden (non
display) colour code-points:
>>> motley.stylize('{{{filename}:|green}@{line:d|orange}: <52}| {msg}')
'{\x1b[;32m{filename}\x1b[0m@\x1b[;38;2;255;165;0m{line:d}\x1b[0m: <84}| {msg}'


You can also use the well known x11 colour names
>>> motley.format('{:|aquamarine,I/lightgrey}', 'Hello world')
'\x1b[;38;2;127;255;212;3;48;2;211;211;211mHello world\x1b[0m'


RGB colour are given like so:
>>> motley.format('{:s|(122,0,0),B,I,_/(171,100,41)}', 'Hello world')
'\x1b[;38;2;122;0;0;1;3;4;48;2;171;100;41mHello world\x1b[0m'


Finally, the stylize function can also be used as a partial formatter that will
substitute all available fields, and leave the rest unaltered instead of borking.
>>> motley.format_partial('Give me as {many} as you {can}', many='much')
'Give me as much as you {can}'

"""


# std
import re
import functools as ftl
from textwrap import dedent
from collections import UserString
from string import Formatter as BuiltinFormatter

# third-party
from loguru import logger

# local
from recipes.iter import cofilter
from recipes.oo.temp import temporarily
from recipes.functionals import not_none
from recipes.logging import LoggingMixin
from recipes.string.brackets import (BracketParser, UnpairedBracketError,
                                     csplit, level)

# relative
from . import ansi, codes
from .codes.resolve import InvalidEffect


# ---------------------------------------------------------------------------- #
DEFAULT_FG_MARK = '|'
DEFAULT_BG_MARK = '/'

STRING_CLASSES = (str, UserString)
# [[fill]align][sign][#][0][width][grouping_option][.precision][type]

# re.compile(rf'''(?x)
#     (?P<colon>:)?
#     (?(colon)({spec_pattern})|)
#     \}
# ''')

RGX_FMT_SPEC_BASE = r'''(?x)
    # :?
    (?P<spec>
    # [[fill]align][sign][#][0][width][grouping_option][.precision][type]
        (?: # non-capture
            (?P<fill>[^{}])      # fill only valid if followed by align
            (?=[<>=^])           # lookahead (doesn't consume)
        )?
        (?P<align>[<>=^]?)       # can have align without fill
        (?P<sign>[+\- ]?)
        (?P<alt>\#?)
        (?P<width>\d*)
        (?P<grouping>[_,]?)
        (?P<precision>(?:\.\d+)?)
        (?P<type>[bcdeEfFgGnosxX%]?)
    )
'''


@ftl.lru_cache()
def get_spec_regex(fg_mark=DEFAULT_FG_MARK, bg_mark=DEFAULT_BG_MARK):
    return re.compile(rf'''{RGX_FMT_SPEC_BASE}
    # Colour / style format directives
    (?P<style>
        ({re.escape(fg_mark)}(?P<fg>[ \w,\[\]\(\)_\- ]*))?  # foreground 
        ({re.escape(bg_mark)}(?P<bg>[ \w,\[\]\(\) ]*))?     # background 
    )
''')


# def get_fmt_regex(fg_mark=DEFAULT_FG_MARK, bg_mark=DEFAULT_BG_MARK):
#     spec_rgx = unflag(get_spec_regex(fg_mark, bg_mark).pattern).lstrip('\n')
#     return re.compile(rf'''(?x) # RGX_FORMAT_DIRECTIVE =
#         (?P<text>)
#         \{{
#             (?P<name>[\d\w.\[\]]*)
#             (?P<conversion>(![rsa])?)
#             :?
#             {spec_rgx}
#         \}}
#     ''')


def _apply_style(string, **style):

    if not any(style.values()):
        return string

    # apply style
    logger.opt(lazy=True).debug('{}', lambda: f'Applying {style} to {string!r}')

    try:
        return codes.apply(string, **style)
    except InvalidEffect:  # as err:
        # The block above will fail for the short format spec style
        # eg: 'Bk_' to mean 'bold,black,underline' etc

        # Try again with characters
        maybe_short_spec = _, *rest = style.pop('fg')
        if not rest:
            # error was legit
            raise

        logger.debug('`motley.codes.apply` failed. Retrying with args = {},'
                     ' kws = {} on string:\n{!r}',
                     tuple(maybe_short_spec), style, string)
        try:
            return codes.apply(string, *maybe_short_spec, **style)
        except InvalidEffect as err2:
            raise err2  # from err

# def parse_spec(spec):
#     RGX_FORMAT_DIRECTIVE.search(spec)

# def _non_display_width(self, spec, value, mo):
#     if isinstance(value, (str, UserString)) and mo['width']:
#         return ansi.length_codes(value)
#     return False


# def get_formatter_for_type(kls, precision, short):
#     """

#     Parameters
#     ----------
#     precision
#     short

#     Returns
#     -------

#     """

#     # NOTE: single dispatch not a good option here due to formatting
#     #   subtleties

#     # if len(self.dtypes) != 1:
#     #     return ppr.PrettyPrinter(
#     #         precision=precision, minimalist=short).pformat

#     # nb since it's a set, don't try types_[0]
#     # type_ = type(obj)
#     # all data in this column is of the same type
#     if issubclass(kls, str):  # NOTE -  this includes np.str_!
#         return echo0

#     if not issubclass(kls, numbers.Real):
#         return str

#     # right_pad = 0
#     sign = ''
#     if issubclass(kls, numbers.Integral):
#         if short:
#             precision = 0

#     else:  # real numbers
#         # if short and (self.align[col_idx] in '<>'):
#         #     right_pad = precision + 1
#         sign = (' ' * int(np.any(self.data < 0)))

#     return ftl.partial(ppr.decimal,
#                        precision=precision,
#                        short=short,
#                        sign=sign,
#                        thousands=' ')

def _is_adjacent(a, b):
    indices = cofilter(not_none, a.indices, b.indices, (0, 1))
    if a.is_open():
        for i, j, k in zip(*indices):
            return (i + 1 == j), i, k
    return False, None, None

    # escaped = True  # FIXME does this ever get run if level == 0 ?????
    # for i, j, k in zip(*indices):
    #     if k:
    #         # swap order of indices since  outer closing preceeds inner
    #         # closing for closed double pairs
    #         i, j = j, i

    #     escaped &= (i + 1 == j)
    # return escaped, i, k


class Formatter(BuiltinFormatter, LoggingMixin):
    """
    Implements a formatting syntax for string colouring and styling.
    """
    parser = BracketParser('{}')
    _rgb_parser = BracketParser('()')
    # supporting [] is more complicated because of ansi codes containing these:
    # Eg '\x1b[;1;34m'

    # TODO: ('{:%Y-%m-%d %H:%M:%S}', datetime.datetime(2010, 7, 4, 12, 15, 58)):

    def __init__(self, fg=DEFAULT_FG_MARK, bg=DEFAULT_BG_MARK, adjust_widths=True):
        self.adjust_widths = bool(adjust_widths)
        self.spec_regex = get_spec_regex(fg, bg)
        # self.fmt_regex = get_fmt_regex(fg, bg)
        # self.parser = BracketParser('{}')

    def parse(self, string):
        # yields # literal_text, field_name, format_spec, conversion

        # NOTE: all these need to be supported
        # >>> format('')
        # >>> format('{{}}')
        # >>> format('hello {}', 'world')
        # >>> format('hello {world}', world='world')
        # >>> format('hello {world!r:s}', world='world')
        # >>> format('hello {world[0]:-<5s}', world='world')
        # >>> format('{::^11s}', 'x')

        self.logger.opt(lazy=True).debug('Recieved format string:{0[0]}> {0[1]!r}',
                                         lambda: ('\n' * (len(string) > 40), string))

        i = 0
        pos = 0
        match = None
        braces = self.parser.findall(string, condition=(level == 0))
        while i < len(braces):
            match = braces[i]
            self.logger.debug('MATCH {}, pos = {}\n{!r}', i, pos, match)
            if match.is_open():
                # open brace
                if i == len(braces) - 1:
                    # final brace
                    escaped = False
                else:
                    escaped, j, k = _is_adjacent(match, (match := braces[i + 1]))
                
                if escaped:
                    # Open double
                    self.logger.debug('Found escaped (double) brace {!r} at {}.',
                                      '{}'[k] * 2, j)
                    yield string[pos:j + 1], None, None, None
                    pos = next(filter(None, match.indices)) + 1
                    i += 2
                    continue
                else:
                    # open single. throw
                    j = match.indices.index(None)
                    raise UnpairedBracketError(string,
                                               ('opening', 'closing')[j],
                                               {'}{'[j]: [match.indices[not bool(j)]]})

            # closed braces
            # Check if this is a closed double brace
            if (match.enclosed.startswith('{') and match.enclosed.endswith('}')
                    and (inner := self.parser.match(match.enclosed))
                    and inner.indices == (0, len(match.enclosed) - 1)):
                # closed double
                self.logger.debug('Found closed double brace pair at {}.', match.indices)
                yield string[pos:match.start + 1], None, None, None
                yield from self.parse(inner.enclosed)
                yield '}', None, None, None
            else:
                # closed single
                self.logger.debug('Found braced group at position {.start}', match)
                yield string[pos:match.start], *self.parse_brace_group(match.enclosed)

            pos = match.end + 1
            i += 1

        # case no braces
        if match is None:
            self.logger.debug('No braced expressions in: {!r}', string)
            yield string, None, None, None

        # Final part of string
        elif (match.start or match.end) + 1 != len(string):
            yield string[match.end + 1:], None, None, None

            # continue
            # # spec_match = self.spec_regex.search(match.enclosed)
            # # spec_match['spec']
            # for match in (match, next_match):
            #     self.logger.opt(lazy=True).debug('{}', lambda: dedent(f'''\
            #         Found braced group at position {match.start}:
            #             literal_text = {string[pos:match.start]!r}
            #             {match.enclosed = !r}''')
            #                                      )
            #     # literal_text, field_name, format_spec, conversion
            #     yield string[pos:match.start], *self.parse_brace_group(match)
            #     # yield string[pos:match.start], field, spec, convert
            #     pos = match.end + 1

    def parse_brace_group(self, string):

        # parse braces
        field, spec, convert = self._parse_brace_group(string)

        self.logger.opt(lazy=True).debug(
            '{}', lambda: dedent(f'''
                field_name   = {field!r}
                format_spec  = {spec!r}
                conversion   = {convert!r}\
            ''').replace('\n', '\n    '),
        )

        return field, spec, convert

    def _parse_brace_group(self, field):
        # defaults
        spec = ''  # >>> format('hello {}', 'world')
        convert = None
        # field = match.enclosed

        # if field is None:
        #     return field, spec, convert

        if '!' in field:
            field, *_spec = self.parser.rcsplit(field, '!', 1)
            # spec might still be empty: ' {{0!r}:<{width}}'
            if _spec:
                spec, = _spec
                convert, spec = spec[0], spec[2:]

            self.logger.opt(lazy=True).debug(
                '{}', lambda: f'Parsed {field = }; {convert = }; {spec = }')

        if ':' in field:
            # split field name, spec
            field_spec = self.parser.rcsplit(field, ':', 1)
            if len(field_spec) == 2:
                field, spec = field_spec

            self.logger.opt(lazy=True).debug(
                '{}', lambda: f'Parsed {field = }; {spec = }')

            # handle edge case: filling with colon: "{::<11s}"
            if field.endswith(':'):
                field = field[:-1]
                spec = f':{spec}'

        # literal_text, field_name, format_spec, conversion
        return field, spec, convert

    def _parse_spec(self, value, spec):
        self.logger.debug('Received value={!r}, spec={!r}', value, spec)

        # get the part that `builtins.format` understands
        if spec_match := self.spec_regex.fullmatch(spec):
            # FIXME: is this regex even necessary??? Check performance etc
            spec = spec_match['spec']
            fg = spec_match['fg']
            bg = spec_match['bg']
            # if spec:
            #     self.logger.opt(lazy=True).debug('Parsed the following fields:\n{}',
            #                                      lambda: pformat(spec_match.groupdict()))
        else:
            if not self.parser.match(spec):
                raise ValueError(f'Invalid format specifier: {spec!r}')

            self.logger.debug('Nested braces in spec: {!r}. Parsing manually.',
                              spec)
            # Parse spec the hard way
            style = ''
            if '|' in spec:
                spec, *style = self.parser.rcsplit(spec, '|', 1)

            fg, *bg = ''.join(style).split('/')

        #
        style = dict(fg=fg, bg=bg)
        #
        # else:
        # self.logger.opt(lazy=True).debug('Parsed spec = {!r}', spec)

        # if the value is a string which has style applied, adjust the
        # width field to compensate for non-display characters
        spec = self._adjust_width_for_hidden_characters(spec, value, spec_match)

        # get color directives
        for fg_or_bg, val in list(style.items()):
            # split comma separated names like "aquamarine,I"
            # but ignore rgb color directives eg: [1,33,124], (0, 0, 0)
            if not val:
                continue

            if ',' in val:
                rgb = self._rgb_parser.match(val, must_close=True)
                style[fg_or_bg] = csplit(style[fg_or_bg],
                                         getattr(rgb, 'brackets', None))

        #
        self.logger.debug('parsed value={!r}, spec={!r}, style={!r}',
                          value, spec, style)

        return value, spec, style

    def _should_adjust_width(self, spec, value, spec_match):
        # self.logger.debug('Checking {!r}', value)
        return (self.adjust_widths and spec_match and (width := spec_match['width'])
                and isinstance(value, STRING_CLASSES) and ansi.has_ansi(value))
        # self.logger.opt(lazy=True).debug(
        #     '{}', lambda: f'{width = }; {ansi.has_ansi(value) = }')
        #     return (width and ansi.has_ansi(value))
        # return False

    def _adjust_width_for_hidden_characters(self, spec, value, spec_match):
        """
        If the value is a string which has style applied, adjust the
        width field to compensate for non-display characters
        """
        if not self._should_adjust_width(spec, value, spec_match):
            return spec

        spec_info = spec_match.groupdict()
        # remove the base level groups in the regex
        for _ in ('spec', 'style', 'fg', 'bg'):
            spec_info.pop(_)

        spec_info['width'] = str(int(spec_match['width']) + ansi.length_codes(value))
        self.logger.info('Adjusting field width from {[width]} to {[width]} '
                         'since string has colour formatting code points with '
                         'zero display width.', spec_match, spec_info)
        return ''.join(spec_info.values())

    def get_field(self, field_name, args, kws):
        # eg: field_name = '0[name]' or 'label.title' or 'some_keyword'
        self.logger.opt(lazy=True).debug(
            '{}', lambda: f'{field_name = }, {args = }, {kws = }')

        if self.parser.match(field_name):
            # brace expression in field name!
            self.logger.debug('Found braced expression in field name. Recursing'
                              ' on {!r}', field_name)

            # restore previous _wrap_field state after recursing
            sub = self.format(field_name, *args, **kws)
            return sub, None

        return super().get_field(field_name, args, kws)

    def format_field(self, value, spec):
        """
        [summary]

        Parameters
        ----------
        value : object
            The object to be formatted.
        spec : str
            The format specification. The standard python formatting directives
            can be suffixed with a "|", follwed by the comma-separated
            foreground (text) colour and style directives, and/or a "/" followed
            by the background colour. If the list of effects are given by their
            single character names, the commas can be omitted.

        Examples
        --------
        >>> fmt = Formatter()
        >>> fmt.format_field('Hello world', '|gBI_/k')
        >>> fmt.format_field(101.101, ' >15.4d|red,B,I,_/k}"
        >>> fmt.format_field('Hello world', ':s|aquamarine,I/lightgrey}')
        >>> fmt.format('Hello world', '(122,0,0),B,I,_/k}')

        Returns
        -------
        str
            Formatted, colourized, stylized string.

        Raises
        ------
        ValueError
            If the standard format specifier is invalid.
        motley.codes.resolve.InvalidEffect
            If the colour / style directives could not be resolved.
        """
        self.logger.debug('Formatting {!r} with {!r} at parent', value, spec)
        value, spec, style = self._parse_spec(value, spec)

        # delegate formatting
        # self.logger.debug('Formatting {!r} with {!r} at parent', value, spec)
        return _apply_style(
            super().format_field(value, spec),      # calls  builtins.format
            **style
        )

    def convert_field(self, value, conversion):
        if conversion is None:
            return value
        if conversion in 'rsa':
            return super().convert_field(value, conversion)
        if conversion == 'q':
            return repr(str(value))

    def format_partial(self, format_string, *args, **kws):
        self.logger.debug('Recieved format string:{}> {!r}',
                          '\n' * (len(format_string) > 40), format_string)
        return PartialFormatter().format(format_string, *args, **kws)

    # alias
    stylize = partial_format = format_partial


class PartialFormatter(Formatter):
    """
    Apply styling to string by resolving the styling part of the format spec
    and adding the ansi codes into the correct positions. Field widths are
    also adapted to compensate for hidden (non-display) characters.
    """

    _wrap_field = False
    _empty_field_name = False

    # def format(self, format_string, /, *args, **kws):
    #     return Formatter.format(self, format_string, *args, **kws)

    def parse(self, string):
        for literal_text, field_name, spec, convert in super().parse(string):
            self._empty_field_name = not bool(field_name)
            # have to keep track of `_wrap_field` state here and restore after
            # yield since this may change for nested braces eg:
            # stylize(' {0:<{width}|b}={1:<{width}}', width=10)
            # logger.info(
            #     f'\n  {self._wrap_field = }\n  '
            #     f'{bool(spec and field_name and self.parser.match(field_name, -1)) = }')
            # self._wrap_field = bool(spec and field_name and self.parser.match(field_name, -1))

            with temporarily(self, _wrap_field=self._wrap_field):
                yield literal_text, field_name, spec, convert

    def get_field(self, field_name, args, kws):
        # eg: field_name = '0[name]' or 'label.title' or 'some_keyword'
        self.logger.opt(lazy=True).debug(
            '{}', lambda: f'{field_name = }, {args = }, {kws = }')

        # NOTE: have to resolve nested first since there may be nested braces in
        # field name, and we have to possibly wrap those fields.
        self._wrap_field = True
        if self.parser.match(field_name):
            # self._wrap_field = True
            # brace expression in field name!
            self.logger.debug('Found braced expression in field name, recursing'
                              ' on {!r}', field_name)
            # restore previous _wrap_field state after recursing
            # with temporarily(self, _wrap_field=self._wrap_field):
            sub = self.format(field_name, *args, **kws)
            #self._wrap_field = True
            return sub, None

        self.logger.debug('Trying to retrieve field value with\n    '
                          'Formatter.get_field({!r}, args = {}, kws = {})',
                          field_name, args, kws)

        if (args or kws):
            try:
                result = BuiltinFormatter.get_field(self, field_name, args, kws)
                self._wrap_field = False
            except LookupError as err:
                # KeyError
                # If `Formatter.get_field` failed, this field name is
                # unavailable and needs to be kept unaltered. We do that by
                # replacing `field_name` with `{field_name}` wrapped in braces.
                # This leaves the string unaltered after substitution.
                # result = (field_name, None)

                # IndexError
                # by this time the `auto_arg_index` will have been substituted
                # for empty field names. We have to undo that to obtain the
                # original field specifier which may have been empty.
                result = ('' if self._empty_field_name else field_name, None)
                self.logger.debug('Formatter.get_field failed with\n    {!r}'
                                  '\n  Returning: value= {}, key= {}',
                                  err, *result)
            else:
                self.logger.debug('Formatter.get_field succeeded. Returning: '
                                  'value= {}, key= {}', *result)

        else:
            result = ('' if self._empty_field_name else field_name, None)
            self.logger.debug('No args or kws avaliable, know to wrap without '
                              'needing to attempting super call. Returning: '
                              'value= {}, key= {}', *result)

        # logger.critical('WRAP: {}', self._wrap_field)
        return result

    def format_field(self, value, spec):
        self.logger.debug('value = {!r}, spec = {!r}', value, spec)

        # convert str necessary to measure field width in _parse_spec
        value, spec, style = self._parse_spec(str(value), spec)

        # Should we wrap the field in braces again?
        really_wrap = not any(style.values()) or spec
        if self._wrap_field and really_wrap:
            self.logger.debug('Wrapping: value = {!r}, spec = {!r}', value, spec)
            value = '{'f'{value}{f":{spec}" if spec else ""}''}'
            # value = ':'.join((value, spec)).join('{}')
        else:
            self.logger.debug('Not wrapping; {}', value)

        return _apply_style(value, **style)

        # else:
        #     self.logger.debug('Passing up for formatting: value = {!r}, spec = {!r}',
        #                 value, spec)
        #     return super().format_field(value, spec)

        # self.logger.debug('Formatted field:\n{}', ff)
        # return ff

    # def _parse_spec(self, value, spec):

    #     value, spec, style = super()._parse_spec(value, spec)

    def convert_field(self, value, conversion):
        if self._wrap_field and conversion:
            self.logger.debug("Appending: '!{}' to {!r}", conversion, value)
            return f'{value}!{conversion}'

        if conversion:
            self.logger.debug('Passing to Formatter for {} convert: {}', conversion, value)
        return super().convert_field(value, conversion)

    def _should_adjust_width(self, spec, value, spec_match):
        # Subtlety: We only need to adjust the field width if the field name
        # does not contain braces. This is because the result returned by this
        # partial formatter will have the colors substituted, and will most
        # likely be formatted again to get the fully formatted result. If there
        # are (colourized) braces to substitute in the field name, these will be
        # handled upon the second formatting where the width of the format spec
        # will then be adjusted. We therefore leave it unaltered here to avoid
        # adjusting the spec width twice.

        # self.logger.debug('Checking {!s}', value)
        # self.logger.debug(f'{self.parser.match(value) = } '
        #              f'{super()._should_adjust_width(spec, value, spec_match) = }')
        return (
            self.parser.match(value) is None
            and
            super()._should_adjust_width(spec, value, spec_match)
        )

    # def get_value(self, key, args, kwargs):
    #     self.logger.debug(f'{key=:}, {args=:}, {kwargs=:}', )
    #     return super().get_value(key, args, kwargs)


# aliases
# sourcery skip: avoid-builtin-shadow
Stylize = PartialFormatter
formatter = Formatter()
format = formatter.format
stylize = format_partial = partial_format = formatter.format_partial
