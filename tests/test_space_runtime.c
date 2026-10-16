#define _POSIX_C_SOURCE 200809L
#include "space_run.h"
#include <unistd.h>

#define CHECK(value) do { if(!(value)) { \
  fprintf(stderr, "FAIL runtime line %d\n", __LINE__); return 1; } } while(0)

static void field(size address, size width, size value)
{
  size bit;
  for(bit = 0; bit < width; ++bit)
  {
    unsigned char mask = (unsigned char)(1u << (7 - (address + bit) % 8));
    unsigned char *byte = (unsigned char *)&space[(address + bit) / 8];
    *byte = (unsigned char)((*byte & ~mask) | ((value >> bit & 1u) ? mask : 0));
  }
}

static void instruction(size slot, size n, size dst, size src)
{
  field(slot * INSTRUCTION_SIZE, N_SIZE, n);
  field(slot * INSTRUCTION_SIZE + N_SIZE, ADDRESS_SIZE, dst);
  field(slot * INSTRUCTION_SIZE + N_SIZE + ADDRESS_SIZE, ADDRESS_SIZE, src);
}

static void log_event(const space_event *event, void *context)
{
  (void)context;
  printf("event channel=%d slot=%u n=%u dst=%u src=%u copied=%u error=%u\n",
         event->channel, event->slot, event->n, event->dst, event->src,
         event->copied, event->error);
}

int main(void)
{
  FILE *in = tmpfile(), *out = tmpfile();
  uint64_t limit = 1;
  space_result result;
  const unsigned char byte = 0xA5;
  CHECK(in && out);

  /* A zero limit distinguishes an idle processor from an active one,
   * and an exact-limit halt is still idle, not a limit stop. */
  CHECK(space_init(NULL, 0) == 0);
  limit = 0;
  result = space_run(in, out, &limit, NULL, NULL);
  CHECK(result.ticks == 0 && result.reason == SPACE_STOP_IDLE);
  instruction(0, PROCESSOR_BITS, 0, PROCESSOR_BITS);
  result = space_run(in, out, &limit, NULL, NULL);
  CHECK(result.ticks == 0 && result.reason == SPACE_STOP_LIMIT);
  CHECK(processor[0][0] == PROCESSOR_BITS);
  limit = 1;
  result = space_run(in, out, &limit, NULL, NULL);
  CHECK(result.ticks == 1 && result.reason == SPACE_STOP_IDLE);
  CHECK(processor[0][0] == 0);

  /* The runner resumes existing memory instead of restoring a built-in core. */
  CHECK(space_init(NULL, 0) == 0);
  instruction(0, 8, 65536, 65544);
  space[8193] = (char)byte;
  result = space_run(in, out, &limit, NULL, NULL);
  CHECK(result.ticks == 1 && result.reason == SPACE_STOP_LIMIT);
  CHECK((unsigned char)space[8192] == byte);
  space[8193] = 0x3C;
  result = space_run(in, out, &limit, NULL, NULL);
  CHECK(result.ticks == 1 && result.reason == SPACE_STOP_LIMIT);
  CHECK((unsigned char)space[8192] == 0x3C);

  /* New data can be read after EOF without rewinding or replacing the stream. */
  CHECK(space_init(NULL, 0) == 0);
  instruction(1, 8, 65536, 0);
  CHECK(space_step(in, out, log_event, NULL) == SPACE_STEP_DONE);
  CHECK(feof(in));
  CHECK(pwrite(fileno(in), &byte, 1, 0) == 1);
  CHECK(space_step(in, out, log_event, NULL) == SPACE_STEP_DONE);
  space_read_processor();
  CHECK((unsigned char)space[8192] == byte && processor[1][2] == 16);

  /* Rejected initial images leave memory intact; overlapping image load works. */
  CHECK(space_init(NULL, 1) == -1);
  CHECK(space_init(&byte, (size_t)VM_SPACE_BYTES + 1) == -1);
  CHECK((unsigned char)space[8192] == byte);
  CHECK(space_init(space + 8192, 1) == 0);
  CHECK((unsigned char)space[0] == byte && space[8192] == 0);
  CHECK(fclose(in) == 0 && fclose(out) == 0);
  puts("OK runtime: resume, retry after EOF, initial image bounds");
  return 0;
}
