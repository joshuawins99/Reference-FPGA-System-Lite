# Reference-FPGA-System-Lite

For the full system: https://github.com/joshuawins99/Reference-FPGA-System

## What is it?
This is an FPGA Register System that contains a softcore RISC-V CPU that can communicate with a host computer or mcu. The system utilizes a simple UART for communication. The design intent was for this to be as easy to drop into a design as possible and provide a debug interface to interact with the FPGA using a computer with scripting.

## Compatibility
This project was aimed to provide compatibility across a wide range of FPGAs from various vendors. This has stemmed from the full system project which has been tested on a variety of FPGAs. Any tool with SystemVerilog/Verilog support "should" work with this system.

## Building
There are a few requirements for building this system:
* Bash
* Python >= 3.7
* riscv32 gcc tools
* Optional: sv2v

Run the build_single_module.sh script:
```bash
./build_single_module.sh
```
This should generate a file named ref_fpga_sys_lite.sv. This file along with scripts/generate_cpu_instance.py make up the complete system. Copy these two files into your project to use. A config file must also be provided. Details below.

There is also a ```--c-folder``` option to the build_single_module.sh script. This allows the use of custom C code. Add the folder path to the C code after the option flag.

Release builds can be found in the releases section.

## How do I use it?
Create a folder and run the python script from a level up from the created folder. The folder can be any name and will reflect the name of the package:
```bash
mkdir cpu_test
ls
cpu_test ref_fpga_sys_lite.sv generate_cpu_instance.py
```

### Config Creation
Now create a config file named cpu_config.txt and place it in the cpu_test folder. It follows this format:
```
#CPU Config File
#Parameters follow Name : Value : Width (Optional)
#BUILTIN_MODULES are included modules
#Modules follow enumeration name : Enable TRUE/FALSE : Address Bounds
#Optionally a base address can be appended to USER_MODULES
#Module definitions under USER_MODULES can have the AUTO type followed by the number of registers
#USER_MODULES: 'h9200
#   my_module_e : TRUE : AUTO : 3
#This will automatically assign register addresses and will be printed to console
#A C Header and Python Header are also generated
#If a parameter is to be used for number of registers:
#   my_module_e : TRUE : AUTO : {Parameter}
#If the script is to infer the number of registers:
#   my_module_e : TRUE : AUTO
#Manually placed register locations can also be placed at the same time
#If individual registers are not wished to be displayed, a : NOEXPREGS can be placed at the end of a module
#Place extra modules not included by default in USER_MODULES

CONFIG_PARAMETERS:
    #C_Code_Folder : C_Code

BUILTIN_PARAMETERS:
    FPGAClkSpeed : 40000000,
    BaudRateCPU : 230400,
    address_width : 16,
    data_width : 32,
    RAM_Size : 'h2000,
    Program_CPU_Start_Address : 'h0 : {31:0},
    VersionStringSize : 64,
    EnableCPUIRQ : 0,
    UseSERV : 0 #Toggles the use of either PicoRV32(0) or SERV(1)
    
USER_PARAMETERS:
    
BUILTIN_MODULES:
    ram_e : TRUE : {0, RAM_Size} : NOEXPREGS,
    version_string_e : TRUE : {'h8000, 'h8000+(VersionStringSize-1)*4} : NOEXPREGS,
    io_e : TRUE : {'h9000, 'h900C},
    uart_e : TRUE : {'h9100, 'h9110}
    
USER_MODULES:
```

Additionally, Names, Descriptions, and Permissions can be added for modules and registers.
```
USER_MODULES:
    timer_e     : TRUE : AUTO : 3,
        Name : Timer
        Description : Will wait until set value expires and then change the output
        Reg0 :
            Name :  Set Timer Value
            Description : Sets the timer value
            Permissions : Write
        Reg1 :
            Name :  Start Timer
            Description : Starts the timer
            Permissions : Write
        Reg2 :
            Name : Read Timer Status
            Description : Reads if timer is still busy or finished
            Permissions : Read
```

