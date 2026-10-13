#include <stdint.h>

/* Compiler guest helper. Every operation uses 32-bit cells and requires
 * neither a host arithmetic opcode nor a 64-bit compiler runtime. */
typedef struct { uint32_t lo, hi; } cc_u64;

static cc_u64 cc_u64_add(cc_u64 a, cc_u64 b)
{
    cc_u64 r = {a.lo+b.lo, a.hi+b.hi};
    r.hi += r.lo < a.lo;
    return r;
}
static cc_u64 cc_u64_neg(cc_u64 a)
{
    cc_u64 r = {~a.lo, ~a.hi}, one = {1, 0};
    return cc_u64_add(r, one);
}
static cc_u64 cc_u64_sub(cc_u64 a, cc_u64 b)
{
    return cc_u64_add(a, cc_u64_neg(b));
}
static int cc_u64_less(cc_u64 a, cc_u64 b)
{
    return a.hi < b.hi || (a.hi == b.hi && a.lo < b.lo);
}
static cc_u64 cc_u64_left(cc_u64 a)
{
    cc_u64 r = {a.lo << 1, (a.hi << 1) | (a.lo >> 31)};
    return r;
}
static cc_u64 cc_u64_right(cc_u64 a, int sign)
{
    cc_u64 r = {(a.lo >> 1) | (a.hi << 31), a.hi >> 1};
    if (sign) r.hi |= a.hi & 0x80000000u;
    return r;
}
static int cc_integer64_fold(unsigned op, const uint32_t *in, uint32_t *out)
{
    cc_u64 a = {in[0], in[1]}, b = {in[2], in[3]}, r = {0, 0};
    switch (op) {
    case 0: r = cc_u64_add(a, b); break;
    case 1: r = cc_u64_sub(a, b); break;
    case 2: r.lo = a.lo == b.lo && a.hi == b.hi; break;
    case 3:
        a.hi ^= 0x80000000u; b.hi ^= 0x80000000u;
        r.lo = cc_u64_less(a, b); break;
    case 4: r.lo = cc_u64_less(a, b); break;
    case 5: r.lo = a.lo & b.lo; r.hi = a.hi & b.hi; break;
    case 6: r.lo = a.lo | b.lo; r.hi = a.hi | b.hi; break;
    case 7: r.lo = a.lo ^ b.lo; r.hi = a.hi ^ b.hi; break;
    case 8: r.lo = ~a.lo; r.hi = ~a.hi; break;
    case 9: case 10: case 11:
        if (b.hi || b.lo >= 64) return 0;
        r = a;
        for (unsigned i=0; i<b.lo; ++i)
            r = op == 9 ? cc_u64_left(r) : cc_u64_right(r, op == 11);
        break;
    case 12:
        for (unsigned i=0; i<64; ++i) {
            if (b.lo & 1) r = cc_u64_add(r, a);
            a = cc_u64_left(a); b = cc_u64_right(b, 0);
        }
        break;
    case 13: case 14: case 15: case 16: {
        unsigned sign_a=0, sign_b=0;
        cc_u64 q = {0, 0};
        if (!(b.lo | b.hi)) return 0;
        if (op == 13 || op == 15) {
            if (a.hi == 0x80000000u && !a.lo &&
                b.hi == 0xffffffffu && b.lo == 0xffffffffu) return 0;
            sign_a = a.hi >> 31; sign_b = b.hi >> 31;
            if (sign_a) a = cc_u64_neg(a);
            if (sign_b) b = cc_u64_neg(b);
        }
        for (int i=63; i>=0; --i) {
            unsigned carry = r.hi >> 31;
            r = cc_u64_left(r);
            r.lo |= (i < 32 ? a.lo >> i : a.hi >> (i-32)) & 1;
            if (carry || !cc_u64_less(r, b)) {
                r = cc_u64_sub(r, b);
                if (i < 32) q.lo |= 1u << i;
                else q.hi |= 1u << (i-32);
            }
        }
        if (op == 13 || op == 14) {
            r = q;
            if (sign_a != sign_b) r = cc_u64_neg(r);
        } else if (sign_a) r = cc_u64_neg(r);
        break;
    }
    case 17: r.lo = (a.lo | a.hi) != 0; break;
    default: return 0;
    }
    out[0] = r.lo; out[1] = r.hi;
    return 1;
}
