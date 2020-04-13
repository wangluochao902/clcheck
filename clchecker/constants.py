
BASETYPE = '''

// base type for the DSL
VERSION:
    content=/[\S]+/
;

NOTWHITESPACE:
    content=/[\S]+/
;

PATH:
    content=/(?:\/)?(?:[\*\w\-\.]*\/)*[\*\w\-\.]+/
;

DIR:
    content=/(?:\/)?(?:[\*\w\-\.]*\/)*[\*\w\.\-]+(?:\/)?/
;

PKG:
//    content=/[\w\*][:\w\.\-\*\+]*/
    content=/[\S]+/
;
'''