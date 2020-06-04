
BASETYPE = r'''

// base type for the DSL
VERSION:
    /(?!-)[^=\s]+/ | STRING
;

bANY:
    STRING | /(?<!(\w|\-))(?!-)[\S]+(?!(\w|\-))/
;

ANY:
    STRING | /(?!-)[\S]+/
;

bPATHorDIR:
    bPATH | bDIR
;

PATH:
    /(?!-)\/?(\S*\/)*\S+/ | STRING
;

bPATH:
    /(?<!(\w|\-))(?!-)\/?(\S*\/)*\S+/ | STRING
;

DIR:
    /(?!-)\/?(\S*\/)*\S+\/?/ | STRING
;

bDIR:
    /(?<!(\w|\-))(?!-)\/?(\S*\/)*\S+\/?/ | STRING
;

PKG:
    /(?!-)[^=\s]+/
;

bPKG:
    /(?<!(\w|\-))(?!-)[^=\s]+/
;

sINT:
    /[-+]?[0-9]+(?=(\s|$))/
;

INT:
    sINT | /"[-+]?[0-9]+"(?=(\s|$))|'[-+]?[0-9]+'(?=(\s|$))/
;
'''