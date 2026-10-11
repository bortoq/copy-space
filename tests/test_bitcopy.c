#include "space.h"

static unsigned get_bit(const unsigned char *p, size_t bit)
{
  return (p[bit / 8] >> (7 - bit % 8)) & 1;
}

static void reference(size_t n, const unsigned char *src, size_t a,
                      unsigned char *dst, size_t b)
{
  size_t i;
  for(i = 0; i < n; ++i)
  {
    unsigned char mask = (unsigned char)(1u << (7 - (b + i) % 8));
    dst[(b + i) / 8] = (unsigned char)((dst[(b + i) / 8] & ~mask) |
                                    (get_bit(src, a + i) ? mask : 0));
  }
}

int main(void)
{
  const size_t lengths[] = {0, 1, 2, 7, 8, 9, 15, 16, 31, 32,
                           63, 64, 65, 71, 127, 128, 129, 255};
  size_t a, b, k, mode, pattern, cases = 0;
  bitcpy(0, NULL, 0, NULL, 0);
  for(pattern = 0; pattern < 4; ++pattern)
    for(a = 0; a < 8; ++a)
      for(b = 0; b < 8; ++b)
        for(k = 0; k < sizeof lengths / sizeof lengths[0]; ++k)
          for(mode = 0; mode < 4; ++mode)
          {
            unsigned char original[128], expected[128], actual[128];
            unsigned char source[128];
            size_t n = lengths[k], src = a, dst = b, i;
            for(i = 0; i < sizeof original; ++i)
            {
              original[i] = pattern == 0 ? 0 : pattern == 1 ? 255 :
                            (unsigned char)(0xA5 + i * (pattern == 2 ? 37 : 19));
              source[i] = (unsigned char)(0x3C + i * 43);
            }
            if(mode == 2) src += 512;
            if(mode == 3) dst += 512;
            memcpy(expected, original, sizeof original);
            memcpy(actual, original, sizeof original);
            reference(n, mode == 0 ? source : original, src, expected, dst);
            bitcpy(n, mode == 0 ? source : actual, src, actual, dst);
            for(i = 0; i < sizeof source; ++i)
              if(source[i] != (unsigned char)(0x3C + i * 43)) return 1;
            if(memcmp(actual, expected, sizeof actual))
            {
              fprintf(stderr, "FAIL bitcpy: pattern=%lu mode=%lu src=%lu dst=%lu n=%lu\n",
                      (unsigned long)pattern, (unsigned long)mode, (unsigned long)src,
                      (unsigned long)dst, (unsigned long)n);
              return 1;
            }
            ++cases;
          }

  /* Exact allocations expose any read beyond the requested source. */
  for(a = 0; a < 8; ++a)
    for(b = 0; b < 8; ++b)
      for(k = 1; k < sizeof lengths / sizeof lengths[0]; ++k)
      {
        size_t n = lengths[k], ns = (a + n + 7) / 8, nd = (b + n + 7) / 8;
        unsigned char *src = malloc(ns), *dst = malloc(nd), *expected = malloc(nd);
        size_t i;
        if(!src || !dst || !expected) return 1;
        for(i = 0; i < ns; ++i) src[i] = (unsigned char)(0xA5 + i * 37);
        memset(dst, 0x3C, nd);
        memcpy(expected, dst, nd);
        reference(n, src, a, expected, b);
        bitcpy(n, src, a, dst, b);
        if(memcmp(dst, expected, nd)) return 1;
        free(src); free(dst); free(expected);
        ++cases;
      }
  printf("OK bitcpy: %lu independent comparisons\n", (unsigned long)cases);
  return 0;
}
