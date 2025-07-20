#!/usr/bin/env python3
import sys
import os

def run_generated_script():
    original_dir = os.getcwd()

    # Paths relative to where this script is located
    this_script_dir = os.path.dirname(os.path.abspath(__file__))
    generator_dir = os.path.join(this_script_dir, "cpu_config")

    try:
        # Patch import path
        sys.path.insert(0, os.path.abspath(generator_dir))
        import combine_gen_cpu_deps

        # Generate and execute code
        code = combine_gen_cpu_deps.generate_script(write_to_file=False)
        fake_file_path = os.path.abspath(__file__)
        print(fake_file_path)
        exec(code, {"__name__": "__main__", "__file__": fake_file_path})

    finally:
        sys.path.pop(0)

run_generated_script()
