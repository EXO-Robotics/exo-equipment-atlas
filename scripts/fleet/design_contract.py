#!/usr/bin/env python3
"""Pure-Python contract helpers for fleet structural-study designs."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0.0"
ARCHETYPES = (
    "wheeled_tractor",
    "tracked_tractor",
    "twin_track_tractor",
    "combine",
    "forage_harvester",
    "high_clearance_sprayer",
    "self_propelled_mower",
    "square_baler",
    "self_propelled_round_baler",
    "articulated_hauler",
    "excavator",
)
PALETTES = ("oxide", "sand", "sage", "slate", "amber")
MACHINE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CONFIGURATION_ID_PATTERN = re.compile(r"^[A-Z0-9]+(?:[A-Z0-9._-]*[A-Z0-9])?$")
DIMENSION_LIMITS_M = {
    "length": (1.5, 35.0),
    "width": (1.0, 60.0),
    "height": (1.0, 12.0),
}


class DesignContractError(ValueError):
    """Raised when a design cannot safely drive deterministic authoring."""


def _plain_object(value: Any) -> bool:
    return isinstance(value, dict) and all(isinstance(key, str) for key in value)


def _string_list(value: Any, label: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise DesignContractError(f"{label} must be an array of nonempty strings")
    if len(value) != len(set(value)):
        raise DesignContractError(f"{label} must not contain duplicates")
    return value


def validate_design(payload: Any) -> dict[str, Any]:
    """Validate and normalize one JSON-compatible fleet design."""

    if not _plain_object(payload):
        raise DesignContractError("design must be a JSON object")
    allowed = {
        "schema_version",
        "machine_id",
        "display_name",
        "configuration_id",
        "archetype",
        "dimensions_m",
        "carrier_dimensions_m",
        "attachment_span_m",
        "tracked_front",
        "tailgate",
        "palette",
        "published_constraints_used",
        "reconstructed_values",
        "unresolved_choices",
        "mechanical_gaps",
    }
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise DesignContractError(f"unsupported design key(s): {', '.join(unknown)}")

    required = {
        "schema_version",
        "machine_id",
        "display_name",
        "configuration_id",
        "archetype",
        "dimensions_m",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise DesignContractError(f"missing required design key(s): {', '.join(missing)}")
    if payload["schema_version"] != SCHEMA_VERSION:
        raise DesignContractError(
            f"schema_version must be {SCHEMA_VERSION} (found {payload['schema_version']!r})"
        )
    machine_id = payload["machine_id"]
    if not isinstance(machine_id, str) or not MACHINE_ID_PATTERN.fullmatch(machine_id):
        raise DesignContractError("machine_id must be lowercase kebab-case")
    display_name = payload["display_name"]
    if not isinstance(display_name, str) or not display_name.strip() or len(display_name) > 120:
        raise DesignContractError("display_name must be a nonempty string no longer than 120 characters")
    configuration_id = payload["configuration_id"]
    if not isinstance(configuration_id, str) or not CONFIGURATION_ID_PATTERN.fullmatch(configuration_id):
        raise DesignContractError("configuration_id must be a stable uppercase token")
    archetype = payload["archetype"]
    if archetype not in ARCHETYPES:
        raise DesignContractError(f"archetype must be one of: {', '.join(ARCHETYPES)}")

    dimensions = payload["dimensions_m"]
    if not _plain_object(dimensions) or set(dimensions) != set(DIMENSION_LIMITS_M):
        raise DesignContractError("dimensions_m must contain exactly length, width, and height")
    normalized_dimensions: dict[str, float] = {}
    for axis, (minimum, maximum) in DIMENSION_LIMITS_M.items():
        value = dimensions[axis]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise DesignContractError(f"dimensions_m.{axis} must be numeric")
        value = float(value)
        if not minimum <= value <= maximum:
            raise DesignContractError(
                f"dimensions_m.{axis} must be between {minimum:g} and {maximum:g} metres"
            )
        normalized_dimensions[axis] = value

    carrier_dimensions = payload.get("carrier_dimensions_m")
    normalized_carrier = None
    if carrier_dimensions is not None:
        if not _plain_object(carrier_dimensions) or set(carrier_dimensions) != set(DIMENSION_LIMITS_M):
            raise DesignContractError("carrier_dimensions_m must contain exactly length, width, and height")
        normalized_carrier = {}
        for axis in DIMENSION_LIMITS_M:
            value = carrier_dimensions[axis]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or float(value) <= 0:
                raise DesignContractError(f"carrier_dimensions_m.{axis} must be a positive number")
            value = float(value)
            if value > normalized_dimensions[axis] + 1e-9:
                raise DesignContractError(
                    f"carrier_dimensions_m.{axis} cannot exceed dimensions_m.{axis}"
                )
            normalized_carrier[axis] = value

    attachment_span = payload.get("attachment_span_m")
    if attachment_span is not None:
        if isinstance(attachment_span, bool) or not isinstance(attachment_span, (int, float)):
            raise DesignContractError("attachment_span_m must be numeric")
        attachment_span = float(attachment_span)
        if not 0.5 <= attachment_span <= normalized_dimensions["width"] + 1e-9:
            raise DesignContractError(
                "attachment_span_m must be between 0.5 m and dimensions_m.width"
            )

    tracked_front = payload.get("tracked_front", False)
    if not isinstance(tracked_front, bool):
        raise DesignContractError("tracked_front must be boolean")
    if tracked_front and archetype != "combine":
        raise DesignContractError("tracked_front is only valid for the combine archetype")
    tailgate = payload.get("tailgate", True)
    if not isinstance(tailgate, bool):
        raise DesignContractError("tailgate must be boolean")
    if "tailgate" in payload and archetype != "articulated_hauler":
        raise DesignContractError("tailgate is only valid for the articulated_hauler archetype")

    palette = payload.get("palette", "oxide")
    if palette not in PALETTES:
        raise DesignContractError(f"palette must be one of: {', '.join(PALETTES)}")
    reconstructed = payload.get("reconstructed_values", {})
    if not _plain_object(reconstructed):
        raise DesignContractError("reconstructed_values must be a JSON object")

    normalized = dict(payload)
    normalized["dimensions_m"] = normalized_dimensions
    if normalized_carrier is not None:
        normalized["carrier_dimensions_m"] = normalized_carrier
    if attachment_span is not None:
        normalized["attachment_span_m"] = attachment_span
    normalized["tracked_front"] = tracked_front
    normalized["tailgate"] = tailgate
    normalized["palette"] = palette
    normalized["published_constraints_used"] = _string_list(
        payload.get("published_constraints_used"), "published_constraints_used"
    )
    normalized["reconstructed_values"] = reconstructed
    normalized["unresolved_choices"] = _string_list(
        payload.get("unresolved_choices"), "unresolved_choices"
    ) or ["exact order configuration and option package"]
    normalized["mechanical_gaps"] = _string_list(
        payload.get("mechanical_gaps"), "mechanical_gaps"
    ) or ["machine-specific motion limits, hidden pivots, anchors, and collision envelopes"]
    return normalized


def load_design(path: str | Path) -> dict[str, Any]:
    source = Path(path).resolve()
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DesignContractError(f"could not read design {source}: {error}") from error
    return validate_design(payload)
