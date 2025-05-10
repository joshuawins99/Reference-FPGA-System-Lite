import cpu_reg_package::*;
module main_ecp5 (
    input  logic       clk_i,
    input  logic       reset_i,
    output logic [7:0] ex_data_o,
    input  logic       uart_rx_i,
    output logic       uart_tx_o
);

    bus_rv32 cpubus();

    assign cpubus.clk_i   = clk_i;
    assign cpubus.reset_i = reset_i;

    assign ex_data_o = cpubus.external_data_o[7:0];
    assign cpubus.external_data_i = '0;

    assign uart_tx_o = cpubus.uart_tx_o;
    assign cpubus.uart_rx_i = uart_rx_i;


    main_rv32 #(
        .FPGAClkSpeed        (FPGAClkSpeed)
    ) m1 (
        .cpubus              (cpubus)
    );

endmodule
