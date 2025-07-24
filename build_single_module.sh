#!/bin/bash

MODELSIM_ROOT_DIR=/root/QuestaSim/questasim/linux_x86_64
CUSTOM_C_FOLDER="C_Code"
BUILD_MODE=""
VERSION_TYPE=""

resolve_path() {
    local INPUT_PATH="$1"
    INPUT_PATH="${INPUT_PATH%/}"
    if [ -d "$INPUT_PATH" ]; then
        (cd "$INPUT_PATH" && pwd)
    else
        echo "Error: directory does not exist: $INPUT_PATH" >&2
        exit 1
    fi
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -build)
            BUILD_MODE=true
            VERSION_TYPE="$2"
            shift 2
            ;;
        --c-folder)
            CUSTOM_C_FOLDER="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

CUSTOM_C_FOLDER="$(resolve_path "$CUSTOM_C_FOLDER")"

rm -f ref_fpga_sys_lite.sv *.tar.gz sim_result.txt

cd rv32_gcc
./build.sh --c-folder "$CUSTOM_C_FOLDER"
cd ..

cd rtl
echo -n '`define version_string ' > version_string.svh
if [ "$BUILD_MODE" = true ]; then
    if [ "$VERSION_TYPE" = REL ]; then
        echo -n '"' >> version_string.svh
        echo -n "REL " >> version_string.svh
        cat ../version >> version_string.svh
    else
        echo -n '"' >> version_string.svh
        echo -n "DEV " >> version_string.svh
        echo -n "$VERSION_TYPE" >> version_string.svh
    fi
else 
    echo -n '"' >> version_string.svh
    echo -n "DEV " >> version_string.svh
    git rev-parse --verify HEAD | cut -c1-7 | xargs echo -n >> version_string.svh
fi
echo -n ' ' >> version_string.svh
date --date 'now' '+%a %b %d %r %Z %Y' | sed -e 's/$/"/' -e 's/,/","/g' >> version_string.svh
cd ..

scripts/create_memory_module.py mem_init.mem rtl/picosoc_mem.v
scripts/concatenate_modules.sh cpu_system_filelist.txt ref_fpga_sys_lite.sv

irq_result=$(nm rv32_gcc/a.elf | grep -w irq | awk '{print $1}')

if [ -n "$irq_result" ]; then
    echo "Found IRQ Function at: 0x$irq_result"
    echo "\`define CPUIRQAddress 32'h$irq_result" > irq.sv
else
    echo "No IRQ Function Found"
    echo "\`define CPUIRQAddress 32'h00000000" > irq.sv
fi

cat ref_fpga_sys_lite.sv >> irq.sv
mv irq.sv ref_fpga_sys_lite.sv

if [ "$BUILD_MODE" = true ] && [ "$VERSION_TYPE" = REL ]; then
    cd sim
    ../scripts/generate_cpu_instance.py
    $MODELSIM_ROOT_DIR/vsim -c -do main_tb.do >> ../sim_result.txt
    cd ..

    if grep -q "Testbench Passed!" sim_result.txt; then
        echo "Testbench Passed!"
        scripts/cpu_config/combine_gen_cpu_deps.py
        tar -czf v$(cat version).tar.gz ref_fpga_sys_lite.sv generate_cpu_instance.py
        rm generate_cpu_instance.py
    else
        echo "Testbench Failed!"
    fi
fi