/* vmrep_attach.h — attach vmrep instrumentation to VM hooks
 *
 * This keeps VM core decoupled from vmrep: the core only calls vm->hooks.*
 * Host tools may attach vmrep explicitly when metrics are desired.
 */
#ifndef COPYSPACE_VMREP_ATTACH_H_
#define COPYSPACE_VMREP_ATTACH_H_

#include "space.h"

void vmrep_attach(vm_t *vm);

#endif
