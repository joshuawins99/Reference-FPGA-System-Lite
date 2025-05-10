#!/bin/bash
cd ..

rm -f main.bin
rm -f converted.v
rm -f ref_fpga_sys_lite.sv

./build_single_module.sh

../sv2v ref_fpga_sys_lite.sv cpu_reg_package.sv example/main_ecp5.sv -w converted.v
yosys -q -p "abc_new; read_verilog -sv -nooverwrite converted.v; hierarchy -top main_ecp5; synth_ecp5 -top main_ecp5 -json main.json"
nextpnr-ecp5 --25k --package CABGA256 --speed 6 --json main.json --textcfg main.config --lpf example/pin_config_ecp5.lpf --lpf-allow-unconstrained --randomize-seed
ecppack --compress --bit main.bit main.config
rm -f main.config main.json
mv main.bit main.bin