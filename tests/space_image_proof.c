/*
 * IMAGE PROOF RUNNER
 *
 * purpose: run active space semantics against a fixed IN image,
 * capture OUT, and optionally dump final space bytes for proof/debug.
 */
#include "space_run.h"
#include "core.h"
#include "space_trace.h"

enum {
  DEFAULT_TICKS = 1024,
};

static void die(const char *msg)
{
  fprintf(stderr, "%s\n", msg);
  exit(1);
}

static void write_file(const char *path, const unsigned char *buf, size_t len)
{
  FILE *f = fopen(path, "wb");
  if(!f)
    die("cannot open output file");
  if(len > 0 && fwrite(buf, 1, len, f) != len)
    die("cannot write output file");
  if(fclose(f) != 0)
    die("cannot write output file");
}

static void write_processor_dump(const char *path)
{
  FILE *f;
  unsigned i;
  f = fopen(path, "w");
  if(!f)
    die("cannot open processor dump file");
  space_read_processor();
  for(i = 0; i < PROCESSOR_N; ++i)
    fprintf(f, "%u %u %u %u\n", i, processor[i][0], processor[i][1], processor[i][2]);
  if(fclose(f) != 0)
    die("cannot write processor dump file");
}

int main(int argc, char **argv)
{
  const char *in_path = NULL;
  const char *out_path = NULL;
  const char *dump_path = NULL;
  const char *dump_proc_path = NULL;
  const char *report_path = NULL;
  const char *trace_path = NULL;
  const char *core_path = NULL;
  uint64_t ticks = DEFAULT_TICKS;
  const uint64_t *limit = &ticks;
  FILE *in;
  FILE *out;
  FILE *trace = NULL;
  space_result result;
  int i;

  for(i = 1; i < argc; ++i)
  {
    if(strcmp(argv[i], "--in") == 0 && i + 1 < argc)
      in_path = argv[++i];
    else if(strcmp(argv[i], "--out") == 0 && i + 1 < argc)
      out_path = argv[++i];
    else if(strcmp(argv[i], "--dump-space") == 0 && i + 1 < argc)
      dump_path = argv[++i];
    else if(strcmp(argv[i], "--dump-processor") == 0 && i + 1 < argc)
      dump_proc_path = argv[++i];
    else if(strcmp(argv[i], "--report") == 0 && i + 1 < argc)
      report_path = argv[++i];
    else if(strcmp(argv[i], "--trace") == 0 && i + 1 < argc)
      trace_path = argv[++i];
    else if(strcmp(argv[i], "--core") == 0 && i + 1 < argc)
      core_path = argv[++i];
    else if(strcmp(argv[i], "--unlimited") == 0)
      limit = NULL;
    else if(strcmp(argv[i], "--ticks") == 0 && i + 1 < argc)
    {
      if(space_parse_ticks(argv[++i], &ticks) != 0)
        die("invalid tick count");
      limit = &ticks;
    }
    else
      die("usage: space_image_proof --in FILE [--core FILE] [--out FILE] [--dump-space FILE] [--dump-processor FILE] [--ticks N | --unlimited] [--report FILE] [--trace FILE]");
  }
  if(!in_path)
    die("usage: space_image_proof --in FILE [--core FILE] [--out FILE] [--dump-space FILE] [--dump-processor FILE] [--ticks N | --unlimited] [--report FILE] [--trace FILE]");

  in = fopen(in_path, "rb");
  if(!in)
    die("cannot open input file");
  out = out_path ? fopen(out_path, "wb") : tmpfile();
  if(!out)
    die("cannot open output file");
  setvbuf(out, NULL, _IONBF, 0);
  if(trace_path)
  {
    trace = fopen(trace_path, "w");
    if(!trace)
      die("cannot open trace file");
  }

  if((core_path ? core_load_file(core_path) : core_init()) != 0)
    die("cannot load core");
  result = space_run(in, out, limit, trace ? space_trace_event : NULL, trace);
  if(trace)
    fprintf(trace, "stop %llu %s\n", (unsigned long long)result.ticks,
            space_stop_name(result.reason));
  fclose(in);
  if(fclose(out) != 0)
    die("cannot write output file");
  if(dump_path)
    write_file(dump_path, (unsigned char*)space, sizeof space);
  if(dump_proc_path)
    write_processor_dump(dump_proc_path);
  if(trace && fclose(trace) != 0)
    die("cannot write trace file");
  if(report_path)
  {
    FILE *report = fopen(report_path, "w");
    if(!report)
      die("cannot open report file");
    fprintf(report, "in=%s\ncore=%s\nunlimited=%d\nrequested_ticks=%llu\nticks=%llu\nstop=%s\nspace_bytes=%u\nprocessor_n=%u\n",
            in_path, core_path ? core_path : "default", !limit,
            (unsigned long long)ticks, (unsigned long long)result.ticks,
            space_stop_name(result.reason), VM_SPACE_BYTES, PROCESSOR_N);
    if(fclose(report) != 0)
      die("cannot write report file");
  }

  return result.reason == SPACE_STOP_ERROR ? 1 : 0;
}
