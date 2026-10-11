#ifndef COPY_SPACE_PFORTH_CONFIG_H
#define COPY_SPACE_PFORTH_CONFIG_H
#include "copy_space.h"
#undef EXIT
#define EXIT(code) cs_exit(code)
#undef PF_ASSERT
#define PF_ASSERT(condition) do { if(!(condition)) cs_exit(70); } while(0)
#endif
