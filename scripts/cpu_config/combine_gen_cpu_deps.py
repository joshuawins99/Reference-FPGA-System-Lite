#!/usr/bin/env python3
import os
import stat

def generate_script(write_to_file=True):
    current_directory = os.path.dirname(os.path.abspath(__file__))
    modules = [
        "cpu_config_parser.py", 
        "headers.py", 
        "registers.py", 
        "verilog.py", 
        "main_gen_cpu_instance.py"
    ]
    output_file = f"{current_directory}/../../generate_cpu_instance.py"
    local_modules = [os.path.splitext(m)[0] for m in modules]

    output_lines = ["#!/usr/bin/env python3\n"]

    for filename in modules:
        with open(f"{current_directory}/{filename}", "r") as f:
            for line in f:
                if any(
                    line.strip().startswith(f"from {mod} ") or 
                    line.strip().startswith(f"import {mod}")
                    for mod in local_modules
                ):
                    continue
                output_lines.append(line)
            output_lines.append("\n")

    if write_to_file:
        with open(output_file, "w") as out:
            out.writelines(output_lines)
        os.chmod(output_file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    else:
        return "".join(output_lines)


if __name__ == "__main__":
    generate_script()