#include <stdint.h>
#include "FreeRTOS.h"

void vAssertCalled(const char *file, int line) {
  (void)file;
  (void)line;
  for (;;) {}
}

void freertos_risc_v_application_interrupt_handler(void) {
  for (;;) {}
}

void freertos_risc_v_application_exception_handler(void) {
  for (;;) {}
}

/* no real timer source in this environment */
void vPortSetupTimerInterrupt(void) {}
