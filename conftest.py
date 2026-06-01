"""
conftest.py — repo root
Ensures `core/`, `data/`, and `app/` are importable from any test.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
