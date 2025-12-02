MEMORY
{
  RAM (rwx) : ORIGIN = 0x0, LENGTH = 0x2000 /* Total 8KB */
}

SECTIONS
{
  /* Code section */
  .text : {
    . = 0x0; /* Start program at 0x0 */
    *(.text.startup) /* Place startup routines */
    *(.text)
    *(.rodata*)
    . = ALIGN(4); /* Ensure alignment */
  } > RAM

  /* Track the end of .text */
  _text_end = ALIGN(4); /* Align end of .text */

  /* Initialized data section */
  .data : {
    _data_start = .; /* Start of .data in RAM */
    *(.data)
    . = ALIGN(4); /* Ensure alignment */
    _data_end = .; /* End of .data in RAM */
  } > RAM

  /* Small data section (e.g., _impure_ptr) */
  .sdata : {
    _sdata_start = ALIGN(4); /* Start of .sdata */
    *(.sdata)
    *(.sdata.*)
    *(.gnu.linkonce.s.*)
    . = ALIGN(4); /* Ensure alignment */
    _sdata_end = .; /* End of .sdata */
  } > RAM

  /* Uninitialized data section */
  .bss : {
    _bss_start = ALIGN(4); /* Start of .bss in RAM */
    *(.bss)
    *(COMMON)
    . = ALIGN(4); /* Ensure alignment */
    _bss_end = .; /* End of .bss in RAM */
  } > RAM

  /* Place stack at the top of RAM */
  .stack (NOLOAD) : {
    . = ALIGN(4);
    __stack_end = .; /* Bottom of stack */
    . = . + 0x400;   /* Reserve 256 bytes for stack */
    __stack_top = .; /* Top of stack */
  } > RAM
   _end = .;
}
