    .option norvc
    .option norelax
    .section .text.start
    .global _start
_start:
    call rv_example
    ecall
1:
    j 1b
