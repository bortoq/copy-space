# file: Makefile
# date: 2026-05-05 (updated 2026-05-07)
#
# Build: Copy-Space VM tools + std7_fixed mkimage + (optional) legacy C token tests.
# Binaries are emitted only into build/bin (no root-level binaries).

SHELL := /bin/sh

-include config.mk

CC ?= cc
CFLAGS ?= -O2 -g -std=c99 -Wall -Wextra
CPPFLAGS ?=
LDFLAGS ?=
LDLIBS ?=

OBJDIR := build/obj
BINDIR := build/bin

INCLUDES := -Isrc -Isrc/vm

# Build legacy C token-tests? (default: no)
# Enable via: make tok   OR   make TOK=1 bins
TOK ?= 0

# -------------------- sources --------------------

VM_SRCS := \
  src/vm/space.c \
  src/vm/bitcpy.c

# optional vmrep module
VMREP_SRC := $(wildcard src/vm/diag/vmrep.c)
ifneq ($(VMREP_SRC),)
VM_SRCS += $(VMREP_SRC)
endif

# tools: build every src/tools/*.c into build/bin/<basename>
TOOLS_SRCS := $(sort $(wildcard src/tools/*.c))

# mkimage std7_fixed
ifneq ("$(wildcard src/mkimage/std7_fixed/legacy.c)","")
MKIMAGE_SRCS := src/mkimage/mkimage_std7_fixed.c $(sort $(wildcard src/mkimage/std7_fixed/*.c))
else
MKIMAGE_SRCS := src/mkimage/mkimage_std7_fixed.c
endif

# token tests: auto-discover (legacy; optional build)
TOK_SRCS := $(sort $(wildcard src/tokens/mktok_test_*.c))

# -------------------- objects --------------------

VM_OBJS      := $(addprefix $(OBJDIR)/,$(VM_SRCS:.c=.o))
TOOLS_OBJS   := $(addprefix $(OBJDIR)/,$(TOOLS_SRCS:.c=.o))
MKIMAGE_OBJS := $(addprefix $(OBJDIR)/,$(MKIMAGE_SRCS:.c=.o))
TOK_OBJS     := $(addprefix $(OBJDIR)/,$(TOK_SRCS:.c=.o))

ALL_OBJS := $(VM_OBJS) $(TOOLS_OBJS) $(MKIMAGE_OBJS) $(TOK_OBJS)
DEPS := $(ALL_OBJS:.o=.d)

# -------------------- binaries --------------------

# tools binaries
TOOLS_BINS := $(patsubst src/tools/%.c,$(BINDIR)/%,$(TOOLS_SRCS))

# mkimage binary (fixed name)
MKIMAGE := $(BINDIR)/mkimage_std7_fixed

# token test binaries (legacy; optional)
TOK_BINS := $(patsubst src/tokens/%.c,$(BINDIR)/%,$(TOK_SRCS))

BINS_BASE := $(TOOLS_BINS) $(MKIMAGE)
BINS := $(BINS_BASE) $(if $(filter 1,$(TOK)),$(TOK_BINS),)

# -------------------- rules --------------------

.PHONY: all bins tok clean test tdd list-tok list-tools

all: bins

bins: $(BINS)

# Build legacy token-tests explicitly (even if TOK=0)
tok: $(TOK_BINS)

list-tok:
	@printf "%s\n" $(TOK_SRCS)

list-tools:
	@printf "%s\n" $(TOOLS_SRCS)

$(OBJDIR)/%.o: %.c
	@mkdir -p "$(dir $@)"
	$(CC) $(CPPFLAGS) $(CFLAGS) $(INCLUDES) -MMD -MP -c "$<" -o "$@"

# link tools: build/bin/<name> from build/obj/src/tools/<name>.o + vm objs
$(TOOLS_BINS): $(BINDIR)/%: $(OBJDIR)/src/tools/%.o $(VM_OBJS)
	@mkdir -p "$(dir $@)"
	$(CC) $(LDFLAGS) -o "$@" $^ $(LDLIBS)

# link token tests: build/bin/<name> from build/obj/src/tokens/<name>.o + vm objs
$(TOK_BINS): $(BINDIR)/%: $(OBJDIR)/src/tokens/%.o $(VM_OBJS)
	@mkdir -p "$(dir $@)"
	$(CC) $(LDFLAGS) -o "$@" $^ $(LDLIBS)

# mkimage
$(MKIMAGE): $(MKIMAGE_OBJS) $(VM_OBJS)
	@mkdir -p "$(dir $@)"
	$(CC) $(LDFLAGS) -o "$@" $^ $(LDLIBS)

test: bins
	./scripts/test_all.sh

tdd: bins
	./scripts/tdd/run_all.sh

clean:
	rm -rf build tmp out

-include $(DEPS)

.PHONY: sched-demo sched-test sched-bench sched-pilot

sched-demo:
	python3 scripts/scheduler/demo_run.py

sched-test:
	./scripts/test_scheduler.sh

sched-bench:
	python3 scripts/scheduler/gen_ref_pack.py >/dev/null
	python3 scripts/scheduler/bench_v0.py | tail -n 40

# expects: examples/demands.csv (or pass your own via scripts/scheduler/pilot_run.sh)
sched-pilot:
	./scripts/scheduler/pilot_run.sh --csv examples/demands.csv --bw 256 --outdir tmp/pilot
