#!/usr/bin/env python3
import os
import re
import sys
import subprocess
import shutil

def list_folders(directory):
    """Returns a list of folders in the given directory."""
    if not os.path.exists(directory):
        raise ValueError(f"The directory '{directory}' does not exist.")

    return [f for f in os.listdir(directory) if os.path.isdir(os.path.join(directory, f))]

def check_config_files(directory):
    """Returns a dictionary indicating whether each folder contains a cpu_config.txt file."""
    folders = list_folders(directory)  # Getting the list of folders
    return {folder: os.path.exists(os.path.join(directory, folder, "cpu_config.txt")) for folder in folders}  # Corrected iteration

def parse_config(file_path):
    """Parses the cpu_config.txt file and returns a structured dictionary."""
    config_data = {}
    current_section = None

    with open(file_path, "r") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#"):  # Skip empty lines or comments
                continue

            # Match section headers
            #section_match = re.match(r"(\w+):", line)
            section_match = re.match(r"^(\w+):\s*(.*)?$", line)

            # Match parameters with optional bit-width
            param_match = re.match(r"(\w+)\s*:\s*(\"[^\"]+\"|[^\s:]+)(?:\s*:\s*\{(\d+:\d+)\})?", line)

            # Match module entries with flags and bounds
            module_match = re.match(r"(\w+)\s*:\s*(TRUE|FALSE)\s*:\s*\{([^}]+)\}", line)

            # Match AUTO keyword (e.g. AUTO : 4)
            auto_module_expr_match = re.match(r"(\w+)\s*:\s*(TRUE|FALSE)\s*:\s*AUTO\s*:\s*\{(.+?)\}", line)
            auto_module_literal_match = re.match(r"(\w+)\s*:\s*(TRUE|FALSE)\s*:\s*AUTO\s*:\s*(\d+)", line)

            if section_match:
                current_section = section_match.group(1)
                config_data.setdefault(current_section, {})
                remainder = section_match.group(2).strip() if section_match.group(2) else ""
                # If there's something after the colon, it's a BaseAddress
                if remainder:
                    config_data[current_section]["BaseAddress"] = remainder

            elif param_match and current_section in ["BUILTIN_PARAMETERS", "USER_PARAMETERS", "CONFIG_PARAMETERS"]:
                key = param_match.group(1)
                value = param_match.group(2).rstrip(",")
                bit_width = param_match.group(3)

                if bit_width:
                    config_data[current_section][key] = {
                        "value": value,
                        "bit_width": bit_width
                    }
                else:
                    config_data[current_section][key] = {
                        "value": value
                    }
            
            elif auto_module_expr_match and current_section in ["BUILTIN_MODULES", "USER_MODULES"]:
                key = auto_module_expr_match.group(1)
                flag = auto_module_expr_match.group(2)
                reg_count = auto_module_expr_match.group(3)
                config_data[current_section][key] = {
                    "flag": flag,
                    "auto": True,
                    "registers": reg_count
                }

            elif auto_module_literal_match and current_section in ["BUILTIN_MODULES", "USER_MODULES"]:
                key = auto_module_literal_match.group(1)
                flag = auto_module_literal_match.group(2)
                reg_count = int(auto_module_literal_match.group(3))
                config_data[current_section][key] = {
                    "flag": flag,
                    "auto": True,
                    "registers": reg_count
                }

            elif module_match and current_section in ["BUILTIN_MODULES", "USER_MODULES"]:
                key = module_match.group(1)
                flag = module_match.group(2)
                bounds = [b.strip().rstrip(",") for b in module_match.group(3).split(",")]
                config_data[current_section][key] = {
                    "flag": flag,
                    "bounds": bounds
                }

    return config_data

def process_configs(directory_path):
    """Processes all config files in multiple folders and returns parsed data without saving files."""
    parsed_configs = {}  # Store parsed configs for each folder

    for folder in os.listdir(directory_path):
        folder_path = os.path.join(directory_path, folder)
        config_path = os.path.join(folder_path, "cpu_config.txt")

        if os.path.isdir(folder_path) and os.path.exists(config_path):  # Ensure it's a valid folder with a config file
            parsed_configs[folder] = parse_config(config_path)  # Parse each folder’s config file

    return parsed_configs  # Returns parsed configs

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

        print(f"Generated and saved SystemVerilog package for {package_name}: {output_file}")

