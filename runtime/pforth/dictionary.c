/* Use the upstream endian helpers and unsupported-file stubs. Its cloning
 * loader is unused: our writable dictionary is already in the initial image. */
#define pfLoadStaticDictionary pfLoadClonedStaticDictionary
#include "../../third_party/pforth/csrc/pf_save.c"
#undef pfLoadStaticDictionary

PForthDictionary pfLoadStaticDictionary(void)
{
    pfDictionary_t *dic = (pfDictionary_t *)pfAllocMem(sizeof *dic);
    if(!dic) return NULL;
    pfSetMemory(dic, 0, sizeof *dic);
    gCurrentDictionary = dic;
    dic->dic_HeaderBase = PTR_TO_VMA(MinDicNames);
    dic->dic_HeaderLimit = dic->dic_HeaderBase+sizeof MinDicNames;
    dic->dic_HeaderPtr = dic->dic_HeaderBase+HEADERPTR;
    dic->dic_CodeBase = PTR_TO_VMA(MinDicCode);
    dic->dic_CodeLimit = dic->dic_CodeBase+sizeof MinDicCode;
    dic->dic_CodePtr = dic->dic_CodeBase+CODEPTR;
    gVarContext = dic->dic_HeaderBase+RELCONTEXT;
    gNumPrimitives = NUM_PRIMITIVES;
    if(FindSpecialXTs() < 0)
    {
        pfFreeMem(dic);
        gCurrentDictionary = NULL;
        return NULL;
    }
    return dic;
}
