module serv_rf_ram
  #(parameter width = 32,                      // Must be non-zero
    parameter csr_regs = 4,
    parameter total_regs = 32 + csr_regs,
    parameter depth = total_regs * 32 / width, // Total bits divided by width
    parameter addr_bits = $clog2(depth),
    parameter reg_index_bits = $clog2(total_regs))
   (
    input wire                  i_clk,
    input wire [addr_bits-1:0] i_waddr,
    input wire [width-1:0]     i_wdata,
    input wire                 i_wen,
    input wire [addr_bits-1:0] i_raddr,
    input wire                 i_ren,
    output wire [width-1:0]    o_rdata
    );

   // Compile-time check for valid width
   initial begin
      if (width == 0)
         $fatal("Parameter 'width' must be non-zero.");
   end

   // Memory declaration
   reg [width-1:0] memory [0:depth-1];
   reg [width-1:0] rdata;

   // Write and read logic
   always @(posedge i_clk) begin
      if (i_wen)
         memory[i_waddr] <= i_wdata;
      rdata <= i_ren ? memory[i_raddr] : {width{1'bx}};
   end

   // Register zero detection using safe slicing
   localparam reg_index_msb = addr_bits - 1;
   localparam reg_index_lsb = addr_bits - reg_index_bits;

   wire [reg_index_bits-1:0] reg_index = i_raddr[reg_index_msb : reg_index_lsb];
   reg regzero;

   always @(posedge i_clk)
      regzero <= (reg_index == 0);

   // Output masking for x0 reads
   assign o_rdata = rdata & ~{width{regzero}};

   // Optional memory clearing
`ifdef SERV_CLEAR_RAM
   integer i;
   initial begin
      for (i = 0; i < depth; i = i + 1)
         memory[i] = {width{1'b0}};
   end
`endif

endmodule
