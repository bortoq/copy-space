# config.mk — project configuration (override via environment or make VAR=...).
CC ?= cc

# Build flags (no -Werror by default; project is experimental)
CFLAGS  ?= -std=c11 -O2 -Wall -Wextra
CPPFLAGS?=
LDFLAGS ?=

# Runtime defaults for tests
SPACE_BYTES  ?= 524288
PROCESSOR_N  ?= 64
LIFE_COMPILE ?= 20000000
LIFE_RUN     ?= 20000000

# Two images for the "stable word addresses across pool sizes" check
POOL_SMALL ?= 4096
POOL_BIG   ?= 32768
