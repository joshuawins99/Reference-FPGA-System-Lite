import cpu_reg_package::*;
module bus_cdc_single #(
    parameter bus_cdc_start_address = 0,
    parameter bus_cdc_end_address   = 0
)(
    input  logic                     clk_dst_i,
    input  logic                     cpuside_clk_i,
    input  logic                     cpuside_cpu_reset_i,
    input  logic                     cpuside_we_i,
    input  logic [address_width-1:0] cpuside_address_i,
    input  logic [data_width-1:0]    cpuside_data_i,
    output logic                     cpuside_cpu_halt_o,
    input  logic [data_width-1:0]    moduleside_data_i,
    output logic [data_width-1:0]    moduleside_data_o,
    output logic [address_width-1:0] moduleside_address_o,
    output logic                     moduleside_we_o,
    output logic [data_width-1:0]    cpuside_module_data_o
);

    typedef struct packed {
        logic                     we;
        logic [address_width-1:0] address;
        logic [data_width-1:0]    data;
    } bus_signals_t;

    localparam bundled_signals_width  = $bits(bus_signals_t);

    logic [address_width-1:0] address_reg               = '0;
    logic                     start_halt                = '0;
    logic                     continue_halt             = '0;
    logic                     cpu_signals_read_pulse    = 1'b0;
    logic                     cpu_rempty;
    logic                     cpu_write_fifo_pulse      = 1'b0;
    logic                     cpu_halt_fifo_in;

    logic                     module_signals_read_pulse = 1'b0;
    logic                     module_write_fifo_pulse   = 1'b0;
    logic                     module_rempty;
    logic [data_width-1:0]    data_to_cpu_fifo;

    bus_signals_t             cpu_signals_in;
    bus_signals_t             cpu_signals_synced;

    //Assign relevant bus signals to synchronize.
    assign cpu_signals_in = '{
        we:      cpuside_we_i, 
        address: cpuside_address_i, 
        data:    cpuside_data_i
    };

    //Register incoming address to determine if its changed.
    always_ff @(posedge cpuside_clk_i) begin
        address_reg <= cpu_signals_in.address;
    end

    //Determine when an address is within the bounds specified and if so put into fifo.
    always_comb begin
        if (cpu_signals_in.address >= bus_cdc_start_address && cpu_signals_in.address <= bus_cdc_end_address) begin
            if (cpu_signals_in.address != address_reg) begin
                cpu_write_fifo_pulse = 1'b1;
            end else begin
                cpu_write_fifo_pulse = 1'b0;
            end
        end else begin
            cpu_write_fifo_pulse = 1'b0;
        end
    end

    //CPU to Module CDC Domain FIFO for Writes.
    async_fifo #(
        .DSIZE       (bundled_signals_width),
        .ASIZE       (4),
        .AWFULLSIZE  (1),
        .AREMPTYSIZE (1),
        .FALLTHROUGH ("TRUE")
    ) sync_from_cpu (
        .wclk        (cpuside_clk_i),
        .wrst_n      (!cpuside_cpu_reset_i),
        .winc        (cpu_write_fifo_pulse),
        .wdata       (cpu_signals_in),
        .awfull      (cpu_halt_fifo_in),
        .rclk        (clk_dst_i),
        .rrst_n      (!cpuside_cpu_reset_i),
        .rinc        (cpu_signals_read_pulse),
        .rdata       (cpu_signals_synced),
        .rempty      (cpu_rempty),
        .arempty     ()
    );

    //Logic to determine when valid data has been output on the sync_from_cpu fifo.
    //Also pulse reads if fifo almost full with cpu_halt_fifo_in signal.
    always_ff @(posedge clk_dst_i) begin
        cpu_signals_read_pulse <= 1'b0;
        if ((cpu_rempty == 1'b0 && cpu_signals_read_pulse == 1'b0) || (cpu_rempty == 1'b0 && cpu_halt_fifo_in == 1'b1)) begin
            cpu_signals_read_pulse <= 1'b1;
        end else begin
            cpu_signals_read_pulse <= 1'b0;
        end
    end

    //Pulse bus signals in clk_dst_i domain to act the same as in main clk domain.
    //If not pulsed, will cause erroneous writes into sync_to_cpu fifo.
    assign moduleside_we_o        = (cpu_signals_read_pulse == 1) ? cpu_signals_synced.we      : '0;
    assign moduleside_address_o   = (cpu_signals_read_pulse == 1) ? cpu_signals_synced.address : '0;
    assign moduleside_data_o      = (cpu_signals_read_pulse == 1) ? cpu_signals_synced.data    : '0;

    //Logic to determine if the transaction is a read. If it is then halt cpu to wait for data.
    always_ff @(posedge cpuside_clk_i) begin
        start_halt <= 1'b0;
        if (cpu_write_fifo_pulse == 1'b1) begin
            if (cpu_signals_in.we == 1'b0) begin
                start_halt <= 1'b1;
            end else begin
                start_halt <= 1'b0;
            end
        end else begin
            start_halt <= 1'b0;
        end
    end

    //Register cpu_signals_read_pulse as data will be valid on module in clk_dst_i domain on next cycle.
    //Only pulse module_write_fifo_pulse when doing a read operation.
    always_ff @(posedge clk_dst_i) begin
        if (cpu_signals_read_pulse == 1'b1 && cpu_signals_synced.we == 1'b0) begin
            module_write_fifo_pulse <= 1'b1;
        end else begin
            module_write_fifo_pulse <= 1'b0;
        end
    end

    //Module CDC to CPU Domain FIFO for Reads.
    async_fifo #(
        .DSIZE       (data_width),
        .ASIZE       (4),
        .AWFULLSIZE  (1),
        .AREMPTYSIZE (1),
        .FALLTHROUGH ("TRUE")
    ) sync_to_cpu (
        .wclk        (clk_dst_i),
        .wrst_n      (!cpuside_cpu_reset_i),
        .winc        (module_write_fifo_pulse),
        .wdata       (moduleside_data_i),
        .awfull      (),
        .rclk        (cpuside_clk_i),
        .rrst_n      (!cpuside_cpu_reset_i),
        .rinc        (module_signals_read_pulse),
        .rdata       (data_to_cpu_fifo),
        .rempty      (module_rempty),
        .arempty     ()
    );

    //Ensure that erroneous data isn't fed back into the cpu and only strobe the data when valid. Defaults to 0.
    always_comb begin
        if (module_signals_read_pulse == 1'b1) begin
            cpuside_module_data_o = data_to_cpu_fifo;
        end else begin
            cpuside_module_data_o = '0;
        end
    end

    //Logic to disable cpu halting after data should be valid.
    always_ff @(posedge cpuside_clk_i) begin
        if (start_halt == 1'b1) begin
            continue_halt <= 1'b1;
        end
        if (module_rempty == 1'b0 && module_signals_read_pulse == 1'b0) begin
            continue_halt <= 1'b0;
            module_signals_read_pulse <= 1'b1;
        end else begin
            module_signals_read_pulse <= 1'b0;
        end
    end

    assign cpuside_cpu_halt_o = start_halt | continue_halt | cpu_halt_fifo_in;

endmodule