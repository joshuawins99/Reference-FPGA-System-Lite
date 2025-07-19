#!/usr/bin/env python3
import os
current_directory = os.path.dirname(os.path.abspath(__file__))

with open(f"{current_directory}/main_gen_cpu_instance.py") as f:
    code = f.read()
exec(code)