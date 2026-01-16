#!/usr/bin/env python

# Copyright (c) 2026 SoftBank Corp.
# 
# <<licensetext>>

import os


def _read_text(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def load_instruction_text() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return _read_text(os.path.join(base_dir, "instruction.txt"))


def load_spec_summary_text() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return _read_text(os.path.join(base_dir, "spec_summary.txt"))


def load_spec_full_text() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return _read_text(os.path.join(base_dir, "spec_full.txt"))
