# CDC Module
A clock domain crossing bridge has been added in order to facilitate the use of modules on different clock domains. An example of using this can be seen below.
```Verilog
import cpu_test_package::*;
module cpu_with_cdc_test (
    input logic clk_i,
    input logic reset_i,
    input logic uart_rx_i,
    output logic uart_tx_o
);

    //Some PLL for clk_30 here

    logic cdc_clocks [num_entries];

    assign cdc_clocks[user_module_1_e] = clk_30; //One clock

    localparam bypass_config_t bypass_config = {
        //add_cdc_entry(enum, cdc bypass, busy enable)
        add_cdc_entry(user_module_1_e,  0, 0),
        add_cdc_entry(user_module_2_e,  1, 1)
    };

    //For modules with the cdc bypass option checked, the main system clock will be automatically assigned

    localparam logic [num_entries-1:0] cdc_bypass_mask = build_bypass_mask(bypass_config);
    localparam logic [num_entries-1:0] module_busy_en_mask = build_busy_mask(bypass_config);

    cpu_test_bus_rv32 cdc_cpubus [num_entries]();

    cpu_test_cdc_top #(
        .cdc_bypass_mask     (cdc_bypass_mask),
        .module_busy_en_mask (module_busy_en_mask)
    ) m1 (
        .clk_i               (clk_i),
        .reset_i             (reset_i),
        .external_data_i     ('0),
        .external_data_o     (),
        .uart_rx_i           (uart_rx_i),
        .uart_tx_o           (uart_tx_o),
        .irq_i               ('0),
        .external_cpu_halt_i ('0),
        .cdc_clks_i          (cdc_clocks),
        .cdc_cpubus          (cdc_cpubus)
    );

    //In the clk_30 domain
    user_module_1_e #(
        .BaseAddress   (get_address_start(user_module_1_e)),
        .address_width (address_width),
        .data_width    (data_width)
    ) test_mod_1 (
        .clk_i         (cdc_cpubus[user_module_1_e].clk_i),
        .reset_i       (cdc_cpubus[user_module_1_e].cpu_reset_o),
        .address_i     (cdc_cpubus[user_module_1_e].address_o),
        .data_i        (cdc_cpubus[user_module_1_e].data_o),
        .data_o        (cdc_cpubus[user_module_1_e].data_i[user_module_1_e]),
        .rd_wr_i       (cdc_cpubus[user_module_1_e].we_o)
    );

    //In the clk_i domain
    user_module_2_e #(
        .BaseAddress   (get_address_start(user_module_2_e)),
        .address_width (address_width),
        .data_width    (data_width)
    ) test_mod_2 (
        .clk_i         (cdc_cpubus[user_module_2_e].clk_i),
        .reset_i       (cdc_cpubus[user_module_2_e].cpu_reset_o),
        .address_i     (cdc_cpubus[user_module_2_e].address_o),
        .data_i        (cdc_cpubus[user_module_2_e].data_o),
        .data_o        (cdc_cpubus[user_module_2_e].data_i[user_module_2_e]),
        .rd_wr_i       (cdc_cpubus[user_module_2_e].we_o),
        .busy_o        (cdc_cpubus[user_module_2_e].module_busy_i)
    );

endmodule
```
Modules have the option to either have their data available one clock cycle later as normal, or by setting a 1 in the bypass_config mask, have a busy signal to have the cdc module wait until valid data is signaled from the downstream module. These modules follow exactly the same behavior as ones that would in the same clock domain. The cdc_top module will actively halt the cpu automatically to wait for the read data from the downstream modules to be valid. 

## Configuring bypass_config_t
With the bypass_config_t type, a localparam is made to define the modules and if they should use the cdc synchronization or not. Passthrough mode is enabled when cdc bypass is set to 1 for a given module. The default is an entry that is bypassed and doesnt require a busy (1, 0). Modules that fit this type do not require an entry and dont utilize the CDC FIFOs.