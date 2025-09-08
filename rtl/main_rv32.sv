module main_rv32 
import cpu_reg_package::*;
(
`ifndef SIM
    bus_rv32.from_cpu  cpubus
`else
    input  logic                     clk_i,
    input  logic                     reset_i,
    output logic [data_width-1:0]    cpu_data_o,
    input  data_reg_inputs_t         cpu_data_i,
    input  logic                     cpu_halt_i,
    output logic                     cpu_we_o,
    output logic [3:0]               we_ram_o,
    input  logic                     irq_i,
    output logic [address_width-1:0] address,
    output logic [data_width-1:0]    external_data_o,
    input  logic [data_width-1:0]    external_data_i,
    input  logic                     uart_rx_i,
    output logic                     uart_tx_o,
    output logic                     reset
`endif
);

`ifndef SIM
    logic                     clk_i;
    logic                     reset_i;
    logic [data_width-1:0]    cpu_data_o;
    logic                     cpu_we_o;
    logic [3:0]               we_ram_o;
    logic                     irq_i;
    logic [address_width-1:0] address;
    logic                     cpu_halt_i;

    logic [data_width-1:0]    external_data_o;
    logic [data_width-1:0]    external_data_i;

    logic                     uart_rx_i;
    logic                     uart_tx_o;

    logic                     reset = 1'b1;

`endif

    data_reg_inputs_t data_reg_inputs;
    data_reg_inputs_t data_reg_inputs_interface;
    data_reg_inputs_t data_reg_inputs_combined;

`ifndef SIM
    assign clk_i                     = cpubus.clk_i;
    assign reset_i                   = cpubus.reset_i;
    assign irq_i                     = cpubus.irq_i;
    assign cpubus.data_o             = cpu_data_o;
    assign data_reg_inputs_interface = cpubus.data_i;
    assign cpubus.we_o               = cpu_we_o;
    assign cpubus.address_o          = address;
    assign cpubus.cpu_reset_o        = reset;
    assign cpu_halt_i                = cpubus.cpu_halt_i;
    assign cpubus.external_data_o    = external_data_o;
    assign external_data_i           = cpubus.external_data_i;
    assign uart_rx_i                 = cpubus.uart_rx_i;
    assign cpubus.uart_tx_o          = uart_tx_o;
    assign cpubus.we_ram_o           = we_ram_o;
`endif

    logic irq_io;
    logic irq_combined;

//******************************************* Data Registers and Mux *******************************************
    logic [data_width-1:0]      data_reg;  
    logic [address_width-1:0]   address_reg;

    always_ff @(posedge clk_i) begin
        if (cpu_halt_i == 1'b0) begin
            address_reg <= address;
        end else begin
            address_reg <= address_reg;
        end
    end 

    always_comb begin //Array Slicing to combine the internal and external modules on bus
        for (int i = 0; i <= uart_e; i++) begin
            data_reg_inputs_combined[i] = data_reg_inputs[i];
        end
        for (int i = uart_e+1; i < num_entries; i++) begin
        `ifndef SIM
            data_reg_inputs_combined[i] = data_reg_inputs_interface[i];
        `else
            data_reg_inputs_combined[i] = cpu_data_i[i];
        `endif
        end
    end

    always_comb begin
        data_reg = '0;
        for (int unsigned i = 0; i < num_entries; i++) begin
            if (address_reg >= get_address_mux(2*i+1) && address_reg <= get_address_mux(2*i)) begin
                data_reg = data_reg_inputs_combined[(num_entries-1)-i];
            end
        end
    end
//************************************************************************************************************

    logic [63:0]                reset_counter = '0;
    logic                       reset_initial = 1'b1;

    always_ff @(posedge clk_i) begin
        if (reset_i == 1'b1) begin
            reset <= 1'b1;
            reset_counter <= '0;
        end else if (reset_counter >= 5) begin
            reset <= 1'b0;
            reset_initial <= 1'b0;
        end else begin
            reset <= 1'b1;
            reset_counter <= reset_counter + 1'b1;
        end
    end

    always_comb begin
        if (EnableCPUIRQ == 1) begin
            irq_combined = irq_i | irq_io;
        end else begin
            irq_combined = 0;
        end
    end

    generate
        if (UseSERV == 1) begin
            cpu_rv32_serv #(
                .ProgramStartAddress (Program_CPU_Start_Address),
                .StackAddress        (),
                .address_width       (address_width),
                .EnableCPUIRQ        (EnableCPUIRQ)
            ) cpu1 (
                .clk_i      (clk_i),
                .reset_i    (reset & reset_initial), //Only reset on power up since the program can not be reloaded into ram
                .address_o  (address),
                .cpu_halt_i (cpu_halt_i),
                .data_i     (data_reg),
                .data_o     (cpu_data_o),
                .we_o       (cpu_we_o),
                .we_ram_o   (we_ram_o),
                .irq_i      (irq_combined)
            );
        end else begin
            cpu_rv32 #(
                .ProgramStartAddress (Program_CPU_Start_Address),
                .StackAddress        (),
                .address_width       (address_width),
                .EnableCPUIRQ        (EnableCPUIRQ)
            ) cpu1 (
                .clk_i      (clk_i),
                .reset_i    (reset & reset_initial), //Only reset on power up since the program can not be reloaded into ram
                .address_o  (address),
                .cpu_halt_i (cpu_halt_i),
                .data_i     (data_reg),
                .data_o     (cpu_data_o),
                .we_o       (cpu_we_o),
                .we_ram_o   (we_ram_o),
                .irq_i      (irq_combined)
            );
        end
    endgenerate

    bram_contained_rv32 #(
        .BaseAddress    (get_address_start(ram_e)),
        .EndAddress     (get_address_end(ram_e)),
        .address_width  (address_width),
        .data_width     (32),
        .ram_size       (RAM_Size),
        .pre_fill       (1),
        .pre_fill_start (Program_CPU_Start_Address)
    ) ram1 (
        .clk            (clk_i),
        .addr           (address),
        .wr             (we_ram_o),
        .din            (cpu_data_o),
        .dout           (data_reg_inputs[ram_e])
    );

    version_string #(
        .BaseAddress         (get_address_start(version_string_e)),
        .NumCharacters       (VersionStringSize),
        .CharsPerTransaction (1),
        .address_width       (address_width),
        .data_width          (8),
        .Address_Wording     (4)
    ) version_string_1 (
        .clk_i               (clk_i),
        .address_i           (address),
        .data_i              (cpu_data_o),
        .rd_wr_i             (cpu_we_o),
        .data_o              (data_reg_inputs[version_string_e])
    );

    io_cpu #(
        .BaseAddress     (get_address_start(io_e)),
        .address_width   (address_width),
        .data_width      (data_width),
        .Address_Wording (4)
    ) io_rv32_1 (
        .clk_i           (clk_i),
        .reset_i         (reset),
        .address_i       (address),
        .data_i          (cpu_data_o),
        .data_o          (data_reg_inputs[io_e]),
        .ex_data_i       (external_data_i),
        .ex_data_o       (external_data_o),
        .rd_wr_i         (cpu_we_o),
        .irq_o           (irq_io)
    );

    uart_cpu #(
        .BaseAddress     (get_address_start(uart_e)),
        .address_width   (address_width),
        .FPGAClkSpeed    (FPGAClkSpeed),
        .UARTBaudRate    (BaudRateCPU),
        .Address_Wording (4)
    ) uart_rv32_1 (
        .clk_i           (clk_i),
        .reset_i         (reset),
        .address_i       (address),
        .data_i          (cpu_data_o),
        .data_o          (data_reg_inputs[uart_e]),
        .rd_wr_i         (cpu_we_o),
        .uart_tx_o       (uart_tx_o),
        .uart_rx_i       (uart_rx_i)
    ); 

endmodule
