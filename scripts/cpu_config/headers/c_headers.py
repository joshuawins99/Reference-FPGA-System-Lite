import os
import sys
import re

sys.path.append('../')

from cpu_config_helpers import sanitize_identifier
from registers import reorder_tree

def export_c_headers(parsed_configs, submodule_reg_map, directory_path, reg_width_bytes=4, user_modules_only=False, new_c_header=False):
    for cpu_name, cpu_config in parsed_configs.items():
        output_dir = cpu_name
        os.makedirs(f"{directory_path}/{output_dir}", exist_ok=True)
        current_submodule_map = reorder_tree(submodule_reg_map)[cpu_name]

        c_filename = os.path.join(directory_path, output_dir, f"{cpu_name}_registers.h")

        c_lines = []
        c_module_storage = []
        c_lines_storage = []

        # C Header Boilerplate
        if not new_c_header:
            c_lines.append("// Auto-generated register map header")
            c_lines.append("#pragma once\n")
            c_lines.append("#include <stdint.h>")
            c_lines.append("#include <stddef.h>\n")
            c_lines.append("typedef struct {")
            c_lines.append("    uintptr_t base;")
            c_lines.append("    size_t count;")
            c_lines.append("    size_t address_wording;")
            c_lines.append("} CompactRegisterBlock;\n")
            c_lines.append("#define REG_AT(block, index) ((uintptr_t)((block).base + (index) * (block).address_wording))\n")
        else:
            c_lines.append(f"""
#ifndef {cpu_name.upper()}_H
#define {cpu_name.upper()}_H                         
#include <stdint.h>
#include <stddef.h>

typedef struct {{
    uintptr_t base;
    size_t count;
    size_t address_wording;
}} CompactRegisterBlock;

typedef struct {{
    CompactRegisterBlock block;
    size_t offset;
}} Register;

static inline uintptr_t RegAt(CompactRegisterBlock blk, size_t index) {{
    return blk.base + index * blk.address_wording;
}}

static inline uintptr_t RegAddr(Register reg) {{
    return RegAt(reg.block, reg.offset);
}}

static inline void Write32(Register reg, uint32_t val) {{
    volatile uint32_t *ptr = (volatile uint32_t *)RegAddr(reg);
    *ptr = val;
}}

static inline uint32_t Read32(Register reg) {{
    volatile uint32_t *ptr = (volatile uint32_t *)RegAddr(reg);
    return *ptr;
}}

static inline void Write8(Register reg, uint8_t val) {{
    volatile uint8_t *ptr = (volatile uint8_t *)RegAddr(reg);
    *ptr = val;
}}

static inline uint8_t Read8(Register reg) {{
    volatile uint8_t *ptr = (volatile uint8_t *)RegAddr(reg);
    return *ptr;
}}
                          
""")
            
        temp_module_storage = []
        temp_c_storage = []
        array_mask = []

        # Modules
        module_sections = ["USER_MODULES"] if user_modules_only else ["BUILTIN_MODULES", "USER_MODULES"]

        for section in module_sections:
            for module_name, module in cpu_config.get(section, {}).items():
                temp_module_storage = []
                if module_name == "BaseAddress" or not isinstance(module, dict):
                    continue
                if module.get("flag") != "TRUE" or "bounds" not in module:
                    continue
                if any(x.module_name == module_name for x in current_submodule_map) and not new_c_header:
                    continue
                try:
                    start_addr = module["bounds"][0]
                    end_addr = module["bounds"][1]
                except Exception:
                    continue

                reg_count = ((end_addr - start_addr) // reg_width_bytes) + 1
                subregisters = module.get("subregisters", 0)
                module_id = module_name.upper()
                mod_meta = module.get("metadata", {})
                mod_name_str = mod_meta.get("name", module_name)
                mod_desc_str = mod_meta.get("description", "").strip()
                mod_reg_expand_str = mod_meta.get("expand_regs", '')
                mod_repeat_inst = mod_meta.get("repeat_instance", '')
                mod_repeat_info = module.get("repeat", {"value": {}, "expand_regs": {}, "repeat_of": {}})

                if "submodule_of" in module:
                    for submodule in current_submodule_map:
                        if submodule.module_name == module_name:
                            base_module_reg_expand = submodule.base_reg_exp
                            break
                else:
                    base_module_reg_expand = ""

                if base_module_reg_expand == "TRUE":
                    continue

                # === Module Documentation ===
                if not new_c_header:
                    c_lines.append(f"// Module: {mod_name_str} ({module_name})")
                c_lines_storage.append(f"// Module: {mod_name_str} ({module_name})")
                if mod_desc_str:
                    desc_lines = mod_desc_str.split('\n')
                    formatted_desc = f"// Module Description: {desc_lines[0]}"
                    for line in desc_lines[1:]:
                        formatted_desc += f"\n//                     {line}"
                    if not new_c_header:
                        c_lines.append(formatted_desc)
                    c_lines_storage.append(formatted_desc)
                temp_module_storage.append(f"# Module: {mod_name_str} ({module_name})")
                if mod_desc_str:
                    desc_lines = mod_desc_str.split('\n')
                    formatted_desc = f"# Module Description: {desc_lines[0]}"
                    for line in desc_lines[1:]:
                        formatted_desc += f"\n#                     {line}"
                    temp_module_storage.append(formatted_desc)

                c_enum_entries = []
                c_addr_macros = []

                if (mod_reg_expand_str == 'FALSE' or (mod_repeat_inst == 'TRUE' and mod_repeat_info["expand_regs"] == 'FALSE' and mod_reg_expand_str == 'FALSE')):
                    modified_range_reg_count = max(1, reg_count - subregisters)
                    for i in range(modified_range_reg_count):
                        addr = start_addr + i * reg_width_bytes
                        reg_key = f"Reg{i}"
                        reg_info = module.get("regs", {}).get(reg_key, {})
                        reg_name_raw = reg_info.get("name", f"Reg{i}")
                        reg_desc = reg_info.get("description", "").strip()
                        reg_perm = reg_info.get("permissions", "").strip()
                        reg_name_id = sanitize_identifier(reg_name_raw)
                        entry_name = f"{module_id}_{reg_name_id}"

                        if new_c_header and i == 0:
                            c_lines_storage.append(f"typedef struct {{")
                            c_lines_storage.append(f"    CompactRegisterBlock block;")
                            for idx, entry in enumerate(current_submodule_map):
                                    if entry.module_parent == module_name:
                                        full_submodule_name = entry.module_name
                                        sub_module = str(full_submodule_name.split(entry.separator)[-1])
                                        c_lines_storage.append(f"    {full_submodule_name}_t {sub_module};")
                        add_reg_comma = ","
                        if (i == (reg_count-subregisters)-1):
                            add_reg_comma = ""
                        if (reg_count-subregisters) > 0:
                            temp_c_storage.append(f"    .{reg_name_id.lower()} = {{ {{0x{start_addr:04X} , {reg_count}, {reg_width_bytes} }}, {i} }}{add_reg_comma}")
                        else:
                            temp_c_storage.append(f"}};\n")

                        comma = "," if i < (reg_count-subregisters) - 1 else ""
                        if reg_desc:
                            desc_lines = reg_desc.split('\n')
                        if not new_c_header:
                            c_enum_entries.append(f"    {entry_name} = {i}{comma} // {reg_name_raw}")
                            c_addr_macros.append(f"#define {entry_name}_ADDR 0x{addr:04X}")
                            if reg_desc:
                                formatted_desc = f"// Register Description: {desc_lines[0]}"
                                for line in desc_lines[1:]:
                                    formatted_desc += f"\n//                      {line}"
                                c_addr_macros.append(formatted_desc)
                            if reg_perm:
                                c_addr_macros.append(f"// Register Permissions: {reg_perm}")
                        else:
                            if i < (reg_count-subregisters)-1 and (reg_count-subregisters) > 0:
                                c_lines_storage.append(f"    Register {reg_name_id.lower()}; // [{reg_perm if reg_perm else 'R/W'}] {' '.join(desc_lines)}")
                            else:
                                if (reg_count-subregisters) > 0:
                                    c_lines_storage.append(f"    Register {reg_name_id.lower()}; // [{reg_perm if reg_perm else 'R/W'}] {' '.join(desc_lines)}")
                                c_lines_storage.append(f"}} {module_id.lower()}_t;\n")
                                c_lines_storage.append(f"static const {module_id.lower()}_t {module_id.lower()} = {{")
                                c_lines_storage.append(f"    .block = {{ 0x{start_addr:04X}, {reg_count}, {reg_width_bytes} }},")
                                for idx, entry in enumerate(current_submodule_map):
                                    if entry.module_parent == module_name:
                                        full_submodule_name = entry.module_name
                                        sub_module = str(full_submodule_name.split(entry.separator)[-1])
                                        if (idx < len(current_submodule_map)-1) or (reg_count-subregisters) > 0:
                                            c_lines_storage.append(f"    .{sub_module} = {full_submodule_name},")
                                        else:
                                            c_lines_storage.append(f"    .{sub_module} = {full_submodule_name}")
                else:
                    c_lines_storage.append(f"typedef struct {{")
                    c_lines_storage.append(f"   CompactRegisterBlock block;")
                    c_lines_storage.append(f"}} {module_id.lower()}_t;\n")
                    c_lines_storage.append(f"static const {module_id.lower()}_t {module_id.lower()} = {{")
                    c_lines_storage.append(f"   .block = {{ 0x{start_addr:04X}, {reg_count}, {reg_width_bytes} }}")
                    c_lines_storage.append(f"}};\n")
                
                c_lines_storage.extend(temp_c_storage)
                if temp_c_storage and (reg_count-subregisters) > 0:
                    c_lines_storage.append(f"}};\n")
                    
                #Generate Repeat Module Arrays
                if not mod_repeat_info.get("value", {}) and subregisters > 0:
                    array_type = ""
                    adding_array = 0
                    for entry in current_submodule_map:
                        if entry.module_parent == module_name and cpu_config.get(section, {}).get(entry.module_name).get("repeat", {}).get("value", None):
                            if adding_array == 0:
                                c_lines_storage.append(f"// Repeat Instance Iterable Array(s) of {entry.module_parent}")
                            module_name_stripped = entry.module_name.split(entry.separator)[-1]
                            base_module_match = re.match(r"(.+?)(?:_\d+)?$", module_name_stripped)
                            base_module = base_module_match.group(1)
                            if module_name_stripped == base_module:
                                array_type = entry.module_name
                                c_lines_storage.append(f"static __attribute__((unused))")
                                array_name = entry.module_name.split(entry.separator)[-1]
                                array_count = array_mask.count(array_name)
                                array_iterator = f"_{array_count}" if array_count != 0 else ""
                                c_lines_storage.append(f"{entry.module_name}_t* {array_name}_array{array_iterator}[] = {{")
                                array_mask.append(array_name)
                                adding_array = 1
                                for entry in current_submodule_map:
                                    if entry.module_parent == module_name and cpu_config.get(section, {}).get(entry.module_name).get("repeat", {}).get("value", None) and adding_array == 1:
                                        module_name_stripped = entry.module_name.split(entry.separator)[-1]
                                        if module_name_stripped == base_module or module_name_stripped.startswith(base_module + "_"):
                                            c_lines_storage.append(f"   ({array_type}_t*)&{entry.module_name},")
                                if adding_array == 1:
                                    c_lines_storage[-1] = c_lines_storage[-1].replace(",", "") #Remove comma from last entry
                                    c_lines_storage.append(f"}};\n")
                c_module_storage[0:0] = c_lines_storage
                c_lines_storage = []
                temp_c_storage = []
                if not new_c_header:
                    c_lines.extend(c_addr_macros)
                    c_lines.append(f"static const CompactRegisterBlock {module_id} = {{ 0x{start_addr:04X}, {reg_count}, {reg_width_bytes} }};\n")

        if new_c_header:
            for entry in c_module_storage:
                c_lines.append(entry)
            c_lines.append("#endif")
        
        with open(c_filename, "w") as f:
            f.write("\n".join(c_lines))
        print(f"C header for {cpu_name} saved to: {c_filename}")