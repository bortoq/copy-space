#ifndef SPACE_RUN_H_
#define SPACE_RUN_H_

#include "space.h"

typedef enum {
  SPACE_STOP_IDLE,
  SPACE_STOP_LIMIT,
  SPACE_STOP_ERROR
} space_stop;

typedef struct {
  uint64_t ticks;
  space_stop reason;
} space_result;

typedef void (*space_run_observer)(uint64_t tick, const space_event *event, void *context);

space_result space_run(FILE *in, FILE *out, const uint64_t *limit,
                       space_run_observer observe, void *context);
const char *space_stop_name(space_stop reason);
int space_parse_ticks(const char *text, uint64_t *ticks);

#endif