current_directory = os.path.dirname(os.path.abspath(__file__))

def update_cpu_modules_file(parsed_configs, base_directory, reference_file="ref_fpga_sys_lite.sv"):
    """Reads a reference SystemVerilog file, replaces import statements and updates bus logic based on enabled modules."""
    reference_file = os.path.join(current_directory, reference_file)
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

        print(f"Saved SystemVerilog Module file: {output_file}")

def get_c_code_folders(parsed_configs):
    """Extracts C_CODE_FOLDER values from the parsed configs if present."""
    c_folders = {}
    for cpu_name, config in parsed_configs.items():
        for section in ["CONFIG_PARAMETERS"]:
            params = config.get(section, {})
            folder_info = params.get("C_Code_Folder")
            if folder_info:
                c_folders[cpu_name] = folder_info["value"]
    return c_folders

def resolve_expression(expr, parameter_table=None):
    expr = str(expr).strip()

    # Convert SystemVerilog-style literals (e.g. 16'h4000, 8'd255, 32'b101010)
    def sv_number_to_python(match):
        raw = match.group(0)
        try:
            if "'" in raw:
                _, radix_value = raw.split("'")
                radix = radix_value[0].lower()
                value = radix_value[1:].replace("_", "")  # Remove underscores
                if radix == 'h':
                    return str(int(value, 16))
                elif radix == 'd':
                    return str(int(value, 10))
                elif radix == 'b':
                    return str(int(value, 2))
                elif radix == 'o':
                    return str(int(value, 8))
        except Exception:
            print(f"[WARN] Could not parse SV literal: {raw}")
        return raw  # fallback

    # Replace SV literals before parameter substitution
    expr = re.sub(r"\d*'[hdbonHDBON][0-9a-fA-F_]+", sv_number_to_python, expr)

    # Replace parameters using token-aware substitution
    if parameter_table:
        # Longer names first to prevent partial collisions
        for param in sorted(parameter_table.keys(), key=lambda p: -len(p)):
            val = str(parameter_table[param])
            expr = re.sub(rf"\b{re.escape(param)}\b", val, expr)

    # Evaluate arithmetic expression
    try:
        result = eval(expr, {"__builtins__": None}, {})
        return result
    except Exception:
        print(f"[WARN] Could not evaluate expression: {expr}")
        return None

