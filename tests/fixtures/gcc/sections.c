/* Multiple init-style code sections and separately placed volatile data.
 * Runtime reads and noipa keep the placement test out of constant folding. */
_Static_assert(sizeof(unsigned)==4, "32-bit unsigned ABI");
#define DECLARE(N) \
    static volatile unsigned cell##N \
        __attribute__((section(".data.cell" #N))) = (N)*2654435761U+7U; \
    static unsigned __attribute__((noipa, section(".init.text.step" #N))) \
        step##N(void) { return cell##N; }
#define ALL(M) \
    M(0) M(1) M(2) M(3) M(4) M(5) M(6) M(7) M(8) M(9) \
    M(10) M(11) M(12) M(13) M(14) M(15) M(16) M(17) M(18) M(19) \
    M(20) M(21) M(22) M(23) M(24) M(25) M(26) M(27) M(28) M(29) \
    M(30) M(31) M(32) M(33) M(34) M(35) M(36) M(37) M(38) M(39)
ALL(DECLARE)
unsigned value(void)
{
    unsigned hash=5381U;
#define CHECK(N) hash=(hash*33U)^step##N();
    ALL(CHECK)
    return hash;
}
