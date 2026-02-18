from registers import reorder_tree, resolve_expression, build_parameter_table
from collections import namedtuple
from math import ceil
import copy
import re
import os

def get_code_folders(parsed_configs):
    """Extracts CODE_FOLDER values from the parsed configs if present."""
    code_folders = {}
    for cpu_name, config in parsed_configs.items():
        for section in ["CONFIG_PARAMETERS"]:
            params = config.get(section, {})
            folder_info = None
            if "C_Code_Folder" in params:
                print("Warning: C_Code_Folder parameter deprecated! Use Code_Folder instead.")
                folder_info = params.get("C_Code_Folder")
            if "Code_Folder" in params:
                folder_info = params.get("Code_Folder")
            if folder_info:
                code_folders[cpu_name] = folder_info["value"]
    return code_folders

def parse_file_path(input_param, config_data):
    """
    Replaces placeholders like {KEY} in input_param using CONFIG_PARAMETERS from config_data.
    Each CONFIG_PARAMETERS entry is expected to be a dict with a 'value' key.
    """
    config_params = config_data.get("CONFIG_PARAMETERS", {}) #Get all items in CONFIG_PARAMETERS field
    pattern = re.compile(r"\{(\w+)\}") #Create a match regex object

    def replace_placeholder(match):
        key = match.group(1)
        param_entry = config_params.get(key)
        if isinstance(param_entry, dict) and "value" in param_entry: #Checks if the parameter exists and has a value
            return str(param_entry["value"]) #Returns the value as a string
        else:
            raise SyntaxError(f"CONFIG_PARAMETERS missing or malformed for key: '{key}'")

    return pattern.sub(replace_placeholder, input_param) #Will call replace_placeholder as needed if a match occurs

def list_folders(directory):
    """Returns a list of folders in the given directory."""
    if not os.path.exists(directory):
        raise FileNotFoundError(f"The directory '{directory}' does not exist.")

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

def resolve_mod_include_filepath(base_dir, include_path, include_file_dirs):
    for dir_path in include_file_dirs:
        # Each candidate should be resolved relative to the current file's directory
        candidate = os.path.normpath(os.path.join(base_dir, dir_path, include_path))
        if os.path.exists(candidate):
            return candidate

def scrape_metadata(config_data, file_path, include_file_dirs, include_file, config_file_lines, current_line_index, has_name, has_description, indent_amount=0):
    include_path = parse_file_path(include_file, config_data)
    current_path = None
    base_dir = os.path.dirname(os.path.abspath(file_path))

    current_path = resolve_mod_include_filepath(base_dir, include_path, include_file_dirs)

    # Fallback if nothing matched
    if current_path is None:
        current_path = os.path.normpath(os.path.join(base_dir, include_path))

    inside_metadata = False
    metadata_block = []
    inside_register = False
    filtered_block = []

    spaces = " " * indent_amount

    with open(current_path, "r") as file:
        for line in file:
            if "@ModuleMetadataBegin" in line:
                inside_metadata = True
                continue
            elif "@ModuleMetadataEnd" in line:
                inside_metadata = False
                break
            if inside_metadata:
                metadata_block.append(spaces + line)

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

def get_base_module(config_data):
    is_submodule = []
    for section in ["BUILTIN_MODULES","USER_MODULES"]:
        for module_name, module in config_data.get(section, {}).items():
            submodule_data = module.get('submodule_of', '')
            if submodule_data:
                is_submodule.append((module_name, True))
            else:
                is_submodule.append((module_name, False))

    if not is_submodule:
        return None
    
    if is_submodule[-1][1] is not True:
        result = is_submodule[-1][0]
    else:
        for pair in reversed(is_submodule):
            if pair[1] is not True:
                result = pair[0]
                break
    return result

def get_indent_level(raw_line):
    return len(raw_line) - len(raw_line.lstrip(" "))

def normalize_indent(line, indent_size=4):
    line = line.expandtabs(indent_size)  # Convert tabs to spaces
    stripped = line.lstrip()
    leading_spaces = len(line) - len(stripped)
    indent_level = leading_spaces // indent_size
    return " " * (indent_level * indent_size) + stripped

