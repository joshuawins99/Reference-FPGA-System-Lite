import os
import re

def generate_systemverilog(config):
    """Generates a complete SystemVerilog package including parameters, modules, addresses, and functions."""
    module_entries = []
    address_entries = []
    parameter_entries = []

    # Automatically get the top-level key (package name)
    package_base_name = next(iter(config))  # Dynamically selects the first key (e.g., "cpu1")
    package_name = f"{package_base_name}_package"  # Append _package to the name
    builtin_modules = config[package_base_name].get("BUILTIN_MODULES", {})
    user_modules = config[package_base_name].get("USER_MODULES", {})
    builtin_parameters = config[package_base_name].get("BUILTIN_PARAMETERS", {})
    user_parameters = config[package_base_name].get("USER_PARAMETERS", {})

    # Combine module lists to ensure commas are placed correctly
    all_modules = {**builtin_modules, **user_modules}
    module_list = [
        module
        for module, data in all_modules.items()
        if isinstance(data, dict) and data.get("flag") == "TRUE"
    ]

    # Generate module bus enumeration with an extra comma before num_entries
    for module in module_list:
        module_entries.append(f"        {module},")

    if module_entries:  # Ensure the last entry also has a comma before num_entries
        module_entries[-1] = module_entries[-1].replace(",", ",")  # Redundant step, but ensures clarity

    module_entries.append("        num_entries")  # num_entries should have no trailing comma

    # Generate localparams for BUILTIN_PARAMETERS and USER_PARAMETERS with optional bit-width
    for param_section in [builtin_parameters, user_parameters]:
        for param, details in param_section.items():
            param_value = details["value"]  # Extract actual parameter value
            bit_width = details.get("bit_width")  # Extract optional bit-width

            if bit_width:
                parameter_entries.append(f"    localparam logic [{bit_width}] {param:<30} = {param_value};")
            else:
                parameter_entries.append(f"    localparam              {param:<30} = {param_value};")

    # Generate module addresses for BUILTIN_MODULES and USER_MODULES
    for i, module in enumerate(module_list):
        details = all_modules[module]
        comma = "," if i < len(module_list) - 1 else ""  # Add comma except last entry
        address_entries.append(f"        add_address({details['bounds'][0]}, {details['bounds'][1]}){comma} // {module}")

    module_enum = "\n".join(module_entries)
    module_addresses = "\n".join(address_entries)
    parameters = "\n".join(parameter_entries)

    systemverilog_code = f"""
package {package_name};

{parameters}

    function [(2*address_width)-1:0] add_address (
        input logic [address_width-1:0] start_address,
        input logic [address_width-1:0] end_address
    );
        begin
            add_address[address_width-1:0] = end_address;
            add_address[2*address_width-1:address_width] = start_address;
        end
    endfunction

    //Enter a new enumeration for every new module added to the bus
    typedef enum {{
{module_enum}
    }} module_bus;

    //Each enumeration gets a start and end address with the start address on the left and the end address on the right
    localparam [2*(address_width*num_entries)-1:0] module_addresses = {{
{module_addresses}
    }};

    function [address_width-1:0] get_address_start (
        input [$clog2(num_entries):0] val
    );
        begin
            get_address_start = module_addresses[(2*((num_entries-1)-val)+1)*address_width +: address_width];
        end
    endfunction

    function [address_width-1:0] get_address_end (
        input [$clog2(num_entries):0] val
    );
        begin
            get_address_end = module_addresses[(2*((num_entries-1)-val))*address_width +: address_width];
        end
    endfunction

    function [address_width-1:0] get_address_mux (
        input [$clog2(num_entries):0] val
    );
        begin
            get_address_mux = module_addresses[val*address_width +: address_width];
        end
    endfunction

    typedef logic [data_width-1:0] data_reg_inputs_t [0:num_entries-1];

endpackage
    """

    return systemverilog_code.strip()

def save_systemverilog_files(parsed_configs, base_directory):
    """Loops through parsed configs and saves corresponding SystemVerilog files."""
    for package_base_name, config in parsed_configs.items():
        package_name = f"{package_base_name}_package"  # Append _package to the name

        if not config:  # Skip empty configs
            print(f"Warning: No data found for {package_base_name}. Skipping.")
            continue

        systemverilog_output = generate_systemverilog({package_base_name: config})

        # Define the output file path inside the respective package directory
        folder_path = os.path.join(base_directory, package_base_name)  # Folder remains original
        output_file = os.path.join(folder_path, f"{package_name}.sv")  # Append _package to filename

        os.makedirs(folder_path, exist_ok=True)

        with open(output_file, "w") as file:
            file.write(systemverilog_output)

        print(f"Generated and saved SystemVerilog package for {package_name}: {os.path.abspath(output_file)}")

