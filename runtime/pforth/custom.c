#include "pf_all.h"

CFunc0 CustomFunctionTable[1] = {0};
Err CompileCustomFunctions(void) { return 0; }

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
