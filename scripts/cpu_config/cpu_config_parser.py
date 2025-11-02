import os
import re

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

def list_folders(directory):
    """Returns a list of folders in the given directory."""
    if not os.path.exists(directory):
        raise ValueError(f"The directory '{directory}' does not exist.")

    return [f for f in os.listdir(directory) if os.path.isdir(os.path.join(directory, f))]

def check_config_files(directory, config_file_names):
    """Returns a dictionary indicating whether each folder contains any acceptable config file."""
    folders = list_folders(directory)

    return {
        folder: any(
            os.path.exists(os.path.join(directory, folder, name))
            for name in config_file_names
        )
        for folder in folders
    }

def scrape_metadata(file_path, include_file, config_file_lines, current_line_index, has_name, has_description):
    current_path = os.path.join(os.path.dirname(file_path), include_file)
    inside_metadata = False
    metadata_block = []
    inside_register = False
    filtered_block = []

    with open(current_path, "r") as file:
        for line in file:
            if "@ModuleMetadataBegin" in line:
                inside_metadata = True
                continue
            elif "@ModuleMetadataEnd" in line:
                inside_metadata = False
                break
            if inside_metadata:
                metadata_block.append(line)

    for line in metadata_block:
        if re.match(r"(Reg\d+)\s*:", line):
            inside_register = True
        if not inside_register:
            if has_name and re.match(r"Name\s*:\s*(.+)", line):
                continue
            if has_description and re.match(r"Description\s*:\s*(.+)", line):
                continue
        filtered_block.append(line)

    for i in range(len(filtered_block)):
        config_file_lines.insert(current_line_index+i, filtered_block[i])

