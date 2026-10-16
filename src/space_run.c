#include "space_run.h"
#include <errno.h>

typedef struct {
  uint64_t tick;
  space_run_observer observe;
  void *context;
} observation;

static void forward_event(const space_event *event, void *context)
{
  observation *state = context;
  state->observe(state->tick, event, state->context);
}

const char *space_stop_name(space_stop reason)
{
  static const char *names[] = {"idle", "limit", "error"};
  return names[reason];
}

int space_parse_ticks(const char *text, uint64_t *ticks)
{
  char *end;
  unsigned long long value;
  if(text[0] < '0' || text[0] > '9')
    return -1;
  errno = 0;
  value = strtoull(text, &end, 0);
  if(errno || *end || value > UINT64_MAX)
    return -1;
  *ticks = (uint64_t)value;
  return 0;
}

space_result space_run(FILE *in, FILE *out, const uint64_t *limit,
                       space_run_observer observe, void *context)
{
  space_result result = {0, SPACE_STOP_IDLE};
  observation state = {0, observe, context};
  for(;;)
  {
    if(limit && result.ticks == *limit)
    {
      /* An idle processor takes precedence over the tick limit. */
      if(space_active())
        result.reason = SPACE_STOP_LIMIT;
      break;
    }
    state.tick = result.ticks;
    /* space_step checks activity before servicing channels or copies.
     * Reading all processor fields here as well duplicates that work. */
    space_step_result step = space_step(in, out, observe ? forward_event : NULL, &state);
    if(step == SPACE_STEP_IDLE)
      break;
    if(step == SPACE_STEP_ERROR)
    {
      result.reason = SPACE_STOP_ERROR;
      break;
    }
    if(result.ticks != UINT64_MAX)
      ++result.ticks;
  }
  space_read_processor();
  return result;
}
