#ifndef SPACE_TRACE_H_
#define SPACE_TRACE_H_

#include "space_run.h"

/* Observer context is a FILE*; serialization is outside the emulator kernel. */
void space_trace_event(uint64_t tick, const space_event *event, void *context);

typedef struct {
  FILE *file;
  uint64_t copies;
  uint64_t channels;
} space_channel_trace;
void space_trace_channel_event(uint64_t tick, const space_event *event, void *context);

#endif
