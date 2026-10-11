#ifndef COPY_SPACE_PFORTH_ASSERT_H
#define COPY_SPACE_PFORTH_ASSERT_H
#include "copy_space.h"
#define assert(condition) do { if(!(condition)) cs_exit(70); } while(0)
#endif