def resolve_all_expressions(config_data):
    parameters_list = build_parameter_table(config_data)
    working_config_data = copy.deepcopy(config_data)

    #Resolve parameters first
    for section, data in working_config_data.items():
        if section in ["BUILTIN_PARAMETERS", "USER_PARAMETERS"]:
            for parameter, parameter_data in data.items():
                current_parameter_data = parameter_data.get("value")
                working_config_data[section][parameter]["value"] = resolve_expression(current_parameter_data, parameters_list)

    #Resolve Module Bounds
    for section, data in working_config_data.items():
        if section in ["BUILTIN_MODULES", "USER_MODULES"]:
            for module, module_data in data.items():
                current_bounds = module_data.get("bounds")
                if current_bounds:
                    bound_upper = resolve_expression(current_bounds[0], parameters_list)
                    bound_lower = resolve_expression(current_bounds[1], parameters_list)
                    if not bound_upper%1 == 0 or not bound_lower%1 == 0:
                        raise ValueError(f"Module Bounds for '{module}' don't resolve to an integer")
                    working_config_data[section][module]["bounds"] = [int(bound_upper), int(bound_lower)]

    # Resolve Repeats
    for section, data in working_config_data.items():
        if section in ["BUILTIN_MODULES", "USER_MODULES"]:
            for module, module_data in data.items():
                current_repeat = module_data.get("repeat", {})
                if current_repeat:
                    repeat_num = resolve_expression(current_repeat.get("value", 0), parameters_list)
                    if not repeat_num%1 == 0:
                        raise ValueError(f"Repeat Count for '{module}' doesn't resolve to an integer")
                    working_config_data[section][module]["repeat"]["value"] = int(repeat_num)

    #Resolve Field Bounds
    for section, data in working_config_data.items():
        if section in ["BUILTIN_MODULES", "USER_MODULES"]:
            for module, module_data in data.items():
                current_regs = module_data.get("regs", {})
                if current_regs:
                    for reg_name, data in current_regs.items():
                        field_info = data.get("fields", {})
                        reg_name_value = data.get("name", "")
                        if field_info:
                            for field_name, data in field_info.items():
                                current_bounds = data.get("bounds", {})
                                bound_upper = resolve_expression(current_bounds[0], parameters_list)
                                bound_lower = resolve_expression(current_bounds[1], parameters_list)
                                if not bound_upper%1 == 0 or not bound_lower%1 == 0:
                                    print(f"Warning: Field '{reg_name_value if reg_name_value else reg_name}'->'{field_name}' Bounds in '{module}' don't resolve to an integer")
                                working_config_data[section][module]["regs"][reg_name]["fields"][field_name]["bounds"] = [int(ceil(bound_upper)), int(ceil(bound_lower))]

    #Resolve Register Counts
    for section, data in working_config_data.items():
        if section in ["BUILTIN_MODULES", "USER_MODULES"]:
            for module, module_data in data.items():
                reg_count = module_data.get("registers", {})
                if reg_count:
                    resolved_register_count = resolve_expression(reg_count, parameters_list)
                    if not resolved_register_count%1 == 0:
                        raise ValueError(f"Register Count for '{module}' doesn't resolve to an integer")
                    working_config_data[section][module]["registers"] = int(resolved_register_count)

    return working_config_data

