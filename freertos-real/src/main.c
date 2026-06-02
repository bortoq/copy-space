#include <stdint.h>
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"
#include "timers.h"

static QueueHandle_t q;
static volatile uint32_t g_tx = 0;
static volatile uint32_t g_rx = 0;
static volatile uint32_t g_ticks = 0;

static void producer_task(void *arg) {
  (void)arg;
  uint32_t v = 1;
  for (;;) {
    xQueueSend(q, &v, portMAX_DELAY);
    g_tx = v;
    v++;
    vTaskDelay(pdMS_TO_TICKS(10));
  }
}

static void consumer_task(void *arg) {
  (void)arg;
  uint32_t v;
  for (;;) {
    if (xQueueReceive(q, &v, portMAX_DELAY) == pdPASS) {
      g_rx = v;
    }
    taskYIELD();
  }
}

static void timer_cb(TimerHandle_t t) {
  (void)t;
  g_ticks++;
}

void vApplicationTickHook(void) {}
void vApplicationIdleHook(void) {}
void vApplicationStackOverflowHook(TaskHandle_t xTask, char *pcTaskName) {
  (void)xTask;
  (void)pcTaskName;
  for (;;) {}
}
void vApplicationMallocFailedHook(void) {
  for (;;) {}
}

int main(void) {
  q = xQueueCreate(8, sizeof(uint32_t));
  configASSERT(q != NULL);

  TimerHandle_t tm = xTimerCreate("tm", pdMS_TO_TICKS(50), pdTRUE, NULL, timer_cb);
  configASSERT(tm != NULL);
  configASSERT(xTimerStart(tm, 0) == pdPASS);

  configASSERT(xTaskCreate(producer_task, "prod", 512, NULL, tskIDLE_PRIORITY + 2, NULL) == pdPASS);
  configASSERT(xTaskCreate(consumer_task, "cons", 512, NULL, tskIDLE_PRIORITY + 1, NULL) == pdPASS);

  vTaskStartScheduler();
  for (;;) {}
}
