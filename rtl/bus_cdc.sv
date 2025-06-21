import cpu_reg_package::*;
module bus_cdc #(
    parameter bus_cdc_start_address = 0,
    parameter bus_cdc_end_address   = 0
)(
    input logic       cdc_clks_i [num_entries],
    bus_rv32.from_cpu cpubus_i,
    bus_rv32.from_cpu cpubus_o   [num_entries]
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

    logic [num_entries-1:0] cpu_halt_int;

    always_comb begin
        for (int i = start_num_entry_index; i <= end_num_entry_index; i++) begin
            if (cpu_halt_int[i] == 1'b1) begin
                cpubus_i.cpu_halt_i = 1'b1;
                break;
            end else begin
                cpubus_i.cpu_halt_i = 1'b0;
            end
        end
    end

    data_reg_inputs_t module_data;

    genvar i;
    generate
        for (i = start_num_entry_index; i <= end_num_entry_index; i++) begin : bus_cdc_inst_gen
            bus_cdc_single #(
                .bus_cdc_start_address (get_address_start(i)),
                .bus_cdc_end_address   (get_address_end(i)),
                .EntriesIndex          (i)
            ) bus_cdc_inst (
                .clk_dst_i             (cdc_clks_i[i]),
                .cpubus_i              (cpubus_i),
                .cpubus_o              (cpubus_o[i]),
                .cpu_halt_o            (cpu_halt_int[i]),
                .module_data_o         (module_data)
            );

            assign cpubus_i.data_i[i] = module_data[i];
        end
    endgenerate


endmodule