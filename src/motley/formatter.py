"""
Stylizing strings with extended format directives.
"""

# std
import re
import functools as ftl
from collections import UserString
from string import Formatter as BuiltinFormatter

# third-party
from loguru import logger

# local
from recipes.regex import unflag
from recipes.string.brackets import BracketParser, xsplit, level

# relative
from . import codes, ansi
from .codes.resolve import InvalidEffect


# f"{String('Hello world'):rBI_/k}"
# f"{String('Hello world'):red,B,I,_/k}"
# String.format("{'Hello world':aquamarine,I/lightgrey}")
# String("{'Hello world':[122,0,0],B,I,_/k}")


DEFAULT_FG_SWITCH = '|'
DEFAULT_BG_SWITCH = '/'


# [[fill]align][sign][#][0][width][grouping_option][.precision][type]

# RGX_STD_FMT = r'''
#     (?P<fill>.?)
#     (?P<align>[<>=^]?)
#     (?P<sign>[+\- ]?)
#     (?P<width>\d*)
#     (?P<grouping>[_,]?)
#     (?P<precision>(?:\.\d+)?)
#     (?P<type>[bcdeEfFgGnosxX%]?)
# '''
# # THIS REGEX DOESN'T capture the fact that you cannot have fill without align

@ftl.lru_cache()
def get_spec_regex(fg_switch=DEFAULT_FG_SWITCH, bg_switch=DEFAULT_BG_SWITCH):
    return re.compile(rf'''(?x)
        (?P<spec>
            (?P<fill>[^{fg_switch}]?)  # FIXME
            (?P<align>[<>=^]?)
            (?P<sign>[+\- ]?)
            (?P<width>\d*)
            (?P<grouping>[_,]?)
            (?P<precision>(?:\.\d+)?)
            (?P<type>[bcdeEfFgGnosxX%]?)
        )
        (?P<effects>
            ({re.escape(fg_switch)}(?P<fg>[ \w,_\-\[\]\(\)]*))?
            ({re.escape(bg_switch)}(?P<bg>[ \w,\[\]\(\)]*))?
        )
    ''')


def get_fmt_regex(fg_switch=DEFAULT_FG_SWITCH, bg_switch=DEFAULT_BG_SWITCH):
    spec_rgx = unflag(get_spec_regex(fg_switch, bg_switch).pattern).lstrip('\n')
    return re.compile(rf'''(?x) # RGX_FORMAT_DIRECTIVE =
        (?P<text>)
        \{{
            (?P<name>[\d\w.\[\]]*)
            (?P<conversion>(![rsa])?)
            :?
            {spec_rgx}
        \}}
    ''')


def _apply_style(string, **effects):
    # apply effects
    try:
        return codes.apply(string, **effects)
    except InvalidEffect:  # as err:
        fg, *rest = effects.pop('fg')
        if not rest:
            raise

        # The block above will fail for the short format spec style
        # eg: 'Bk_' to mean 'bold,black,underline' etc
        try:
            return codes.apply(string, fg, *rest, **effects)
        except InvalidEffect as err2:
            raise err2  # from err

# def parse_spec(spec):
#     RGX_FORMAT_DIRECTIVE.search(spec)

# def _non_display_width(self, spec, value, mo):
#     if isinstance(value, (str, UserString)) and mo['width']:
#         return ansi.length_codes(value)
#     return False


