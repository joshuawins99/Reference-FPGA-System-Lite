import cpu_reg_package::*;

interface bus_rv32;
    logic                     clk_i;
    logic                     reset_i;
    logic [address_width-1:0] address_o;
    data_reg_inputs_t         data_i;
    logic                     we_o;
    logic [data_width-1:0]    data_o;
    logic                     irq_i;
    logic                     cpu_reset_o;
    logic [data_width-1:0]    external_data_i;
    logic [data_width-1:0]    external_data_o;
    logic                     uart_tx_o;
    logic                     uart_rx_i;

    modport to_cpu (
        input  clk_i,
        input  reset_i,
        output address_o,
        input  data_i,
        output we_o,
        output data_o,
        input  irq_i,
        output cpu_reset_o,
        input  external_data_i,
        output external_data_o,
        output uart_tx_o,
        input  uart_rx_i
    );

    modport from_top (
        output clk_i,
        output reset_i,
        input  address_o,
        output data_i,
        input  we_o,
        input  data_o,
        output irq_i,
        input  cpu_reset_o,
        output external_data_i,
        input  external_data_o,
        input  uart_tx_o,
        output uart_rx_i
    );
endinterface