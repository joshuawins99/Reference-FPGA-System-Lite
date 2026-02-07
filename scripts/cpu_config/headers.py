import os
import re
from registers import resolve_expression, build_parameter_table, reorder_tree

def sanitize_identifier(text):
        return re.sub(r'\W+', '_', text.strip()).upper()

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
        
        parameter_table = build_parameter_table(cpu_config)

        # Modules
        module_sections = ["USER_MODULES"] if user_modules_only else ["BUILTIN_MODULES", "USER_MODULES"]

        for section in module_sections:
            for module_name, module in cpu_config.get(section, {}).items():
                if module_name == "BaseAddress" or not isinstance(module, dict):
                    continue
                if module.get("flag") != "TRUE" or "bounds" not in module:
                    continue
                if any(x.module_name == module_name for x in current_submodule_map):
                    continue
                try:
                    start_addr = resolve_expression(module["bounds"][0], parameter_table)
                    end_addr = resolve_expression(module["bounds"][1], parameter_table)
                except Exception:
                    continue

                reg_count = ((end_addr - start_addr) // reg_width_bytes) + 1
                subregisters = int(resolve_expression(module.get("subregisters", "0"), parameter_table))
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
        
        with open(zig_filename, "w") as f:
            f.write("\n".join(zig_lines))
        print(f"Zig header for {cpu_name} saved to: {zig_filename}")

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

        # Parameter Table
        parameter_table = build_parameter_table(cpu_config)

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
                    start_addr = resolve_expression(module["bounds"][0], parameter_table)
                    end_addr = resolve_expression(module["bounds"][1], parameter_table)
                except Exception:
                    continue

                reg_count = ((end_addr - start_addr) // reg_width_bytes) + 1
                subregisters = int(resolve_expression(module.get("subregisters", "0"), parameter_table))
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

def export_python_headers(parsed_configs, submodule_reg_map, directory_path, reg_width_bytes=4, user_modules_only=False, new_python_header=False):
    for cpu_name, cpu_config in parsed_configs.items():
        output_dir = cpu_name
        os.makedirs(f"{directory_path}/{output_dir}", exist_ok=True)
        current_submodule_map = reorder_tree(submodule_reg_map)[cpu_name]

        py_filename = os.path.join(directory_path, output_dir, f"{cpu_name}_registers.py")

        py_lines = []
        module_storage = []

        # Python Header Boilerplate
        if not new_python_header:
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
        else:
            py_lines.append("""\
# Auto-generated register map header
from enum import Enum

class BitField:
    def __init__(self, fields):
        # fields: list of tuples (name, pos, length, [desc])
        self.fields = {}
        for field in fields:
            name, pos, length = field[:3]
            desc = field[3] if len(field) > 3 else ''
            self.fields[name] = (pos, length, desc)

    def extract(self, value):
        result = {}
        for name, (pos, length, _) in self.fields.items():
            mask = (1 << length) - 1
            result[name] = (value >> pos) & mask
        return result

    def modify(self, original_value, updates):
        value = original_value
        for name, new_val in updates.items():
            if name not in self.fields:
                raise KeyError(f"Bit field '{name}' not defined")
            pos, length, _ = self.fields[name]
            mask = ((1 << length) - 1) << pos
            value = (value & ~mask) | ((new_val << pos) & mask)
        return value

class BitProxy:
    def __init__(self, register, name, pos, length, description=''):
        self.register = register
        self.name = name
        self.pos = pos
        self.length = length
        self.description = description

    def read(self, interface=None):
        iface = interface or Register.interface
        if 'R' not in self.register.permission:
            raise PermissionError(f"Bit field '{self.name}' is write-only")
        full_value = iface.read(self.register.address)
        mask = (1 << self.length) - 1
        return (full_value >> self.pos) & mask

    def write(self, value, interface=None):
        iface = interface or Register.interface
        if 'W' not in self.register.permission:
            raise PermissionError(f"Bit field '{self.name}' is read-only")
        current = iface.read(self.register.address)
        mask = ((1 << self.length) - 1) << self.pos
        new_value = (current & ~mask) | ((value << self.pos) & mask)
        iface.write(self.register.address, new_value)

class Register:
    interface = None

    def __init__(self, name, address, permission, description='', bitfield=None):
        self.name = name
        self.address = address
        if not permission:
            self.permission = 'R/W'
        elif permission in ('R', 'W', 'R/W'):
            self.permission = permission
        else:
            self.permission = 'R/W'
        self.description = description
        self.bitfield = bitfield

        if bitfield:
            for field_name, (pos, length, desc) in bitfield.fields.items():
                proxy = BitProxy(self, field_name, pos, length, desc)
                setattr(self, field_name, proxy)

    def read(self, interface=None):
        iface = interface or Register.interface
        if 'R' not in self.permission:
            raise PermissionError(f"Register '{self.name}' is write-only")
        return iface.read(self.address)

    def write(self, value, interface=None):
        iface = interface or Register.interface
        if 'W' not in self.permission:
            raise PermissionError(f"Register '{self.name}' is read-only")
        iface.write(self.address, value)

class CompactRegisterBlock:
    def __init__(self, base, count, address_wording, module_defs=None, register_defs=None, sub_blocks=None):
        self.base = base
        self.count = count
        self.address_wording = address_wording
        self.name = module_defs[0] if module_defs else None
        self.desc = module_defs[1] if module_defs else None
        self._registers = {}
        self._sub_blocks = {}
        self._offsets = {}
        self._bit_proxies = {}

        # Initialize registers
        if register_defs:
            for i, reg_def in enumerate(register_defs):
                if i >= count:
                    raise ValueError(f'Too many register definitions for count={count}')
                name, perm = reg_def[0], reg_def[1]
                desc = reg_def[2] if len(reg_def) > 2 else ''
                bitfield_def = reg_def[3] if len(reg_def) > 3 else None
                addr = (self.base + reg_def[4]) if len(reg_def) > 4 else self.reg_at(i)
                self._offsets[name.lower()] = reg_def[4] if len(reg_def) > 4 else None
                bitfield = BitField(bitfield_def) if bitfield_def else None
                reg = Register(name, addr, perm, desc, bitfield)
                self._registers[name.lower()] = reg
                setattr(self, name.lower(), reg)
                if bitfield:
                    for field_name, (pos, length, desc) in bitfield.fields.items():
                        proxy = BitProxy(reg, field_name, pos, length, desc)
                        self._bit_proxies[f"{name.lower()}.{field_name}"] = proxy
                        setattr(reg, field_name, proxy)

        # Initialize nested blocks
        if sub_blocks:
            for block_def in sub_blocks:
                name, offset, block = block_def
                block._rebase(self.base + offset)
                self._sub_blocks[name.lower()] = block
                setattr(self, name.lower(), block)

    def reg_at(self, index):
        if index >= self.count:
            raise IndexError(f'Register index {index} out of bounds (max {self.count - 1})')
        return self.base + index * self.address_wording

    def reg(self, index):
        if index >= self.count:
            raise IndexError(f'Register index {index} out of bounds (max {self.count - 1})')
        addr = self.base + index * self.address_wording
        return Register(f'reg_{index}', addr, 'R/W')

    def __getitem__(self, name):
        name = name.lower()
        if name in self._registers:
            return self._registers[name]
        elif name in self._sub_blocks:
            return self._sub_blocks[name]
        raise KeyError(f"No register or sub-block named '{name}'")

    def __dir__(self):
        return sorted(
            list(self._registers.keys()) +
            list(self._sub_blocks.keys()) +
            ['describe', 'reg_at', 'reg']
        )

    def _rebase(self, new_base):
        offset_delta = new_base - self.base
        old_base = self.base
        self.base = new_base

        # Rebase registers
        for i, (name, reg) in enumerate(self._registers.items()):
            offset = self._offsets.get(name)
            if offset is not None:
                reg.address = self.base + offset
            else:
                reg.address = self.reg_at(i)

        # Rebase sub-blocks recursively
        for name, block in self._sub_blocks.items():
            relative_offset = block.base - old_base
            block._rebase(new_base + relative_offset)

    def describe(self, indent=0):
        pad = '  ' * indent
        if self.name:
            print(f"{pad}Module Name: {self.name}")
        if self.desc:
            desc_lines = self.desc.splitlines()

            prefix = f"{pad}Module Description: "
            first_line = f"{prefix}{desc_lines[0]}"
            print(first_line)

            # indent subsequent lines to align with the description text
            subsequent_indent = ' ' * len(prefix)

            for line in desc_lines[1:]:
                print(f"{subsequent_indent}{line}")

        print(f"{pad}Register Block @ 0x{self.base:04X} ({self.count} registers):")
        for name, reg in self._registers.items():
            if reg.description:
                desc_lines = reg.description.splitlines()
                prefix = f"{pad}  {name} @ 0x{reg.address:04X} [{reg.permission}]"
                dash = " - "  # include the space after the dash
                first_line = f"{prefix}{dash}{desc_lines[0]}"
                print(first_line)

                # indent so subsequent lines start exactly after " - "
                subsequent_indent = ' ' * (len(prefix) + len(dash))

                for line in desc_lines[1:]:
                    print(f"{subsequent_indent}{line}")
            else:
                print(f"{pad}  {name} @ 0x{reg.address:04X} [{reg.permission}]")
            if reg.bitfield:
                for field_name, (pos, length, desc) in reg.bitfield.fields.items():
                    prefix = f"{pad}    BitField '{field_name}': bits [{pos+length-1}:{pos}]"
                    dash = " - "
                    if desc:
                        desc_lines = desc.splitlines()

                        # first line
                        first_line = f"{prefix}{dash}{desc_lines[0]}"
                        print(first_line)

                        # indent subsequent lines so they align with description text
                        subsequent_indent = ' ' * (len(prefix) + len(dash))

                        for line in desc_lines[1:]:
                            print(f"{subsequent_indent}{line}")
                    else:
                        print(prefix)
        for name, block in self._sub_blocks.items():
            print(f"{pad}  Sub-block '{name}' @ 0x{block.base:04X}:")
            block.describe(indent + 2)

class TransportInterface:
    def write(self, data: str):
        raise NotImplementedError
    def read(self) -> str:
        raise NotImplementedError

class SerialTransport(TransportInterface):
    def __init__(self, serial_obj):
        self.serial = serial_obj
    def write(self, data: str):
        self.serial.write(data.encode('utf-8'))
    def read(self) -> str:
        # ASCII text
        read_data = self.serial.readline()
        return read_data.decode('utf-8').strip()
    def read_raw(self) -> bytes:
        # raw bytes
        return self.serial.readline()

class FPGAInterface:
    def __init__(self, transport: TransportInterface, queue_enabled=0):
        self.transport = transport
        self.queue_enabled = queue_enabled
        Register.interface = self

    def read(self, address):
        cmd = f"rFPGA,{int(address)}\\n"
        self.transport.write(cmd)
        if self.queue_enabled == 0:
            read_data = self.transport.read()
            if not read_data:
                return "Read Error"
            return int(read_data)

    def write(self, address, value):
        cmd = f"wFPGA,{int(address)},{int(value)}\\n"
        self.transport.write(cmd)
                            
    def version(self):
        cmd = f"readFPGAVersion\\n"
        self.transport.write(cmd)
        return self.transport.read()
    
    def __dir__(self):
        # Collect all callable methods (functions)
        funcs = [
            name for name in dir(type(self))
            if callable(getattr(type(self), name, None)) and not name.startswith("_")
        ]
        funcs += [
            name for name, val in self.__dict__.items()
            if callable(val) and not name.startswith("_")
        ]

        # Collect all register blocks (instances of CompactRegisterBlock)
        blocks = [
            name for name, val in self.__dict__.items()
            if isinstance(val, CompactRegisterBlock)
        ]
        blocks += [
            name for name in dir(type(self))
            if isinstance(getattr(type(self), name, None), CompactRegisterBlock)
        ]

        return sorted(set(funcs + blocks))

    def list_blocks(self):
        # Look at both instance and class attributes
        blocks = []

        # Instance-level
        for name, obj in self.__dict__.items():
            if isinstance(obj, CompactRegisterBlock):
                blocks.append((name, obj))

        # Class-level
        for name, obj in vars(type(self)).items():
            if isinstance(obj, CompactRegisterBlock):
                blocks.append((name, obj))

        if not blocks:
            print("No CompactRegisterBlock instances found.")
            return

        print("Available Modules (Sorted By Base Address):")
        for name, block in sorted(blocks, key=lambda item: item[1].base):
            print(f"    {name} - {block.count} register(s) @ 0x{block.base:04X}")
        """)
            
        temp_module_storage = []

        # Parameter Table
        parameter_table = build_parameter_table(cpu_config)

        # Modules
        module_sections = ["USER_MODULES"] if user_modules_only else ["BUILTIN_MODULES", "USER_MODULES"]

        for section in module_sections:
            for module_name, module in cpu_config.get(section, {}).items():
                temp_module_storage = []
                if module_name == "BaseAddress" or not isinstance(module, dict):
                    continue
                if module.get("flag") != "TRUE" or "bounds" not in module:
                    continue
                if any(x.module_name == module_name for x in current_submodule_map) and not new_python_header:
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
                temp_module_storage.append(f"# Module: {mod_name_str} ({module_name})")
                if mod_desc_str:
                    desc_lines = mod_desc_str.split('\n')
                    formatted_desc = f"# Module Description: {desc_lines[0]}"
                    for line in desc_lines[1:]:
                        formatted_desc += f"\n#                     {line}"
                    temp_module_storage.append(formatted_desc)

                py_addr_lines = []

                py_lines.extend(py_addr_lines)
                if not new_python_header:
                    py_lines.append(f"{module_id} = CompactRegisterBlock(0x{start_addr:04X}, {reg_count}, {reg_width_bytes})\n")
                else:
                    #Submodule specific Logic
                    subblock_name = None
                    hidden_entry_prefix = ""
                    if any(x.module_name == module_name for x in current_submodule_map) and module.get("submodule_of", "") or any(x.base_module == module_name for x in current_submodule_map):
                        current_module = ""
                        subblock_placed = False
                        for idx, entry in enumerate(current_submodule_map):
                            if entry.module_parent == module_name and cpu_config[entry.section][entry.module_name]["flag"] == 'TRUE':
                                if entry.base_reg_exp == 'TRUE':
                                    continue
                                sub_module = str(entry.module_name.split(entry.separator)[-1])
                                get_current_addr = module.get("bounds")
                                get_sub_addr = cpu_config[entry.section][entry.module_name]["bounds"]
                                offset_from_base = resolve_expression(get_sub_addr[0], parameter_table)-resolve_expression(get_current_addr[0], parameter_table)
                                if current_module != module_id:
                                    current_module = module_id
                                    temp_module_storage.append(f"_{module_id}_subblocks = [")
                                    subblock_placed = True
                                temp_module_storage.append(f"    ('{sub_module}', {offset_from_base}, _{entry.module_name}),")
                            if idx == len(current_submodule_map)-1 and subblock_placed:
                                temp_module_storage.append(f"]")
                        if subblock_placed == True:
                            subblock_name = f"_{module_id}_subblocks"
                    hidden_entry_prefix = "_"
                    #Normal Module Logic
                    register_defs = []
                    if (mod_reg_expand_str == 'FALSE' or (mod_repeat_inst == 'TRUE' and mod_repeat_info["expand_regs"] == 'FALSE' and mod_reg_expand_str == 'FALSE')):
                        field_defs = []
                        for i in range(reg_count):
                            reg_key = f"Reg{i}"
                            reg_info = module.get("regs", {}).get(reg_key, {})
                            field_info = reg_info.get("fields")
                            reg_fields = []
                            if field_info:
                                for field_name, field_data in field_info.items():
                                    try:
                                        upper_bounds = resolve_expression(field_data['bounds'][0], parameter_table)
                                        lower_bounds = resolve_expression(field_data['bounds'][1], parameter_table)
                                        if upper_bounds < 0 or lower_bounds < 0 or upper_bounds == None or lower_bounds == None:
                                            raise SyntaxError(f"Field Bounds for {module_name} is not valid")
                                        width = abs(upper_bounds - lower_bounds)+1
                                    except Exception:
                                        raise SyntaxError(f"Field Bounds for {module_name} is not valid")
                                    field_name = sanitize_identifier(field_data.get('name', ''))
                                    reg_fields.append((field_name.lower(), lower_bounds, width, field_data.get('description', '')))
                            else:
                                reg_fields.append((None, None, None, None))
                            field_defs.append(reg_fields)
                            reg_name_raw = reg_info.get("name", f"Reg{i}")
                            reg_name_id = sanitize_identifier(reg_name_raw)
                            if (re.fullmatch(r'REG\d+', reg_name_id)): #Check for default name. Assume it shouldn't be exposed if it is
                                continue
                            reg_perm = reg_info.get("permissions", "").strip()
                            reg_desc = reg_info.get("description", "").strip()
                            if reg_perm not in ("R", "W", "R/W"):
                                reg_perm = "R/W"
                            register_defs.append((reg_name_id.lower(), reg_perm, reg_desc))
                        if not(all(i[0] == '' for i in register_defs)): #Check to see if register name field is empty. If so, dont add register_defs
                            temp_module_storage.append(f"_{module_id}_reg_defs = [")
                            for idx, (name, perm, desc) in enumerate(register_defs):
                                fields = field_defs[idx]
                                if not (len(fields) == 1 and all(v is None for v in fields[0])):
                                    formatted_fields = "[\n"
                                    for f_name, f_low, f_width, f_desc in fields:
                                        formatted_fields += f"    ({repr(f_name)}, {repr(f_low)}, {repr(f_width)}, {repr(f_desc)}),\n"
                                    formatted_fields += "]"
                                    line = f"({repr(name)}, {repr(perm)}, {repr(desc)}, {formatted_fields})"
                                else:
                                    line = f"({repr(name)}, {repr(perm)}, {repr(desc)})"
                                if idx < len(register_defs)-1:
                                    temp_module_storage.append(line + ",")
                                else:
                                    temp_module_storage.append(line)
                                    temp_module_storage.append(f"]")
                    if register_defs:
                        temp_module_storage.append(f"{hidden_entry_prefix}{module_id.lower()} = CompactRegisterBlock(0x{start_addr:04X}, {reg_count}, {reg_width_bytes}, {(mod_name_str,mod_desc_str)}, _{module_id}_reg_defs, {subblock_name})\n")
                    else:
                        temp_module_storage.append(f"{hidden_entry_prefix}{module_id.lower()} = CompactRegisterBlock(0x{start_addr:04X}, {reg_count}, {reg_width_bytes}, {(mod_name_str,mod_desc_str)}, None, {subblock_name})\n")
                    if not(any(x.module_name == module_name for x in current_submodule_map)):
                        temp_module_storage.append(f"FPGAInterface.{module_id.lower()} = _{module_id.lower()}")
                    module_storage[0:0] = temp_module_storage

        for entry in module_storage:
            py_lines.append(entry)

        with open(py_filename, "w") as f:
            f.write("\n".join(py_lines))
        print(f"Python header for {cpu_name} saved to: {py_filename}\n")

def export_per_cpu_headers(parsed_configs, submodule_reg_map, directory_path, reg_width_bytes=4, user_modules_only=False, new_python_header=False, new_c_header=False, zig_header=False):
    
    export_c_headers(parsed_configs=parsed_configs, submodule_reg_map=submodule_reg_map, directory_path=directory_path, reg_width_bytes=reg_width_bytes, user_modules_only=user_modules_only, new_c_header=new_c_header)
    export_python_headers(parsed_configs=parsed_configs, submodule_reg_map=submodule_reg_map, directory_path=directory_path, reg_width_bytes=reg_width_bytes, user_modules_only=user_modules_only, new_python_header=new_python_header)
    if zig_header:
        export_zig_headers(parsed_configs=parsed_configs, submodule_reg_map=submodule_reg_map, directory_path=directory_path, reg_width_bytes=reg_width_bytes, user_modules_only=user_modules_only)
