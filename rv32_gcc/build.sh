#!/bin/bash

CUSTOM_C_FOLDER="../C_Code"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --c-folder)
            CUSTOM_C_FOLDER="$2"
            shift 2
            ;;
        *)
            echo "Unknown option in build.sh: $1"
            exit 1
            ;;
    esac
done

echo "Using C source folder: $CUSTOM_C_FOLDER"

cp "$CUSTOM_C_FOLDER"/* .

riscv32-unknown-elf-gcc -std=c99 -mabi=ilp32 -march=rv32i -nostartfiles -Os -static \
-specs=nano.specs -Wl,-Tsections.lds -Wl,-Map=output.map -o a.elf start.s main.c

riscv32-unknown-elf-objcopy -O binary a.elf a.out

python3 convert_bin_init.py -RV32

mv mem_init.mem ../
