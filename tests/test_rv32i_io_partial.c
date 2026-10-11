#define _GNU_SOURCE
#include "core.h"
#include "space_trace.h"
#include <errno.h>
#include <sys/types.h>

/* Device fixture: three bytes succeed, then the stream reports an I/O error. */
typedef struct {
  size_t copied, limit;
  const char *input;
  char bytes[3];
} device;

static ssize_t read_device(void *context, char *buffer, size_t bytes)
{
  device *state = context;
  if(state->copied == state->limit)
  {
    errno = EIO;
    return -1;
  }
  if(bytes > state->limit - state->copied)
    bytes = state->limit - state->copied;
  memcpy(buffer, state->input + state->copied, bytes);
  state->copied += bytes;
  return (ssize_t)bytes;
}

static ssize_t write_device(void *context, const char *buffer, size_t bytes)
{
  device *state = context;
  if(bytes > 3 - state->copied)
    bytes = 3 - state->copied;
  memcpy(state->bytes + state->copied, buffer, bytes);
  state->copied += bytes;
  errno = EIO;
  return (ssize_t)bytes;
}

int main(int argc, char **argv)
{
  device state = {0, 3, "abc", {0}};
  cookie_io_functions_t functions = {read_device, write_device, NULL, NULL};
  FILE *in, *out, *cookie, *trace, *dump, *accepted;
  int output, failed = 0;
  uint64_t ticks = 10000;
  space_result result;
  char *packet = NULL;
  if(argc != 6 && argc != 7)
    return 1;
  if(argc == 7)
  {
    char *end;
    unsigned long long limit = strtoull(argv[6], &end, 10);
    FILE *file;
    if(strcmp(argv[2], "stream") != 0 || !*argv[6] || *end ||
       limit > VM_SPACE_BYTES || core_init() != 0)
      return 1;
    file = fopen(argv[1], "rb");
    packet = malloc((size_t)limit + 1);
    if(!file || !packet || fread(packet, 1, (size_t)limit, file) != limit)
      return 1;
    if(fclose(file) != 0)
      return 1;
    state.input = packet;
    state.limit = (size_t)limit;
  }
  else if(core_load_file(argv[1]) != 0)
    return 1;
  output = strcmp(argv[2], "out") == 0;
  cookie = fopencookie(&state, output ? "w" : "r", functions);
  in = output ? tmpfile() : cookie;
  out = output ? cookie : tmpfile();
  trace = fopen(argv[3], "w");
  if(!in || !out || !trace)
    return 1;
  setvbuf(out, NULL, _IONBF, 0);
  result = space_run(in, out, &ticks, space_trace_event, trace);
  fprintf(trace, "stop %llu %s\n", (unsigned long long)result.ticks, space_stop_name(result.reason));
  if(fclose(trace) != 0)
    failed = 1;
  dump = fopen(argv[4], "wb");
  if(!dump)
    return 1;
  if(fwrite(space, 1, sizeof space, dump) != sizeof space)
    failed = 1;
  if(fclose(dump) != 0)
    failed = 1;
  accepted = fopen(argv[5], "wb");
  if(!accepted)
    return 1;
  if(output && fwrite(state.bytes, 1, state.copied, accepted) != state.copied)
    failed = 1;
  if(fclose(accepted) != 0)
    failed = 1;
  fclose(in);
  fclose(out);
  free(packet);
  return failed || result.reason != SPACE_STOP_IDLE;
}
