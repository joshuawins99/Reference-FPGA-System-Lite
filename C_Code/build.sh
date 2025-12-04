#!/bin/bash

riscv32-unknown-elf-gcc -std=gnu99 -mabi=ilp32 -march=rv32i -nostartfiles -Os -static \
-specs=nano.specs -Wl,-Tsections.lds -Wl,-Map=output.map -Wall -Werror -flto -fstack-usage -o a.elf start.s main.c

riscv32-unknown-elf-objcopy -O binary a.elf a.out

python3 convert_bin_init.py -RV32
