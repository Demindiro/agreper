#!/usr/bin/env python3

import re

# https://stackoverflow.com/a/6041965
RE_URL = re.compile(r'(https?://([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-]))')
RE_EM = re.compile(r'\*(.*?)\*')
RE_LIST = re.compile(r'(-|[0-9]\.) .*')

def html(text):
    # Replace angle brackets to prevent XSS
    # Also replace ampersands to prevent surprises.
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    html = ['<p>']
    lines = text.split('\n')
    in_code = False
    in_list = False

    for l in lines:
        if l == '':
            in_list = False
            if in_code:
                html.append('</pre>')
                in_code = False
            html.append('</p><p>')
            continue
        if l.startswith('  '):
            in_list = False
            l = l[2:]
            if not in_code:
                html.append('<pre>')
                in_code = True
            html.append(l)
            continue
        if in_code:
            html.append('</pre>')
            in_code = False
        l = RE_EM.sub(r'<em>\1</em>', l)
        l = RE_URL.sub(r'<a href="\1">\1</a>', l)
        if RE_LIST.match(l):
            if in_list:
                html.append('<br>')
            in_list = True
        else:
            in_list = False
        html.append(l)

    if in_code:
        html.append('</pre>')
    html.append('</p>')
    return '\n'.join(html)


if __name__ == '__main__':
    import sys
    print(html(sys.stdin.read()))