def assign_auto_addresses(parsed_configs, alignment=4, reg_width_bytes=4):
    """
    Assigns memory addresses to modules with 'auto': True using BaseAddress and overlap avoidance.
    Handles symbolic expressions and scans forward from BaseAddress using proper masking.
    """

    def find_free_address(used_ranges, needed_size, start_from=0x0000):
        addr = (start_from + alignment - 1) & ~(alignment - 1)
        while True:
            end_addr = addr + needed_size - 1
            overlap = any(not (end_addr < s or addr > e) for s, e in used_ranges)
            if not overlap:
                return addr
            addr += alignment

    for cpu_name, cpu_config in parsed_configs.items():
        # Step 1: Build parameter table
        parameter_table = {}
        for param_section in ["BUILTIN_PARAMETERS", "USER_PARAMETERS"]:
            for name, data in cpu_config.get(param_section, {}).items():
                val = data.get("value")
                try:
                    parameter_table[name] = (
                        int(val.replace("'h", ""), 16)
                        if isinstance(val, str) and val.startswith("'h")
                        else int(val)
                    )
                except Exception:
                    continue

        global_mask = []  # Tracks all used address ranges globally

        # Step 2: Process sections independently
        for section_name in ["BUILTIN_MODULES", "USER_MODULES"]:
            section = cpu_config.get(section_name, {})
            if not isinstance(section, dict):
                continue

            # Step 3: Resolve section BaseAddress
            base_expr = section.get("BaseAddress")
            try:
                section_ptr = (
                    resolve_expression(base_expr, parameter_table)
                    if base_expr else 0x0000
                )
                section_ptr = (section_ptr + alignment - 1) & ~(alignment - 1)
            except Exception:
                print(f"[WARN] Could not resolve BaseAddress for {section_name}")
                section_ptr = 0x0000

            # Step 4: Build local address mask for this section
            local_mask = []
            for mod_name, mod in section.items():
                if mod_name == "BaseAddress" or not isinstance(mod, dict):
                    continue
                bounds = mod.get("bounds")
                if bounds and isinstance(bounds, list) and len(bounds) == 2:
                    try:
                        start = resolve_expression(bounds[0], parameter_table)
                        end = resolve_expression(bounds[1], parameter_table)
                        if start is not None and end is not None:
                            local_mask.append((start, end))
                            global_mask.append((start, end))
                        else:
                            print(f"[WARN] Skipping unresolved bounds for {mod_name}: {bounds}")
                    except Exception:
                        print(f"[WARN] Could not resolve bounds for {mod_name}: {bounds}")

            # Step 5: Assign auto modules
            for mod_name, mod in section.items():
                if mod_name == "BaseAddress" or not isinstance(mod, dict):
                    continue
                if mod.get("flag") == "TRUE" and mod.get("auto", False):
                    raw_reg_count = str(mod.pop("registers", None))
                    try:
                        reg_count = int(resolve_expression(raw_reg_count, parameter_table))
                    except Exception:
                        print(f"[WARN] Failed to resolve register count for {mod_name}")
                        continue

                    mod.pop("auto", None)
                    if reg_count < 1:
                        print(f"[WARN] Invalid register count for {mod_name}")
                        continue

                    needed_size = reg_count * reg_width_bytes
                    start_addr = find_free_address(global_mask + local_mask, needed_size, section_ptr)
                    end_addr = start_addr + (reg_count - 1) * reg_width_bytes

                    mod["bounds"] = [f"'h{start_addr:X}", f"'h{end_addr:X}"]

                    #print(f"\n[DEBUG] Attempting to assign '{mod_name}'")
                    #print(f"[DEBUG] Raw registers: {raw_reg_count}")
                    #print(f"[DEBUG] Resolved register count: {reg_count}")
                    #print(f"[DEBUG] Needed size: {needed_size}")
                    #print(f"[DEBUG] Starting from section BaseAddress: 0x{section_ptr:X}")
                    #print(f"[DEBUG] Global mask: {[f'{s:#06X}-{e:#06X}' for s, e in global_mask]}")
                    #print(f"[DEBUG] Local mask: {[f'{s:#06X}-{e:#06X}' for s, e in local_mask]}")

                    # Track new range
                    local_mask.append((start_addr, end_addr))
                    global_mask.append((start_addr, end_addr))
                    section_ptr = end_addr + 1
                    #print(f"[DEBUG] Assigned bounds for '{mod_name}': {mod['bounds']}")

            # Step 6: Clean up BaseAddress
            section.pop("BaseAddress", None)

