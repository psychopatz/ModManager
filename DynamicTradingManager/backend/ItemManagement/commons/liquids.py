"""Helpers for reading vanilla fluid-container metadata."""

import re

from .vanilla_loader import get_stat


_TRUE_VALUES = {"true", "yes", "1"}


def has_fluid_container(props):
    """Return True when the item defines a FluidContainer component."""
    return "component fluidcontainer" in (props or "").lower()


def extract_raw_property(props, key, default=""):
    """Extract a raw property value without coercing it."""
    match = re.search(rf"{key}\s*=\s*([^,\n]+)", props or "", re.IGNORECASE)
    return match.group(1).strip() if match else default


def normalize_fluid_identifier(raw_value):
    """Normalize a vanilla Fluid property to a stable lookup key."""
    value = str(raw_value or "").strip().strip('"')
    if not value:
        return None

    value = value.split(":", 1)[0].strip()
    if not value or value.lower() in _TRUE_VALUES:
        return None

    if value.startswith("Base."):
        value = value[5:]

    return value


def get_fluid_metadata(item_id, props):
    """Return normalized fluid-container metadata for a vanilla item."""
    raw_fluid = extract_raw_property(props, "Fluid")
    return {
        "item_id": item_id,
        "capacity": get_stat(props, "Capacity", 0.0),
        "display_category": extract_raw_property(props, "DisplayCategory"),
        "replace_on_deplete": extract_raw_property(props, "ReplaceOnDeplete"),
        "raw_fluid": raw_fluid,
        "default_fluid": normalize_fluid_identifier(raw_fluid),
    }
