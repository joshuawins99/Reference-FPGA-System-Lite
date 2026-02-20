# VELOCitE (Verilog Embedded LOgic Core Engine)

## What is it?
This is an FPGA Register System that contains a softcore RISC-V CPU that can communicate with a host computer or mcu. The system utilizes a simple UART for communication. The design intent was for this to be as easy to drop into a design as possible and provide a debug interface to interact with the FPGA using a computer with scripting.

## Compatibility
This project was aimed to provide compatibility across a wide range of FPGAs from various vendors. This has been tested on Artix7, Cyclone IV, Cyclone V, and ECP5 (Yosys w/sv2v) currently. Any tool with SystemVerilog/Verilog support "should" work with this system.

## Docs
* [Getting Started](./docs/getting_started.md)
* [Config File Format](./docs/config_file_format.md)
* [Generator Script Options](./docs/generator_script_options.md)
* [Custom Modules](./docs/custom_modules.md)
* [CDC Module](./docs/cdc_module.md)


## License
This project is licensed under the CERN Open Hardware Licence Version 2 - Weakly Reciprocal (CERN-OHL-W-2.0). See the [LICENSE](./LICENSE) file for details.

## Contribution Request
While this repository is licensed under the CERN-OHL-W license, I kindly ask — as a courtesy — that any fixes or improvements be contributed back to the upstream project, provided they do not expose or infringe upon proprietary internal designs or trade secrets.