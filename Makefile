# file: Makefile
# purpose: minimal build for Copy-Space demo1 baseline

SHELL := /bin/sh

CC ?= cc
CFLAGS ?= -O2 -g -std=c99 -Wall -Wextra
CPPFLAGS ?=
LDFLAGS ?=
LDLIBS ?=

OBJDIR := build/obj
BINDIR := build/bin

INCLUDES := -Isrc

EMULATOR_SRCS := src/space.c src/bitcopy.c
EMULATOR_OBJS := $(addprefix $(OBJDIR)/,$(EMULATOR_SRCS:.c=.o))
RUN_SRCS := src/space_run.c src/core.c src/space_trace.c
SPACE_SRCS := src/space_main.c $(RUN_SRCS) $(EMULATOR_SRCS)
SPACE_OBJS := $(addprefix $(OBJDIR)/,$(SPACE_SRCS:.c=.o))
SPACE_DEPS := $(SPACE_OBJS:.o=.d)

ASM_SRCS := src/assembler.c src/bitcopy.c
ASM_OBJS := $(addprefix $(OBJDIR)/,$(ASM_SRCS:.c=.o))
ASM_DEPS := $(ASM_OBJS:.o=.d)

PROOF_SRCS := tests/space_image_proof.c $(RUN_SRCS) $(EMULATOR_SRCS)
PROOF_OBJS := $(addprefix $(OBJDIR)/,$(PROOF_SRCS:.c=.o))
PROOF_DEPS := $(PROOF_OBJS:.o=.d)

BIN := $(BINDIR)/space $(BINDIR)/assembler
PROOF_BIN := $(BINDIR)/space_image_proof
BITCOPY_BIN := $(BINDIR)/test_bitcopy
BITCOPY_OBJ := $(OBJDIR)/tests/test_bitcopy.o
RUNTIME_BIN := $(BINDIR)/test_space_runtime
RUNTIME_OBJ := $(OBJDIR)/tests/test_space_runtime.o
IO_PARTIAL_BIN := $(BINDIR)/test_rv32i_io_partial
IO_PARTIAL_OBJ := $(OBJDIR)/tests/test_rv32i_io_partial.o

.PHONY: all bins bins-large clean test test-clean tdd test-sanitize test-rv32i-c pforth pforth-job test-pforth test-file-job copy-c copy-c-job test-copy-c

all: bins

bins: $(BIN)

bins-large: $(BINDIR)/space-64m

$(BINDIR)/space-64m: $(SPACE_SRCS) src/space.h src/core.h src/support.h src/space_run.h src/space_trace.h
	@mkdir -p "$(dir $@)"
	$(CC) $(CPPFLAGS) $(CFLAGS) $(INCLUDES) -UVM_SPACE_BYTES -DVM_SPACE_BYTES=67108864 $(SPACE_SRCS) $(LDFLAGS) -o "$@" $(LDLIBS)

$(OBJDIR)/%.o: %.c
	@mkdir -p "$(dir $@)"
	$(CC) $(CPPFLAGS) $(CFLAGS) $(INCLUDES) -MMD -MP -c "$<" -o "$@"

$(BINDIR)/space: $(SPACE_OBJS)
	@mkdir -p "$(dir $@)"
	$(CC) $(LDFLAGS) -o "$@" $^ $(LDLIBS)

$(BINDIR)/assembler: $(ASM_OBJS)
	@mkdir -p "$(dir $@)"
	$(CC) $(LDFLAGS) -o "$@" $^ $(LDLIBS)

$(BINDIR)/space_image_proof: $(PROOF_OBJS)
	@mkdir -p "$(dir $@)"
	$(CC) $(LDFLAGS) -o "$@" $^ $(LDLIBS)

$(BITCOPY_BIN): $(BITCOPY_OBJ) $(OBJDIR)/src/bitcopy.o
	@mkdir -p "$(dir $@)"
	$(CC) $(LDFLAGS) -o "$@" $^ $(LDLIBS)