class Formatter(BuiltinFormatter):
    """
    Implements a formatting syntax for string colorization and styling.
    """
    _partial = False
    _rgb_parser = BracketParser('[]', '()')

    # TODO: ('{:%Y-%m-%d %H:%M:%S}', datetime.datetime(2010, 7, 4, 12, 15, 58)):

    def __init__(self, fg=DEFAULT_FG_SWITCH, bg=DEFAULT_BG_SWITCH):
        self.spec_regex = get_spec_regex(fg, bg)
        self.fmt_regex = get_fmt_regex(fg, bg)
        self.parser = BracketParser('{}')

    def parse(self, string):
        try:
            parts = list(super().parse(string))
            yield from parts
            return
        except ValueError as err:
            msg = str(err)
            if not msg.endswith(("Single '}' encountered in format string",
                                 "unexpected '{' in field name",
                                 "expected '}' before end of string")):
                logger.debug('builtin format parser failed with: {}', err)
                raise err

        logger.debug('parsing: {}', string)

        pos = 0
        match = None
        itr = self.parser.iterate(string, must_close=True,
                                  condition=(level == 0))
        for match in itr:
            *field, spec = xsplit(match.enclosed, delimeter=':')
            if field:
                # handle edge case: filling with colon: "{::<10s}"
                if '::' in match.enclosed:
                    field = field[:-1]
                    spec = ':' + spec

                field = ':'.join(field)
            else:
                field = spec
                spec = ''

            #  (literal_text, field_name, format_spec, conversion)
            logger.debug('literal_text={!r}, field_name={!r}, format_spec={!r}',
                         string[pos:match.start], field, spec)
            yield string[pos:match.start], field, spec, None

            pos = match.end + 1

        if match and (match.end + 1 != len(string)):
            yield string[match.end + 1:], None, None, None

    def get_field(self, field_name, args, kws):
        if '{' in field_name:
            logger.debug('recursing on {}', field_name)
            # z = self.format(field_name, *args, **kws)
            # logger.debug(f'{z=}')
            return self.format(field_name, *args, **kws), None

        return super().get_field(field_name, args, kws)

    def _parse_spec(self, value, spec):

        logger.debug('received value={!r}, spec={!r}', value, spec)

        # print(f'{spec=}')
        mo = self.spec_regex.fullmatch(spec)
        if mo is None:
            raise ValueError(f'Invalid format specifier: {spec!r}')

        # get the spec that builtins.format understands
        spec = mo['spec']
        logger.opt(lazy=True).trace('{}', mo.groupdict)

        # if the value is a string which has effects applied, adjust the
        # width field to compensate for non-display characters
        spec = self._adjust_width_for_hidden_characters(spec, value, mo)

        # get color directives
        effects = dict(fg=mo['fg'] or '',
                       bg=mo['bg'] or '')
        for fg_or_bg, val in list(effects.items()):
            # split comma separated names like "aquamarine,I"
            # but ignore rgb color directives eg: [1,33,124], (0, 0, 0)
            if not val:
                continue

            if ',' in val:
                rgb = self._rgb_parser.match(val, must_close=True)
                effects[fg_or_bg] = xsplit(effects[fg_or_bg],
                                           getattr(rgb, 'brackets', None))

        #
        logger.debug('parsed value={!r}, spec={!r}, effects={!r}',
                     value, spec, effects)

        return value, spec, effects

    def _adjust_width(self, spec, value, mo):
        if isinstance(value, (str, UserString)) and mo['width']:
            return int(mo['width']) + ansi.length_codes(value)
        return

    def _adjust_width_for_hidden_characters(self, spec, value, mo):
        """
        if the value is a string which has effects applied, adjust the
        width field to compensate for non-display characters
        """
        width = self._adjust_width(spec, value, mo)
        if width:
            spec_info = mo.groupdict()
            # remove the base level groups in the regex
            for _ in ('spec', 'effects', 'fg', 'bg'):
                spec_info.pop(_)
            spec_info['width'] = str(width)
            return ''.join(spec_info.values())
        return spec

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
        >>> fmt.format('Hello world', '[122,0,0],B,I,_/k}')

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

        value, spec, effects = self._parse_spec(value, spec)

        # delegate formatting
        logger.debug('Formatting {!r} with {!r} at parent', value, spec)
        return _apply_style(
            super().format_field(value, spec),      # calls  builtins.format
            **effects
        )

    def convert_field(self, value, conversion):
        if conversion is None:
            return value
        if conversion in 'rsa':
            return super().convert_field(value, conversion)
        if conversion == 'q':
            return repr(str(value))

    def stylize(self, format_string, *args, **kws):
        return PartialFormatter().format(format_string, *args, **kws)
        # stylized = Stylizer().format(format_string)
        # return self.format(stylized, *args, **kws)

    format_partial = stylize

    # with self.temporarily(patial=True):
    #   return self.format(format_string, *args, **kws)
    # self._partial = True
    # result = self.format(format_string, *args, **kws)
    # self._partial = False
    # return result


class Stylizer(Formatter):
    """
    Apply styling to string by resolving the styling part of the format spec
    and adding the ansi codes into the correct positions. Field widths are
    also adapted to compensate for hidden (non-display) characters.
    """
    # _current_level = 0
    # _max_level = 0
    _wrap = True

    def get_field(self, field_name, args, kws):
        # eg: field_name = '0[name]' or 'label.title' or '{some_keyword}'
        if '{' in field_name:
            # self._current_level += 1
            logger.debug('recursing on {}', field_name)
            sub = self.format(field_name, *args, **kws)
            self._wrap = False
            # self._current_level -= 1
            return sub, None
        self._wrap = True
        return field_name, None

    def format_field(self, value, spec):
        value, spec, effects = self._parse_spec(value, spec)
        value = ':'.join(filter(None, (value, spec)))
        # print(self._current_level, value, effects, spec)
        # Can we remove the enclosing braces?
        # if self._current_level < self._max_level or spec:
        # logger.
        logger.debug('wrap = {}, spec = {!r}', self._wrap, spec)
        if self._wrap or spec:
            value = value.join('{}')
        logger.debug('applying {} to {!r}', effects, value)
        return _apply_style(value, **effects)


class PartialFormatter(Stylizer):

    def get_field(self, field_name, args, kws):
        try:
            # logger.debug('trying at parent Formatter {}', field_name)
            result = Formatter.get_field(self, field_name, args, kws)
            self._wrap = False
            return result

        except KeyError:
            self._wrap = True
            return field_name, None

    def _adjust_width(self, spec, value, mo):
        # Subtlety: We only need to adjust the field width if the field name
        # doesn't contain braces. This is because the result returned by this
        # partial formatter will have the colors substituted, and will most
        # likely be formatted again to get the fully formatted result. If there
        # are (colourized) braces to substitute in the field name, these will be
        # handled upon the second formatting where the width of the format spec
        # will then be adjusted. We therefore leave it unaltered here to avoid
        # adjusting the spec width twice.
        return super()._adjust_width(spec, value, mo) and ('{' not in value)


formatter = Formatter()
stylize = formatter.stylize
format_partial = formatter.format_partial
format = formatter.format
