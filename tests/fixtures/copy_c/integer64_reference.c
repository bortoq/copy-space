#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

/* Independent GNU C oracle, used only by the test runner on the host. */
int main(void)
{
    unsigned op;
    uint64_t a, b, r;
    while (scanf("%u %" SCNx64 " %" SCNx64, &op, &a, &b) == 3) {
        switch (op) {
        case 0: r = a + b; break;
        case 1: r = a - b; break;
        case 2: r = a == b; break;
        case 3: r = (int64_t)a < (int64_t)b; break;
        case 4: r = a < b; break;
        case 5: r = a & b; break;
        case 6: r = a | b; break;
        case 7: r = a ^ b; break;
        case 8: r = ~a; break;
        case 9: r = a << b; break;
        case 10: r = a >> b; break;
        case 11: r = (uint64_t)((int64_t)a >> b); break;
        case 12: r = a * b; break;
        case 13: r = (uint64_t)((int64_t)a / (int64_t)b); break;
        case 14: r = a / b; break;
        case 15: r = (uint64_t)((int64_t)a % (int64_t)b); break;
        case 16: r = a % b; break;
        case 17: r = a != 0; break;
        case 18: r = (((a + b) ^ b) * b) / b; break;
        default: return 2;
        }
        printf("%016" PRIx64 "\n", r);
    }
    return ferror(stdin) ? 1 : 0;
}
