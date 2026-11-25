#!/usr/bin/env python3
"""
Convenience launcher for Horticulture LinkedIn Post & Book Visibility Dashboard.
Runs on http://localhost:8082
"""
import os
import sys
import subprocess

TARGET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "post_generator.py")

if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, TARGET, "--serve"] + sys.argv[1:]))
