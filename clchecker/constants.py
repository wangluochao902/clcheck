
BASETYPE = '''

// base type for the DSL
VERSION:
    /[^=\s]+/ | STRING
;

ANY:
    STRING | /[\S]+/
;

PATH:
    /(?:\/)?(?:[\*\w\-\.]*\/)*[\*\w\-\.]+/ | STRING
;

DIR:
    /(?:\/)?(?:[\*\w\-\.]*\/)*[\*\w\.\-]+(?:\/)?/ | STRING
;

PKG:
//    /[\w\*][:\w\.\-\*\+]*/
    /[^=\s]+/
;
'''