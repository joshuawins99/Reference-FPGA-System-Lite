#!/usr/bin/env python3
import sys

def generate_verilog(mem_file, output_file, words=256, offset=0, prefill=1):
    with open(mem_file, 'r') as f:
        mem_data = [line.strip() for line in f.readlines()]

    num_entries = len(mem_data)

    verilog_code = f"""module picosoc_mem #(
    parameter address_width = 16,
    parameter integer WORDS = {words},
    parameter integer OFFSET = {offset},
    parameter integer PREFILL = {prefill}
) (
    input clk,
    input [3:0] wen,
    input [address_width-1:0] addr,
    input [31:0] wdata,
    output reg [31:0] rdata
);

    // Memory array declaration
    reg [7:0] mem1 [0:WORDS-1];
    reg [7:0] mem2 [0:WORDS-1];
    reg [7:0] mem3 [0:WORDS-1];
    reg [7:0] mem4 [0:WORDS-1];

    initial begin
        for(int i = 0; i < WORDS; i++) begin
            mem1[i] = 0;
            mem2[i] = 0;
            mem3[i] = 0;
            mem4[i] = 0;
        end
        if (PREFILL) begin
"""

    # Embed initialization statements within the initial block
    for idx, line in enumerate(mem_data):
        verilog_code += f"            mem1[OFFSET + {idx}] = 8'h{line[-2:]};\n"
        verilog_code += f"            mem2[OFFSET + {idx}] = 8'h{line[-4:-2]};\n"
        verilog_code += f"            mem3[OFFSET + {idx}] = 8'h{line[-6:-4]};\n"
        verilog_code += f"            mem4[OFFSET + {idx}] = 8'h{line[-8:-6]};\n"

    # Fill remaining entries with zero
    for idx in range(num_entries, words):
        verilog_code += f"            mem1[OFFSET + {idx}] = 8'h00;\n"
        verilog_code += f"            mem2[OFFSET + {idx}] = 8'h00;\n"
        verilog_code += f"            mem3[OFFSET + {idx}] = 8'h00;\n"
        verilog_code += f"            mem4[OFFSET + {idx}] = 8'h00;\n"

    verilog_code += """        end
    end

    always @(posedge clk) begin
        rdata <= {mem4[addr], mem3[addr], mem2[addr], mem1[addr]};
    end

    always @(posedge clk) begin
        if (wen[0]) mem1[addr] <= wdata[ 7: 0];
        if (wen[1]) mem2[addr] <= wdata[15: 8];
        if (wen[2]) mem3[addr] <= wdata[23:16];
        if (wen[3]) mem4[addr] <= wdata[31:24];
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
