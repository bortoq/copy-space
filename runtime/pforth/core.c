/* Keep the upstream source intact; its public text API has one unconditional
 * strlen call despite PF_NO_CLIB. Use pForth's own length implementation. */
#define strlen pfCStringLength
#include "../../third_party/pforth/csrc/pf_core.c"
