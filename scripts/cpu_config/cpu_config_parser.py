import os
import re
from cpu_config_helpers import *

def parse_config(file_path):
    """Parses the cpu_config.txt file and returns a structured dictionary, including metadata and multiline support."""
    config_data = {}
    current_section = None
    current_base_section = None
    current_module = None
    current_register = None
    current_field = None
    pending_key = None
    pending_value = ""
    current_line_index = 0
    got_register_name = False
    got_register_description = False
    infer_module_registers = {}
    got_submodule = False
    current_base_module = None
    current_submodule_indent = 0
    submodule_indexes = []
    submodule_name_append = None
    include_file_dirs = []
    got_module_name = False
    got_module_description = False

    indent_size = 4
    submodule_indent_size = indent_size * 2
    submodule_identifier = "____"

    # Pattern matching compile
    section_re = re.compile(r"^(\w+):\s*(.*)?$")
    param_re = re.compile(r"(\w+)\s*:\s*(\"[^\"]+\"|\{[^}]+\}|[^\s:]+)(?:\s*:\s*\{(\d+:\d+)\})?")
    module_re = re.compile(r"(\w+)\s*:\s*(TRUE|FALSE)\s*:\s*\{([^}]+)\}(?:\s*:\s*(\w+))?")
    auto_expr_re = re.compile(r"(\w+)\s*:\s*(TRUE|FALSE)\s*:\s*AUTO\s*:\s*\{(.+?)\}(?:\s*:\s*(\w+))?")
    auto_literal_re = re.compile(r"(\w+)\s*:\s*(TRUE|FALSE)\s*:\s*AUTO\s*:\s*(\d+)(?:\s*:\s*(\w+))?")
    auto_simple_re = re.compile(r"(\w+)\s*:\s*(TRUE|FALSE)\s*:\s*AUTO(?:\s*:\s*(\w+))?")
    reg_re = re.compile(r"(Reg\d+)\s*:")
    field_re = re.compile(r"(Field\d+)\s*:")
    name_re = re.compile(r"Name\s*:\s*(.+)")
    repeat_re = re.compile(r"Repeat\s*:\s*(\d+|\{[^}]+\})(?:\s*:\s*(\w+))?")
    desc_re = re.compile(r"Description\s*:\s*(.+)")
    bounds_re =  re.compile(r"Bounds\s*:\s*\[\s*([^\]:]+)\s*:\s*([^\]]+)\s*\]")
    permissions_re = re.compile(r"Permissions\s*:\s*(.+)")
    module_include_re = re.compile(r"Module_Include\s*:\s*(.+)")

    with open(file_path, "r") as file:
        config_file_lines = [normalize_indent(line, indent_size) for line in file]

    for raw_line in config_file_lines:
        current_line_index = current_line_index + 1
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        # Handle multiline continuation
        if pending_key:
            if line.endswith("\\"):
                pending_value += "\n" + line.rstrip("\\").strip()
                continue
            else:
                pending_value += "\n" + line.strip()
                # Finalize the pending value
                if current_register and (not got_register_description or not got_register_name):
                    config_data[current_section][current_module]["regs"][current_register][pending_key] = pending_value.strip()
                    if pending_key == "description":
                        got_register_description = True
                    if pending_key == "name":
                        got_register_name = True
                elif current_field:
                    config_data[current_section][current_module]["regs"][current_register]["fields"][current_field]["description"] = pending_value.strip()
                else:
                    config_data[current_section][current_module]["metadata"][pending_key] = pending_value.strip()
                    got_module_description = True
                pending_key = None
                pending_value = ""
                continue

        # Pattern matching
        section_match = section_re.match(line)
        param_match = param_re.match(line)
        module_match = module_re.match(line)
        auto_expr_match = auto_expr_re.match(line)
        auto_literal_match = auto_literal_re.match(line)
        auto_simple_match = auto_simple_re.match(line)
        reg_match = reg_re.match(line)
        field_match = field_re.match(line)
        bounds_match = bounds_re.match(line)
        name_match = name_re.match(line)
        repeat_match = repeat_re.match(line)
        desc_match = desc_re.match(line)
        permissions_match = permissions_re.match(line)
        module_include_match = module_include_re.match(line)

        if section_match:
            if (section_match.group(1) == "SUBMODULE"):
                current_base_section = current_section
                if current_module:
                    if not submodule_indexes:
                        submodule_indexes.append((current_module, get_indent_level(raw_line)-submodule_indent_size))
                    next_line = config_file_lines[current_line_index]
                    next_line = next_line.strip()
                    sub_module_match = module_re.match(next_line) or auto_expr_re.match(next_line) or auto_literal_re.match(next_line) or auto_simple_re.match(next_line)
                    if not sub_module_match.group(1):
                        raise SyntaxError(f"'{next_line}' is not valid")
                    submodule_indexes.append((sub_module_match.group(1), get_indent_level(raw_line)))
                    if submodule_indexes[-1][1] - submodule_indexes[-2][1] > submodule_indent_size:
                        raise SyntaxError(f"'{next_line}' indention is not valid. Did you skip a level?")
                    current_section = current_base_section
                    got_submodule = True
                    current_submodule_indent = get_indent_level(raw_line)
                    qualified_chain = []
                    target_indent = current_submodule_indent
                    for name, indent in reversed(submodule_indexes):
                        if indent == target_indent:
                            qualified_chain.insert(0, name)
                            target_indent -= submodule_indent_size
                        elif indent < target_indent:
                            # Stop once we've walked up the hierarchy
                            break
                    submodule_name_append = submodule_identifier.join(qualified_chain)
                    # Walk backward through submodule_indexes to find the first module with indent 4 less
                    for prev_name, prev_indent in reversed(submodule_indexes[:-1]):
                        if prev_indent == current_submodule_indent - submodule_indent_size:
                            current_base_module = prev_name
                            break
                    else:
                        raise SyntaxError(f"Indentation incorrect within module '{submodule_indexes[:-1][0][0]}'")
                else:
                    raise SyntaxError(f"'{line}' is not valid")
            else:
                current_section = section_match.group(1)
            config_data.setdefault(current_section, {})
            infer_module_registers.setdefault(current_section, {})
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
            if submodule_name_append:
                key = submodule_name_append
                submodule_name_append = None
            else:
                key = auto_expr_match.group(1)
            flag = auto_expr_match.group(2)
            reg_count = auto_expr_match.group(3)
            expand_regs = auto_expr_match.group(4)
            got_register_name = False
            got_register_description = False
            got_module_name = False
            got_module_description = False
            
            if got_submodule:
                config_data[current_section][key] = {
                    "flag": flag,
                    "auto": True,
                    "registers": reg_count,
                    "metadata": {},
                    "regs": {},
                    "include_file" : {},
                    "submodule_of" : current_base_module
                }
            else:
                submodule_indexes = []
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
            current_field = None
            got_submodule = False
            current_base_module = None

        elif auto_literal_match and current_section in ["BUILTIN_MODULES", "USER_MODULES"]:
            if submodule_name_append:
                key = submodule_name_append
                submodule_name_append = None
            else:
                key = auto_literal_match.group(1)
            flag = auto_literal_match.group(2)
            reg_count = int(auto_literal_match.group(3))
            expand_regs = auto_literal_match.group(4)
            got_register_name = False
            got_register_description = False
            got_module_name = False
            got_module_description = False

            if got_submodule:
                config_data[current_section][key] = {
                    "flag": flag,
                    "auto": True,
                    "registers": reg_count,
                    "metadata": {},
                    "regs": {},
                    "include_file" : {},
                    "submodule_of" : current_base_module
                }
            else:
                submodule_indexes = []
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
            current_field = None
            got_submodule = False
            current_base_module = None

        elif auto_simple_match and current_section in ["BUILTIN_MODULES", "USER_MODULES"]:
            if submodule_name_append:
                key = submodule_name_append
                submodule_name_append = None
            else:
                key = auto_simple_match.group(1)
            flag = auto_simple_match.group(2)
            expand_regs = auto_simple_match.group(3)
            got_register_name = False
            got_register_description = False
            got_module_name = False
            got_module_description = False

            if got_submodule:
                config_data[current_section][key] = {
                    "flag": flag,
                    "auto": True,
                    "registers": None,  #Will be inferred later
                    "metadata": {},
                    "regs": {},
                    "include_file": {},
                    "submodule_of" : current_base_module
                }
            else:
                submodule_indexes = []
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
            current_field = None
            infer_module_registers[current_section][current_module] = 0
            got_submodule = False
            current_base_module = None

        elif module_match and current_section in ["BUILTIN_MODULES", "USER_MODULES"]:
            if submodule_name_append:
                key = submodule_name_append
                submodule_name_append = None
            else:
                key = module_match.group(1)
            flag = module_match.group(2)
            bounds = [b.strip().rstrip(",") for b in module_match.group(3).split(",")]
            expand_regs = module_match.group(4)
            got_register_name = False
            got_register_description = False
            got_module_name = False
            got_module_description = False

            if got_submodule:
                config_data[current_section][key] = {
                    "flag": flag,
                    "bounds": bounds,
                    "metadata": {},
                    "regs": {},
                    "include_file" : {},
                    "submodule_of" : current_base_module
                }
            else:
                submodule_indexes = []
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
            current_field = None
            got_submodule = False
            current_base_module = None

        elif current_module and module_include_match:
            if (current_register == None):
                include_file = module_include_match.group(1)
                absolute_path = os.path.normpath(os.path.dirname(parse_file_path(include_file, config_data)))
                resolved_mod_filepath = resolve_mod_include_filepath(os.path.dirname(os.path.abspath(file_path)), parse_file_path(include_file, config_data), include_file_dirs)
                config_data[current_section][key]["metadata"]["module_filepath"] = resolved_mod_filepath
                if absolute_path not in include_file_dirs:
                    include_file_dirs.append(absolute_path)
                existing_metadata = config_data[current_section][current_module]["metadata"]
                has_name = "name" in existing_metadata
                has_description = "description" in existing_metadata
                scrape_metadata(config_data, file_path, include_file_dirs, include_file, config_file_lines, current_line_index, has_name, has_description, get_indent_level(raw_line))
            else:
                raise SyntaxError(f"Registers Defined and Module Include Specified in Entry: '{current_module}'")
            
        elif current_register and field_match:
            current_field = field_match.group(1)
            config_data[current_section][current_module]["regs"][current_register].setdefault("fields", {})
            config_data[current_section][current_module]["regs"][current_register]["fields"].setdefault(current_field, {})
            config_data[current_section][current_module]["regs"][current_register]["fields"][current_field] = {
                "name" : {},
                "bounds" : {},
                "description" : {}
            }
        
        elif current_field and bounds_match:
            bounds = [bounds_match.group(1), bounds_match.group(2)]
            config_data[current_section][current_module]["regs"][current_register]["fields"][current_field]["bounds"] = bounds

        elif current_module and reg_match:
            got_register_name = False
            got_register_description = False
            current_register = reg_match.group(1)
            if current_register in config_data[current_section][current_module]["regs"]:
                raise SyntaxError(f"Register '{current_register}' Redefinition in Entry: '{current_module}'")
            config_data[current_section][current_module]["regs"].setdefault(current_register, {})
            if current_module in infer_module_registers[current_section]:
                infer_module_registers[current_section][current_module] += 1

        elif current_module and name_match:
            name_val = name_match.group(1)
            if current_register and not got_register_name:
                config_data[current_section][current_module]["regs"][current_register]["name"] = name_val
                got_register_name = True
            elif current_field:
                config_data[current_section][current_module]["regs"][current_register]["fields"][current_field]["name"] = name_val
            else:
                if got_module_name == False:
                    got_module_name = True
                    config_data[current_section][current_module]["metadata"]["name"] = name_val

        elif current_module and repeat_match:
            repeat_val = repeat_match.group(1)
            expand_regs = repeat_match.group(2)

            #remove braces if present
            if repeat_val.startswith("{") and repeat_val.endswith("}"):
                repeat_val = repeat_val[1:-1]

            if not (got_register_name or got_register_description):
                config_data[current_section][current_module].setdefault("repeat", {})
                config_data[current_section][current_module]["repeat"]["value"] = repeat_val
            else:
                raise SyntaxError(f"Repeat value not correct in Entry: '{current_module}'")
            
            if expand_regs == "NOEXPREGS":
                config_data[current_section][current_module]["repeat"]["expand_regs"] = 'TRUE'
            elif not expand_regs:
                config_data[current_section][current_module]["repeat"]["expand_regs"] = 'FALSE'
            else:
                raise SyntaxError(f"Repeat value not correct in Entry: '{current_module}'")

        elif current_module and desc_match:
            desc_val = desc_match.group(1)
            if desc_val.endswith("\\"):
                pending_key = "description"
                pending_value = desc_val.rstrip("\\").strip()
            else:
                if current_register and not got_register_description:
                    config_data[current_section][current_module]["regs"][current_register]["description"] = desc_val.strip()
                    got_register_description = True
                elif current_field:
                    config_data[current_section][current_module]["regs"][current_register]["fields"][current_field]["description"] = desc_val.strip()
                else:
                    if got_module_description == False:
                        got_module_description = True
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
                raise SyntaxError(f"Unknown permission string encountered: '{perm_val}'")
            if current_register:
                config_data[current_section][current_module]["regs"][current_register]["permissions"] = new_perm_val
        
        else:
            raise SyntaxError(f"'{line}' is not valid")

    #Populate Register Count for AUTO Inferred Registers
    for section, data in infer_module_registers.items():
        for mod, count in data.items():
            if count > 0:
                config_data[section][mod]["registers"] = count
            else:
                #Didn't find any Regx entries. Maybe there are submodules?
                #Should error in the auto allocator if there aren't
                config_data[section][mod]["registers"] = 0

    return compute_config_submodules(config_data, submodule_identifier)

def process_configs(directory_path, config_file_names):
    """Processes config files in multiple folders and returns parsed data."""
    parsed_configs = {}
    submodule_reg_map = {}

    for folder in os.listdir(directory_path):
        folder_path = os.path.join(directory_path, folder)
        config_path = None
        if not os.path.isdir(folder_path):
            continue  # Skip files; only process directories
        for name in config_file_names:
            potential_path = os.path.join(folder_path, name)
            if os.path.exists(potential_path):
                config_path = potential_path
                break  # Found a valid config file; no need to keep checking
        if config_path:
            parsed_configs[folder], submodule_reg_map[folder] = parse_config(config_path)

    return parsed_configs, submodule_reg_map