"""Initial scalar qualification checks; pointer and aggregate rules follow."""
valid = [
 ('const-int',b'int main(){const int x=7;return x;}',7),
 ('const-short',b'int main(){const short x=-1;return x+8;}',7),
 ('volatile-int',b'int main(){volatile int x=7;x+=2;return x;}',9),
 ('const-array',b'int main(){const int a[2]={1,7};return a[1];}',7),
 ('qualifier-guest',b'int main(){const int x=7;return x;}',7),
]
invalid = [
 ('const-write',b'int main(){const int x=1;x=7;return x;}'),
 ('const-increment',b'int main(){const int x=1;x++;return x;}'),
 ('const-initializer-write',b'int main(){const int x=1;int y=(x=7);return y;}'),
]
