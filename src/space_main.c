#include "space_run.h"
#include "core.h"
#include "space_trace.h"

int main(int argc, char **argv)
{
  space_result result;
  const char *core_path = NULL;
  const char *dump_path = NULL;
  const char *trace_path = NULL;
  FILE *trace = NULL;
  int channels_only = 0;
  space_channel_trace channel_trace = {NULL, 0, 0};
  uint64_t ticks = 0;
  const uint64_t *limit = NULL;
  int i;
  for(i = 1; i < argc; ++i)
  {
    if(strcmp(argv[i], "--core") == 0 && i + 1 < argc)
      core_path = argv[++i];
    else if(strcmp(argv[i], "--dump-space") == 0 && i + 1 < argc)
      dump_path = argv[++i];
    else if(strcmp(argv[i], "--trace") == 0 && i + 1 < argc)
    {
      if(trace_path && channels_only) { fprintf(stderr, "choose one trace mode\n"); return 1; }
      trace_path = argv[++i];
    }
    else if(strcmp(argv[i], "--trace-channels") == 0 && i + 1 < argc)
    {
      if(trace_path && !channels_only) { fprintf(stderr, "choose one trace mode\n"); return 1; }
      trace_path = argv[++i];
      channels_only = 1;
    }
    else if(strcmp(argv[i], "--ticks") == 0 && i + 1 < argc)
    {
      if(space_parse_ticks(argv[++i], &ticks) != 0)
      {
        fprintf(stderr, "invalid tick count\n");
        return 1;
      }
      limit = &ticks;
    }
    else
    {
      fprintf(stderr, "usage: space [--core FILE] [--ticks N] [--dump-space FILE] [--trace FILE | --trace-channels FILE]\n");
      return 1;
    }
  }
  if((core_path ? core_load_file(core_path) : core_init()) != 0)
  {
    fprintf(stderr, "cannot load core\n");
    return 1;
  }
  if(trace_path)
  {
    trace = fopen(trace_path, "w");
    if(!trace)
    {
      fprintf(stderr, "cannot open trace file\n");
      return 1;
    }
  }
  setvbuf(stdout, NULL, _IONBF, 0);
  channel_trace.file = trace;
  result = space_run(stdin, stdout, limit,
                     trace ? (channels_only ? space_trace_channel_event : space_trace_event) : NULL,
                     channels_only ? (void *)&channel_trace : (void *)trace);
  if(trace)
  {
    int failed;
    if(channels_only)
      fprintf(trace, "counts %llu %llu\n", (unsigned long long)channel_trace.copies,
              (unsigned long long)channel_trace.channels);
    fprintf(trace, "stop %llu %s\n", (unsigned long long)result.ticks,
            space_stop_name(result.reason));
    failed = ferror(trace);
    if(fclose(trace) != 0 || failed)
    {
      fprintf(stderr, "cannot write trace file\n");
      return 1;
    }
  }
  if(dump_path)
  {
    FILE *dump = fopen(dump_path, "wb");
    int failed;
    if(!dump)
    {
      fprintf(stderr, "cannot open space dump\n");
      return 1;
    }
    failed = fwrite(space, 1, sizeof space, dump) != sizeof space;
    if(fclose(dump) != 0 || failed)
    {
      fprintf(stderr, "cannot write space dump\n");
      return 1;
    }
  }
  return result.reason == SPACE_STOP_ERROR ? 1 : 0;
}
