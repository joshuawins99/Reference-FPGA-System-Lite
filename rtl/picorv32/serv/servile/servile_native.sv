module servile_native #(
    parameter ProgramStartAddress = 0,
    parameter address_width       = 16,
    parameter width               = 1,
    parameter sim                 = 0,
    parameter [0:0] debug         = 1'b0,
    parameter with_csr            = 0,
    parameter [0:0] compress      = 0,
    parameter [0:0] align         = compress
)(
    input logic                      clk_i,
    input logic                      reset_i,
    output logic [address_width-1:0] address_o,
    output logic [31:0]              data_o,
    input  logic [31:0]              data_i,
    output logic [3:0]               write_strb_o,
    output logic                     data_valid_o,
    input  logic                     data_valid_i
);

    localparam csr_regs = with_csr*4;
    localparam rf_width = width * 2;
    localparam rf_l2d   = $clog2((32+csr_regs)*32/rf_width);

    logic [31:0] wb_mem_adr;
    logic [31:0] wb_mem_dat;
    logic [3:0]  wb_mem_sel;
    logic        wb_mem_we;
    logic        wb_mem_stb;
    logic [31:0] wb_mem_rdt;
    logic        wb_mem_ack;

    logic [rf_l2d-1:0]   rf_waddr;
    logic [rf_width-1:0] rf_wdata;
    logic                rf_wen;
    logic [rf_l2d-1:0]   rf_raddr;
    logic                rf_ren;
    logic [rf_width-1:0] rf_rdata;

    wishbone_to_native_mem #(
        .address_width (address_width)
    ) ram (
        // Wishbone interface
        .i_wb_clk     (clk_i),
        .i_wb_rst     (reset_i),
        .i_wb_adr     (wb_mem_adr[address_width-1:2]),
        .i_wb_cyc     (wb_mem_stb),
        .i_wb_we      (wb_mem_we) ,
        .i_wb_sel     (wb_mem_sel),
        .i_wb_dat     (wb_mem_dat),
        .o_wb_rdt     (wb_mem_rdt),
        .o_wb_ack     (wb_mem_ack),

        //Native Interface
        .address_o    (address_o),
        .data_o       (data_o),
        .data_i       (data_i),
        .write_strb_o (write_strb_o),
        .data_valid_o (data_valid_o),
        .data_valid_i (data_valid_i)   
    );

    serv_rf_ram #(
        .width (rf_width),
        .csr_regs (csr_regs)
    ) rf_ram (
        .i_clk    (clk_i),
        .i_waddr  (rf_waddr),
        .i_wdata  (rf_wdata),
        .i_wen    (rf_wen),
        .i_raddr  (rf_raddr),
        .i_ren    (rf_ren),
        .o_rdata  (rf_rdata)
    );

    servile #(
        .reset_pc       (ProgramStartAddress),
        .reset_strategy ("MINI"),
        .width          (width),
        .sim            (sim[0]),
        .debug          (debug),
        .with_c         (compress[0]),
        .with_csr       (with_csr[0]),
        .with_mdu       (0)
    ) cpu (
        .i_clk          (clk_i),
        .i_rst          (reset_i),
        .i_timer_irq    (0),

        .o_wb_mem_adr   (wb_mem_adr),
        .o_wb_mem_dat   (wb_mem_dat),
        .o_wb_mem_sel   (wb_mem_sel),
        .o_wb_mem_we    (wb_mem_we),
        .o_wb_mem_stb   (wb_mem_stb),
        .i_wb_mem_rdt   (wb_mem_rdt),
        .i_wb_mem_ack   (wb_mem_ack),

        .o_wb_ext_adr   (),
        .o_wb_ext_dat   (),
        .o_wb_ext_sel   (),
        .o_wb_ext_we    (),
        .o_wb_ext_stb   (),
        .i_wb_ext_rdt   ('0),
        .i_wb_ext_ack   ('0),

        .o_rf_waddr     (rf_waddr),
        .o_rf_wdata     (rf_wdata),
        .o_rf_wen       (rf_wen),
        .o_rf_raddr     (rf_raddr),
        .o_rf_ren       (rf_ren),
        .i_rf_rdata     (rf_rdata)
    );

endmodule
