#!/usr/bin/env python3
import os
import subprocess
import shutil
import argparse
from cpu_config_parser import *
from verilog import *
from registers import *
from headers import *

config_file_names = ["cpu_config.txt", "cpu_config.cfg"]

directory_path = "."
build_script = "build_single_module.sh"
reference_system_file = "ref_fpga_sys_lite.sv"

parser = argparse.ArgumentParser(prog="generate_cpu_instance.py", description="Generate CPU Instance", add_help=False,
                                 formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=50))
parser.add_argument( "--help", action="help", help="Show this help message and exit")
parser.add_argument("--build", action='store_true', help="Build CPU Code and create combined output sv")
parser.add_argument("--configs-path", help="Config directories path")
parser.add_argument("--gen-headers", nargs="+", help="Generate header files. Options are: new-python, new-c, zig, verilog-muxes, verilog-regs, strip-verilog")
parser.add_argument("--print-all-registers", action='store_true', help="Prints all registers to console")
parser.add_argument("--print-user-registers", action='store_true', help="Prints user registers to console")
parser.add_argument("--save-all-registers", action='store_true', help="Saves all registers to a cpu_registers.txt file")
parser.add_argument("--save-user-registers", action='store_true', help="Saves user registers to a cpu_registers.txt file")

args = parser.parse_args()

if args.configs_path:
    directory_path = args.configs_path

absolute_path = os.path.abspath(directory_path)

#folders = list_folders(directory_path)
#print(folders)

config_files = check_config_files(absolute_path, config_file_names)
#print(config_files)
if not any(config_files.values()):
    raise FileNotFoundError("No Config Files Found")

filtered_dirs = [dir_name for dir_name in config_files if config_files.get(dir_name)]
#print(filtered_dirs)

parsed_configs, submodule_reg_map = process_configs(absolute_path, config_file_names)
#print(parsed_configs)
assign_auto_addresses(parsed_configs, submodule_reg_map)
#print(parsed_configs)

if args.print_all_registers:
    if (filtered_dirs):
        dump_all_registers_from_configs(parsed_configs, submodule_reg_map, absolute_path, user_modules_only=False)

if args.save_all_registers:
    if (filtered_dirs):
        dump_all_registers_from_configs(parsed_configs, submodule_reg_map, absolute_path, user_modules_only=False, save_to_file=True,print_to_console=False)

if args.print_user_registers:
    if (filtered_dirs):
        dump_all_registers_from_configs(parsed_configs, submodule_reg_map, absolute_path, user_modules_only=True)

if args.save_user_registers:
    if (filtered_dirs):
        dump_all_registers_from_configs(parsed_configs, submodule_reg_map, absolute_path, user_modules_only=True, save_to_file=True, print_to_console=True)

zig_header = False
if args.gen_headers:
    new_python_header = False
    new_c_header = False
    verilog_muxes = False
    verilog_regs = False
    strip_verilog = False
    for header in args.gen_headers:
        match header:
            case "strip-verilog": #Strips cpu name from prefix of generated packages and modules
                strip_verilog = True
            case "new-python":
                new_python_header = True
            case "new-c":
                new_c_header = True
            case "zig":
                zig_header = True
            case "verilog-muxes":
                verilog_muxes = True
            case "verilog-regs":
                verilog_regs = True
    
    if (filtered_dirs):
        export_per_cpu_headers(parsed_configs, submodule_reg_map, absolute_path, user_modules_only=False, 
                               new_python_header=new_python_header, new_c_header=new_c_header, zig_header=zig_header, 
                               verilog_muxes=verilog_muxes, verilog_regs=verilog_regs, strip_verilog=strip_verilog) 

c_code_folders = get_c_code_folders(parsed_configs)
#print(c_code_folders)

default_c_code_path = "C_Code"  #Default Folder

def go_up_n_levels(path, levels):
    for _ in range(levels):
        path = os.path.dirname(path)
    return path

current_directory = os.path.abspath(__file__)

if args.build:
    if os.path.exists(f"{go_up_n_levels(current_directory,3)}/{build_script}"):
        default_c_code_path = os.path.join(current_directory,go_up_n_levels(current_directory,3),default_c_code_path)
        if (filtered_dirs):
            for cpu_name in filtered_dirs:
                config_folder = c_code_folders.get(cpu_name)
                build_folder = (
                    os.path.join(absolute_path, cpu_name, config_folder)
                    if config_folder
                    else default_c_code_path
                )
                build_folder = os.path.abspath(build_folder)
                parent_directory = go_up_n_levels(current_directory,3)
                print(f"Running build for {cpu_name} using C Code folder: {build_folder}\n")
                try:
                    if args.gen_headers:
                        if (build_folder != default_c_code_path): 
                            if os.path.exists(f"{build_folder}/{cpu_name}_registers.h"):
                                os.remove(f"{build_folder}/{cpu_name}_registers.h")
                            print(f"Moved generated header: {absolute_path}/{cpu_name}/{cpu_name}_registers.h -> {build_folder}\n")
                            shutil.move(f"{absolute_path}/{cpu_name}/{cpu_name}_registers.h", build_folder)
                            if zig_header:
                                if os.path.exists(f"{build_folder}/{cpu_name}_registers.zig"):
                                    os.remove(f"{build_folder}/{cpu_name}_registers.zig")
                                print(f"Moved generated header: {absolute_path}/{cpu_name}/{cpu_name}_registers.zig -> {build_folder}\n")
                                shutil.move(f"{absolute_path}/{cpu_name}/{cpu_name}_registers.zig", build_folder)
                    result = subprocess.run(["bash", f"{build_script}", "--c-folder", build_folder], cwd=parent_directory, capture_output=True, text=True)
                    print(result.stdout + result.stderr)
                except FileNotFoundError:
                    raise FileNotFoundError (f"Build folder not found for {cpu_name}: {build_folder}")

                curr_config_dict = {cpu_name: parsed_configs.get(cpu_name)}
                save_systemverilog_files(curr_config_dict, submodule_reg_map, absolute_path)
                update_cpu_modules_file(curr_config_dict, absolute_path, reference_file=f"{parent_directory}/{reference_system_file}")
                subprocess.run(["bash", "-c", "git clean -fdx"], cwd=parent_directory, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        raise FileNotFoundError(f"{go_up_n_levels(current_directory,3)}/{build_script} not found. Are you using the source repo?")

else:
    if os.path.exists(f"{go_up_n_levels(current_directory,1)}/{reference_system_file}"):
        if (filtered_dirs):
            save_systemverilog_files(parsed_configs, submodule_reg_map, absolute_path)
            update_cpu_modules_file(parsed_configs, absolute_path, reference_file=reference_system_file)
    else:
        raise FileNotFoundError(f"{go_up_n_levels(current_directory,1)}/{reference_system_file} not found. Are you using a release build?")


#systemverilog_output = generate_systemverilog(parsed_configs)
#print(systemverilog_output)
