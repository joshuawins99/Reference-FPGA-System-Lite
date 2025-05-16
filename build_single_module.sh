#!/bin/bash

MODELSIM_ROOT_DIR=/root/intelFPGA/20.1/modelsim_ase/bin/

rm -f ref_fpga_sys_lite.sv
rm -f *.tar.gz
rm -f sim_result.txt

cd rv32_gcc
./build.sh
cd ..
cd rtl

echo -n '`define version_string ' > version_string.svh
if [ "$1" = -build ]; then
    if [ "$2" = REL ]; then
        echo -n '"' >> version_string.svh
        echo -n "REL " >> version_string.svh
        cat ../version >> version_string.svh
    else
        echo -n '"' >> version_string.svh
        echo -n "DEV " >> version_string.svh
        echo -n $2 >> version_string.svh
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

if [ "$1" = -build ]; then
    if [ "$2" = REL ]; then
        cd sim
        $MODELSIM_ROOT_DIR/vsim -c -do main_tb.do >> ../sim_result.txt
        cd ..

        search_string="Testbench Passed!"
        file="sim_result.txt"

        if grep -q "$search_string" "$file"; then
            echo "Testbench Passed!"
            tar -czf v$(cat version).tar.gz ref_fpga_sys_lite.sv cpu_reg_package.sv
        else
            echo "Testbench Failed!"
        fi
    fi
fi