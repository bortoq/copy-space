"""Narrow character constants and escape decoding compared with GCC ILP32."""
expressions = [
 ('char-ascii',br"'A'",65),('char-zero',br"'\0'",0),
 ('char-newline',br"'\n'",10),('char-tab',br"'\t'",9),
 ('char-quote',br"'\''",39),('char-backslash',br"'\\'",92),
 ('char-double-quote',br"'\"'",34),('char-question',br"'\?'",63),
 ('char-bell',br"'\a'",7),('char-backspace',br"'\b'",8),
 ('char-formfeed',br"'\f'",12),('char-return',br"'\r'",13),
 ('char-vtab',br"'\v'",11),('char-escape',br"'\e'",27),
 ('char-escape-upper',br"'\E'",27),('char-octal',br"'\101'",65),
 ('char-hex',br"'\x41'",65),('char-signed',br"'\xff'",-1),
 ('char-octal-signed',br"'\377'",-1),('char-octal-truncate',br"'\777'",-1),
 ('char-hex-truncate',br"'\x123'",35),('char-multi',br"'AB'",16706),
 ('char-multi-high',br"'\xff\x80'",65408),('char-four',br"'ABCD'",1094861636),
 ('char-five',br"'xABCD'",1094861636),('char-size',br"sizeof('A')",4),
 ('char-splice',b"'a\\\nb'",24930),
]
valid = [(name,b'int main(){return '+expr+b';}',value) for name,expr,value in expressions]
valid += [
 ('char-enum',br"enum E{A='A',B='B'};int main(){return B-A;}",1),
 ('char-array',br"int main(){char a[3]={'a','b','c'};return a[2];}",99),
 ('char-guest',br"int main(){return '\n'+'A';}",75),
]
invalid = [
 ('char-empty',br"int main(){return ''; }"),
 ('char-unclosed',br"int main(){return 'a; }"),
 ('char-empty-hex',br"int main(){return '\x'; }"),
 ('char-line-break',b"int main(){return 'a\nb';}"),
 ('char-universal-pending',br"int main(){return '\u00e9';}"),
 ('char-wide-pending',br"int main(){return L'a';}"),
]
