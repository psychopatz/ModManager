"""Compatibility facade for manual editor operations.

This module intentionally stays small; implementation lives in the
ManualManagement subsystem modules.
"""

from .service import (
    create_manual_definition,
    delete_manual_definition,
    load_manual_editor_data,
    save_manual_definition,
)

__all__ = [
    "create_manual_definition",
    "delete_manual_definition",
    "load_manual_editor_data",
    "save_manual_definition",
]
