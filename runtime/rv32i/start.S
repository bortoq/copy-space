    .option norvc
    .option norelax
    .section .text.start
    .global _start
_start:
    call main
    call cs_exit
1:
    j 1b
