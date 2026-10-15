/* SPDX-License-Identifier: Apache-2.0 */
/* Low 64 bits of multiplication for generated little-endian copy programs.
 * Only 32-bit arithmetic is used, so compiling this helper cannot call itself. */
#if __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error "copyspace target helpers require little-endian word order"
#endif
typedef __UINT32_TYPE__ cs_target_u32;
typedef __UINT64_TYPE__ cs_target_u64;
union cs_target_double_word {
    cs_target_u64 value;
    struct { cs_target_u32 low, high; } word;
};
_Static_assert(sizeof(cs_target_u32) == 4, "32-bit words required");
_Static_assert(sizeof(union cs_target_double_word) == 8, "64-bit product required");

cs_target_u64 __muldi3(cs_target_u64 left, cs_target_u64 right)
{
    union cs_target_double_word a = {.value = left}, b = {.value = right}, result;
    cs_target_u32 a0 = a.word.low & 65535, a1 = a.word.low >> 16;
    cs_target_u32 b0 = b.word.low & 65535, b1 = b.word.low >> 16;
    cs_target_u32 low = a0 * b0;
    cs_target_u32 middle = a1 * b0 + (low >> 16);
    cs_target_u32 high = middle >> 16;
    middle = (middle & 65535) + a0 * b1;
    result.word.low = (middle << 16) | (low & 65535);
    result.word.high = a1 * b1 + high + (middle >> 16) +
                       a.word.low * b.word.high + a.word.high * b.word.low;
    return result.value;
}
