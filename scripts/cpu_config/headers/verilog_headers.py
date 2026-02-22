import os
from collections import namedtuple

from cpu_config_helpers import sanitize_identifier
from registers import reorder_tree

def export_verilog_headers(parsed_configs, submodule_reg_map, directory_path, reg_width_bytes=4, user_modules_only=False, verilog_muxes=False, verilog_regs=False, strip_verilog=False):
    regs_package_mask_list = []
    mux_package_mask_list = []
    generate_files = True
    for cpu_name, cpu_config in parsed_configs.items():
        output_dir = cpu_name
        os.makedirs(f"{directory_path}/{output_dir}", exist_ok=True)
        current_submodule_map = reorder_tree(submodule_reg_map)[cpu_name]
        verilog_filename = os.path.join(directory_path, output_dir, f"{cpu_name}_muxes.sv")
        verilog_lines = []
        verilog_lines.append(f"// Auto-generated data mux modules and packages\n")
        #Case where function is called and no submodules are present
        try:
            submodule_separator = current_submodule_map[0].separator
        except:
            print(f"Warning: Verilog headers not generated due to no submodules")
            submodule_separator = " "
            generate_files = False
        mod_reg_package = []
        local_regs_package_mask_list = []
        local_mux_package_mask_list = []
        module_sections = ["USER_MODULES"] if user_modules_only else ["BUILTIN_MODULES", "USER_MODULES"]

        for section in module_sections:
            for module_name, module in cpu_config.get(section, {}).items():
                mod_regs = module.get("regs", {})
                mod_reg_offsets = []

                if not cpu_config[section][module_name]["metadata"].get("repeat_instance", ''):
                    for idx, _ in enumerate(mod_regs):
                        reg_key = f"Reg{idx}"
                        reg_info = module.get("regs", {}).get(reg_key, {})
                        reg_name = sanitize_identifier(reg_info.get('name',{})).lower()
                        mod_reg_offsets.append(f"localparam {reg_name}_offset = 'h{(idx*reg_width_bytes):04X};")
                    
                    module_name_stripped = str(module_name.split(submodule_separator)[-1])
                    stripped_name = module_name if not strip_verilog else module_name_stripped
                    if mod_reg_offsets:
                        if not local_regs_package_mask_list.count(stripped_name) > 1:
                            if not regs_package_mask_list.count(stripped_name) > 1:
                                mod_reg_offsets_joined = "\n    ".join(mod_reg_offsets)
                                regs_package_mask_list.append(stripped_name)
                                mod_reg_package.append(f"""\
package {stripped_name}_regs_package;
    {mod_reg_offsets_joined}

    function logic [31:0] get_address (
        input logic [31:0] BaseAddress,
        input logic [31:0] Offset
    );
        begin
            get_address = BaseAddress+Offset;
        end
    endfunction
endpackage                       
""")
                        else:
                           raise RuntimeError(f"Multiple definitions of module instance name: '{module_name}'. Please rename.") 

                if module_name == "BaseAddress" or not isinstance(module, dict):
                    continue
                if not any(x.module_parent == module_name for x in current_submodule_map):
                    continue
                if module.get("flag") != "TRUE" or "bounds" not in module:
                    continue
                try:
                    start_addr = module["bounds"][0]
                    end_addr = module["bounds"][1]
                except Exception:
                    continue

                reg_count = ((end_addr - start_addr) // reg_width_bytes) + 1
                subregisters = module.get("subregisters", "0")
                mod_meta = module.get("metadata", {})
                mod_name_str = mod_meta.get("name", module_name)
                mod_desc_str = mod_meta.get("description", "").strip()

                num_ports = 0
                offset = 0
                mod_params_data = []
                mod_params_base_addresses = []
                mod_params_reg_count = []
                mod_params_instances_tuple = namedtuple("mod_params_instances_tuple", ["module_name", "repeat_instance",])
                mod_num_instances = []
                mod_params_num_instances = []
                mod_input_ports = []
                mod_data_tuple = namedtuple("mod_data_tuple", ["index", "module_name",])
                mod_data_i_values = []
                mod_data_i_assignments = []

                if cpu_config[section][module_name]["metadata"].get("repeat_instance", ''):
                    continue

                if (reg_count-subregisters) >= 1: #Account for if the module itself has registers
                    stripped_name = str(module_name.split(submodule_separator)[-1])
                    stripped_module_name = stripped_name
                    stripped_name = module_name if not strip_verilog else module_name_stripped
                    if not local_mux_package_mask_list.count(stripped_name) > 1:
                        if not mux_package_mask_list.count(stripped_name) > 1:
                            mod_params_data.append(f"                   '{{'h{offset:04X}, {reg_count-subregisters}}}, // {stripped_module_name}\n")
                            mod_params_base_addresses.append(f"localparam {stripped_module_name}_offset = 'h{offset:04X};")
                            repeat_instance = cpu_config[section][module_name]["metadata"].get("repeat_instance", '')
                            if not repeat_instance:
                                mod_params_reg_count.append(f"localparam {stripped_module_name}_reg_count = {reg_count-subregisters};")
                                local_mux_package_mask_list.append(stripped_name)
                            mod_input_ports.append(f"input  logic [31:0] {stripped_module_name}_data_i,")
                            mod_data_i_values.append(mod_data_tuple(num_ports, stripped_module_name))
                            offset += (reg_count-subregisters)*reg_width_bytes
                            num_ports += 1
                    else:
                        raise RuntimeError(f"Multiple definitions of module instance name: '{module_name}'. Please rename.")

                for elements in current_submodule_map:
                    if module_name == elements.module_parent:
                        stripped_name = str(elements.module_name.split(submodule_separator)[-1])
                        stripped_module_name = stripped_name
                        stripped_name = elements.module_name if not strip_verilog else stripped_name
                        if not local_mux_package_mask_list.count(stripped_name) > 1:
                            if not mux_package_mask_list.count(stripped_name) > 1:
                                current_module_start_addr = cpu_config[section][elements.module_name]["bounds"][0]
                                current_module_end_addr = cpu_config[section][elements.module_name]["bounds"][1]
                                current_module_reg_count = ((current_module_end_addr - current_module_start_addr) // reg_width_bytes) + 1
                                mod_params_data.append(f"                   '{{'h{offset:04X}, {current_module_reg_count}}}, // {stripped_module_name}\n")
                                mod_params_base_addresses.append(f"localparam {stripped_module_name}_offset = 'h{offset:04X};")
                                repeat_instance = cpu_config[section][elements.module_name]["metadata"].get("repeat_instance", '')
                                if not repeat_instance:
                                    mod_params_reg_count.append(f"localparam {stripped_module_name}_reg_count = {current_module_reg_count};")
                                    local_mux_package_mask_list.append(stripped_name)
                                mod_num_instances.append(mod_params_instances_tuple(stripped_module_name, repeat_instance))
                                mod_input_ports.append(f"input  logic [31:0] {stripped_module_name}_data_i,")
                                mod_data_i_values.append(mod_data_tuple(num_ports, stripped_module_name))
                                num_ports += 1
                                offset += (current_module_reg_count)*reg_width_bytes
                        else:
                            raise RuntimeError(f"Multiple definitions of module instance name: '{stripped_name}'. Please rename.")

                mod_params_data[-1] = mod_params_data[-1].replace("},", "} ") #Remove comma from last entry
                mod_params_base_address_joined = "\n    ".join(mod_params_base_addresses)
                mod_params_reg_count_joined = "\n    ".join(mod_params_reg_count)

                mod_input_ports[-1] = mod_input_ports[-1].replace("},", "} ") #Remove comma from last entry
                mod_input_ports_joined = "\n    ".join(mod_input_ports)

                for elements in mod_data_i_values:
                    mod_data_i_assignments.append(f"assign data_i_gen[{elements.index}] = {elements.module_name}_data_i;")
                
                mod_params_num_instances_module_name = None
                num_instance_counter = 1
                for elements in mod_num_instances:
                    if not elements.repeat_instance:
                        if mod_params_num_instances_module_name is not None:
                            mod_params_num_instances.append(f"localparam {mod_params_num_instances_module_name}_num_instances = {num_instance_counter};")
                        mod_params_num_instances_module_name = elements.module_name
                        num_instance_counter = 1
                    else:
                        num_instance_counter += 1
                if mod_params_num_instances_module_name is not None:
                    mod_params_num_instances.append(f"localparam {mod_params_num_instances_module_name}_num_instances = {num_instance_counter};")

                mod_params_num_instances_joined = "\n    ".join(mod_params_num_instances)

                mod_data_i_assignments_joined = "\n    ".join(mod_data_i_assignments)

                if num_ports <= 1: #If num_ports 1 or less, no need for a mux
                    continue

                # Documentation
                verilog_lines.append(f"// Module: {mod_name_str} ({module_name.split(submodule_separator)[-1]})")
                if mod_desc_str:
                    desc_lines = mod_desc_str.split('\n')
                    formatted_desc = f"// Module Description: {desc_lines[0]}"
                    for line in desc_lines[1:]:
                        formatted_desc += f"\n//                     {line}"
                    verilog_lines.append(formatted_desc)

                verilog_boilerplate = f"""\
package {module_name if not strip_verilog else module_name.split(submodule_separator)[-1]}_mux_package;
    {mod_params_base_address_joined}
    {mod_params_reg_count_joined}
    {mod_params_num_instances_joined}
endpackage

module {module_name if not strip_verilog else module_name.split(submodule_separator)[-1]}_mux #(
    parameter BaseAddress = 0
)(
    input  logic        clk_i,
    input  logic        reset_i,
    input  logic [31:0] address_i,
    {mod_input_ports_joined}
    output logic [31:0] data_o

);
    typedef struct packed {{
        logic [31:0] base_offset;
        logic [31:0] num_regs;
    }} mux_t;

    localparam int unsigned NUM_PORTS = {num_ports};
    localparam mux_t MODULE_PARAMS [NUM_PORTS] = '{{\n{"".join(mod_params_data)}                }};

    logic [31:0] data_i_gen [NUM_PORTS];
    logic [31:0] data_o_gen;

    logic [$clog2(NUM_PORTS)-1:0] sel_index;
    logic [$clog2(NUM_PORTS)-1:0] sel_index_reg;
    logic                         address_hit;
    logic [31:0]                  start_addr;
    logic [31:0]                  end_addr;

    {mod_data_i_assignments_joined}

    always_comb begin
        sel_index = sel_index_reg;
        address_hit = 1'b0;

        for (int unsigned i = 0; i < NUM_PORTS; i++) begin
            start_addr = MODULE_PARAMS[i].base_offset + BaseAddress;
            end_addr   = MODULE_PARAMS[i].base_offset + BaseAddress + MODULE_PARAMS[i].num_regs*{reg_width_bytes};

            if (address_i >= start_addr && address_i < end_addr) begin
                sel_index = i;
                address_hit = 1'b1;
                break;
            end
        end
    end

    always_ff @(posedge clk_i) begin
        if (reset_i == 1'b1) begin
            sel_index_reg <= '0;
        end else if (address_hit == 1) begin
            sel_index_reg <= sel_index;
        end
    end

    always_comb begin
        data_o = '0;
        for (int unsigned i = 0; i < NUM_PORTS; i++) begin
            if (sel_index_reg == i) begin
                data_o = data_i_gen[i];
            end
        end
    end

endmodule
"""
                verilog_lines.append(verilog_boilerplate)

        for item in local_mux_package_mask_list:
            mux_package_mask_list.append(item)

        for item in local_regs_package_mask_list:
            regs_package_mask_list.append(item)

        if generate_files == True:
            with open(verilog_filename, "w") as f:
                if verilog_muxes:
                    f.write("\n".join(verilog_lines))
                if verilog_regs:
                    f.write("\n".join(mod_reg_package))
            print(f"Verilog mux modules and packages for {cpu_name} saved to: {verilog_filename}")