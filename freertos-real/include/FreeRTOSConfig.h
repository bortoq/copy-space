#ifndef FREERTOS_CONFIG_H
#define FREERTOS_CONFIG_H

#define configUSE_PREEMPTION                    1
#define configUSE_PORT_OPTIMISED_TASK_SELECTION 1
#define configUSE_IDLE_HOOK                     0
#define configUSE_TICK_HOOK                     0
#define configCPU_CLOCK_HZ                      1000000UL
#define configTICK_RATE_HZ                      1000
#define configMAX_PRIORITIES                    8
#define configMINIMAL_STACK_SIZE                256
#define configTOTAL_HEAP_SIZE                   (32 * 1024)
#define configMAX_TASK_NAME_LEN                 16
#define configUSE_16_BIT_TICKS                  0
#define configIDLE_SHOULD_YIELD                 1
#define configUSE_MUTEXES                       1
#define configQUEUE_REGISTRY_SIZE               8
#define configCHECK_FOR_STACK_OVERFLOW          2
#define configUSE_RECURSIVE_MUTEXES             1
#define configUSE_MALLOC_FAILED_HOOK            1
#define configUSE_APPLICATION_TASK_TAG          0
#define configUSE_COUNTING_SEMAPHORES           1
#define configGENERATE_RUN_TIME_STATS           0

#define configSUPPORT_DYNAMIC_ALLOCATION        1
#define configSUPPORT_STATIC_ALLOCATION         0


#define configENABLE_MPU                       1
#define configUSE_MPU_WRAPPERS_V1              0
#define configSYSTEM_CALL_STACK_SIZE           256
#define configENABLE_ACCESS_CONTROL_LIST       1
#define configPROTECTED_KERNEL_OBJECT_POOL_SIZE 256
#define configUSE_TIMERS                        1
#define configTIMER_TASK_PRIORITY               (configMAX_PRIORITIES - 1)
#define configTIMER_QUEUE_LENGTH                8
#define configTIMER_TASK_STACK_DEPTH            (configMINIMAL_STACK_SIZE * 2)

#define configUSE_TASK_NOTIFICATIONS            1
#define configTASK_NOTIFICATION_ARRAY_ENTRIES   1

#define INCLUDE_vTaskDelay                      1
#define INCLUDE_vTaskDelayUntil                 1
#define INCLUDE_vTaskDelete                     1
#define INCLUDE_vTaskSuspend                    1
#define INCLUDE_xTaskGetCurrentTaskHandle       1
#define INCLUDE_xTaskGetSchedulerState          1

/* Required by this RISC-V port; set to zero for no real CLINT/mtime. */
#define configCLINT_BASE_ADDRESS                0x0
#define configMTIME_BASE_ADDRESS                0x0
#define configMTIMECMP_BASE_ADDRESS             0x0

#endif
