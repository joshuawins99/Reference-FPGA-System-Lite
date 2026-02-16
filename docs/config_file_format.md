# Config File Format
Refer to [Getting Started](./getting_started.md) for basic overview of file format. This document covers specifics in how the format works.

## Parameters
Parameters can be configured a number of ways:
* A path (CONFIG_PARAMETERS): 
    * ```Folder : ../../path_to_folder```
* Normal Parameter: 
    * ```NumObjects : 72```
* Using Verilog syntax:
    * ```Address : 'h4000 or 'd, 'b, 'o```
* With a bit width:
    * ```BitMask : 'h80 : {15:0}```

## Module Blocks
USER_MODULES can optionally have a base address eg. USER_MODULES: 'h9000

## Module Instantiations
Module instantiations have a few modes they can be instantiated with:
* Using defined address bounds:
    * ```my_module_e : TRUE: {'h9000, 'h900C}```
* Using defined address bounds with expressions:
    * ```version_string_e : TRUE : {'h8000, 'h8000+(VersionStringSize-1)*4}```
* Using AUTO and a register count literal:
    * ```my_module_e : TRUE : AUTO : 3```
* Using AUTO and an expression:
    * ```my_module_e : TRUE : AUTO : {myModuleRegCount}```
* Using AUTO and no literal or expression (requires Module_Include to read registers):
    * ```my_module_e : TRUE : AUTO```

Module instantiations require either TRUE or FALSE as part of the second argument. This indicates on whether it should be included in the system. Setting to FALSE effectively disables it.

Optionally, a ```NOEXPREGS``` can be added if the desire is to treat the group as a block of memory with no distinct registers that is used like this: ```my_module_e : TRUE : AUTO : NOEXPREGS```

## Registers, Names, Descriptions, and Permissions
Every module and register can have a name and description. Registers can also have a permissions entry. These provide data to the system in order to automatically assign addresses and to generate rich headers with the names and descriptions included. An example is shown here:
```
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
```
A ```Description :``` field can also be escaped by a ```\``` to make it multiline. Permissions can be of type: ```Read, Read/Write, and Write```. Each register entry follows the ```Regx :``` standard. Each ```Reg :``` must have a number after it as this corresponds to the order.

## Fields
A register can have one or more fields that slice the register into multiple sub registers that correspond to a bit range. These follow the normal Verilog convention of [msb:lsb] and are used like this with the ```Bounds :``` keyword:
```
Reg0 :
    Name : Test Register
    Description : A register description
    Field0 :
        Name : First 3 bits
        Description : First 3 desc line 1 \
        line 2
        Bounds : [2:0]
    Field1 :
        Name : Next 2 bits
        Bounds : [4:3]
```
These will be used in the ```new-python``` option of the header generation where it will perform a read/modify/write operation on the register to just read or write to those specific bits in the register. Fields can also have a dedicated name and desciption associated with them as well.

## Module_Include
The ```Module_Include``` keyword is used to define a file in which register metadata resides. This data has a form that looks like this. This can also be inlined right into the module instantiation as Module_Include just inlines this into the parser anyways.

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

* Example:
```
my_module_e : TRUE : AUTO
    Module_Include : file.sv      
```
This effectively expands to:
```
my_module_e : TRUE : AUTO 
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
```
The CONFIG_PARAMETERS folder path can also be used like this:
```
my_module_e : TRUE : AUTO
    Module_Include : {Folder}/file.sv
```
The data from file.sv will be searched for the ```@ModuleMetadataBegin``` and ```@ModuleMetadataEnd``` keywords. This tells the parser what to inline.

## Repeat
The ```Repeat :``` keyword is used to allow multiple instantiations of the same module without manually typing out each instance. A ```Repeat : 1``` means instantiate the original module and also create a second one. Repeat modules follow the convention of {original module_name}_{repeat number}.
```
my_module_e : TRUE : AUTO
    Repeat : 2
    Module_Include : {Folder}/file.sv
```
In this example, ```my_module_e```, ```my_module_e_1```, and ```my_module_e_2``` will be created.

## Submodules
Submodules are a module that is contained within another module. This makes nesting possible and allows for contiguous address allocation of an entire hierarchy. This used in conjunction with the ```verilog-muxes``` option in ```--gen-headers``` provides automatic muxes in order to make submodules parametric and address independent. An example of using a submodule is shown here using the ```SUBMODULE:``` keyword.
```
USER_MODULES:
    timer_e : TRUE : AUTO
        Module_Include : {REF_PATH}/rtl/timer_cpu.sv
        SUBMODULE:
            dac_e : TRUE : AUTO
                Name : DAC SPI Controller
                Description : SPI Master for Controlling DAC
                Module_Include : {REF_PATH}/rtl/dac_controller.sv
                SUBMODULE:
                    spi_e : TRUE : AUTO
                        Module_Include : {REF_PATH}/rtl/spi.sv
```
Submodules can be any n levels deep and proper indentation must be followed. The parser will error if the indentation is incorrect.