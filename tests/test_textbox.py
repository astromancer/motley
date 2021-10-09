from motley.textbox import TextBox, textbox

import itertools as itt
texts = ['Hello world!',
         'Hello\nworld!']
styles = ('', '-', '--', '.', ':', '=')
boldness = False, True
for text, style, bold in itt.product(texts, styles, boldness):
    try:
        print(textbox(text, style=style, bold=bold))
    except Exception as err:
        print(err)


# ◆──────◆
# │Hello │
# │world!│
# ◆──────◆