def update_cpu_modules_file(parsed_configs, base_directory, reference_file="ref_fpga_sys_lite.sv"):
    """Reads a reference SystemVerilog file, replaces import statements and updates bus logic based on enabled modules."""
    #current_directory = os.path.dirname(os.path.abspath(__file__))
    #reference_file = os.path.join(current_directory, reference_file)
    if not os.path.exists(reference_file):
        print(f"Error: Reference file '{reference_file}' not found.")
        return

    # Read the reference file content
    with open(reference_file, "r") as file:
        ref_content = file.read()

    for package_base_name, config in parsed_configs.items():
        modified_package_name = f"{package_base_name}_package"  # Append _package to the name

        # Replace import statement with the modified package name
        updated_content = ref_content.replace("import cpu_reg_package::*;", f"import {modified_package_name}::*;")

        updated_content = re.sub(r"\bmodule main_rv32\b", f"module {package_base_name}_top", updated_content)

        MODULES_LIST = {
            "cpu_rv32",
            "bram_contained_rv32",
            "version_string",
            "uart_cpu",
            "io_cpu", 
            "picorv32*",
            "picosoc_mem",
            "async_fifo",
            "sync_r2w",
            "sync_w2r",
            "sync_ptr",
            "wptr_full",
            "fifomem",
            "rptr_empty",
            "uart_tx",
            "uart_rx",
            "uart_parity",
            "uart_clk_div",
            "uart_debouncer",
            "bus_rv32",
            "bus_cdc_bridge",
            "edge_synchronizer",
            "bus_cdc"
        }

        for module_pattern in MODULES_LIST:
            if "*" in module_pattern:
                base_pattern = module_pattern.replace("*", "")  # Remove '*'
                
                # Match any word containing the base pattern
                updated_content = re.sub(rf"\b(\w*{base_pattern}\w*)\b", package_base_name + "_" + r"\1", updated_content)
            else:
                # Standard replacement for exact matches
                updated_content = re.sub(rf"\b{module_pattern}\b", f"{package_base_name}_{module_pattern}", updated_content)

        # Also replace the package declaration inside the file
        updated_content = updated_content.replace(f"package {package_base_name};", f"package {modified_package_name};")

        # Identify the last enabled built-in module
        builtin_modules = config.get("BUILTIN_MODULES", {})
        enabled_modules = [module for module, details in builtin_modules.items() if details["flag"] == "TRUE"]

        if enabled_modules:
            last_enabled_module = enabled_modules[-1]
            updated_content = updated_content.replace("for (int i = 0; i <= uart_e;", f"for (int i = 0; i <= {last_enabled_module};")
            updated_content = updated_content.replace("for (int i = uart_e+1;", f"for (int i = {last_enabled_module}+1;")
        else:
            # No built-in modules enabled, comment out the first loop entirely
            updated_content = updated_content.replace(
                "        for (int i = 0; i <= uart_e; i++) begin\n" +
                "            data_reg_inputs_combined[i] = data_reg_inputs[i];\n" +
                "        end",
                "//         for (int i = 0; i <= uart_e; i++) begin\n" +
                "//             data_reg_inputs_combined[i] = data_reg_inputs[i];\n" +
                "//         end"
            )
            
            # Adjust the second loop to start at i = 0
            updated_content = updated_content.replace("for (int i = uart_e+1;", "for (int i = 0;")  

        # Comment out the entire instantiation block if the module is disabled
        # Define a mapping of module identifiers to their actual module names
        MODULE_NAME_MAPPING = {
            "uart_e"          : "uart_cpu",
            "io_e"            : "io_cpu",
            "version_string_e": "version_string",
            "ram_e"           : "bram_contained_rv32"
        }

        for module, details in builtin_modules.items():
            if details["flag"] == "FALSE":
                # Lookup the correct module name from the dictionary, fallback to default if missing
                module_name = package_base_name + "_" + MODULE_NAME_MAPPING.get(module, module)  # If not in mapping, keep original

                # Updated regex pattern to match only the correct module instantiation block
                pattern = rf"{module_name}\s*#\([\s\S]*?\)\s*;"

                # Apply the comment transformation (only on the first occurrence)
                updated_content = re.sub(pattern, lambda match: "\n".join(["// " + line for line in match.group(0).split("\n")]), updated_content, flags=re.DOTALL, count=1)


        # Define output file path inside the respective package directory
        folder_path = os.path.join(base_directory, package_base_name)  # Keep original folder name
        output_file = os.path.join(folder_path, f"{package_base_name}_fpga_sys_lite.sv")  # Append _fpga_sys_lite

        os.makedirs(folder_path, exist_ok=True)

        with open(output_file, "w") as file:
            file.write(updated_content)

        print(f"Saved SystemVerilog Module file: {os.path.abspath(output_file)}")