def dump_all_registers_from_configs(parsed_configs, save_to_file=False, file_path="all_cpu_registers.txt", reg_width_bytes=4, user_modules_only=False):
    """
    Resolves symbolic expressions and dumps register addresses for all CPUs in parsed_configs.
    Skips inactive modules. Supports address expressions and optionally limits output to USER_MODULES.
    ASCII-only output.
    """

    lines = []
    lines.append("Register Address Map")
    lines.append("=" * 20)

    for cpu_name, cpu_config in parsed_configs.items():
        lines.append(f"\nCPU: {cpu_name}")

        # Build parameter lookup
        parameter_table = {}
        for section in ["BUILTIN_PARAMETERS", "USER_PARAMETERS"]:
            for param_name, param_data in cpu_config.get(section, {}).items():
                val = param_data.get("value")
                try:
                    if isinstance(val, str) and val.startswith("'h"):
                        parameter_table[param_name] = int(val.replace("'h", ""), 16)
                    else:
                        parameter_table[param_name] = int(val)
                except ValueError:
                    continue

        section_list = ["USER_MODULES"] if user_modules_only else ["BUILTIN_MODULES", "USER_MODULES"]

        for section in section_list:
            lines.append(f"  Section: {section}")
            for module_name, module in cpu_config.get(section, {}).items():

                if module_name == "BaseAddress":
                    continue  # Skip base directive

                if not isinstance(module, dict):
                    continue  # Skip anything malformed

                if module.get("flag") != "TRUE":
                    continue
                if "bounds" not in module:
                    lines.append(f"    Warning: {module_name} missing bounds")
                    continue

                try:
                    start_addr = resolve_expression(module["bounds"][0], parameter_table)
                    end_addr = resolve_expression(module["bounds"][1], parameter_table)
                except Exception as e:
                    lines.append(f"    Error in {module_name}: {e}")
                    continue

                reg_count = ((end_addr - start_addr) // reg_width_bytes) + 1
                lines.append(
                    f"    Module: {module_name} | {reg_count} registers | Bounds: 'h{start_addr:04X} to 'h{end_addr:04X}"
                )
                for i in range(reg_count):
                    reg_addr = start_addr + i * reg_width_bytes
                    lines.append(f"      Register {i} at address: 'h{reg_addr:04X}")

    output = "\n".join(lines)
    print(output)
    print("")

    if save_to_file:
        with open(file_path, "w") as f:
            f.write(output)
        print(f"\nRegister map saved to: {file_path}")

class CompactRegisterBlock:
    def __init__(self, base, count, address_wording):
        self.base = base
        self.count = count
        self.address_wording = address_wording

    def reg_at(self, index):
        return self.base + index * self.address_wording

def export_per_cpu_headers(parsed_configs, reg_width_bytes=4, user_modules_only=False):
    """
    Generates both C-style headers and Python register map files per CPU.
    Each output includes CompactRegisterBlock definitions and register constants.
    """

    def resolve_expression(expr, parameter_table):
        expr = expr.strip().replace("'h", "0x")
        for param, val in parameter_table.items():
            expr = expr.replace(param, str(val))
        return eval(expr, {"__builtins__": None}, {})

    for cpu_name, cpu_config in parsed_configs.items():
        output_dir = cpu_name
        os.makedirs(output_dir, exist_ok=True)

        c_filename = os.path.join(output_dir, f"{cpu_name}_registers.h")
        py_filename = os.path.join(output_dir, f"{cpu_name}_registers.py")

        c_lines = []
        py_lines = []

        # C header boilerplate
        c_lines.append("// Auto-generated register map header")
        c_lines.append("#pragma once\n")
        c_lines.append("#include <stdint.h>\n")
        c_lines.append("typedef struct {")
        c_lines.append("    uintptr_t base;")
        c_lines.append("    size_t count;")
        c_lines.append("    size_t address_wording;")
        c_lines.append("} CompactRegisterBlock;\n")
        c_lines.append("#define REG_AT(block, index) ((uintptr_t)((block).base + (index) * (block).address_wording))\n")

        # Python boilerplate
        py_lines.append("# Auto-generated register map header\n")
        py_lines.append("class CompactRegisterBlock:")
        py_lines.append("    def __init__(self, base, count, address_wording):")
        py_lines.append("        self.base = base")
        py_lines.append("        self.count = count")
        py_lines.append("        self.address_wording = address_wording\n")
        py_lines.append("    def reg_at(self, index):")
        py_lines.append("        return self.base + index * self.address_wording\n")

        # Extract parameters
        parameter_table = {}
        for section in ["BUILTIN_PARAMETERS", "USER_PARAMETERS"]:
            for param_name, param_data in cpu_config.get(section, {}).items():
                val = param_data.get("value")
                try:
                    parameter_table[param_name] = int(val.replace("'h", ""), 16) if isinstance(val, str) and val.startswith("'h") else int(val)
                except ValueError:
                    continue

        module_sections = ["USER_MODULES"] if user_modules_only else ["BUILTIN_MODULES", "USER_MODULES"]

        for section in module_sections:
            for module_name, module in cpu_config.get(section, {}).items():
                if module_name == "BaseAddress" or not isinstance(module, dict):
                    continue
                if module.get("flag") != "TRUE" or "bounds" not in module:
                    continue

                try:
                    start_addr = resolve_expression(module["bounds"][0], parameter_table)
                    end_addr = resolve_expression(module["bounds"][1], parameter_table)
                except Exception:
                    continue

                reg_count = ((end_addr - start_addr) // reg_width_bytes) + 1
                module_id = module_name.upper()

                # C macros
                for i in range(reg_count):
                    addr = start_addr + i * reg_width_bytes
                    c_lines.append(f"#define {module_id}_REG{i} 0x{addr:04X}")
                c_lines.append(f"CompactRegisterBlock {module_id} = {{ 0x{start_addr:04X}, {reg_count}, {reg_width_bytes} }};\n")

                # Python constants
                for i in range(reg_count):
                    addr = start_addr + i * reg_width_bytes
                    py_lines.append(f"{module_id}_REG{i} = 0x{addr:04X}")
                py_lines.append(f"{module_id} = CompactRegisterBlock(0x{start_addr:04X}, {reg_count}, {reg_width_bytes})\n")

        with open(c_filename, "w") as f:
            f.write("\n".join(c_lines))
        print(f"C header saved: {c_filename}")

        with open(py_filename, "w") as f:
            f.write("\n".join(py_lines))
        print(f"Python header saved: {py_filename}\n")

directory_path = "."
build_script = "build_single_module.sh"

#folders = list_folders(directory_path)
#print(folders)

config_files = check_config_files(directory_path)
#print(config_files)

filtered_dirs = [dir_name for dir_name in config_files if config_files.get(dir_name)]
#print(filtered_dirs)

parsed_configs = process_configs(directory_path)
#print(parsed_configs)
assign_auto_addresses(parsed_configs)
#print(parsed_configs)

if "--print-all-registers" in sys.argv:
    dump_all_registers_from_configs(parsed_configs,user_modules_only=False)

if "--print-user-registers" in sys.argv:
    dump_all_registers_from_configs(parsed_configs,user_modules_only=True)

if "--gen-headers" in sys.argv:
    export_per_cpu_headers(parsed_configs,user_modules_only=False)

c_code_folders = get_c_code_folders(parsed_configs)
#print(c_code_folders)

default_c_code_path = "C_Code"  #Default Folder

if "--build" in sys.argv:
    absolute_path = os.path.abspath(".")
    for cpu_name in filtered_dirs:
        config_folder = c_code_folders.get(cpu_name)
        build_folder = (
            os.path.join(absolute_path, cpu_name, config_folder)
            if config_folder
            else os.path.join(directory_path, default_c_code_path)
        )
        parent_directory = os.path.dirname(current_directory)
        print(f"Running build for {cpu_name} using C Code folder: {build_folder}\n")
        try:
            if "--gen-headers" in sys.argv:
                if os.path.exists(f"{build_folder}/{cpu_name}_registers.h"):
                    os.remove(f"{build_folder}/{cpu_name}_registers.h")
                print(f"Moved header {cpu_name}/{cpu_name}_registers.h to {build_folder}\n")
                shutil.move(f"{cpu_name}/{cpu_name}_registers.h", build_folder)
            result = subprocess.run(["bash", build_script, "--c-folder", build_folder], cwd=parent_directory, capture_output=True, text=True)
            print(result.stdout + result.stderr)
        except FileNotFoundError:
            print(f"Build folder not found for {cpu_name}: {build_folder}")

        curr_config_dict = {cpu_name: parsed_configs.get(cpu_name)}
        save_systemverilog_files(curr_config_dict, directory_path)
        update_cpu_modules_file(curr_config_dict, directory_path, reference_file="../ref_fpga_sys_lite.sv")
        subprocess.run(["bash", "-c", "git clean -fdx"], cwd=parent_directory, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

else:
    save_systemverilog_files(parsed_configs, directory_path)
    update_cpu_modules_file(parsed_configs, directory_path)


#systemverilog_output = generate_systemverilog(parsed_configs)
#print(systemverilog_output)
