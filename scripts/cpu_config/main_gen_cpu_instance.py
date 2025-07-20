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

#folders = list_folders(directory_path)
#print(folders)

config_files = check_config_files(directory_path, config_file_names)
#print(config_files)

filtered_dirs = [dir_name for dir_name in config_files if config_files.get(dir_name)]
#print(filtered_dirs)

parsed_configs = process_configs(directory_path, config_file_names)
#print(parsed_configs)
assign_auto_addresses(parsed_configs)
#print(parsed_configs)

if "--print-all-registers" in sys.argv:
    if (filtered_dirs):
        dump_all_registers_from_configs(parsed_configs,user_modules_only=False)

if "--save-all-registers" in sys.argv:
    if (filtered_dirs):
        dump_all_registers_from_configs(parsed_configs,user_modules_only=False, save_to_file=True, file_path="cpu_registers.txt",print_to_console=False)

if "--print-user-registers" in sys.argv:
    if (filtered_dirs):
        dump_all_registers_from_configs(parsed_configs,user_modules_only=True)

if "--save-user-registers" in sys.argv:
    if (filtered_dirs):
        dump_all_registers_from_configs(parsed_configs,user_modules_only=True, save_to_file=True, file_path="cpu_registers.txt", print_to_console=True)

if "--gen-headers" in sys.argv:
    if (filtered_dirs):
        export_per_cpu_headers(parsed_configs,user_modules_only=False)

c_code_folders = get_c_code_folders(parsed_configs)
#print(c_code_folders)

default_c_code_path = "C_Code"  #Default Folder

if "--build" in sys.argv:
    current_directory = os.path.dirname(os.path.abspath(__file__))
    if (filtered_dirs):
        absolute_path = os.path.abspath(".")
        for cpu_name in filtered_dirs:
            config_folder = c_code_folders.get(cpu_name)
            build_folder = (
                os.path.join(absolute_path, cpu_name, config_folder)
                if config_folder
                else os.path.join(directory_path, default_c_code_path)
            )
            parent_directory = os.path.dirname(current_directory)
            print(f"Running build for {cpu_name} using C Code folder: {build_folder}\n")
            try:
                if "--gen-headers" in sys.argv:
                    if os.path.exists(f"{build_folder}/{cpu_name}_registers.h"):
                        os.remove(f"{build_folder}/{cpu_name}_registers.h")
                    print(f"Moved header {cpu_name}/{cpu_name}_registers.h to {build_folder}\n")
                    shutil.move(f"{cpu_name}/{cpu_name}_registers.h", build_folder)
                result = subprocess.run(["bash", f"{build_script}", "--c-folder", build_folder], cwd=parent_directory, capture_output=True, text=True)
                print(result.stdout + result.stderr)
            except FileNotFoundError:
                print(f"Build folder not found for {cpu_name}: {build_folder}")

            curr_config_dict = {cpu_name: parsed_configs.get(cpu_name)}
            save_systemverilog_files(curr_config_dict, directory_path)
            update_cpu_modules_file(curr_config_dict, directory_path, reference_file=f"{parent_directory}/ref_fpga_sys_lite.sv")
            subprocess.run(["bash", "-c", "git clean -fdx"], cwd=parent_directory, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

else:
    if (filtered_dirs):
        save_systemverilog_files(parsed_configs, directory_path)
        update_cpu_modules_file(parsed_configs, directory_path)


#systemverilog_output = generate_systemverilog(parsed_configs)
#print(systemverilog_output)
