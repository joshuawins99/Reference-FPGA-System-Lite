import os
import re

from cpu_config_helpers import sanitize_identifier
from registers import reorder_tree

def export_zig_headers(parsed_configs, submodule_reg_map, directory_path, reg_width_bytes=4, user_modules_only=False):
    for cpu_name, cpu_config in parsed_configs.items():
        output_dir = cpu_name
        os.makedirs(f"{directory_path}/{output_dir}", exist_ok=True)
        current_submodule_map = reorder_tree(submodule_reg_map)[cpu_name]

        zig_filename = os.path.join(directory_path, output_dir, f"{cpu_name}_registers.zig")
        zig_lines = []

        # Zig Header Boilerplate
        zig_lines.append("""\
// Auto-generated register map header
pub const CompactRegisterBlock = struct {
    base: usize,
    count: usize,
    address_wording: usize,

    pub inline fn init(base: usize, count: usize, address_wording: usize) CompactRegisterBlock {
        return CompactRegisterBlock{
            .base = base,
            .count = count,
            .address_wording = address_wording,
        };
    }

    pub inline fn regAt(self: CompactRegisterBlock, index: usize) usize {
        return self.base + index * self.address_wording;
    }
};        
               
pub const Register = struct {
    block: CompactRegisterBlock,
    offset: usize,
    perm: Permission,

    pub const Permission = enum {
        ReadOnly,   // "R"
        WriteOnly,  // "W"
        ReadWrite,  // "R/W"
    };

    pub inline fn addr(self: Register) usize {
        return self.block.regAt(self.offset);
    }

    pub inline fn write32(self: Register, val: u32) void {
        if (self.perm == .ReadOnly)
            @compileError("Attempt to write to a read-only register");
        const ptr: *volatile u32 = @ptrFromInt(self.addr());
        ptr.* = val;
    }

    pub inline fn read32(self: Register) u32 {
        if (self.perm == .WriteOnly)
            @compileError("Attempt to read from a write-only register");
        const ptr: *volatile u32 = @ptrFromInt(self.addr());
        return ptr.*;
    }

    pub inline fn write8(self: Register, val: u8) void {
        if (self.perm == .ReadOnly)
            @compileError("Attempt to write to a read-only register");
        const ptr: *volatile u8 = @ptrFromInt(self.addr());
        ptr.* = val;
    }

    pub inline fn read8(self: Register) u8 {
        if (self.perm == .WriteOnly)
            @compileError("Attempt to read from a write-only register");
        const ptr: *volatile u8 = @ptrFromInt(self.addr());
        return ptr.*;
    }
};                    
""")

        array_mask = []

        # Modules
        module_sections = ["USER_MODULES"] if user_modules_only else ["BUILTIN_MODULES", "USER_MODULES"]

        for section in module_sections:
            for module_name, module in cpu_config.get(section, {}).items():
                if module_name == "BaseAddress" or not isinstance(module, dict):
                    continue
                if module.get("flag") != "TRUE" or "bounds" not in module:
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
                zig_lines.append(f"// Module: {mod_name_str} ({module_name})")
                if mod_desc_str:
                    desc_lines = mod_desc_str.split('\n')
                    formatted_desc = f"// Module Description: {desc_lines[0]}"
                    for line in desc_lines[1:]:
                        formatted_desc += f"\n//                     {line}"
                    zig_lines.append(formatted_desc)

                if (mod_reg_expand_str == 'FALSE' or (mod_repeat_inst == 'TRUE' and mod_repeat_info["expand_regs"] == 'FALSE' and mod_reg_expand_str == 'FALSE')):
                    if any(x.module_name == module_name for x in current_submodule_map) and module.get("submodule_of", ""): #Make submodules private
                        zig_lines.append(f"const {module_id.lower()} = struct {{")
                    else:
                        zig_lines.append(f"pub const {module_id.lower()} = struct {{")
                    for idx, entry in enumerate(current_submodule_map):
                        if entry.module_parent == module_name:
                            full_submodule_name = entry.module_name
                            sub_module = str(full_submodule_name.split(entry.separator)[-1])
                            zig_lines.append(f"    pub const {sub_module} = {full_submodule_name};")
                    zig_lines.append(f"    pub const block = CompactRegisterBlock.init(0x{start_addr:04X}, {reg_count}, {reg_width_bytes});")
                    modified_range_reg_count = max(1, reg_count - subregisters)
                    for i in range(modified_range_reg_count):
                        reg_key = f"Reg{i}"
                        reg_info = module.get("regs", {}).get(reg_key, {})
                        reg_name_raw = reg_info.get("name", f"Reg{i}")
                        reg_perm = reg_info.get("permissions", "").strip()
                        reg_name_id = sanitize_identifier(reg_name_raw)
                        reg_perm_zig = ""
                        if reg_perm:
                            if reg_perm == "R":
                                reg_perm_zig = "ReadOnly"
                            if reg_perm == "W":
                                reg_perm_zig = "WriteOnly"
                            if reg_perm == "R/W":
                                reg_perm_zig = "ReadWrite"
                        else:
                            reg_perm_zig = "ReadWrite"
                        if i < (reg_count-subregisters)-1 and (reg_count-subregisters) > 0:
                            zig_lines.append(f"    pub const {reg_name_id.lower()} = Register{{ .block = block, .offset = {i}, .perm = .{reg_perm_zig} }};")
                        else:
                            if (reg_count-subregisters) > 0:
                                zig_lines.append(f"    pub const {reg_name_id.lower()} = Register{{ .block = block, .offset = {i}, .perm = .{reg_perm_zig} }};")
                            zig_lines.append(f"}};\n")
                else:
                    zig_lines.append(f"pub const {module_id.lower()} = struct {{")
                    zig_lines.append(f"    pub const block = CompactRegisterBlock.init(0x{start_addr:04X}, {reg_count}, {reg_width_bytes});")
                    zig_lines.append(f" }};\n")

                #Generate Repeat Module Arrays
                if not mod_repeat_info.get("value", {}) and subregisters > 0:
                    adding_array = 0
                    for entry in current_submodule_map:
                        if entry.module_parent == module_name and cpu_config.get(section, {}).get(entry.module_name).get("repeat", {}).get("value", None):
                            if adding_array == 0:
                                zig_lines.append(f"// Repeat Instance Iterable Array(s) of {entry.module_parent}")
                            module_name_stripped = entry.module_name.split(entry.separator)[-1]
                            base_module_match = re.match(r"(.+?)(?:_\d+)?$", module_name_stripped)
                            base_module = base_module_match.group(1)
                            if module_name_stripped == base_module:
                                array_name = entry.module_name.split(entry.separator)[-1]
                                array_count = array_mask.count(array_name)
                                array_iterator = f"_{array_count}" if array_count != 0 else ""
                                zig_lines.append(f"pub const {array_name}_array{array_iterator} = [_]type {{")
                                array_mask.append(array_name)
                                adding_array = 1
                                for entry in current_submodule_map:
                                    if entry.module_parent == module_name and cpu_config.get(section, {}).get(entry.module_name).get("repeat", {}).get("value", None) and adding_array == 1:
                                        module_name_stripped = entry.module_name.split(entry.separator)[-1]
                                        if module_name_stripped == base_module or module_name_stripped.startswith(base_module + "_"):
                                            zig_lines.append(f"    {entry.module_name},")
                                if adding_array == 1:
                                    zig_lines[-1] = zig_lines[-1].replace(",", "") #Remove comma from last entry
                                    zig_lines.append(f"}};\n")
        
        with open(zig_filename, "w") as f:
            f.write("\n".join(zig_lines))
        print(f"Zig header for {cpu_name} saved to: {zig_filename}")