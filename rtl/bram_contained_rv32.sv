module bram_contained_rv32 #(
    parameter BaseAddress = 0,
    parameter EndAddress = 0,
    parameter data_width = 8,
    parameter address_width = 8,
    parameter ram_size = 64,
    parameter pre_fill = 0,
    parameter pre_fill_start = 0
) (
    input logic clk,
    input logic [address_width-1:0] addr,
    input logic [3:0] wr,
    input logic [data_width-1:0] din,
    output logic [data_width-1:0] dout
);

    logic [address_width-1:0] ram_addr;
    logic [3:0] ram_we;

    always_comb begin
        if (addr >= BaseAddress && addr <= EndAddress) begin
            ram_addr = addr - BaseAddress;
            ram_we = wr;
        end else begin
            ram_addr = '0;
            ram_we = '0;
        end
    end

    picosoc_mem #(
        .address_width (address_width),
        .WORDS         (ram_size/4),
        .PREFILL       (pre_fill),
        .OFFSET        (pre_fill_start)
    ) psram1 (
        .clk           (clk),
        .addr          (ram_addr >> 2),
        .wen           (ram_we),
        .wdata         (din),
        .rdata         (dout)
    );
    
endmodule