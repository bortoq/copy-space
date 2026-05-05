/* file: src/mkimage/std7_fixed/report.h
 * date: 2026-05-04
 * purpose: unified mkimage summary/meta printing (stderr)
 */
#ifndef STD7_FIXED_REPORT_H_
#define STD7_FIXED_REPORT_H_

#include <stdio.h>
#include "space.h"
#include "layout.h"
#include "addrs.h"

void std7_fixed_print_summary(FILE *err,
                              const char *out_path,
                              const std7_layout_t *L,
                              bitaddr_t art_base,
                              const std7_addrs_t *A);

#endif