"""Display helpers for Streamlit tables."""

from __future__ import annotations

import math
from typing import Any


def format_eur_millions(value: Any) -> str:
    """Format a EUR amount for display, e.g. 110_000_000 → '€110 million'."""
    if value is None:
        return "—"
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return "—"
    if math.isnan(amount):
        return "—"
    if amount == 0:
        return "€0"

    sign = "−" if amount < 0 else ""
    amount = abs(amount)
    millions = amount / 1_000_000

    if millions >= 1:
        if millions >= 100:
            return f"{sign}€{millions:.0f} million"
        if millions >= 10:
            return f"{sign}€{millions:.0f} million"
        return f"{sign}€{millions:.1f} million"

    thousands = amount / 1_000
    if thousands >= 1:
        return f"{sign}€{thousands:.0f} thousand"
    return f"{sign}€{amount:.0f}"


def format_fee(value: Any, *, zero_as_missing: bool = True) -> str:
    """Format EUR as €XM or €XB — matches transfers page aggregate labels."""
    if value is None:
        return "—"
    try:
        amount = float(value)
        if math.isnan(amount):
            return "—"
    except (TypeError, ValueError):
        return "—"
    if amount == 0:
        return "—" if zero_as_missing else "€0M"
    if amount >= 1_000_000_000:
        return f"€{amount / 1_000_000_000:.1f}B"
    millions = amount / 1_000_000
    if abs(millions - round(millions)) < 0.0001:
        return f"€{int(round(millions))}M"
    return f"€{millions:.1f}M"


FEE_AXIS_LABEL_EXPR = """
datum.value >= 1000000000
  ? '€' + format(datum.value / 1000000000, '.1f') + 'B'
  : (abs(datum.value / 1000000 - round(datum.value / 1000000)) < 0.0001
      ? '€' + format(datum.value / 1000000, 'd') + 'M'
      : '€' + format(datum.value / 1000000, '.1f') + 'M')
"""
