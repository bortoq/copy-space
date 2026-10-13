#ifndef COPY_C_PREPROCESS_PHASE2_H
#define COPY_C_PREPROCESS_PHASE2_H
#include "input_files.h"
/* Translation before token recognition. Compiled into the compiler guest,
 * never into the host space emulator. The result fits in the input buffer. */
static unsigned cc_preprocess_phase2_text(unsigned char *source, unsigned length)
{
    unsigned read_at = 0, write_at = 0;
    while (read_at < length) {
        unsigned char byte = source[read_at];
        if (byte == '\\') {
            unsigned next = read_at+1;
            while (next < length && (source[next] == ' ' || source[next] == '\t'
                   || source[next] == '\v' || source[next] == '\f'))
                ++next;
            if (next < length && (source[next] == '\n' || source[next] == '\r')) {
                read_at = next+1;
                if (source[next] == '\r' && read_at < length && source[read_at] == '\n')
                    ++read_at;
                continue;
            }
        }
        ++read_at;
        if (byte == '\r') {
            byte = '\n';
            if (read_at < length && source[read_at] == '\n')
                ++read_at;
        }
        source[write_at++] = byte;
    }
    return write_at;
}
static unsigned cc_preprocess_phase2(unsigned char *source, unsigned length)
{
    return cc_files_magic(source,length) ? length : cc_preprocess_phase2_text(source,length);
}
#endif
