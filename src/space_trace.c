#include "space_trace.h"

void space_trace_event(uint64_t tick, const space_event *event, void *context)
{
  FILE *trace = context;
  if(event->channel)
    fprintf(trace, "channel %llu %u %u %u %u %u\n",
            (unsigned long long)tick, event->slot, event->n, event->dst,
            event->copied, event->error);
  else
    fprintf(trace, "copy %llu %u %u %u %u\n", (unsigned long long)tick,
            event->slot, event->n, event->dst, event->src);
}
