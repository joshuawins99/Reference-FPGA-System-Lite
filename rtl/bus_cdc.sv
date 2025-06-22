import cpu_reg_package::*;
module bus_cdc #(
    parameter bus_cdc_start_address = 0,
    parameter bus_cdc_end_address   = 0
)(
    input logic      cdc_clks_i [num_entries],
    bus_rv32.cdc_in  cpubus_i,
    bus_rv32.cdc_out cpubus_o   [num_entries]
);

    //Function to take address and find the "index" from the packed array.
    function integer reverse_index_lookup (
        input [address_width-1:0] address
    );
        integer i;
        logic [address_width-1:0] int_address;
        begin
            for (i = 0; i < num_entries*2; i++) begin
                int_address = get_address_mux(i);
                if (int_address == address) begin
                    reverse_index_lookup = (num_entries-1) - (i >> 1);
                    break;
                end
            end
        end
    endfunction

    localparam start_num_entry_index  = reverse_index_lookup(bus_cdc_start_address);
    localparam end_num_entry_index    = reverse_index_lookup(bus_cdc_end_address);

    logic [num_entries-1:0]   cpu_halt_int;
    data_reg_inputs_t         module_data;
    logic                     cpuside_cpu_reset;
    logic                     cpuside_we;
    logic [address_width-1:0] cpuside_address;
    logic [data_width-1:0]    cpuside_data_o;
    logic                     cpuside_clk;

    assign cpubus_i.cpu_halt_i = |cpu_halt_int[end_num_entry_index:start_num_entry_index];

    assign cpuside_cpu_reset   = cpubus_i.cpu_reset_o;
    assign cpuside_we          = cpubus_i.we_o;
    assign cpuside_address     = cpubus_i.address_o;
    assign cpuside_data_o      = cpubus_i.data_o;
    assign cpuside_clk         = cpubus_i.clk_i;

    genvar i;
    generate
        for (i = start_num_entry_index; i <= end_num_entry_index; i++) begin : bus_cdc_inst_gen  
        bus_cdc_single #(
                .bus_cdc_start_address  (get_address_start(i)),
                .bus_cdc_end_address    (get_address_end(i))
            ) bus_cdc_inst (
                .clk_dst_i              (cdc_clks_i[i]),
                .cpuside_clk_i          (cpuside_clk),
                .cpuside_cpu_reset_i    (cpuside_cpu_reset),
                .cpuside_we_i           (cpuside_we),
                .cpuside_address_i      (cpuside_address),
                .cpuside_data_i         (cpuside_data_o),
                .cpuside_cpu_halt_o     (cpu_halt_int[i]),
                .moduleside_data_i      (cpubus_o[i].data_i[i]),
                .moduleside_address_o   (cpubus_o[i].address_o),
                .moduleside_we_o        (cpubus_o[i].we_o),
                .moduleside_data_o      (cpubus_o[i].data_o),
                .moduleside_cpu_reset_o (cpubus_o[i].cpu_reset_o),
                .cpuside_module_data_o  (module_data[i])
            );

            assign cpubus_i.data_i[i] = module_data[i];
            assign cpubus_o[i].clk_i  = cdc_clks_i[i];
        end
    endgenerate

endmodule