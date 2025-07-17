# Reference-FPGA-System-Lite

For the full system: https://github.com/joshuawins99/Reference-FPGA-System

## What is it?
This is an FPGA Register System that contains a softcore RISC-V CPU that can communicate with a host computer or mcu. The system utilizes a simple UART for communication.

## Compatibility
This project was aimed to provide compatibility across a wide range of FPGAs from various vendors. This has stemmed from the full system project which has been tested on a variety of FPGAs. Any tool with SystemVerilog/Verilog support "should" work with this system.

## Building
There are a few requirements for building this system:
* Bash
* Python 3
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
#Manually placed register locations can also be placed at the same time
#Place extra modules not included by default in USER_MODULES

CONFIG_PARAMETERS:
    #C_Code_Folder : C_Code

BUILTIN_PARAMETERS:
    FPGAClkSpeed : 40000000,
    BaudRateCPU : 230400,
    address_width : 16,
    data_width : 32,
    RAM_Size : 10240,
    Program_CPU_Start_Address : 'h0 : {31:0},
    VersionStringSize : 64,
    EnableCPUIRQ : 0
    
USER_PARAMETERS:
    
BUILTIN_MODULES:
    ram_e : TRUE : {0, RAM_Size},
    version_string_e : TRUE : {'h8000, 'h8000+(VersionStringSize-1)*4},
    io_e : TRUE : {'h9000, 'h900C},
    uart_e : TRUE : {'h9100, 'h9110}
    
USER_MODULES:
```

Run the python script to generate the module and package file:
```bash
python3 generate_cpu_instance.py
```
Optionally, under the CONFIG_PARAMETERS section is the C_Code_Folder variable. This variable is used when running the generate_cpu_instance.py script with the ``--build`` flag. This allows the python script to both build and place the output files in the correct directory. Multiple unique instances of this system can be used in a single project easily this way. This option will call the build_single_module.sh for each instance of config file automatically so the script itself doesn't have to be run if using it this way.

There are three more flags as part of generate_cpu_instance.py:
    ``--print-all-registers`` -> prints all the registers and their addresses to console
    ``--print-user-registers`` -> prints only the user registers to console
    ``--gen-headers`` -> generates C and Python headers for use in a program 

An example instantiation of the module is as follows. The package name will be {folder name}_package, the top level instantiation will be {folder name}_top, and the interface will be {folder name}_bus_rv32:
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
## Adding Additional Functionality

By creating a new custom module that follows the port structure of the bus_rv32 interface, one can create an accessory module that has custom functionality and can be accessed by the cpu. In order to add a new module, an additional entry must be added to the USER_MODULES list in the cpu_config.txt file and a start and end address must be given to the mdoule. Data reads from custom modules are expected to have their data available one clock cycle after the accompanying address is given. If a combinatorial output is desired, use of the address_reg logic ensures that data is valid when the CPU expects it.

The host side is up to the specfic use case. Anything that supports a UART type device can be used for communication. Three commands are available for communication: rFPGA (read a register from the FPGA), wFPGA (write a value to a register in the FPGA), and readFPGAVersion (reports the build time and version of the FPGA build running). 

## Clock Domain Crossing
A clock domain crossing bridge has been added in order to facilitate the use of modules on different clock domains. An example of using this module can be seen below.
```Verilog
logic cdc_clocks [num_entries];

assign cdc_clocks[user_module_1_e] = clk_30; //One clock
assign cdc_clocks[user_module_2_e] = clk_100; //Another Clock

cpu_test_bus_rv32 cdc_cpubus [num_entries]();

cpu_test_bus_cdc #(
    .bus_cdc_start_address (get_address_start(user_module_1_e)),
    .bus_cdc_end_address   (get_address_end(user_module_2_e))
) cdc_1 (
    .cdc_clks_i            (cdc_clocks),
    .cpubus_i              (cpubus),
    .cpubus_o              (cdc_cpubus)
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
    .rd_wr_i       (cdc_cpubus[user_module_2_e].we_o)
);
```
Modules are still expected to have valid data on a read one cycle after the address is valid. These modules follow exactly the same behavior as ones that would in the same clock domain. The bus_cdc module will actively halt the cpu automatically to wait for the read data from the downstream modules to be valid. The bus_cdc_start_address and bus_cdc_end_address represent the bounds to reserve for cdc modules. It is recommended to use the get_address_start() and get_address_end() functions with the first and last enumeration to get the desired results.