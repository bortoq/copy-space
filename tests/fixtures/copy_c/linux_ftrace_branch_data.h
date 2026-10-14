/* SPDX-License-Identifier: GPL-2.0 */
/* Original declaration from Linux 6.12 include/linux/compiler_types.h. */
struct ftrace_branch_data {
	const char *func;
	const char *file;
	unsigned line;
	union {
		struct {
			unsigned long correct;
			unsigned long incorrect;
		};
		struct {
			unsigned long miss;
			unsigned long hit;
		};
		unsigned long miss_hit[2];
	};
};
