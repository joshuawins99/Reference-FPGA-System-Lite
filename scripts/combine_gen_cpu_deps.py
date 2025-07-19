#!/usr/bin/env python3
import os
import stat

current_directory = os.path.dirname(os.path.abspath(__file__))

modules = ["cpu_config_parser.py", "headers.py", "registers.py", "verilog.py", "main_gen_cpu_instance.py"]
output_file = f"{current_directory}/../generate_cpu_instance.py"

# Get module names without .py extension for matching
local_modules = [os.path.splitext(m)[0] for m in modules]

with open(output_file, "w") as out:
    out.write("#!/usr/bin/env python3\n")
    for filename in modules:
        with open(f"{current_directory}/{filename}", "r") as f:
            for line in f:
                # Skip local imports only (by 'from' or 'import' statements)
                if any(
                    line.strip().startswith(f"from {mod} ") or 
                    line.strip().startswith(f"import {mod}")
                    for mod in local_modules
                ):
                    continue
                out.write(line)
            out.write("\n")

os.chmod(output_file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)