***As of Version 3.12.0*** there is a Module_Include option to embed the register metadata into the modules themselves. Also included with this is the ability to leave a number or expression out after the AUTO as it can be automatically inferred through the register descriptions. Example:
```
USER_MODULES:
    timer_e : TRUE : AUTO
        Module_Include : ../../rtl/timer_cpu.sv
```
***As of Version 3.12.1*** it is also possible to define a path in the CONFIG_PARAMETERS section and use it like this.
```
CONFIG_PARAMETERS:
    REF_PATH : ../../example

USER_MODULES:
    timer_e : TRUE : AUTO
        Module_Include : {REF_PATH}/rtl/timer_cpu.sv
```
The path would resolve to ../../example/rtl/timer_cpu.sv


An example of the metadata block in a module is as shown here:
```
/*@ModuleMetadataBegin
Name : Timer
Description : Will wait until set value expires and then change the output
Reg0 :
    Name : Set Timer Value
    Description : Sets the timer value
    Permissions : Write
Reg1 :
    Name : Start Timer
    Description : Starts the timer
    Permissions : Write
Reg2 :
    Name : Read Timer Status
    Description : Reads if timer is still busy or finished
    Permissions : Read
@ModuleMetadataEnd*/
```
***As of Version 3.13.0*** A new headers option is available through the new-python and new-c options to --gen-headers. Also bit fields are an option to be passed through to the new Python headers. They will be ignored otherwise. They are dictated by a Bounds entry. The bounds works like a normal vector in verilog where [msb:lsb] is the format. An example is shown here:
```
/*@ModuleMetadataBegin
Name : Register
Description : Register Description
Reg0 :
    Name : Zeroth Register
    Description : Zeroth Register Description
    Field0 :
        Name : First Bit
        Bounds : [0:0]
        Description : First Bit Description
    Field1 :
        Name : More bits
        Bounds : [5:1]
        Description : Bits 5 to 1 field
@ModuleMetadataEnd*/
```

***As of Version 3.14.0*** Submodules are now supported as an entry in the config file. This will in turn calculate the addressing for all submodules as well as produce a hierarchy in the new headers.
```
USER_MODULES:
    timer_e : TRUE : AUTO
        Module_Include : {REF_PATH}/rtl/timer_cpu.sv
        SUBMODULE:
            dac_e : TRUE : AUTO
                Name : DAC SPI Controller
                Description : SPI Master for Controlling DAC
                Module_Include : {REF_PATH}/rtl/spi_master.sv
                SUBMODULE:
                    timer_e : TRUE : AUTO
                        Module_Include : {REF_PATH}/rtl/timer_cpu.sv
```

***As of Version 3.16.0*** There is a 'Repeat' keyword. This allows for multiple instances of an entry. Subsequent repeats will get an _{iterator} appended to their name. The number can either be a literal or an {expression}.
```
USER_MODULES:
    pwm_e : TRUE : AUTO
        Repeat : 2
        Module_Include : {REF_PATH}/rtl/pwm_generator.sv
```
In this example, pwm_e, pwm_e_1, and pwm_e_2 will be added.

### System Generation
Run the python script to generate the module and package file:
```bash
python3 generate_cpu_instance.py
# - OR -
./generate_cpu_instance.py
```
Optionally, under the CONFIG_PARAMETERS section is the C_Code_Folder variable. This variable is used when running the generate_cpu_instance.py script with the ``--build`` flag. This allows the python script to both build and place the output files in the correct directory. Multiple unique instances of this system can be used in a single project easily this way. This option will call the build_single_module.sh for each instance of config file automatically so the script itself doesn't have to be run if using it this way. 

NOTE: If using ``--build`` the GCC RISC-V cross compiler has to be installed and this module be brought in as a submodule for example.

Below are the list of flags as part of generate_cpu_instance.py:

    --print-all-registers  -> prints all the registers and their addresses to console
    --print-user-registers -> prints only the user registers to console
    --save-all-registers   -> save all registers info to a file
    --save-user-registers  -> save user registers info to a file 
    --gen-headers          -> generates C and Python headers for use in a program 
    --configs-path         -> specify base folder that the script should look for config folders

