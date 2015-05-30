import asyncio
import json
import re
#from aiohttp          import request, TCPConnector
from aiohttp          import request
from aiohttp.helpers  import FormData
from urllib.parse     import urlsplit

from .common import Get
from .tool import html, htmlparse, jsonparse, regex

def unsafesend(m, send, *, raw=False):
    if raw:
        l = str(m).splitlines()
        send(l, n=len(l), llimit=16, mlimit=5, raw=True)
    else:
        send(m, mlimit=5)

@asyncio.coroutine
def getcode(url):
    site = {
        'codepad.org':         '/html/body/div/table/tbody/tr/td/div[1]/table/tbody/tr/td[2]/div/pre',
        'paste.ubuntu.com':    '//*[@id="contentColumn"]/div/div/div/table/tbody/tr/td[2]/div/pre',
        'cfp.vim-cn.com':      '.',
        'p.vim-cn.com':        '.',
        'www.fpaste.org':      '//*[@id="paste_form"]/div[1]/div/div[3]',
        'bpaste.net':          '//*[@id="paste"]/div/table/tbody/tr/td[2]/div',
        'pastebin.com':        '//*[@id="paste_code"]',
        'code.bulix.org':      '//*[@id="contents"]/pre',
        'ix.io':               '.',
    }

    get = Get()
    u = urlsplit(url)
    xpath = site[u[1]]
    if xpath == '.':
        arg = {'url': url, 'regex': r'(.*)\n'}
        yield from regex(arg, get)
    else:
        arg = {'url': url, 'xpath': xpath}
        yield from html(arg, get)

    return get.line

@asyncio.coroutine
def clear(arg, lines, send):
    pass

# paste

@asyncio.coroutine
def vimcn(arg, lines, send):
    print('vimcn')

    url = 'https://cfp.vim-cn.com/'
    code = '\n'.join(lines) or arg['code']

    if not code:
        raise Exception()

    data = FormData()
    data.add_field('vimcn', code, content_type='multipart/form-data')
    r = yield from request('POST', url, data=data)

    text = yield from r.text()
    esc = re.compile(r'\x1b[^m]*m')
    text = esc.sub('', text)
    line = text.splitlines()
    send('[\\x0302 {0} \\x0f]'.format(line[0]))

