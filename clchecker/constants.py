
BASETYPE = '''

// base type for the DSL
VERSION:
    /(?!-)[^=\s]+/ | STRING
;

sANY:
    STRING | /(?<!(\w|\-))(?!-)[\S]+(?!(\w|\-))/
;

ANY:
    STRING | /(?!-)[\S]+/
;

PATH:
    /(?!-)\/?(\S*\/)*\S+/ | STRING
;

sPATH:
    /(?<!(\w|\-))(?!-)\/?(\S*\/)*\S+/ | STRING
;

DIR:
    /(?!-)\/?(\S*\/)*\S+\/?/ | STRING
;

sDIR:
    /(?<!(\w|\-))(?!-)\/?(\S*\/)*\S+\/?/ | STRING
;

PKG:
    /(?!-)[^=\s]+/
;

sPKG:
    /(?<!(\w|\-))(?!-)[^=\s]+/
;
'''