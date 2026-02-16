# Generator Script Options
There are various options in order to configure the generator script. The list of options can be shown by providing ```--help`` to the script. The options are also shown below:
```
--help                                       Show this help message and exit
--build                                      Build CPU Code and create combined output sv
--configs-path CONFIGS_PATH                  Config directories path
--gen-headers GEN_HEADERS [GEN_HEADERS ...]  Generate header files. Options are: new-python, new-c, zig, verilog-muxes, verilog-regs, strip-verilog
--print-all-registers                        Prints all registers to console
--print-user-registers                       Prints user registers to console
--save-all-registers                         Saves all registers to a cpu_registers.txt file
--save-user-registers                        Saves user registers to a cpu_registers.txt file
```
## --build
Provides a way to build the code that runs on the cpu by the script itself. This build is the last step of the script process where all the dependencies are generated first. A ```build.sh``` file is required for the script to execute. The folder to use for the build is provided by the config file using ```Code_Folder :```. If not provided, the internal default will be used for building. The code provided is a good starting point for adding additional functionality.

## --configs-path
If the script isn't executed from within the folder where the cpu folder exists, the ```--configs-path``` can be provided to point to the relevant folder. This refers to the directory which contains the cpu folder with the config file.

## --gen-headers
Generates relevant header files based on options chosen. If ```--gen-headers``` is called with no arguments, the default Python and C headers are emitted. These are basic headers that provide some information for integration. Using ```new-c``` and ```new-python``` provide the richest hierarchy based options for integration and will be the updated versions moving forward. There are also Zig headers which can be generated with the ```zig``` option. This provides a similar layout to the ```new-c``` headers but for Zig. The ```verilog-muxes```, ```verilog-regs```, and ```strip-verilog``` provide packages and modules for automatic muxing and parameters for address offsets and register counts. Using ```strip-verilog``` just provides the name of the module itself while not using it uses the full hierarchical name of the module.

## Save and Print Registers
The ```--print-all-registers```, ```--save-all-registers```, ```--print-user-registers```, and ```--save-user-registers``` all provide similar functionality where the hierarchy with register names and addresses are provided either to the console or to a file. Using the user options just outputs the custom user registers, while all provides the builtin modules as well.