$(RUNTIME_BIN): $(RUNTIME_OBJ) $(OBJDIR)/src/space_run.o $(EMULATOR_OBJS)
	@mkdir -p "$(dir $@)"
	$(CC) $(LDFLAGS) -o "$@" $^ $(LDLIBS)

$(IO_PARTIAL_BIN): $(IO_PARTIAL_OBJ) $(addprefix $(OBJDIR)/,$(RUN_SRCS:.c=.o)) $(EMULATOR_OBJS)
	@mkdir -p "$(dir $@)"
	$(CC) $(LDFLAGS) -o "$@" $^ $(LDLIBS)

test: bins bins-large $(PROOF_BIN) $(BITCOPY_BIN) $(RUNTIME_BIN) $(IO_PARTIAL_BIN) test-clean
	./scripts/tdd/run_all.sh

tdd: test

test-rv32i-c: bins bins-large $(PROOF_BIN) $(IO_PARTIAL_BIN)
	python3 tests/test_rv32i_c.py
	python3 tests/test_rv32i_io_c.py
	python3 tests/test_rv32i_stream.py
	python3 tests/test_rv32i_memory.py --c
	python3 tests/test_rv32i_layout.py --c

pforth: bins
	python3 scripts/pforth/build.py -o build/pforth/pforth.stream

TASK ?= examples/pforth/demo.fth
JOB ?= build/pforth/job.in
pforth-job: bins
	python3 scripts/pforth/build.py --task "$(TASK)" -o "$(JOB)"

test-file-job: bins
	python3 tests/test_file_job.py

test-pforth: bins
	python3 tests/test_pforth.py

copy-c: bins bins-large
	python3 scripts/copy_c/build.py -o build/copy-c/compiler.stream

COPY_C_SOURCE ?= examples/copy_c/sum.c
COPY_C_JOB ?= build/copy-c/job.in
copy-c-job: copy-c
	python3 scripts/copy_c/job.py "$(COPY_C_SOURCE)" -o "$(COPY_C_JOB)"

test-copy-c: copy-c
	python3 tests/test_copy_c_bitpack.py
	python3 tests/test_copy_c.py

test-sanitize:
	@mkdir -p "$(BINDIR)"
	$(CC) $(CPPFLAGS) -O1 -g -std=c99 -Wall -Wextra -fsanitize=address,undefined -fno-omit-frame-pointer $(INCLUDES) tests/test_bitcopy.c src/bitcopy.c -o "$(BINDIR)/test_bitcopy_sanitize"
	ASAN_OPTIONS=detect_leaks=0 "$(BINDIR)/test_bitcopy_sanitize"
	$(CC) $(CPPFLAGS) -O1 -g -std=c99 -Wall -Wextra -fsanitize=address,undefined -fno-omit-frame-pointer $(INCLUDES) tests/test_space_runtime.c src/space_run.c src/space.c src/bitcopy.c -o "$(BINDIR)/test_space_runtime_sanitize"
	ASAN_OPTIONS=detect_leaks=0 "$(BINDIR)/test_space_runtime_sanitize"
	$(CC) $(CPPFLAGS) -O1 -g -std=c99 -Wall -Wextra -fsanitize=address,undefined -fno-omit-frame-pointer $(INCLUDES) src/assembler.c src/bitcopy.c -o "$(BINDIR)/assembler_sanitize"
	ASAN_OPTIONS=detect_leaks=0 python3 tests/test_assembler.py --assembler "$(BINDIR)/assembler_sanitize"

clean:
	python3 scripts/clean.py

test-clean:
	python3 tests/test_clean.py

-include $(SPACE_DEPS) $(ASM_DEPS) $(PROOF_DEPS) $(BITCOPY_OBJ:.o=.d) $(RUNTIME_OBJ:.o=.d) $(IO_PARTIAL_OBJ:.o=.d)
