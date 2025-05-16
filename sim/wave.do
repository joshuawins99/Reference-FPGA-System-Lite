onerror {resume}
quietly WaveActivateNextPane {} 0
add wave -noupdate /main_tb/clk
add wave -noupdate /main_tb/uart_testbench_1/reset_i
add wave -noupdate /main_tb/uart_testbench_1/uart_txd_o
add wave -noupdate /main_tb/uart_testbench_1/uart_rxd_i
add wave -noupdate /main_tb/uart_testbench_1/data_valid_i
add wave -noupdate /main_tb/uart_testbench_1/data_in_ready_o
add wave -noupdate /main_tb/uart_testbench_1/data_o
add wave -noupdate /main_tb/uart_testbench_1/data_valid_o
add wave -noupdate -radix hexadecimal /main_tb/m1/address
add wave -noupdate /main_tb/m1/uart_rv32_1/take_controlr_o
add wave -noupdate -radix decimal /main_tb/m1/uart_rv32_1/data_o_reg
add wave -noupdate /main_tb/m1/uart_rv32_1/fifo_data_out
add wave -noupdate /main_tb/m1/uart_rv32_1/fifo_read
add wave -noupdate -radix ascii /main_tb/m1/uart_rv32_1/rx_out
add wave -noupdate /main_tb/m1/uart_rv32_1/rx_done
add wave -noupdate /main_tb/m1/uart_rv32_1/fifo_empty
add wave -noupdate /main_tb/m1/uart_rv32_1/async_fifo_uart_6502_1/fifomem/mem
add wave -noupdate /main_tb/m1/uart_rv32_1/async_fifo_uart_6502_1/wfull
add wave -noupdate -radix unsigned /main_tb/ex_data_o
add wave -noupdate -radix unsigned /main_tb/m1/external_data_o
add wave -noupdate /main_tb/m1/io_rv32_1/take_controlw_o
add wave -noupdate /main_tb/address
add wave -noupdate /main_tb/we_o
TreeUpdate [SetDefaultTree]
WaveRestoreCursors {{Cursor 1} {1325588000 ps} 0}
quietly wave cursor active 1
configure wave -namecolwidth 316
configure wave -valuecolwidth 100
configure wave -justifyvalue left
configure wave -signalnamewidth 0
configure wave -snapdistance 10
configure wave -datasetprefix 0
configure wave -rowmargin 4
configure wave -childrowmargin 2
configure wave -gridoffset 0
configure wave -gridperiod 1
configure wave -griddelta 40
configure wave -timeline 0
configure wave -timelineunits ps
update
WaveRestoreZoom {0 ps} {13421772800 ps}
