#!/usr/bin/env python3
"""
Convenience launcher for Horticulture Dictionary Builder (Offline Ollama Edition).
Forwards execution to Dictionary_and_Study_Materials/fill_dictionary_ollama.py
Supports direct batch input from terminal:
  python3 fill_dictionary_ollama.py "air layering, t-budding, rootstock-scion interaction"
"""
import os
import sys
import subprocess

TARGET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Dictionary_and_Study_Materials", "fill_dictionary_ollama.py")

if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, TARGET] + sys.argv[1:]))
