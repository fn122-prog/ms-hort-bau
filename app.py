#!/usr/bin/env python3
"""
Convenience launcher for Horticulture Dictionary Web Dashboard.
Forwards execution to Dictionary_and_Study_Materials/app.py
"""
import os
import sys
import subprocess

TARGET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Dictionary_and_Study_Materials", "app.py")

if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, TARGET] + sys.argv[1:]))
