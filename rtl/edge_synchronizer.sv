module edge_synchronizer #(
    parameter EdgeType   = "Rising", //Acceptable: Rising, Falling, Both
    parameter PulseWidth = 1         //Pulse Duration of Output Signal
)(
    input  logic clk_src_i,
    input  logic clk_dst_i,
    input  logic signal_src_i,
    output logic signal_dst_o
);

    localparam int count_width = (PulseWidth <= 1) ? 1 : $clog2(PulseWidth + 1);

    logic                   signal_src_reg = 0;
    logic                   toggle_src     = 0;
    logic                   sync_1         = 0;
    logic                   sync_2         = 0;
    logic                   sync_d         = 0;
    logic [count_width-1:0] pulse_cnt      = 0;
    logic                   pulse_active   = 0;
    logic                   edge_comparison;
    logic                   toggle_detected;

    assign toggle_detected = sync_2 ^ sync_d;

    //Source Domain
    generate
        if (EdgeType == "Rising") begin
            assign edge_comparison = ~signal_src_reg & signal_src_i;
        end else if (EdgeType == "Falling") begin
            assign edge_comparison = signal_src_reg & ~signal_src_i;
        end else if (EdgeType == "Both") begin
            assign edge_comparison = signal_src_i != signal_src_reg;
        end else begin
            assign edge_comparison = ~signal_src_reg & signal_src_i;
        end
    endgenerate

    always_ff @(posedge clk_src_i) begin
        if (edge_comparison == 1'b1) begin
            signal_src_reg <= signal_src_i;
            toggle_src     <= ~toggle_src;
        end else begin
            signal_src_reg <= signal_src_i;
        end
    end

    //Destination Domain
    always_ff @(posedge clk_dst_i) begin
        sync_1 <= toggle_src;
        sync_2 <= sync_1;
        sync_d <= sync_2;
    end

    always_ff @(posedge clk_dst_i) begin
        if (toggle_detected == 1'b1) begin
            pulse_active <= 1;
            pulse_cnt    <= PulseWidth - 1;
        end else if (pulse_active == 1'b1) begin
            if (pulse_cnt == 0) begin
                pulse_active <= 0;
            end else begin
                pulse_cnt <= pulse_cnt - 1;
            end
        end
    end

    assign signal_dst_o = pulse_active;

endmodule