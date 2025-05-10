#!/bin/bash
rm -f ref_fpga_sys_lite.sv
cd rv32_gcc
./build.sh
cd ..
cd rtl

echo -n '`define version_string ' > version_string.svh
if [ "$1" = -build ]; then
    if [ "$2" = REL ]; then
        echo -n '"' >> version_string.svh
        echo -n "REL " >> version_string.svh
        git rev-parse --verify HEAD | cut -c1-7 | xargs echo -n >> version_string.svh
    else
        echo -n '"' >> version_string.svh
        echo -n "DEV " >> version_string.svh
        echo -n $2 >> version_string.svh
    fi
else 
    echo -n '"' >> version_string.svh
    echo -n "DEV " >> version_string.svh
    echo -n "1234567" >> version_string.svh
fi

echo -n ' ' >> version_string.svh
date --date 'now' '+%a %b %d %r %Z %Y' | sed -e 's/$/"/' -e 's/,/","/g' >> version_string.svh

cd ..

scripts/concatenate_modules.sh cpu_system_filelist.txt ref_fpga_sys_lite.sv