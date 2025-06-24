module bus_cdc_bridge #(
    parameter DataWidth = 8
)(
    input  logic                     clk_src_i,
    input  logic                     reset_i,
    input  logic [DataWidth-1:0]     data_src_i,
    input  logic                     data_src_valid_i,
    output logic [DataWidth-1:0]     data_src_o,
    output logic                     data_src_o_valid_o,
    output logic                     busy_src_o,
    input  logic                     clk_dst_i,
    input  logic [DataWidth-1:0]     data_dst_i,
    input  logic                     data_dst_valid_i,
    output logic [DataWidth-1:0]     data_dst_o,
    output logic                     data_dst_o_valid_o,
    output logic                     busy_dst_o
);

    logic                     src_to_dst_read_pulse    = 1'b0;
    logic                     src_fifo_empty;
    logic                     src_fifo_full;
    logic [DataWidth-1:0]     data_src_synced;

    logic                     dst_to_src_read_pulse    = 1'b0;
    logic                     dst_fifo_empty;
    logic                     dst_fifo_full;
    logic [DataWidth-1:0]     data_dst_synced;

    //SRC to DST Domain FIFO.
    async_fifo #(
        .DSIZE       (DataWidth),
        .ASIZE       (4),
        .AWFULLSIZE  (1),
        .AREMPTYSIZE (1),
        .FALLTHROUGH ("TRUE")
    ) fifo_src_to_dst (
        .wclk        (clk_src_i),
        .wrst_n      (!reset_i),
        .winc        (data_src_valid_i),
        .wdata       (data_src_i),
        .awfull      (src_fifo_full),
        .rclk        (clk_dst_i),
        .rrst_n      (!reset_i),
        .rinc        (src_to_dst_read_pulse),
        .rdata       (data_src_synced),
        .rempty      (src_fifo_empty),
        .arempty     ()
    );

    //Logic to determine when valid data has been output on the src to dst fifo.
    //Also pulse reads if fifo almost full with src_fifo_full signal.
    always_ff @(posedge clk_dst_i) begin
        src_to_dst_read_pulse <= 1'b0;
        if (src_fifo_empty == 1'b0 && src_to_dst_read_pulse == 1'b0) begin
            src_to_dst_read_pulse <= 1'b1;
        end else begin
            src_to_dst_read_pulse <= 1'b0;
        end
    end

    //DST to SRC Domain FIFO.
    async_fifo #(
        .DSIZE       (DataWidth),
        .ASIZE       (4),
        .AWFULLSIZE  (1),
        .AREMPTYSIZE (1),
        .FALLTHROUGH ("TRUE")
    ) fifo_dst_to_src (
        .wclk        (clk_dst_i),
        .wrst_n      (!reset_i),
        .winc        (data_dst_valid_i),
        .wdata       (data_dst_i),
        .awfull      (dst_fifo_full),
        .rclk        (clk_src_i),
        .rrst_n      (!reset_i),
        .rinc        (dst_to_src_read_pulse),
        .rdata       (data_dst_synced),
        .rempty      (dst_fifo_empty),
        .arempty     ()
    );

    //Logic to determine when valid data has been output on the dst to src fifo.
    //Also pulse reads if fifo almost full with dst_fifo_full signal.
    always_ff @(posedge clk_src_i) begin
        if (dst_fifo_empty == 1'b0 && dst_to_src_read_pulse == 1'b0) begin
            dst_to_src_read_pulse <= 1'b1;
        end else begin
            dst_to_src_read_pulse <= 1'b0;
        end
    end

    assign data_src_o         = data_dst_synced;
    assign data_src_o_valid_o = dst_to_src_read_pulse;
    assign busy_src_o         = src_fifo_full;

    assign data_dst_o         = data_src_synced;
    assign data_dst_o_valid_o = src_to_dst_read_pulse;
    assign busy_dst_o         = dst_fifo_full;

endmodule