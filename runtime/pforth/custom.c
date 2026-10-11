#include "pf_all.h"

#ifdef COPY_SPACE_C_COMPILER
/* Guest channel adapters only. Parsing and code generation stay in Forth. */
static cell_t read_bytes(cell_t address, cell_t bytes)
{
    return cs_read((void *)(uintptr_t)address, (unsigned int)bytes);
}
static cell_t write_bytes(cell_t address, cell_t bytes)
{
    return cs_write((const void *)(uintptr_t)address, (unsigned int)bytes);
}
static cell_t exit_guest(cell_t code) { cs_exit((int)code); }
CFunc0 CustomFunctionTable[3] = {
    (CFunc0)read_bytes, (CFunc0)write_bytes, (CFunc0)exit_guest
};
Err CompileCustomFunctions(void)
{
#ifndef PF_NO_INIT
    Err err = CreateGlueToC("CS-READ", 0, C_RETURNS_VALUE, 2);
    if(err < 0) return err;
    err = CreateGlueToC("CS-WRITE", 1, C_RETURNS_VALUE, 2);
    if(err < 0) return err;
    return CreateGlueToC("CS-EXIT", 2, C_RETURNS_VOID, 1);
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
