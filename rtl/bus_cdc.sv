module bus_cdc 
import cpu_reg_package::*;
#(
    parameter                         bus_cdc_start_address = 0,
    parameter                         bus_cdc_end_address   = 0,
    parameter logic [num_entries-1:0] cdc_bypass_mask
)(
    input logic      cdc_clks_i [num_entries],
    input logic      module_busy_en_i [num_entries],
    bus_rv32.cdc_in  cpubus_i,
    bus_rv32.cdc_out cpubus_o   [num_entries],
    output logic     busy_o
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

    typedef struct packed {
        logic                     we;
        logic [3:0]               we_ram;
        logic [address_width-1:0] address;
        logic [data_width-1:0]    data;
    } bus_signals_t;

    localparam start_num_entry_index  = reverse_index_lookup(bus_cdc_start_address);
    localparam end_num_entry_index    = reverse_index_lookup(bus_cdc_end_address);

    logic [num_entries-1:0]   busy_src;
    logic                     cpuside_cpu_reset;
    logic                     cpuside_we;
    logic [address_width-1:0] cpuside_address;
    logic [data_width-1:0]    cpuside_data_o;
    logic                     cpuside_clk;
    logic                     moduleside_cpu_reset [num_entries];
    logic [address_width-1:0] address_reg = '0;
    bus_signals_t             data_cpu_to_module;
    logic [num_entries-1:0]   data_cpu_to_module_valid = '0;
    bus_signals_t             data_cpu_to_module_synced [num_entries];
    logic                     data_cpu_to_module_synced_valid [num_entries];
    bus_signals_t             data_module_to_cpu [num_entries];
    logic [num_entries-1:0]   data_module_to_cpu_valid = '0;
    bus_signals_t             data_module_to_cpu_synced [num_entries];
    logic [num_entries-1:0]   data_module_to_cpu_synced_valid;
    logic [num_entries-1:0]   transaction_pending = '0;
    logic                     module_busy_prev [num_entries];
    logic [num_entries-1:0]   cdc_bypass_busy;

    assign cpuside_cpu_reset   = cpubus_i.cpu_reset_o;
    assign cpuside_clk         = cpubus_i.clk_i;

    assign data_cpu_to_module = '{
        we:      cpubus_i.we_o, 
        we_ram:  cpubus_i.we_ram_o,
        address: cpubus_i.address_o, 
        data:    cpubus_i.data_o
    };

    assign busy_o = |(transaction_pending[end_num_entry_index:start_num_entry_index]) | 
                    |(busy_src[end_num_entry_index:start_num_entry_index]) |
                    |(cdc_bypass_busy[end_num_entry_index:start_num_entry_index]);

    //Register incoming address to determine if its changed.
    always_ff @(posedge cpuside_clk) begin
        address_reg <= data_cpu_to_module.address;
    end

    genvar i;
    generate
        for (i = start_num_entry_index; i <= end_num_entry_index; i++) begin : bus_cdc_inst_gen  
            if (cdc_bypass_mask[i] == 1) begin //Bypass synchronization for straight passthrough
                assign cpubus_o[i].clk_i       = cpuside_clk;
                assign cpubus_i.data_i[i]      = cpubus_o[i].data_i[i];
                assign cpubus_o[i].we_o        = cpubus_i.we_o;
                assign cpubus_o[i].we_ram_o    = cpubus_i.we_ram_o;
                assign cpubus_o[i].address_o   = cpubus_i.address_o;
                assign cpubus_o[i].data_o      = cpubus_i.data_o;
                assign cpubus_o[i].cpu_reset_o = cpubus_i.cpu_reset_o;

                always_comb begin
                    if (module_busy_en_i[i] == 1) begin
                        cdc_bypass_busy[i] = cpubus_o[i].module_busy_i;
                    end else begin
                        cdc_bypass_busy[i] = 0;
                    end
                end 
                assign busy_src[i] = 0;
            end else begin //Synchronize bus signals
                assign cdc_bypass_busy[i] = 0;
                
                //Determine when an address is within the bounds specified and if so put into fifo.
                always_comb begin
                    if (data_cpu_to_module.address >= get_address_start(i) && data_cpu_to_module.address <= get_address_end(i)) begin
                        if (data_cpu_to_module.address != address_reg) begin
                            data_cpu_to_module_valid[i] = 1'b1;
                        end else begin
                            data_cpu_to_module_valid[i] = 1'b0;
                        end
                    end else begin
                        data_cpu_to_module_valid[i] = 1'b0;
                    end
                end

                always_ff @(posedge cdc_clks_i[i]) begin //Store previous busy to check for falling edge
                    if (module_busy_en_i[i] == 1'b1) begin
                        module_busy_prev[i] <= cpubus_o[i].module_busy_i;
                    end else begin
                        module_busy_prev[i] <= 1'b0;
                    end
                end

                always_ff @(posedge cdc_clks_i[i]) begin
                    data_module_to_cpu_valid[i] <= 1'b0;
                    if (module_busy_en_i[i] == 1'b0) begin //Default case where valid data is expected one cycle later with no busy
                        data_module_to_cpu_valid[i] <= data_cpu_to_module_synced_valid[i];
                    end else begin //Other case where a busy is provided by the module
                        if (cpubus_o[i].module_busy_i == 1'b0 && module_busy_prev[i] == 1'b1) begin
                            data_module_to_cpu_valid[i] <= 1'b1;
                        end
                    end
                end

                bus_cdc_bridge #(
                    .DataWidth              ($bits(bus_signals_t))
                ) bus_cdc_inst (
                    .clk_src_i              (cpuside_clk),
                    .reset_i                (cpuside_cpu_reset),
                    .data_src_i             (data_cpu_to_module),
                    .data_src_valid_i       (data_cpu_to_module_valid[i]),
                    .data_src_o             (data_module_to_cpu_synced[i]),
                    .data_src_o_valid_o     (data_module_to_cpu_synced_valid[i]),
                    .busy_src_o             (busy_src[i]),
                    .clk_dst_i              (cdc_clks_i[i]),
                    .data_dst_i             (data_module_to_cpu[i]),
                    .data_dst_valid_i       (data_module_to_cpu_valid[i]),
                    .data_dst_o             (data_cpu_to_module_synced[i]),
                    .data_dst_o_valid_o     (data_cpu_to_module_synced_valid[i]),
                    .busy_dst_o             ()
                );

                //Handle halting of cpu in order to wait for data from a downstream module to return back to cpu domain.
                always_ff @(posedge cpuside_clk) begin
                    if (cpuside_cpu_reset == 1'b0) begin
                        if (data_cpu_to_module_valid[i] == 1'b1) begin
                            transaction_pending[i] <= 1'b1;
                        end
                        if (data_module_to_cpu_synced_valid[i] == 1'b1) begin
                            transaction_pending[i] <= 1'b0;
                        end
                    end else begin
                        transaction_pending[i] <= 1'b0;
                    end
                end

                edge_synchronizer #(
                    .EdgeType               ("Rising"),
                    .PulseWidth             (5)
                ) cdc_reset_inst (
                    .clk_src_i              (cpuside_clk),
                    .clk_dst_i              (cdc_clks_i[i]),
                    .signal_src_i           (cpuside_cpu_reset),
                    .signal_dst_o           (moduleside_cpu_reset[i])
                );

                //Register output of data to the cpu in order to have the data valid when the halt lifts.
                always_ff @(posedge cpuside_clk) begin
                    if (data_module_to_cpu_synced_valid[i] == 1'b1) begin
                        cpubus_i.data_i[i] <= data_module_to_cpu_synced[i].data;
                    end else begin
                        cpubus_i.data_i[i] <= '0;
                    end
                end

                assign data_module_to_cpu[i].data    = cpubus_o[i].data_i[i];
                assign data_module_to_cpu[i].address = '0;
                assign data_module_to_cpu[i].we      = '0;
                assign data_module_to_cpu[i].we_ram  = '0;

                assign cpubus_o[i].clk_i             = cdc_clks_i[i];
                assign cpubus_o[i].cpu_reset_o       = moduleside_cpu_reset[i];

                //Pulse bus signals in clk_dst_i domain to act the same as in main clk domain.
                //If not pulsed, will cause erroneous writes into sync_to_cpu fifo.
                assign cpubus_o[i].data_o            = (data_cpu_to_module_synced_valid[i] == 1) ? data_cpu_to_module_synced[i].data : '0;
                assign cpubus_o[i].address_o         = (data_cpu_to_module_synced_valid[i] == 1) ? data_cpu_to_module_synced[i].address : '0;
                assign cpubus_o[i].we_o              = (data_cpu_to_module_synced_valid[i] == 1) ? data_cpu_to_module_synced[i].we : '0;
                assign cpubus_o[i].we_ram_o          = (data_cpu_to_module_synced_valid[i] == 1) ? data_cpu_to_module_synced[i].we_ram : '0;
            end
        end
    endgenerate

endmodule