def compute_config_submodules(config_data, submodule_identifier):
    #Resolve all expressions
    config_data = resolve_all_expressions(config_data)

    #Build a map of submodules to add to base module recursively
    parameters_list = build_parameter_table(config_data)

    #Account for NOEXPREGS on a tree
    for section, data in config_data.items():
            new_section_data = data
            if section in ["BUILTIN_MODULES", "USER_MODULES"]:
                for module, module_data in data.items():
                    current_module_level = module
                    current_module_expand = module_data.get("metadata").get("expand_regs")
                    current_repeat_expand = module_data.get("repeat", {}).get("expand_regs", {})
                    for module, module_data in data.items():
                        if module.startswith(current_module_level) and (current_module_expand == "TRUE" or current_repeat_expand == "TRUE"):
                            new_section_data[module]["metadata"]["expand_regs"] = current_module_expand
                            new_section_data[module].setdefault("repeat", {})
                            new_section_data[module]["repeat"]["expand_regs"] = current_repeat_expand
            config_data[section] = new_section_data

    #Build list of Repeat Modules and Sort
    repeat_list_initial = []
    for section, section_data in config_data.items():
        if section in ["BUILTIN_MODULES", "USER_MODULES"]:
            for module, module_data in list(section_data.items()):
                repeat_list_initial.append((module, module_data.get("repeat", {}).get("value", 0)))

    def sort_filtered_by_base_and_depth_desc(d):
        def base_name(key):
            return key.split(submodule_identifier, 1)[0]
        def depth(key):
            return key.count(submodule_identifier)
        # 1. Filter out entries with value == 0
        filtered = {k: v for k, v in d.items() if v != 0}
        # 2. Sort by (base, -depth)
        return dict(sorted(filtered.items(), key=lambda item: (base_name(item[0]), -depth(item[0]))))

    repeat_dict_initial_sorted_filtered = sort_filtered_by_base_and_depth_desc(dict(repeat_list_initial))

    def insert_after_match(haystack, needle, new_text):
        #Inserts 'new_text' into 'haystack' immediately after the first occurrence of 'needle'.
        i = haystack.find(needle)
        if i == -1: # Substring not found
            return haystack
        # Rebuild the string using slicing and concatenation
        return haystack[:i + len(needle)] + new_text + haystack[i + len(needle):]
    
    def insert_after_last_match(d, repeat_module, new_items): 
        #Insert new_items after the LAST key in d that starts with repeat_module.
        out = {}
        last_match = None
        # First pass: find the last matching key
        for k in d.keys():
            if k.startswith(repeat_module):
                last_match = k
        # Second pass: rebuild dict with insertion
        for k, v in d.items():
            out[k] = v
            if k == last_match:
                for nk, nv in new_items.items():
                    out[nk] = nv
        return out
    
    def strip_repeat_suffix(name):
        parts = name.rsplit("_", 1)
        return parts[0] if parts[-1].isdigit() else name

    #Account for Repeat entries in modules
    for repeat_module, repeat_count in repeat_dict_initial_sorted_filtered.items():
        for section, section_data in config_data.items():
            if section in ["BUILTIN_MODULES", "USER_MODULES"]:
                # snapshot of the ORIGINAL subtree for this repeat_module
                orig_modules = [(m, section_data[m]) for m in section_data.keys() if m.startswith(repeat_module)]
                for i in range(1, repeat_count+1):
                    new_section_data = {}
                    # only clone from the original snapshot, never from updated config
                    for module, module_data in orig_modules:
                        new_key = insert_after_match(module, repeat_module, f"_{i}")
                        new_section_data[new_key] = copy.deepcopy(module_data)
                        new_section_data[new_key]["metadata"]["repeat_instance"] = 'TRUE'
                        new_section_data[new_key].setdefault("repeat", {})
                        new_section_data[new_key]["repeat"]["repeat_of"] = strip_repeat_suffix(module.split(submodule_identifier)[-1])
                        new_section_data[new_key]["repeat"]["expand_regs"] = module_data.get("repeat", {}).get("expand_regs", "FALSE")
                        if new_section_data[new_key].get("submodule_of"):
                            new_section_data[new_key]["submodule_of"] = insert_after_match(new_section_data[new_key]["submodule_of"], repeat_module, f"_{i}")
                    config_data[section] = insert_after_last_match(config_data[section], repeat_module, new_section_data)

    #Entries -> (base_module, section, module_name, module_parent, register_count, id_count(for enforcing order), separator, base_reg_exp)
    submodule_reg_add_map_tuple = namedtuple("submodule_reg_add_map_tuple", ["base_module", "section", "module_name", "module_parent", "register_count", "id_count", "separator", "base_reg_exp"])
    submodule_reg_add_map = []
    id_count = 0
    for section, data in config_data.items():
        if section == "BUILTIN_MODULES" or section == "USER_MODULES":
            for module, module_data in data.items():
                try:
                    submodule_data = module_data.get('submodule_of', '')
                except:
                    if module == "BaseAddress": continue #Indicates that the section has a base address specified and should be skipped
                    else: raise SyntaxError (f"Module entry {module} not valid")
                registers_to_add = module_data.get('registers', 0)
                if submodule_data:
                    submodule_data = module.split(submodule_identifier)
                    base_reg_exp = config_data[section][submodule_data[0]]["metadata"]["expand_regs"]
                    submodule_reg_add_map.append(submodule_reg_add_map_tuple(submodule_data[0], section, module, submodule_identifier.join(submodule_data[:-1]), registers_to_add, id_count, submodule_identifier, base_reg_exp))
                    id_count +=1

    submodule_reg_add_map_sorted_key = {}
    submodule_reg_add_map_sorted_key["key"] = submodule_reg_add_map
    submodule_reg_add_map_sorted = reorder_tree(submodule_reg_add_map_sorted_key)["key"]
   
    # Build parent -> children map and native counts
    native_counts = {}
    children_map = {}

    for _, section, full, parent, count, _, _, _ in submodule_reg_add_map_sorted:
        # record native count for this module (from tuples)
        native_counts[full] = count

        # build children map
        children_map.setdefault(parent, []).append(full)

        # ensure dict entries exist
        config_data.setdefault(section, {}).setdefault(full, {"registers": 0, "subregisters": 0})
        config_data.setdefault(section, {}).setdefault(parent, {"registers": 0, "subregisters": 0})

    # IMPORTANT: use the base's already-initialized registers as its native count
    # registers is a string; convert to int

    for base, section, _, _, _, _, _, _ in submodule_reg_add_map_sorted:
        if base not in native_counts:
            base_initial = config_data[section].get(base, {}).get("registers", 0)
            native_counts[base] = base_initial

    # Recursive total calculator (native + descendants)
    def compute_total(module):
        total = native_counts.get(module, 0)
        for child in children_map.get(module, []):
            total += compute_total(child)
        return total

    # Fill registers and subregisters for all modules in the tree
    for base, section, full, _, _, _, _, _ in submodule_reg_add_map_sorted:
        total = compute_total(full)
        native = native_counts.get(full, 0)
        config_data[section][full]["registers"] = total # native + children
        config_data[section][full]["subregisters"] = total - native # children only

    # Ensure base (level 0) modules also get updated correctly
    for base, section, _, _, _, _, _, _ in submodule_reg_add_map_sorted:
        total = compute_total(base)
        native = native_counts.get(base, 0)
        config_data[section][base]["registers"] = total
        config_data[section][base]["subregisters"] = total - native

    return config_data, submodule_reg_add_map_sorted