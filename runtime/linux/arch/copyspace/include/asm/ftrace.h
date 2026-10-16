/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef _ASM_COPYSPACE_FTRACE_H
#define _ASM_COPYSPACE_FTRACE_H

#if defined(CONFIG_FUNCTION_TRACER) || defined(CONFIG_FUNCTION_GRAPH_TRACER) || defined(CONFIG_DYNAMIC_FTRACE)
#error "copyspace function tracing is not implemented"
#endif
#include <asm-generic/ftrace.h>

#endif /* _ASM_COPYSPACE_FTRACE_H */
