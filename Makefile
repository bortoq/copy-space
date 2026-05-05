# file: Makefile
# date: 2026-05-05
#
# Build: Copy-Space VM tools + std7_fixed mkimage + token tests (auto-discovery).
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

# token tests: auto-discover
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

# token test binaries
TOK_BINS := $(patsubst src/tokens/%.c,$(BINDIR)/%,$(TOK_SRCS))

BINS := $(TOOLS_BINS) $(MKIMAGE) $(TOK_BINS)

# -------------------- rules --------------------

.PHONY: all bins clean test tdd list-tok list-tools

all: bins

bins: $(BINS)

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
