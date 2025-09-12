module cpu_rv32_serv #(
    parameter ProgramStartAddress = 0,
    parameter StackAddress        = 0,
    parameter address_width       = 32,
    parameter EnableCPUIRQ        = 0
)(
    input  logic                     clk_i,
    input  logic                     reset_i,
    output logic [address_width-1:0] address_o,
    input  logic                     cpu_halt_i,
    input  logic [31:0]              data_i,
    output logic [31:0]              data_o,
    output logic                     we_o,
    output logic [3:0]               we_ram_o,
    input  logic                     irq_i

);

    logic data_valid;
    logic we_pulse;
    logic we_int;
    logic data_valid_reg;
    logic mem_ready_int;
    logic mem_ready;
    logic [address_width-1:0] address;
    logic new_addr_strb;

    always_ff @(posedge clk_i) begin
        if (data_valid == 1'b1) begin
            mem_ready_int <= 1'b1;
        end else begin
            mem_ready_int <= 1'b0;
        end
    end 

    always_comb begin
        if (cpu_halt_i == 1'b1) begin
            mem_ready = 1'b0;
        end else begin
            mem_ready = mem_ready_int;
        end
    end

    servile_native #(
        .ProgramStartAddress (ProgramStartAddress),
        .address_width       (address_width),
        .width               (1),
        .with_csr            (0),
        .compress            (0)
    ) rv32_1 (
        .clk_i               (clk_i),
        .reset_i             (reset_i),
        .address_o           (address),
        .data_o              (data_o),
        .data_i              (data_i),
        .write_strb_o        (we_ram_o),
        .data_valid_o        (data_valid),
        .data_valid_i        (mem_ready & data_valid),
        .irq_i               (irq_i)
    );

    always_comb begin
        if (we_ram_o != 0) begin
            we_int = 1'b1;
        end else begin
            we_int = 1'b0;
        end
    end

    always_ff @(posedge clk_i) begin
        if (we_int == 1'b1) begin
            we_pulse <= 1'b0;
        end else we_pulse <= 1'b1;
    end

    always_ff @(posedge clk_i) begin
        data_valid_reg <= data_valid;
    end

    always_comb begin
        new_addr_strb = data_valid & !data_valid_reg;
    end

    always_comb begin
        if (new_addr_strb == 1) begin
            address_o = address;
        end else begin
            address_o = '0;
        end
    end

    assign we_o = (we_int & we_pulse);

endmodule
