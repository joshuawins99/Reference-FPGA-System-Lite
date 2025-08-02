#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil
from cpu_config_parser import *
from verilog import *
from registers import *
from headers import *

config_file_names = ["cpu_config.txt", "cpu_config.cfg"]

directory_path = "."
build_script = "build_single_module.sh"

if "--configs-path" in sys.argv:
    index = sys.argv.index("--configs-path")
    if index + 1 < len(sys.argv):
        path = sys.argv[index + 1]
        directory_path = path      
    else:
        assert False, "No path provided after --configs-path"

absolute_path = os.path.abspath(directory_path)

#folders = list_folders(directory_path)
#print(folders)

config_files = check_config_files(absolute_path, config_file_names)
#print(config_files)
if not any(config_files.values()):
    assert False, "Error: No Config Files Found"

filtered_dirs = [dir_name for dir_name in config_files if config_files.get(dir_name)]
#print(filtered_dirs)

parsed_configs = process_configs(absolute_path, config_file_names)
#print(parsed_configs)
assign_auto_addresses(parsed_configs)
#print(parsed_configs)

if "--print-all-registers" in sys.argv:
    if (filtered_dirs):
        dump_all_registers_from_configs(parsed_configs, absolute_path, user_modules_only=False)

if "--save-all-registers" in sys.argv:
    if (filtered_dirs):
        dump_all_registers_from_configs(parsed_configs, absolute_path, user_modules_only=False, save_to_file=True,print_to_console=False)

if "--print-user-registers" in sys.argv:
    if (filtered_dirs):
        dump_all_registers_from_configs(parsed_configs,absolute_path, user_modules_only=True)

if "--save-user-registers" in sys.argv:
    if (filtered_dirs):
        dump_all_registers_from_configs(parsed_configs, absolute_path, user_modules_only=True, save_to_file=True, print_to_console=True)

if "--gen-headers" in sys.argv:
    if (filtered_dirs):
        export_per_cpu_headers(parsed_configs, absolute_path, user_modules_only=False)

c_code_folders = get_c_code_folders(parsed_configs)
#print(c_code_folders)

default_c_code_path = "C_Code"  #Default Folder

def go_up_n_levels(path, levels):
    for _ in range(levels):
        path = os.path.dirname(path)
    return path

if "--build" in sys.argv:
    current_directory = os.path.abspath(__file__)
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
                if "--gen-headers" in sys.argv:
                    if (build_folder != default_c_code_path): 
                        if os.path.exists(f"{build_folder}/{cpu_name}_registers.h"):
                            os.remove(f"{build_folder}/{cpu_name}_registers.h")
                        print(f"Moved generated header: {build_folder}/{cpu_name}/{cpu_name}_registers.h -> {build_folder}\n")
                        shutil.move(f"{absolute_path}/{cpu_name}/{cpu_name}_registers.h", build_folder)
                result = subprocess.run(["bash", f"{build_script}", "--c-folder", build_folder], cwd=parent_directory, capture_output=True, text=True)
                print(result.stdout + result.stderr)
            except FileNotFoundError:
                assert False, f"Build folder not found for {cpu_name}: {build_folder}"

            curr_config_dict = {cpu_name: parsed_configs.get(cpu_name)}
            save_systemverilog_files(curr_config_dict, absolute_path)
            update_cpu_modules_file(curr_config_dict, absolute_path, reference_file=f"{parent_directory}/ref_fpga_sys_lite.sv")
            subprocess.run(["bash", "-c", "git clean -fdx"], cwd=parent_directory, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

else:
    if (filtered_dirs):
        save_systemverilog_files(parsed_configs, absolute_path)
        update_cpu_modules_file(parsed_configs, absolute_path)


#systemverilog_output = generate_systemverilog(parsed_configs)
#print(systemverilog_output)
