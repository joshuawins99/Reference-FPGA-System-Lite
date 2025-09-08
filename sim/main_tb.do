quit -sim
vlib work

#vlog -work work -incr -sv ../cpu_reg_package.sv

vdel -lib work -all

vlog -work work -incr -sv cpu_sim/cpu_sim_package.sv

#set raw_files [exec bash ../scripts/convert_filelist.sh ../cpu_system_filelist.txt]
#set filelist [join [split $raw_files " "] "\n"]
#vlog +define+SIM -work work -incr -sv $filelist

vlog +define+SIM -work work -incr -sv cpu_sim/cpu_sim_fpga_sys_lite.sv

vlog -work work -incr -sv main_tb.sv

vsim -t 100ps -voptargs=+acc work.main_tb
do wave.do
run -all
