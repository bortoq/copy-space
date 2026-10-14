    .option norvc
    .option norelax
    .section .text.start
    .global _start
_start:
    call __libc_init_array
    la a0, __libc_fini_array
    call atexit
    bnez a0, 1f
    call main
    call exit
1:
    li a0, 125
    call cs_exit
2:
    j 2b