def parse_config(file_path):
    """Parses the cpu_config.txt file and returns a structured dictionary, including metadata and multiline support."""
    config_data = {}
    current_section = None
    current_module = None
    current_register = None
    pending_key = None
    pending_value = ""
    current_line_index = 0
    got_register_name = False
    got_register_description = False
    infer_module_registers = {}


    with open(file_path, "r") as file:
        config_file_lines = file.readlines()

    for raw_line in config_file_lines:
        current_line_index = current_line_index + 1
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        # Handle multiline continuation
        if pending_key:
            if line.endswith("\\"):
                pending_value += "\n " + line.rstrip("\\").strip()
                continue
            else:
                pending_value += "\n " + line.strip()
                # Finalize the pending value
                if current_register and (not got_register_description or not got_register_name):
                    config_data[current_section][current_module]["regs"][current_register][pending_key] = pending_value.strip()
                    if pending_key == "description":
                        got_register_description = True
                    if pending_key == "name":
                        got_register_name = True
                else:
                    config_data[current_section][current_module]["metadata"][pending_key] = pending_value.strip()
                pending_key = None
                pending_value = ""
                continue

        # Pattern matching
        section_match = re.match(r"^(\w+):\s*(.*)?$", line)
        #param_match = re.match(r"(\w+)\s*:\s*(\"[^\"]+\"|[^\s:]+)(?:\s*:\s*\{(\d+:\d+)\})?", line)
        param_match = re.match(r"(\w+)\s*:\s*(\"[^\"]+\"|\{[^}]+\}|[^\s:]+)(?:\s*:\s*\{(\d+:\d+)\})?", line)
        module_match = re.match(r"(\w+)\s*:\s*(TRUE|FALSE)\s*:\s*\{([^}]+)\}(?:\s*:\s*(\w+))?", line)
        auto_expr_match = re.match(r"(\w+)\s*:\s*(TRUE|FALSE)\s*:\s*AUTO\s*:\s*\{(.+?)\}(?:\s*:\s*(\w+))?", line)
        auto_literal_match = re.match(r"(\w+)\s*:\s*(TRUE|FALSE)\s*:\s*AUTO\s*:\s*(\d+)(?:\s*:\s*(\w+))?", line)
        auto_simple_match = re.match(r"(\w+)\s*:\s*(TRUE|FALSE)\s*:\s*AUTO(?:\s*:\s*(\w+))?", line)

        reg_match = re.match(r"(Reg\d+)\s*:", line)
        name_match = re.match(r"Name\s*:\s*(.+)", line)
        desc_match = re.match(r"Description\s*:\s*(.+)", line)
        permissions_match = re.match(r"Permissions\s*:\s*(.+)", line)
        module_include_match = re.match(r"Module_Include\s*:\s*(.+)", line)

        if section_match:
            current_section = section_match.group(1)
            config_data.setdefault(current_section, {})
            current_module = None
            current_register = None
            remainder = section_match.group(2).strip() if section_match.group(2) else ""
            if remainder:
                config_data[current_section]["BaseAddress"] = remainder

        elif param_match and current_section in ["BUILTIN_PARAMETERS", "USER_PARAMETERS", "CONFIG_PARAMETERS"]:
            key = param_match.group(1)
            value = param_match.group(2).rstrip(",")
            bit_width = param_match.group(3)
            if value.startswith("{") and value.endswith("}"):
                config_data[current_section][key] = {"value": value[1:-1].strip()}
            else:
                config_data[current_section][key] = {"value": value}
                
            if bit_width:
                config_data[current_section][key]["bit_width"] = bit_width

        elif auto_expr_match and current_section in ["BUILTIN_MODULES", "USER_MODULES"]:
            key = auto_expr_match.group(1)
            flag = auto_expr_match.group(2)
            reg_count = auto_expr_match.group(3)
            expand_regs = auto_expr_match.group(4)
            got_register_name = False
            got_register_description = False
            
            config_data[current_section][key] = {
                "flag": flag,
                "auto": True,
                "registers": reg_count,
                "metadata": {},
                "regs": {},
                "include_file" : {}
            }

            if (expand_regs == "NOEXPREGS"):
                config_data[current_section][key]["metadata"]["expand_regs"] = 'TRUE'
            else:
                config_data[current_section][key]["metadata"]["expand_regs"] = 'FALSE'
            current_module = key
            current_register = None

        elif auto_literal_match and current_section in ["BUILTIN_MODULES", "USER_MODULES"]:
            key = auto_literal_match.group(1)
            flag = auto_literal_match.group(2)
            reg_count = int(auto_literal_match.group(3))
            expand_regs = auto_literal_match.group(4)
            got_register_name = False
            got_register_description = False

            config_data[current_section][key] = {
                "flag": flag,
                "auto": True,
                "registers": reg_count,
                "metadata": {},
                "regs": {},
                "include_file" : {}
            }
            
            if (expand_regs == "NOEXPREGS"):
                config_data[current_section][key]["metadata"]["expand_regs"] = 'TRUE'
            else:
                config_data[current_section][key]["metadata"]["expand_regs"] = 'FALSE'
            current_module = key
            current_register = None

        elif auto_simple_match and current_section in ["BUILTIN_MODULES", "USER_MODULES"]:
            key = auto_simple_match.group(1)
            flag = auto_simple_match.group(2)
            expand_regs = auto_simple_match.group(3)
            got_register_name = False
            got_register_description = False

            config_data[current_section][key] = {
                "flag": flag,
                "auto": True,
                "registers": None,  #Will be inferred later
                "metadata": {},
                "regs": {},
                "include_file": {}
            }

            if expand_regs == "NOEXPREGS":
                config_data[current_section][key]["metadata"]["expand_regs"] = 'TRUE'
            else:
                config_data[current_section][key]["metadata"]["expand_regs"] = 'FALSE'
            current_module = key
            current_register = None
            infer_module_registers[current_module] = 0

        elif module_match and current_section in ["BUILTIN_MODULES", "USER_MODULES"]:
            key = module_match.group(1)
            flag = module_match.group(2)
            bounds = [b.strip().rstrip(",") for b in module_match.group(3).split(",")]
            expand_regs = module_match.group(4)
            got_register_name = False
            got_register_description = False

            config_data[current_section][key] = {
                "flag": flag,
                "bounds": bounds,
                "metadata": {},
                "regs": {},
                "include_file" : {}
            }

            if (expand_regs == "NOEXPREGS"):
                config_data[current_section][key]["metadata"]["expand_regs"] = 'TRUE'
            else:
                config_data[current_section][key]["metadata"]["expand_regs"] = 'FALSE'
            current_module = key
            current_register = None

        elif current_module and module_include_match:
            if (current_register == None):
                include_file = module_include_match.group(1)
                existing_metadata = config_data[current_section][current_module]["metadata"]
                has_name = "name" in existing_metadata
                has_description = "description" in existing_metadata
                scrape_metadata(file_path, include_file, config_file_lines, current_line_index, has_name, has_description)
            else:
                raise ValueError(f"Registers Defined and Module Include Specified in Entry: '{current_module}'")
            
        elif current_module and reg_match:
            got_register_name = False
            got_register_description = False
            current_register = reg_match.group(1)
            if current_register in config_data[current_section][current_module]["regs"]:
                raise ValueError(f"Register '{current_register}' Redefinition in Entry: '{current_module}'")
            config_data[current_section][current_module]["regs"].setdefault(current_register, {})
            if current_module in infer_module_registers:
                infer_module_registers[current_module] += 1

        elif current_module and name_match:
            name_val = name_match.group(1)
            if current_register and not got_register_name:
                config_data[current_section][current_module]["regs"][current_register]["name"] = name_val
                got_register_name = True
            else:
                config_data[current_section][current_module]["metadata"]["name"] = name_val

        elif current_module and desc_match:
            desc_val = desc_match.group(1)
            if desc_val.endswith("\\"):
                pending_key = "description"
                pending_value = desc_val.rstrip("\\").strip()
            else:
                if current_register and not got_register_description:
                    config_data[current_section][current_module]["regs"][current_register]["description"] = desc_val.strip()
                    got_register_description = True
                else:
                    config_data[current_section][current_module]["metadata"]["description"] = desc_val.strip()

        elif current_module and permissions_match:
            perm_val = permissions_match.group(1).strip().lower()
            if perm_val in ["r", "read"]:
                new_perm_val = "R"
            elif perm_val in ["w", "write"]:
                new_perm_val = "W"
            elif perm_val in ["rw", "read/write", "write/read"]:
                new_perm_val = "R/W"
            else:
                new_perm_val = "UNKNOWN"
                raise ValueError(f"Unknown permission string encountered: '{perm_val}'")
            if current_register:
                config_data[current_section][current_module]["regs"][current_register]["permissions"] = new_perm_val

    #Populate Register Count for AUTO Inferred Registers
    for mod, count in infer_module_registers.items():
        if count > 0:
            config_data[current_section][mod]["registers"] = count

    return config_data

def process_configs(directory_path, config_file_names):
    """Processes config files in multiple folders and returns parsed data without saving files."""
    parsed_configs = {}

    for folder in os.listdir(directory_path):
        folder_path = os.path.join(directory_path, folder)
        config_path = None
        if not os.path.isdir(folder_path):
            continue  # Skip files; only process directories
        for name in config_file_names:
            potential_path = os.path.join(folder_path, name)
            if os.path.exists(potential_path):
                config_path = potential_path
                break  # Found a valid config file—no need to keep checking
        if config_path:
            parsed_configs[folder] = parse_config(config_path)

    return parsed_configs