@asyncio.coroutine
def bpaste(arg, lines, send):
    print('bpaste')

    url = 'https://bpaste.net/'
    code = '\n'.join(lines) or arg['code']
    lang = (arg['lang'] or 'text').lower()
    #time = arg['time'] or 'never'
    time = 'never'

    if not code:
        raise Exception()

    d = {
        'clipper':         'Clipper',
        'cucumber':        'Cucumber',
        'robotframework':  'RobotFramework',
    }
    lang = d.get(lang) or lang

    data = {
        'code': code,
        'lexer': lang,
        'expiry': time,
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    r = yield from request('POST', url, data=data, headers=headers)

    send('[\\x0302 {0} \\x0f]'.format(r.url))

@asyncio.coroutine
def rust(arg, lines, send):
    print('rust')

    url = 'https://play.rust-lang.org/evaluate.json'
    code = '\n'.join(lines) or arg['code']
    raw = arg['raw']

    if not code:
        raise Exception()

    data = json.dumps({
        'code': code,
        'color': False,
        'optimize': '3',
        'separate_output': True,
        'test': False,
        'version': 'stable',
    })
    headers = {'Content-Type': 'application/json'}
    # ssl has some problem
    #conn = TCPConnector(verify_ssl=False)
    #r = yield from request('POST', url, data=json.dumps(data), headers=headers, connector=conn)
    r = yield from request('POST', url, data=data, headers=headers)
    byte = yield from r.read()

    j = jsonparse(byte)
    error = j.get('rustc')
    result = j.get('program')
    if error:
        unsafesend('\\x0304error:\\x0f {0}'.format(error), send)
    if result:
        unsafesend(result, send, raw=raw)
    else:
        unsafesend('no output', send, raw=raw)

@asyncio.coroutine
def codepad(arg, lines, send):
    print('codepad')

    url = 'http://codepad.org/'
    code = '\n'.join(lines) or arg['code']
    lang = arg['lang'].title()
    run = bool(arg['run'])
    raw = arg['raw']

    if not code:
        raise Exception()

    d = {
        'Text':   'Plain Text',
        'Php':    'PHP',
        'Ocaml':  'OCaml',
    }
    lang = d.get(lang) or lang

    data = {
        'lang': lang,
        'code': code,
        'private': 'True',
        'run': str(run),
        'submit': 'Submit',
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    r = yield from request('POST', url, data=data, headers=headers)

    if run:
        byte = yield from r.read()
        t = htmlparse(byte)
        try:
            result = t.xpath('/html/body/div/table/tbody/tr/td/div[2]/table/tbody/tr/td[2]/div/pre')[0].xpath('string()')
            unsafesend(result, send, raw=raw)
        except IndexError:
            unsafesend('no output', send, raw=raw)
    send('[\\x0302 {0} \\x0f]'.format(r.url))

@asyncio.coroutine
def rextester(arg, lines, send):
    print('rextester')

    url = 'http://rextester.com/rundotnet/Run'

    default = {
        'c#':               (  1, '', '' ),
        'vb.net':           (  2, '', '' ),
        'f#':               (  3, '', '' ),
        'java':             (  4, '', '' ),
        'python':           (  5, '', '' ),
        'c(gcc)':           (  6, '-o a.out source_file.c', '-Wall -std=gnu99 -O2' ),
        'c++(gcc)':         (  7, '-o a.out source_file.cpp', '-Wall -std=c++11 -O2' ),
        'php':              (  8, '', '' ),
        'pascal':           (  9, '', '' ),
        'objective-c':      ( 10, '-o a.out source_file.m', '' ),
        'haskell':          ( 11, '-o a.out source_file.hs', '' ),
        'ruby':             ( 12, '', '' ),
        'perl':             ( 13, '', '' ),
        'lua':              ( 14, '', '' ),
        'nasm':             ( 15, '', '' ),
        'sql':              ( 16, '', '' ),
        'javascript':       ( 17, '', '' ),
        'lisp':             ( 18, '', '' ),
        'prolog':           ( 19, '', '' ),
        'go':               ( 20, '-o a.out source_file.go', '' ),
        'scala':            ( 21, '', '' ),
        'scheme':           ( 22, '', '' ),
        'node.js':          ( 23, '', '' ),
        'python3':          ( 24, '', '' ),
        'octave':           ( 25, '', '' ),
        'c(clang)':         ( 26, '-o a.out source_file.c', '-Wall -std=gnu99 -O2' ),
        'c++(clang)':       ( 27, '-o a.out source_file.cpp', '-Wall -std=c++11 -O2' ),
        'c++(vc++)':        ( 28, '-o a.exe source_file.cpp', '' ),
        'c(vc)':            ( 29, '-o a.exe source_file.c', '' ),
        'd':                ( 30, '-ofa.out source_file.d', '' ),
        'r':                ( 31, '', '' ),
        'tcl':              ( 32, '', '' ),
    }
    alias = {
        # default
        'c':                'c(gcc)',
        'c++':              'c++(gcc)',
        # rename
        'python2':          'python',
        # abbreviation
        'objc':             'objective-c',
        'asm':              'nasm',
        'vb':               'vb.net',
        'node':             'node.js',
        # extension
        'js':               'javascript',
        'py':               'python',
        'py2':              'python',
        'py3':              'python3',
        'rb':               'ruby',
        'hs':               'haskell',
        'pl':               'perl',
        'cpp':              'c++(gcc)',
        'cxx':              'c++(gcc)',
    }

    code = '\n'.join(lines) or arg['code']
    conf = default.get(alias.get(arg['lang'].lower(), arg['lang'].lower()))
    lang = conf[0]
    args = '{0} {1}'.format(conf[1], arg['args'] or conf[2])
    #input = arg['input'] or ''
    input = ''
    raw = arg['raw']

    if not code:
        raise Exception()

    data = {
        'LanguageChoiceWrapper': lang,
        'Program': code,
        'Input': input,
        'CompilerArgs': args,
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    r = yield from request('POST', url, data=data, headers=headers)
    byte = yield from r.read()

    j = jsonparse(byte)
    warnings = j.get('Warnings')
    errors = j.get('Errors')
    result = j.get('Result')
    stats = j.get('Stats')
    files = j.get('Files')
    if warnings:
        unsafesend('\\x0304warnings:\\x0f {0}'.format(warnings), send)
    if errors:
        unsafesend('\\x0304errors:\\x0f {0}'.format(errors), send)
    if result:
        unsafesend(result, send, raw=raw)
    else:
        unsafesend('no output', send, raw=raw)

@asyncio.coroutine
def python3(arg, lines, send):

    arg.update({
        'lang': 'python3',
        'args': None,
        'raw': None,
    })
    lines = ['import code', 'i = code.InteractiveInterpreter()'] + ['i.runsource({})'.format(repr(l)) for l in (lines + [arg['code']])]

    return (yield from rextester(arg, lines, send))

help = [
    ('clear'        , 'clear'),
    ('vimcn'        , 'vimcn (code)'),
    ('bpaste'       , 'bpaste[:lang] (code)'),
    ('rust'         , 'rust (code)'),
    ('codepad'      , 'codepad:<lang> [run] (code)'),
    ('rex'          , 'rex:<lang> [args --] (code)'),
]

func = [
    (clear          , r"clear"),
    (vimcn          , r"vimcn(?:\s+(?P<code>.+))?"),
    (bpaste         , r"bpaste(?::(?P<lang>\S+))?(?:\s+(?P<code>.+))?"),
    (rust           , r"rust(?::(?P<raw>raw))?(?:\s+(?P<code>.+))?"),
    (codepad        , r"codepad:(?P<lang>\S+)(?:\s+(?P<run>run)(?::(?P<raw>raw))?)?(?:\s+(?P<code>.+))?"),
    (rextester      , r"rex:(?P<lang>[^\s:]+)(?::(?P<raw>raw))?(?:\s+(?P<args>.+?)\s+--)?(?:\s+(?P<code>.+))?"),
    (python3        , r">> (?P<code>.+)"),
]
