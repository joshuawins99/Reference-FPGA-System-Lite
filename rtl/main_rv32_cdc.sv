module main_rv32_cdc
import cpu_reg_package::*;
#(
    parameter logic [num_entries-1:0] cdc_bypass_mask
)(
    input  logic                  clk_i,
    input  logic                  reset_i,
    input  logic [data_width-1:0] external_data_i,
    output logic [data_width-1:0] external_data_o,
    input  logic                  uart_rx_i,
    output logic                  uart_tx_o,
    input  logic                  irq_i,
    input  logic                  external_cpu_halt_i,
    input  logic                  cdc_clks_i [num_entries],
    input  logic                  module_busy_en_i [num_entries],
    bus_rv32.cdc_out              cdc_cpubus [num_entries]
);

    logic cdc_busy;

    bus_rv32 cpubus();

    bus_rv32 cdc_cpubus_internal [num_entries]();

    main_rv32 mrv32_1 (
        .cpubus (cpubus)
    );

    assign cpubus.clk_i = clk_i;
    assign cpubus.reset_i = reset_i;

    assign cpubus.irq_i = irq_i;
    assign cpubus.external_data_i = external_data_i;
    assign external_data_o = cpubus.external_data_o;

    assign uart_tx_o = cpubus.uart_tx_o;
    assign cpubus.uart_rx_i = uart_rx_i;

    assign cpubus.cpu_halt_i = cdc_busy | external_cpu_halt_i;

    genvar i;
    generate
        for (i = 0; i < num_entries; i++) begin : internal_cpubus_mapping_inst
            assign cdc_cpubus[i].clk_i                  = cdc_cpubus_internal[i].clk_i;
            assign cdc_cpubus[i].cpu_reset_o            = cdc_cpubus_internal[i].cpu_reset_o;
            assign cdc_cpubus[i].address_o              = cdc_cpubus_internal[i].address_o;
            assign cdc_cpubus[i].data_o                 = cdc_cpubus_internal[i].data_o;
            assign cdc_cpubus[i].we_o                   = cdc_cpubus_internal[i].we_o;
            assign cdc_cpubus[i].we_ram_o               = cdc_cpubus_internal[i].we_ram_o;
            assign cdc_cpubus_internal[i].module_busy_i = cdc_cpubus[i].module_busy_i;
            assign cdc_cpubus_internal[i].data_i[i]     = cdc_cpubus[i].data_i[i];
        end
    endgenerate

    bus_cdc #(
        .bus_cdc_start_address (get_address_start(0)),
        .bus_cdc_end_address   (get_address_end(num_entries-1)),
        .cdc_bypass_mask       (cdc_bypass_mask)
    ) cdc_1 (
        .cdc_clks_i            (cdc_clks_i),
        .module_busy_en_i      (module_busy_en_i),
        .cpubus_i              (cpubus),
        .cpubus_o              (cdc_cpubus_internal),
        .busy_o                (cdc_busy)
    );

endmodule
