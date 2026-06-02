ENTRY(_start)
MEMORY {
  RAM (rwx) : ORIGIN = 0x00000000, LENGTH = 256K
}

SECTIONS {
  .text : {
    *(.text*)
    *(.rodata*)
  } > RAM

  .data : {
    *(.data*)
  } > RAM

  .bss (NOLOAD) : {
    *(.bss*)
    *(COMMON)
  } > RAM

  . = ALIGN(16);
  _end = .;
  . = ORIGIN(RAM) + LENGTH(RAM) - 0x2000;
  _stack_top = .;
}
