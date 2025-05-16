`ifdef SIM
    `include "version_string.svh"
`endif 

module version_string #(
    parameter BaseAddress = 0,
    parameter NumCharacters = 44,
    parameter CharsPerTransaction = 1,
    parameter address_width = 15,
    parameter data_width = 16,
    parameter Address_Wording = 1
)(

    input  logic                     clk_i,
    input  logic                     reset_i,
    input  logic [address_width-1:0] address_i,
    output logic [data_width-1:0]    data_o,
    input  logic [data_width-1:0]    data_i,
    input  logic                     rd_wr_i
);

    localparam Version_String = BaseAddress + 0;

    logic [address_width-1:0] address;

    logic [NumCharacters*8-1:0] date = `version_string;

    function [data_width-1:0] get_characters (
        input logic [$clog2(NumCharacters/CharsPerTransaction):0] val
    );
        begin
            get_characters = date[data_width*val +: data_width];
        end
    endfunction

    logic [data_width-1:0] data;

    always_comb begin
        if (address_i >= Version_String) begin
            address = (address_i-Version_String) / (Address_Wording);
        end else begin
            address = '0;
        end
    end

    always_comb begin
        data = '0;
        if (rd_wr_i == 1'b0) begin
            if (address >= 0 && address < NumCharacters) begin
                data = get_characters((NumCharacters-1)-address);
            end
        end
    end

    always_ff @(posedge clk_i) begin
        data_o <= data;
    end

    //assign data_o = data;

endmodule
