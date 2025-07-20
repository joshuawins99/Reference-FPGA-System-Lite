import os
import re
from registers import resolve_expression
class CompactRegisterBlock:
    def __init__(self, base, count, address_wording):
        self.base = base
        self.count = count
        self.address_wording = address_wording

    def reg_at(self, index):
        return self.base + index * self.address_wording
    
def export_per_cpu_headers(parsed_configs, directory_path, reg_width_bytes=4, user_modules_only=False):

    def sanitize_identifier(text):
        return re.sub(r'\W+', '_', text.strip()).upper()

    for cpu_name, cpu_config in parsed_configs.items():
        output_dir = cpu_name
        os.makedirs(f"{directory_path}/{output_dir}", exist_ok=True)

        c_filename = os.path.join(directory_path, output_dir, f"{cpu_name}_registers.h")
        py_filename = os.path.join(directory_path, output_dir, f"{cpu_name}_registers.py")

        c_lines = []
        py_lines = []

        # C Header Boilerplate
        c_lines.append("// Auto-generated register map header")
        c_lines.append("#pragma once\n")
        c_lines.append("#include <stdint.h>\n")
        c_lines.append("typedef struct {")
        c_lines.append("    uintptr_t base;")
        c_lines.append("    size_t count;")
        c_lines.append("    size_t address_wording;")
        c_lines.append("} CompactRegisterBlock;\n")
        c_lines.append("#define REG_AT(block, index) ((uintptr_t)((block).base + (index) * (block).address_wording))\n")

        # Python Header Boilerplate
        py_lines.append("# Auto-generated register map header")
        py_lines.append("from enum import Enum\n")
        py_lines.append("class CompactRegisterBlock:")
        py_lines.append("    def __init__(self, base, count, address_wording):")
        py_lines.append("        self.base = base")
        py_lines.append("        self.count = count")
        py_lines.append("        self.address_wording = address_wording\n")
        py_lines.append("    def reg_at(self, index):")
        py_lines.append("        if index >= self.count:")
        py_lines.append("            raise IndexError(f'Register index {index} out of bounds (max {self.count - 1})')")
        py_lines.append("        return self.base + index * self.address_wording\n")

        # Parameter Table
        parameter_table = {}
        for section in ["BUILTIN_PARAMETERS", "USER_PARAMETERS"]:
            for param_name, param_data in cpu_config.get(section, {}).items():
                val = param_data.get("value")
                try:
                    parameter_table[param_name] = int(val.replace("'h", ""), 16) if isinstance(val, str) and val.startswith("'h") else int(val)
                except ValueError:
                    continue

        # Modules
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
                mod_meta = module.get("metadata", {})
                mod_name_str = mod_meta.get("name", module_name)
                mod_desc_str = mod_meta.get("description", "").strip()

                # === Module Documentation ===
                c_lines.append(f"// Module: {mod_name_str} ({module_name})")
                if mod_desc_str:
                    c_lines.append(f"// Module Description: {mod_desc_str}")
                py_lines.append(f"# Module: {mod_name_str} ({module_name})")
                if mod_desc_str:
                    py_lines.append(f"# Module Description: {mod_desc_str}")

                enum_name = f"{module_id}_REG"

                # C Enum Collection
                c_enum_entries = []
                c_addr_macros = []

                # Python Enum Block
                #py_lines.append(f"class {enum_name}(Enum):")
                py_enum_entries = []
                py_addr_lines = []

                for i in range(reg_count):
                    addr = start_addr + i * reg_width_bytes
                    reg_key = f"Reg{i}"
                    reg_info = module.get("regs", {}).get(reg_key, {})
                    reg_name_raw = reg_info.get("name", f"Reg{i}")
                    reg_desc = reg_info.get("description", "").strip()
                    reg_perm = reg_info.get("permissions", "").strip()
                    reg_name_id = sanitize_identifier(reg_name_raw)
                    entry_name = f"{module_id}_{reg_name_id}"

                    # C enum entry
                    comma = "," if i < reg_count - 1 else ""
                    c_enum_entries.append(f"    {entry_name} = {i}{comma} // {reg_name_raw}")
                    c_addr_macros.append(f"#define {entry_name}_ADDR 0x{addr:04X}")
                    if reg_desc:
                        c_addr_macros.append(f"// Register Description: {reg_desc}")
                    if reg_perm:
                        c_addr_macros.append(f"// Register Permissions: {reg_perm}")

                    # Python enum entry
                    py_enum_entries.append(f"    {entry_name} = {i}  # {reg_name_raw}")
                    py_addr_lines.append(f"{entry_name}_ADDR = 0x{addr:04X}")
                    if reg_desc:
                        #py_enum_entries.append(f"    #    {reg_desc}")
                        py_addr_lines.append(f"# Register Description: {reg_desc}")
                    if reg_perm:
                        py_addr_lines.append(f"# Register Permissions: {reg_perm}")
                    
                #c_lines.append(f"typedef enum {{")
                #c_lines.extend(c_enum_entries)
                #c_lines.append(f"}} {enum_name};\n")
                c_lines.extend(c_addr_macros)
                c_lines.append(f"const CompactRegisterBlock {module_id} = {{ 0x{start_addr:04X}, {reg_count}, {reg_width_bytes} }};\n")

                #py_lines.extend(py_enum_entries)
                py_lines.extend(py_addr_lines)
                py_lines.append(f"{module_id} = CompactRegisterBlock(0x{start_addr:04X}, {reg_count}, {reg_width_bytes})\n")

        with open(c_filename, "w") as f:
            f.write("\n".join(c_lines))
        print(f"C header saved to: {c_filename}")

        with open(py_filename, "w") as f:
            f.write("\n".join(py_lines))
        print(f"Python header saved to: {py_filename}\n")