module wishbone_to_native_mem #(
    parameter address_width = 16
)(
    input  logic                     i_wb_clk,
    input  logic                     i_wb_rst,
    input  logic [address_width-1:2] i_wb_adr,
    input  logic [31:0]              i_wb_dat,
    input  logic [3:0]               i_wb_sel,
    input  logic                     i_wb_we,
    input  logic                     i_wb_cyc,
    output logic [31:0]              o_wb_rdt,
    output logic                     o_wb_ack,
    //Native Interface
    output logic [address_width-1:0] address_o,
    output logic [31:0]              data_o,
    input  logic [31:0]              data_i,
    output logic [3:0]               write_strb_o,
    output logic                     data_valid_o,
    input  logic                     data_valid_i
    );

    wire [3:0] we = {4{i_wb_we & i_wb_cyc}} & i_wb_sel;

    wire [address_width-3:0] addr = i_wb_adr[address_width-1:2];

    assign o_wb_ack = data_valid_i;

    assign data_o = i_wb_dat;
    assign o_wb_rdt = data_i;

    assign address_o = {addr, 2'b00};
    assign write_strb_o = we;
    assign data_valid_o = i_wb_cyc;

endmodule
