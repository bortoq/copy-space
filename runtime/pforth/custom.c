#include "pf_all.h"

#ifdef COPY_SPACE_C_COMPILER
#include "../copy_c/integer64_fold.h"
#include "../copy_c/preprocess_phase2.h"
#include "../copy_c/preprocess_macros.h"
/* Guest memory/channel primitives. C parsing and copy selection stay in Forth. */
static cell_t read_bytes(cell_t address, cell_t bytes)
{
    return cs_read((void *)(uintptr_t)address, (unsigned int)bytes);
}
static cell_t write_bytes(cell_t address, cell_t bytes)
{
    return cs_write((const void *)(uintptr_t)address, (unsigned int)bytes);
}
static cell_t exit_guest(cell_t code) { cs_exit((int)code); }
static cell_t put_bits(cell_t value, cell_t width, cell_t position,
                       cell_t address, cell_t reversed)
{
    uint32_t bits = (uint32_t)value, at = (uint32_t)position;
    unsigned remaining = (unsigned)width;
    unsigned char *buffer = (unsigned char *)(uintptr_t)address;
    const unsigned char *table = (const unsigned char *)(uintptr_t)reversed;
    if (remaining > 32) cs_exit(2);
    while (remaining) {
        unsigned offset = at & 7, part = 8-offset;
        if (part > remaining) part = remaining;
        unsigned shift = 8-offset-part, mask = ((1u << part)-1) << shift;
        buffer[at >> 3] = (buffer[at >> 3] & ~mask)
                       | ((table[bits & 255] >> offset) & mask);
        bits >>= part;
        at += part;
        remaining -= part;
    }
    return 0;
}
static cell_t fold_integer64(cell_t operation, cell_t input, cell_t output)
{
    return cc_integer64_fold((unsigned)operation,
                            (const uint32_t *)(uintptr_t)input,
                            (uint32_t *)(uintptr_t)output);
}
static cell_t preprocess_phase2(cell_t source, cell_t length)
{
    return (cell_t)cc_preprocess_phase2((unsigned char *)(uintptr_t)source,
                                      (unsigned)length);
}
static cell_t preprocess_macros(cell_t source, cell_t length)
{
    return (cell_t)cc_preprocess_macros((unsigned char *)(uintptr_t)source,
                                      (unsigned)length);
}
CFunc0 CustomFunctionTable[7] = {
    (CFunc0)read_bytes, (CFunc0)write_bytes, (CFunc0)exit_guest, (CFunc0)put_bits,
    (CFunc0)fold_integer64, (CFunc0)preprocess_phase2, (CFunc0)preprocess_macros
};
Err CompileCustomFunctions(void)
{
#ifndef PF_NO_INIT
    Err err = CreateGlueToC("CS-READ", 0, C_RETURNS_VALUE, 2);
    if(err < 0) return err;
    err = CreateGlueToC("CS-WRITE", 1, C_RETURNS_VALUE, 2);
    if(err < 0) return err;
    err = CreateGlueToC("CS-EXIT", 2, C_RETURNS_VOID, 1);
    if(err < 0) return err;
    err = CreateGlueToC("CS-PUT-BITS", 3, C_RETURNS_VOID, 5);
    if(err < 0) return err;
    err = CreateGlueToC("CS-FOLD64", 4, C_RETURNS_VALUE, 3);
    if(err < 0) return err;
    err = CreateGlueToC("CS-PREPROCESS-PHASE2", 5, C_RETURNS_VALUE, 2);
    if(err < 0) return err;
    return CreateGlueToC("CS-PREPROCESS-MACROS", 6, C_RETURNS_VALUE, 2);
#else
    return 0;
#endif
}
#else
CFunc0 CustomFunctionTable[1] = {0};
Err CompileCustomFunctions(void) { return 0; }
#endif

int sdTerminalOut(char c) { return cs_write(&c, 1) == 1 ? 0 : -1; }
int sdTerminalEcho(char c) { (void)c; return 0; }
int sdTerminalIn(void)
{
    unsigned char c;
    int count = cs_read(&c, 1);
    if(count < 0) cs_exit(1);
    return count ? c : -1;
}
int sdTerminalFlush(void) { return 0; }
int sdQueryTerminal(void) { return 0; }
void sdTerminalInit(void) {}
void sdTerminalTerm(void) {}
cell_t sdSleepMillis(cell_t msec) { (void)msec; return PF_ERR_NOT_SUPPORTED; }
