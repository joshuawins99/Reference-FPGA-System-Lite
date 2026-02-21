# Getting Started

### Downloading the System
Release builds are available in the releases section. This getting started guide will assume the use of one of these release builds.

### Prerequisites
* Python >= 3.7

## Constructing a Project
In order to use this system, a folder must be created with the name of what the system instance should be called. This is important as the Verilog packages and all generates files will be prepended with this name. For this example, the folder will live at the level of the two files grabbed from the release tar.
```bash
mkdir cpu_test
ls
cpu_test ref_fpga_sys_lite.sv generate_cpu_instance.py
```
Inside this cpu_test folder, create a file named ```cpu_config.txt```. In this file, the following contents should be pasted.
```
#CPU Config File

CONFIG_PARAMETERS:
    #Code_Folder : C_Code

BUILTIN_PARAMETERS:
    FPGAClkSpeed              : 40000000
    BaudRateCPU               : 115200
    address_width             : 32
    data_width                : 32
    RAM_Size                  : 'h2000
    Program_CPU_Start_Address : 'h0 : {31:0}
    VersionStringSize         : 64
    EnableCPUIRQ              : 0
    UseSERV                   : 0 #Toggles the use of either PicoRV32(0) or SERV(1)
    
USER_PARAMETERS:
    
BUILTIN_MODULES:
    ram_e            : TRUE : {0, RAM_Size-4} : NOEXPREGS
    version_string_e : TRUE : {'h8000, 'h8000+(VersionStringSize-1)*4} : NOEXPREGS
    io_e             : TRUE : {'h9000, 'h900C}
        Module_Include : io.txt
    uart_e           : TRUE : {'h9100, 'h9110}
    
USER_MODULES:

```
This is the file that controls the way the system is generated. Each section has a specific meaning which will be detailed now.

#### CONFIG_PARAMETERS
This is used for defining a Code_Folder or directories for use with includes. This will be ignored for this example.
#### BUILTIN_PARAMETERS
Parameters in this section are passed to the Verilog portion and should not be deleted or added to. The usually relvant ones worth changing are ```FPGAClkSpeed``` which is the clock speed in which this system will be run at and ```BaudRateCPU```. This is used for setting the UART baud rate. For this example, set FPGAClkSpeed to whatever the clock frequency of your clock is and leave ```BaudRateCPU``` untouched.
#### USER_PARAMETERS
This section is used for user created parameters. Feel free to add parameters here that are used within the system. These can also be referenced by some other features with module instantiation.
### BUILTIN_MODULES
This section defines modules that are included with the system. This list should not be changed and the only things to change are the TRUE to FALSE. For this example, leave all set to TRUE.
### USER_MODULES
Much like ```USER_PARAMETERS```, this section is for user created modules. For this example it will be empty, but user created modules should be added to this list if they want to be a part of the system.

Also create a file called ```io.txt``` in the same location with this content. This provides the register descriptions for the io_e module to the system.

Further information on the file format can be found here: [Config File Format](./config_file_format.md)
```
/*@ModuleMetadataBegin
Name : IO
Description : IO Controller and IRQ Mux
Reg0 :
    Name : External Inputs
    Description : Read External Inputs as a bit field
    Permissions : Read
Reg1 :
    Name : External Outputs
    Description : Write to External Outputs as a bit field
    Permissions : Read/Write
Reg2 :
    Name : IRQ Mask
    Description : Set the mask bit corresponding to the External Input to trigger
    Permissions : Read/Write
Reg3 :
    Name : IRQ Clear
    Description : Reading from this register causes the IRQ to clear and will return the bit field with the triggered IRQ
    Permissions : Read
@ModuleMetadataEnd*/
```

## Generating the System
Once the steps above have been completed, it is time to generate the system. To do that simply execute the ```generate_cpu_instance.py``` script. You should see an output similar to this:
```
./generate_cpu_instance.py --gen-headers new-python
C header for cpu_test saved to: /testcpu/cpu_test/cpu_test_registers.h
Python header for cpu_test saved to: /testcpu/cpu_test/cpu_test_registers.py

Generated and saved SystemVerilog package for cpu_test_package: /testcpu/cpu_test/cpu_test_package.sv
Saved SystemVerilog Module file: /testcpu/cpu_test/cpu_test_fpga_sys_lite.sv
```
Four files should have been generated as shown in the console printout. These being ```cpu_test_fpga_sys_lite.sv```, ```cpu_test_package.sv```, ```cpu_test_registers.h```, and ```cpu_test_registers.py```. For the time being, just focus on the two .sv files. These files should be added to a Verilog project. In order to use what was generated, refer to the example top level module below
```Verilog
module top 
import cpu_test_package::*;
(
    input  logic        clk_i,
    input  logic        reset_i,
    input  logic        uart_rx_i,
    output logic        uart_tx_o,
    input  logic [31:0] ex_data_i,
    output logic [31:0] ex_data_o
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
        .uart_rts_o          (),
        .irq_i               ('0),
        .external_cpu_halt_i ('0),
        .cdc_clks_i          ('0),
        .cdc_cpubus          (cdc_cpubus)
    );

endmodule
```
This module is all that is needed to get a functioning system. It provides a UART interface and 32 bit input and output port thats memory mapped.

An assumption will be made that the FPGA that is being targeted has had the relevant tools installed and set up ready to build a project. This guide will not cover this.

## Interacting with the System
Once the project has been build and a suitable UART to USB interface has been connected to a computer, the system can start being used. In order to use the system, refer to the example Python script below. This will utilize the generated python header from before.

```Python
from cpu_test_registers import *

def InitializeSerial(port: str, baudrate: int):
    SerialObj = serial.Serial(port)
    SerialObj.close()
    SerialObj.baudrate = baudrate
    SerialObj.bytesize = 8
    SerialObj.parity  ='N'
    SerialObj.stopbits = 1
    SerialObj.timeout = 1
    SerialObj.rtscts = False
    SerialObj.dsrdtr = False
    SerialObj.xonxoff = False
    SerialObj.open()
    numBufferBytes = SerialObj.in_waiting
    SerialObj.read(size=numBufferBytes)
    SerialObj.reset_input_buffer()
    SerialObj.reset_output_buffer()
    SerialObj.flushInput()
    SerialObj.flushOutput()
    SerialObj.write('\n'.encode('utf-8'))
    return SerialObj

SerialObj = InitializeSerial("/dev/ttyUSB0", 115200)
fpga_inst = FPGAInterface(SerialTransport(SerialObj))
fpga_inst.list_blocks()

print(fpga_inst.version())

fpga_inst.io_e.external_outputs.write(1)
read_data = fpga_inst.io_e.external_outputs.read()

print("Read Data from external_outputs register: ", read_data)
```

This script, upon running, should print the version, light up an LED if one was assigned to the ex_data_o signal, and print the read result from the same register that was written to.

If all seems good, the system has been configured correctly and ready for customization. Have fun!!!