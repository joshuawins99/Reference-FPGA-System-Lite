#!/usr/bin/env python3
import sys

def generate_verilog(mem_file, output_file, words=256, offset=0, prefill=1):
    with open(mem_file, 'r') as f:
        mem_data = [line.strip() for line in f.readlines()]

    num_entries = len(mem_data)

    verilog_code = f"""module picosoc_mem #(
    parameter integer WORDS = {words},
    parameter integer OFFSET = {offset},
    parameter integer PREFILL = {prefill}
) (
    input clk,
    input [3:0] wen,
    input [15:0] addr,
    input [31:0] wdata,
    output reg [31:0] rdata
);

    // Memory array declaration
    reg [31:0] mem [0:WORDS-1];

    initial begin
        if (PREFILL) begin
"""

    # Embed initialization statements within the initial block
    for idx, line in enumerate(mem_data):
        verilog_code += f"            mem[OFFSET + {idx}] = 32'h{line};\n"

    # Fill remaining entries with zero
    for idx in range(num_entries, words):
        verilog_code += f"            mem[OFFSET + {idx}] = 32'h00000000;\n"

    verilog_code += """        end
    end

    always @(posedge clk) begin
        rdata <= mem[addr];
        if (wen[0]) mem[addr][ 7: 0] <= wdata[ 7: 0];
        if (wen[1]) mem[addr][15: 8] <= wdata[15: 8];
        if (wen[2]) mem[addr][23:16] <= wdata[23:16];
        if (wen[3]) mem[addr][31:24] <= wdata[31:24];
    end
endmodule
"""

    with open(output_file, 'w') as f:
        f.write(verilog_code)

if __name__ == "__main__":
    if len(sys.argv) < 3 or len(sys.argv) > 5:
        print("Usage: python script.py input.mem output.v [offset] [prefill]")
    else:
        offset = int(sys.argv[3]) if len(sys.argv) >= 4 else 0
        prefill = int(sys.argv[4]) if len(sys.argv) == 5 else 1
        generate_verilog(sys.argv[1], sys.argv[2], offset=offset, prefill=prefill)
