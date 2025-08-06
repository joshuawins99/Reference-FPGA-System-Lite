import re

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

    if re.search(r"[a-zA-Z_]\w*", expr):
        return None  # Still contains unresolved variables

    # Evaluate arithmetic expression
    try:
        result = eval(expr, {"__builtins__": None}, {})
        return result
    except Exception:
        print(f"[WARN] Could not evaluate expression: {expr}")
        return None

def build_parameter_table(parsed_configs):
    for cpu_name, cpu_config in parsed_configs.items():
        parameter_table = {}

        # Flatten all parameters
        all_parameters = {}
        for param_section in ["BUILTIN_PARAMETERS", "USER_PARAMETERS"]:
            all_parameters.update(cpu_config.get(param_section, {}))

        unresolved = {name: data.get("value") for name, data in all_parameters.items()}
        max_attempts = len(unresolved)

        for attempt in range(max_attempts):
            progress_made = False
            for name, val in list(unresolved.items()):
                try:
                    result = resolve_expression(val, parameter_table)
                    if result is not None:
                        resolved_value = int(result)
                        parameter_table[name] = resolved_value
                        unresolved.pop(name)
                        #print(f"[PASS {attempt+1}] Resolved {name} = {resolved_value}")
                        progress_made = True
                except Exception as e:
                    print(f"[ERROR] {name}: {e}")

            if not progress_made:
                #print(f"[INFO] No progress made on pass {attempt+1}")
                break

        for name, val in unresolved.items():
            print(f"[WARN] Unresolved: {name} = {val}")
            
    return parameter_table

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
        parameter_table = build_parameter_table(parsed_configs)

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

def dump_all_registers_from_configs(parsed_configs, file_path, file_name="cpu_registers.txt", print_to_console=True, save_to_file=False, reg_width_bytes=4, user_modules_only=False):
    """
    Resolves symbolic expressions and dumps register addresses with metadata for all CPUs.
    ASCII-only output with clean indentation and structured formatting.
    """
    lines = []
    lines.append("Register Address Map")
    lines.append("====================")

    for cpu_name, cpu_config in parsed_configs.items():
        lines.append("")
        lines.append(f"Instance: {cpu_name}")

        # Build parameter lookup
        parameter_table = build_parameter_table(parsed_configs)

        section_list = ["USER_MODULES"] if user_modules_only else ["BUILTIN_MODULES", "USER_MODULES"]

        for section in section_list:
            lines.append("")
            lines.append(f"    Section: {section}")

            for module_name, module in cpu_config.get(section, {}).items():
                if module_name == "BaseAddress" or not isinstance(module, dict):
                    continue
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

                # Module metadata
                mod_meta = module.get("metadata", {})
                mod_name_str = mod_meta.get("name", module_name)
                mod_desc_str = mod_meta.get("description", "")

                lines.append("")
                lines.append(f"        -> Module: {mod_name_str} ({module_name})")
                lines.append(f"            - Bounds: 'h{start_addr:04X} to 'h{end_addr:04X}")
                lines.append(f"            - Register Count: {reg_count}")
                if mod_desc_str:
                    indent = " " * 12
                    desc_lines = mod_desc_str.split('\n')
                    formatted_desc = f"{indent}- Description: {desc_lines[0]}"
                    for line in desc_lines[1:]:
                        formatted_desc += f"\n{indent}              {line}"
                    lines.append(formatted_desc)

                # Register metadata
                for i in range(reg_count):
                    reg_addr = start_addr + i * reg_width_bytes
                    reg_key = f"Reg{i}"
                    reg_info = module.get("regs", {}).get(reg_key, {})
                    reg_name_str = reg_info.get("name", f"Reg{i}")
                    reg_desc_str = reg_info.get("description", "")
                    reg_perm_str = reg_info.get("permissions", "")

                    lines.append("")
                    lines.append(f"            -> {reg_key}: {reg_name_str}")
                    lines.append(f"                - Address: 'h{reg_addr:04X}")
                    if reg_desc_str:
                        indent = " " * 16
                        desc_lines = reg_desc_str.split('\n')
                        formatted_desc = f"{indent}- Description: {desc_lines[0]}"
                        for line in desc_lines[1:]:
                            formatted_desc += f"\n{indent}              {line}"
                        lines.append(formatted_desc)
                    if reg_perm_str:
                        lines.append(f"                - Permissions: {reg_perm_str}")

    output = "\n".join(lines)
    if (print_to_console == True):
        print(output)

    if save_to_file:
        combined_file_path = file_path+"/"+file_name
        with open(combined_file_path, "w") as f:
            f.write(output)
        print(f"\nRegister map saved to: {file_path}")