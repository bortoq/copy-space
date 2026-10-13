#include <inttypes.h>
#include <stdio.h>
#include "integer64_fold.h"

int main(void)
{
    unsigned op;
    uint64_t a,b;
    while (scanf("%u %" SCNx64 " %" SCNx64, &op, &a, &b) == 3) {
        uint32_t input[4] = {(uint32_t)a, (uint32_t)(a >> 32),
                             (uint32_t)b, (uint32_t)(b >> 32)};
        uint32_t output[2] = {0, 0};
        int valid=cc_integer64_fold(op, input, output);
        printf("%d %08" PRIx32 "%08" PRIx32 "\n",valid,output[1],output[0]);
    }
    return ferror(stdin) ? 1 : 0;
}
