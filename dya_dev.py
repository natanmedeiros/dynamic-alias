#!/usr/bin/env python3
"""
Development runner for Dynamic Alias.
Allows running the application without installation.
Usage: python dya_dev.py [args]
"""
import sys
import os

# Add src directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.insert(0, src_dir)

if __name__ == "__main__":
    try:
        from dynamic_alias.main import main
        main()
    except ImportError as e:
        print(f"Error starting application: {e}")
        sys.exit(1)
