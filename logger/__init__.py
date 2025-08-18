#!/usr/bin/env python3
"""
Logger Package for logging utilities.
"""

from .repository_dumper import dump_repository_on_exit

__all__ = [
    'dump_repository_on_exit'
] 