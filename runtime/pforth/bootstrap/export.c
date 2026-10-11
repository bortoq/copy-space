#include "pf_all.h"

static void put_word(uint32_t value)
{
    unsigned char raw[4];
    for(unsigned int i=0; i<4; ++i) raw[i] = (unsigned char)(value >> (8*i));
    if(cs_write(raw, 4) != 4) cs_exit(1);
}

int main(void)
{
    ExecToken entry = 0;
    char line[TIB_SIZE];
    unsigned int length = 0;
    pfSetQuiet(1);
    if(sizeof(cell_t) != 4 || !IsHostLittleEndian()) return 70;
    if(pfInitialize(NULL, 1, &entry)) return 3;
    for(;;)
    {
        unsigned char c;
        int count = cs_read(&c, 1);
        if(count < 0) return 1;
        if(count == 0 || c == '\n')
        {
            line[length] = 0;
            if(length && pfInterpretText(line)) return 2;
            length = 0;
            if(count == 0) break;
        }
        else
        {
            if(length == sizeof line-1) return 2;
            line[length++] = (char)c;
        }
    }
    if(gVarState || pfGetStackDepth()) return 2;
    uint32_t names = gCurrentDictionary->dic_HeaderPtr-gCurrentDictionary->dic_HeaderBase;
    uint32_t code = gCurrentDictionary->dic_CodePtr-gCurrentDictionary->dic_CodeBase;
    if(cs_write("PFD1", 4) != 4) return 1;
    put_word(names);
    put_word(code);
    put_word(gVarContext-gCurrentDictionary->dic_HeaderBase);
    put_word(NUM_PRIMITIVES);
    if(cs_write((void *)(uintptr_t)gCurrentDictionary->dic_HeaderBase, names) != (int)names ||
       cs_write((void *)(uintptr_t)gCurrentDictionary->dic_CodeBase, code) != (int)code)
        return 1;
    pfTerminate();
    return 0;
}
