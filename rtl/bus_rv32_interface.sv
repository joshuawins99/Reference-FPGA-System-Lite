interface bus_rv32;
import cpu_reg_package::*;

    logic                     clk_i;
    logic                     reset_i;
    logic [address_width-1:0] address_o;
    data_reg_inputs_t         data_i;
    logic                     we_o;
    logic [3:0]               we_ram_o;
    logic [data_width-1:0]    data_o;
    logic                     irq_i;
    logic                     cpu_reset_o;
    logic                     cpu_halt_i;
    logic [data_width-1:0]    external_data_i;
    logic [data_width-1:0]    external_data_o;
    logic                     uart_tx_o;
    logic                     uart_rx_i;
    logic                     uart_rts_o;
    logic                     module_busy_i;

    modport to_cpu (
        input  clk_i,
        input  reset_i,
        input  address_o,
        output data_i,
        input  we_o,
        input  we_ram_o,
        input  data_o,
        output irq_i,
        input  cpu_reset_o,
        output cpu_halt_i,
        output external_data_i,
        input  external_data_o,
        input  uart_tx_o,
        output uart_rx_i,
        input  uart_rts_o
    );

    modport from_cpu (
        input  clk_i,
        input  reset_i,
        output address_o,
        input  data_i,
        output we_o,
        output we_ram_o,
        output data_o,
        input  irq_i,
        output cpu_reset_o,
        input  cpu_halt_i,
        input  external_data_i,
        output external_data_o,
        output uart_tx_o,
        input  uart_rx_i,
        output uart_rts_o
    );

    modport cdc_in (
        input  clk_i,
        input  address_o,
        output data_i,
        input  we_o,
        input  we_ram_o,
        input  data_o,
        input  cpu_reset_o
    );

    modport cdc_out (
        output clk_i,
        output address_o,
        input  data_i,
        output we_o,
        output we_ram_o,
        output data_o,
        output cpu_reset_o,
        input  module_busy_i
    );
    
endinterface