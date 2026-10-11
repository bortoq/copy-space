#ifndef SPACE_TRACE_H_
#define SPACE_TRACE_H_

#include "space_run.h"

/* Observer context is a FILE*; serialization is outside the emulator kernel. */
void space_trace_event(uint64_t tick, const space_event *event, void *context);

#endif
