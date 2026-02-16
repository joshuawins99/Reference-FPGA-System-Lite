# Custom Modules
By creating a new custom module that follows the port structure of the bus_rv32 interface, one can create an accessory module that has custom functionality and can be accessed by the cpu. In order to add a new module, an additional entry must be added to the USER_MODULES list in the cpu_config.txt file and a start and end address must be given to the mdoule. Data reads from custom modules are expected to have their data available one clock cycle after the accompanying address is given. An example of a custom module and the interfacing are shown below.
```Verilog
/*@ModuleMetadataBegin
Name : PWM Generator
Description : Generates a configurable duty cycle signal at the set PWMFreq
Reg0 :
    Name : PWM Value
    Description : Sets the desired duty cycle output
    Permissions : Read/Write
@ModuleMetadataEnd*/
module pwm_generator #(
    parameter BaseAddress   = 0,
    parameter address_width = 16,
    parameter data_width    = 8,
    parameter FPGAClkSpeed  = 50000000, //In Hz
    parameter PWMFreq       = 500000 //In Hz
)(
    input  logic                     clk_i,
    input  logic                     reset_i,
    input  logic [address_width-1:0] address_i,
    input  logic [data_width-1:0]    data_i,
    output logic [data_width-1:0]    data_o,
    input  logic                     rd_wr_i,
    output logic                     pwm_o
);

    localparam ReadWritePWMValue = BaseAddress + 0;

    localparam MaxCounterValue = (PWMFreq > FPGAClkSpeed) ? 1 : FPGAClkSpeed / PWMFreq;

    logic [data_width-1:0]              pwm_value   = '0;
    logic [$clog2(MaxCounterValue)+1:0] counter     = '0;
    logic                               pwm_out_reg = '0;

    always_ff @(posedge clk_i) begin //Data Reads
        if (reset_i == 1'b0) begin
            if (rd_wr_i == 1'b0) begin
                unique case (address_i)
                    ReadWritePWMValue : begin
                        data_o[data_width-1:0] <= pwm_value;
                    end
                    default : begin
                        data_o <= '0;
                    end
                endcase
            end
        end else begin
            data_o <= '0;
        end
    end

    always_ff @(posedge clk_i) begin //Data Writes
        if (reset_i == 1'b0) begin
            if (rd_wr_i == 1'b1) begin
                unique case (address_i)
                    ReadWritePWMValue : begin
                        pwm_value <= data_i[data_width-1:0];
                    end
                    default : begin
                        pwm_value <= pwm_value;
                    end
                endcase
            end
        end else begin
            pwm_value <= '0;
        end
    end

    always_ff @(posedge clk_i) begin
        if (reset_i == 1'b0) begin
            counter <= counter + 1;
            if (counter >= MaxCounterValue) begin
                counter <= '0;
            end
        end else begin
            counter <= '0;
        end
    end

    always_ff @(posedge clk_i) begin
        if (reset_i == 1'b0) begin
            if (counter >= pwm_value && pwm_value < MaxCounterValue-1) begin
                pwm_out_reg <= 0;
            end else begin
                pwm_out_reg <= 1;
            end
        end else begin
            pwm_out_reg <= 0;
        end
    end

    assign pwm_o = pwm_out_reg;

endmodule
```
Now interfacing the module with the rest of the system can be seen here:
```Verilog
module top 
import cpu_test_package::*;
(
    input  logic        clk_i,
    input  logic        reset_i,
    input  logic        uart_rx_i,
    output logic        uart_tx_o,
    input  logic [31:0] ex_data_i,
    output logic [31:0] ex_data_o,
    output logic        pwm_o
)

    localparam bypass_config_t bypass_config = '0;
    localparam logic [num_entries-1:0] cdc_bypass_mask = build_bypass_mask(bypass_config);
    localparam logic [num_entries-1:0] module_busy_en_mask = build_busy_mask(bypass_config);

    cpu_test_bus_rv32 cdc_cpubus [num_entries]();

    cpu_test_cdc_top #(
        .cdc_bypass_mask     (cdc_bypass_mask),
        .module_busy_en_mask (module_busy_en_mask)
    ) m1 (
        .clk_i               (clk_i),
        .reset_i             ('0),
        .external_data_i     (ex_data_i),
        .external_data_o     (ex_data_o),
        .uart_rx_i           (uart_rx_i),
        .uart_tx_o           (uart_tx_o),
        .irq_i               ('0),
        .external_cpu_halt_i ('0),
        .cdc_clks_i          ('0),
        .cdc_cpubus          (cdc_cpubus)
    );

    pwm_generator #(
        .BaseAddress   (get_address_start(pwm_e)),
        .address_width (address_width),
        .data_width    (data_width),
        .FPGAClkSpeed  (FPGAClkSpeed),
        .PWMFreq       (200000)
    ) pwm_1 (
        .clk_i         (cdc_cpubus[pwm_e].clk_i),
        .reset_i       (cdc_cpubus[pwm_e].cpu_reset_o),
        .address_i     (cdc_cpubus[pwm_e].address_o),
        .data_i        (cdc_cpubus[pwm_e].data_o),
        .data_o        (cdc_cpubus[pwm_e].data_i[pwm_e]),
        .rd_wr_i       (cdc_cpubus[pwm_e].we_o),
        .pwm_o         (pwm_o)
    );

endmodule
```
It must also be added to cpu_config.txt, so a pwm_e entry will be added to user modules.
```
USER_MODULES:
pwm_e : TRUE : AUTO
        Module_Include : pwm_generator.sv
```
Now it can be accessed like this in the Python side using the ```new-python``` headers.
```Python
from cpu_test_registers import *

SerialObj = InitializeSerial("/dev/ttyUSB0", 115200)
fpga_inst = FPGAInterface(SerialTransport(SerialObj))
fpga_inst.list_blocks()

fpga_inst.pwm_e.pwm_value.write(100)
read_data = fpga_inst.pwm_e.pwm_value.read()

print(read_data)
```