### RTL Instantiation Usage
An example instantiation of the module is as follows. The package name will be {folder name}_package, the top level instantiation will be {folder name}_top, and the interface will be {folder name}_bus_rv32: (Refer to the [Integrated CDC Module](#integrated-cdc-module) section for the most up to date way of instantiation. The method shown here also is still supported.)
```Verilog
import cpu_test_package::*;
module ref_fpga_sys_lite_top_example (
    input  logic        clk_i,
    input  logic        reset_i,
    input  logic        uart_rx_i,
    output logic        uart_tx_o,
    input  logic [31:0] ex_data_i,
    output logic [31:0] ex_data_o
);

cpu_test_bus_rv32 cpubus();

assign cpubus.clk_i           = clk_i;
assign cpubus.reset_i         = reset_i;

assign ex_data_o              = cpubus.external_data_o;
assign cpubus.external_data_i = ex_data_i;

assign uart_tx_o              = cpubus.uart_tx_o;
assign cpubus.uart_rx_i       = uart_rx_i;

//Needs to be 0 if not using CDC module discussed down below
assign cpubus.cpu_halt_i      = 1'b0;

cpu_test_top m1 (
    .cpubus (cpubus)
);

endmodule
```

A few parameters in the config file have to be configured to the specific project. The most important one to check is FPGAClkSpeed. Set this to the frequency of clk_i which corresponds to the example instantiation above.

Also take note of the BaudRateCPU parameter. This is the baud rate the UART is configured to run at. The default configuration is 230400 Baud, 1 Stop Bit, and no parity bit.

### Python Scripting Example
Using the python functions below, try to read the FPGA Version String. Expected output should resemble this:
```Python
import serial
import serial.tools.list_ports

SerialObj = serial.Serial("/dev/ttyUSB1")
SerialObj.close()
SerialObj.baudrate = 230400
SerialObj.bytesize = 8
SerialObj.parity  ='N'
SerialObj.stopbits = 1
SerialObj.rtscts = False
SerialObj.dsrdtr = False
SerialObj.xonxoff = False
print(SerialObj.get_settings())
SerialObj.open()
numBufferBytes = SerialObj.in_waiting
SerialObj.read(size=numBufferBytes)
SerialObj.flushInput()
SerialObj.flushOutput()
SerialObj.write('\n'.encode('utf-8'))

def readFPGAVersion():
    SerialObj.write('readFPGAVersion\n'.encode('utf-8'))
    readVersion = SerialObj.readline()
    readVersion = readVersion[:-1]
    print(readVersion.decode('utf-8'))
    
def writeFPGA(addr, data):
    strtosend = 'wFPGA,' + str(int(addr)) + ',' + str(int(data)) + '\n'
    SerialObj.write(strtosend.encode('utf-8'))

def readFPGA(addr):
    strtosend = 'rFPGA,'+ str(addr) + '\n'
    SerialObj.write(strtosend.encode('utf-8'))
    readData = SerialObj.readline()
    readData = readData[:-1]
    return int(readData.decode('utf-8'))
```

```
>>> readFPGAVersion()
DEV 1234567 Fri May 09 07:51:37 PM PDT 2025
```

In order to do reads and writes to the built in I/O module, the start and end addresses can be found in the cpi_reg_package.sv file. Here is an example of writing to the output register and reading from the input register using the default addresses.

```
>>> writeFPGA(36868, 10)   -> Where 10 is the decimal number to put on the output register
>>> print(readFPGA(36868)) -> Read the data of the output register
10                         -> Should return 10

>>> print(readFPGA(36864)) -> Should return the decimal equivalent of the data on the input register
```

Running the ``help`` command in a serial console connected to the system will show the available commands. Documentation of these commands is not currently available. The io.c file in C_Code has the relevent information for using these commands.

Also with the ``--gen-headers`` option, the enum name can be used instead of the raw address numbers. This is accomplished like so:

```Python
from cpu_test_registers import *

writeFPGA(IO_E.reg_at(1), 10) # Writes the value 10 to the first register in the IO_E block

print(readFPGA(IO_E.reg_at(0))) # Reads the input IO register
```

If the individual registers are given names, these names can also be used instead. For example this is an autogenerated header portion for a timer_e module:

```Python
# Module: Timer (timer_e)
# Module Description: Will wait until set value expires and then change the output
TIMER_E_SET_TIMER_VALUE_ADDR = 0x4110
# Register Description: Sets the timer value
# Register Permissions: W
TIMER_E_START_TIMER_ADDR = 0x4114
# Register Description: Starts the timer
# Register Permissions: W
TIMER_E_READ_TIMER_STATUS_ADDR = 0x4118
# Register Description: Reads if timer is still busy or finished
# Register Permissions: R
TIMER_E = CompactRegisterBlock(0x4110, 3, 4)
```

## Adding Additional Functionality

By creating a new custom module that follows the port structure of the bus_rv32 interface, one can create an accessory module that has custom functionality and can be accessed by the cpu. In order to add a new module, an additional entry must be added to the USER_MODULES list in the cpu_config.txt file and a start and end address must be given to the mdoule. Data reads from custom modules are expected to have their data available one clock cycle after the accompanying address is given. If a combinatorial output is desired, use of the address_reg logic ensures that data is valid when the CPU expects it.

The host side is up to the specfic use case. Anything that supports a UART type device can be used for communication. Three commands are available for communication: rFPGA (read a register from the FPGA), wFPGA (write a value to a register in the FPGA), and readFPGAVersion (reports the build time and version of the FPGA build running). 

## Clock Domain Crossing
A clock domain crossing bridge has been added in order to facilitate the use of modules on different clock domains. An example of using this module can be seen below.
```Verilog
logic cdc_clocks [num_entries];

assign cdc_clocks[user_module_1_e] = clk_30; //One clock
assign cdc_clocks[user_module_2_e] = clk_100; //Another Clock

localparam bypass_config_t bypass_config = {
    //add_cdc_entry(enum, cdc bypass, busy enable)
    add_cdc_entry(user_module_1_e,  0, 0),
    add_cdc_entry(user_module_2_e,  0, 1),
};

localparam logic [num_entries-1:0] cdc_bypass_mask = build_bypass_mask(bypass_config);
localparam logic [num_entries-1:0] module_busy_en_mask = build_busy_mask(bypass_config);

cpu_test_bus_rv32 cdc_cpubus [num_entries]();

cpu_test_bus_cdc #(
    .bus_cdc_start_address (get_address_start(user_module_1_e)),
    .bus_cdc_end_address   (get_address_end(user_module_2_e)),
    .cdc_bypass_mask       (cdc_bypass_mask),
    .module_busy_en_mask   (module_busy_en_mask)
) cdc_1 (
    .cdc_clks_i            (cdc_clocks),
    .module_busy_en_i      (module_busy_en),
    .cpubus_i              (cpubus),
    .cpubus_o              (cdc_cpubus),
    .busy_o                (cpubus.cpu_halt_i)
);

//In the clk_30 domain
user_module_1_e #(
    .BaseAddress   (get_address_start(user_module_1_e)),
    .address_width (address_width),
    .data_width    (data_width)
) test_mod_1 (
    .clk_i         (cdc_cpubus[user_module_1_e].clk_i),
    .reset_i       (cdc_cpubus[user_module_1_e].cpu_reset_o),
    .address_i     (cdc_cpubus[user_module_1_e].address_o),
    .data_i        (cdc_cpubus[user_module_1_e].data_o),
    .data_o        (cdc_cpubus[user_module_1_e].data_i[user_module_1_e]),
    .rd_wr_i       (cdc_cpubus[user_module_1_e].we_o)
);

//In the clk_100 domain
user_module_2_e #(
    .BaseAddress   (get_address_start(user_module_2_e)),
    .address_width (address_width),
    .data_width    (data_width)
) test_mod_2 (
    .clk_i         (cdc_cpubus[user_module_2_e].clk_i),
    .reset_i       (cdc_cpubus[user_module_2_e].cpu_reset_o),
    .address_i     (cdc_cpubus[user_module_2_e].address_o),
    .data_i        (cdc_cpubus[user_module_2_e].data_o),
    .data_o        (cdc_cpubus[user_module_2_e].data_i[user_module_2_e]),
    .rd_wr_i       (cdc_cpubus[user_module_2_e].we_o),
    .busy_o        (cdc_cpubus[user_module_2_e].module_busy_i)
);
```
Modules are have the option to either have their data available one clock cycle later as normal, or by setting a 1 in the module_busy_en_i bitmask, have a busy signal to have the cdc module wait until valid data is signaled from the downstream module. These modules follow exactly the same behavior as ones that would in the same clock domain. The bus_cdc module will actively halt the cpu automatically to wait for the read data from the downstream modules to be valid. The bus_cdc_start_address and bus_cdc_end_address represent the bounds to reserve for cdc modules. It is recommended to use the get_address_start() and get_address_end() functions with the first and last enumeration to get the desired results. 

For tools like Quartus which do a poor job of resolving drivers, a cdc_bypass_mask is provided that allows for hooking up all modules to the bus_cdc module and not have the extra latency or utilization penalty for doing so. Configuring downstream modules this way in which some may need to be in a separate clock domain makes Quartus happy and not complain about multiple drivers.

## Integrated CDC Module
***As of Version 3.10.0***
An option to have an integrated cdc module is supported. This essentially wraps the cpu and cdc instance into one module to make the instantiation cleaner. With the bypass_config_t type, a localparam is made to define the modules and if they should use the cdc synchronization or not. Passthrough mode is enabled when cdc bypass is set to 1 for a given module. This new module is the preferred way to use this system since everything is integreated into a single package. Using the previous method of instantiation is still supported though. The default is an entry that is bypassed and doesnt require a busy (1, 0). Modules that fit this type do not require an entry.
```Verilog
import cpu_test_package::*;
module cpu_with_cdc_test (
    input logic clk_i,
    input logic reset_i,
    input logic uart_rx_i,
    output logic uart_tx_o
);

    //Some PLL for clk_30 and clk_100 here

    logic cdc_clocks [num_entries];

    assign cdc_clocks[user_module_1_e] = clk_30; //One clock

    localparam bypass_config_t bypass_config = {
        //add_cdc_entry(enum, cdc bypass, busy enable)
        add_cdc_entry(user_module_1_e,  0, 0),
        add_cdc_entry(user_module_2_e,  1, 1),
    };

    //For modules with the cdc bypass option checked, the main system clock will be automatically assigned

    localparam logic [num_entries-1:0] cdc_bypass_mask = build_bypass_mask(bypass_config);
    localparam logic [num_entries-1:0] module_busy_en_mask = build_busy_mask(bypass_config);

    cpu_test_bus_rv32 cdc_cpubus [num_entries]();

    cpu_test_cdc_top #(
        .cdc_bypass_mask     (cdc_bypass_mask),
        .module_busy_en_mask (module_busy_en_mask)
    ) m1 (
        .clk_i               (clk_i),
        .reset_i             (reset_i),
        .external_data_i     ('0),
        .external_data_o     (),
        .uart_rx_i           (uart_rx_i),
        .uart_tx_o           (uart_tx_o),
        .irq_i               ('0),
        .external_cpu_halt_i ('0),
        .cdc_clks_i          (cdc_clocks),
        .cdc_cpubus          (cdc_cpubus)
    );

    //In the clk_30 domain
    user_module_1_e #(
        .BaseAddress   (get_address_start(user_module_1_e)),
        .address_width (address_width),
        .data_width    (data_width)
    ) test_mod_1 (
        .clk_i         (cdc_cpubus[user_module_1_e].clk_i),
        .reset_i       (cdc_cpubus[user_module_1_e].cpu_reset_o),
        .address_i     (cdc_cpubus[user_module_1_e].address_o),
        .data_i        (cdc_cpubus[user_module_1_e].data_o),
        .data_o        (cdc_cpubus[user_module_1_e].data_i[user_module_1_e]),
        .rd_wr_i       (cdc_cpubus[user_module_1_e].we_o)
    );

    //In the clk_i domain
    user_module_2_e #(
        .BaseAddress   (get_address_start(user_module_2_e)),
        .address_width (address_width),
        .data_width    (data_width)
    ) test_mod_2 (
        .clk_i         (cdc_cpubus[user_module_2_e].clk_i),
        .reset_i       (cdc_cpubus[user_module_2_e].cpu_reset_o),
        .address_i     (cdc_cpubus[user_module_2_e].address_o),
        .data_i        (cdc_cpubus[user_module_2_e].data_o),
        .data_o        (cdc_cpubus[user_module_2_e].data_i[user_module_2_e]),
        .rd_wr_i       (cdc_cpubus[user_module_2_e].we_o),
        .busy_o        (cdc_cpubus[user_module_2_e].module_busy_i)
    );

endmodule
```

## License
This project is licensed under the CERN Open Hardware Licence Version 2 - Weakly Reciprocal (CERN-OHL-W-2.0). See the [LICENSE](./LICENSE) file for details.

## Contribution Request
While this repository is licensed under the CERN-OHL-W license, I kindly ask — as a courtesy — that any fixes or improvements be contributed back to the upstream project, provided they do not expose or infringe upon proprietary internal designs or trade secrets.