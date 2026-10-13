_Static_assert((1ULL << 32) == 4294967296ULL, "wide constant");
long long f(long long x) { return x + (1LL << 32); }
int main(void) { return (f(3) >> 32) + (int)f(3); }
