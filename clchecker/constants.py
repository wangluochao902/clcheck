
BASETYPE = '''

// base type for the DSL
VERSION:
    content=/[1-9\*\.]+/
;

RELEASE:
    content=/[^-][\w\.\-\*]*/
;

PATH:
    content=/[^-](?:\/)?(?:[\*\w\-\.]*\/)*[\*\w\-\.]+/
;

DIR:
    content=/[^-](?:\/)?(?:[\*\w\-\.]*\/)*[\*\w\.\-]+(?:\/)?/
;

PKG:
    content=/[\w\*][\w\.\-\*]*/
;
'''