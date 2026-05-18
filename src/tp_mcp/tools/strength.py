"""Tools for TrainingPeaks structured strength workouts.

Strength workouts in TP have a richer structure than endurance workouts:
blocks (Warm Up, Superset, Single Exercise, Circuit, Cool Down) containing
prescriptions (one exercise each) with prescribed sets where each set has
parameter values (reps, weight, time, etc).

These tools speak directly to `api.peakswaresb.com/rx/activity/v1/`, which
is a different API namespace than the rest of TP. They reuse the standard
TPClient OAuth token via StrengthClient.

Public tools:
- tp_get_strength_workout(workout_id)
- tp_search_exercise(query, limit=20)
- tp_create_strength_workout(...)
- tp_update_strength_workout(workout_id, ...)
- tp_delete_strength_workout(workout_id)
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime, date as date_type
from pathlib import Path
from typing import Any

from tp_mcp.client.strength_http import StrengthClient

logger = logging.getLogger("tp-mcp.strength")

# ---------------------------------------------------------------------------
# Exercise library cache
# ---------------------------------------------------------------------------

# We persist the exercise library to disk so repeated tool calls don't re-fetch
# the 234KB blob. The MCP package ships a snapshot under notes-strength-api/
# (captured during reverse-engineering); on first call we load from there if
# the live fetch fails.
_LIB_CACHE_PATH = Path(
    os.environ.get(
        "TP_STRENGTH_LIB_CACHE",
        os.path.expanduser("~/.cache/tp-mcp/strength-library.json"),
    )
)
_BUNDLED_LIB_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "notes-strength-api"
    / "library-content.json"
)
_LIB_CACHE_TTL_SECONDS = 7 * 24 * 3600  # one week
_lib_memory_cache: dict[str, Any] | None = None


async def _load_library() -> dict[str, Any]:
    """Return the strength library, loading from disk or fetching if needed.

    Cache priority: in-memory > disk (if fresh) > live fetch > bundled snapshot.
    """
    global _lib_memory_cache

    if _lib_memory_cache is not None:
        return _lib_memory_cache

    # Disk cache.
    if _LIB_CACHE_PATH.exists():
        age = time.time() - _LIB_CACHE_PATH.stat().st_mtime
        if age < _LIB_CACHE_TTL_SECONDS:
            try:
                _lib_memory_cache = json.loads(_LIB_CACHE_PATH.read_text())
                return _lib_memory_cache
            except Exception as e:
                logger.warning("Failed to load disk lib cache: %s", e)

    # Live fetch.
    try:
        async with StrengthClient() as c:
            r = await c.get("libraryContent")
        if r.success and r.data:
            _lib_memory_cache = r.data
            _LIB_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            _LIB_CACHE_PATH.write_text(json.dumps(r.data))
            return _lib_memory_cache
        logger.warning("Live library fetch failed: %s", r.message)
    except Exception as e:
        logger.warning("Live library fetch errored: %s", e)

    # Bundled fallback.
    if _BUNDLED_LIB_PATH.exists():
        _lib_memory_cache = json.loads(_BUNDLED_LIB_PATH.read_text())
        return _lib_memory_cache

    raise RuntimeError(
        "Could not load TP strength library from any source "
        f"(tried disk={_LIB_CACHE_PATH}, live, bundled={_BUNDLED_LIB_PATH})"
    )


def _exercises_from_library(lib: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract the exercise list from the library payload."""
    data = lib.get("data") or {}
    return data.get("exercises") or []


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


# ---------------------------------------------------------------------------
# Read tools
# ---------------------------------------------------------------------------


def _unwrap(envelope: Any) -> Any:
    """Strip the {"data": ..., "errors": {}} envelope if present."""
    if isinstance(envelope, dict) and "data" in envelope and "errors" in envelope:
        return envelope["data"]
    return envelope


async def tp_get_strength_workout(workout_id: str | int) -> dict[str, Any]:
    """Fetch a structured strength workout by id.

    Args:
        workout_id: TP strength workout id (the integer or its string form).

    Returns:
        Dict with success/error and parsed workout payload.
    """
    async with StrengthClient() as c:
        r = await c.get(f"workouts/{workout_id}")
    if not r.success:
        return {
            "success": False,
            "error_code": r.error_code.name if r.error_code else "API_ERROR",
            "message": r.message,
        }
    return {"success": True, "workout": _unwrap(r.data)}


async def tp_list_strength_workouts(
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """List structured strength workouts in a date range.

    Returns lightweight summary entries (id, date, title, compliancePercent,
    rpe, feel, sequenceSummary). For per-set weight history, follow up with
    `tp_get_strength_workout(workout_id)` on each completed workout, or use
    `tp_get_strength_history` which aggregates that for you.

    Args:
        start_date: 'YYYY-MM-DD' (inclusive).
        end_date: 'YYYY-MM-DD' (inclusive).

    Returns dict with success and `workouts` list.
    """
    async with StrengthClient() as c:
        athlete_id = await c._tp_client.ensure_athlete_id()
        r = await c.get(f"workouts/calendar/{athlete_id}/{start_date}/{end_date}")
    if not r.success:
        return {
            "success": False,
            "error_code": r.error_code.name if r.error_code else "API_ERROR",
            "message": r.message,
        }
    items = _unwrap(r.data) or []
    summaries = []
    for w in items if isinstance(items, list) else []:
        summaries.append(
            {
                "id": w.get("id"),
                "title": w.get("title"),
                "prescribedDate": w.get("prescribedDate"),
                "prescribedStartTime": w.get("prescribedStartTime"),
                "compliancePercent": w.get("compliancePercent"),
                "rpe": w.get("rpe"),
                "feel": w.get("feel"),
                "completedDateTime": w.get("completedDateTime"),
                "executedDurationInSeconds": w.get("executedDurationInSeconds"),
                "sequenceSummary": [
                    {"order": s.get("sequenceOrder"), "title": s.get("title")}
                    for s in (w.get("sequenceSummary") or [])
                ],
            }
        )
    return {
        "success": True,
        "count": len(summaries),
        "start_date": start_date,
        "end_date": end_date,
        "workouts": summaries,
    }


def _extract_set_history(prescription: dict[str, Any]) -> list[dict[str, Any]]:
    """Pull executed reps/weight/duration from each set of a prescription."""
    out = []
    for s in prescription.get("sets") or []:
        if not s.get("isComplete"):
            continue
        values = {}
        for pv in s.get("parameterValues") or []:
            param = pv.get("parameter")
            executed = pv.get("executedValue")
            prescribed = pv.get("prescribedValue")
            if executed is None and prescribed is None:
                continue
            try:
                executed_num = float(executed) if executed is not None else None
            except (TypeError, ValueError):
                executed_num = None
            try:
                prescribed_num = float(prescribed) if prescribed is not None else None
            except (TypeError, ValueError):
                prescribed_num = None
            values[param] = {"executed": executed_num, "prescribed": prescribed_num}
        if values:
            out.append(values)
    return out


async def tp_get_strength_history(
    exercise_name: str | None = None,
    days_back: int = 30,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Aggregate per-exercise load history across recent strength workouts.

    Pulls the strength calendar for the date range, fetches each completed
    workout, walks every block/prescription/set, and returns per-exercise
    history with executed weight, reps, and the workout's RPE.

    Use this in the Sunday Routine to compute progressive overload targets
    for the upcoming week.

    Args:
        exercise_name: Filter by exact title match (case-insensitive). Omit
            to return history for all exercises.
        days_back: How far back from `end_date` (or today) to scan.
        end_date: 'YYYY-MM-DD' end of the window (inclusive). Defaults to today.

    Returns dict with `history` keyed by exercise title:
        {
          "Back Squat": [
            {
              "date": "2026-05-04",
              "workout_id": "19542962",
              "workout_title": "Lower #1 (Squat focus)",
              "rpe": 3,
              "feel": 5,
              "sets": [
                {"reps": 6, "weight_lb": 185},
                ...
              ],
              "max_weight_lb": 205,
              "max_weight_reps": 6,
              "max_weight_set_count": 2
            },
            ...
          ]
        }
    Sorted most-recent first per exercise.
    """
    end = (
        date_type.fromisoformat(end_date)
        if end_date
        else date_type.today()
    )
    start = end - __import__("datetime").timedelta(days=int(days_back))

    listing = await tp_list_strength_workouts(start.isoformat(), end.isoformat())
    if not listing.get("success"):
        return listing
    summaries = listing.get("workouts") or []

    target = exercise_name.strip().lower() if exercise_name else None
    history: dict[str, list[dict[str, Any]]] = {}

    for sw in summaries:
        if not sw.get("compliancePercent") or sw["compliancePercent"] <= 0:
            continue
        wid = sw.get("id")
        if not wid:
            continue
        full = await tp_get_strength_workout(wid)
        if not full.get("success"):
            continue
        w = full["workout"]
        for block in w.get("blocks") or []:
            for p in block.get("prescriptions") or []:
                ex_title = (p.get("exercise") or {}).get("title") or ""
                if target and ex_title.lower() != target:
                    continue
                set_values = _extract_set_history(p)
                if not set_values:
                    continue
                # Distill per-set rep + weight into a flat shape.
                flat_sets = []
                for sv in set_values:
                    entry: dict[str, Any] = {}
                    if "Reps" in sv:
                        entry["reps"] = sv["Reps"]["executed"] or sv["Reps"]["prescribed"]
                    if "RepsPerSide" in sv:
                        entry["reps_per_side"] = (
                            sv["RepsPerSide"]["executed"]
                            or sv["RepsPerSide"]["prescribed"]
                        )
                    if "WeightLb" in sv:
                        entry["weight_lb"] = sv["WeightLb"]["executed"]
                    if "WeightPerSideLb" in sv:
                        entry["weight_per_side_lb"] = sv["WeightPerSideLb"]["executed"]
                    if "Duration" in sv:
                        entry["duration_seconds"] = (
                            sv["Duration"]["executed"] or sv["Duration"]["prescribed"]
                        )
                    flat_sets.append(entry)
                # Compute the heaviest weight set.
                weights = [
                    s.get("weight_lb")
                    for s in flat_sets
                    if isinstance(s.get("weight_lb"), (int, float))
                ]
                max_weight = max(weights) if weights else None
                max_weight_reps = None
                max_weight_set_count = 0
                if max_weight is not None:
                    matching = [s for s in flat_sets if s.get("weight_lb") == max_weight]
                    max_weight_set_count = len(matching)
                    if matching and "reps" in matching[0]:
                        max_weight_reps = matching[0]["reps"]
                history.setdefault(ex_title, []).append(
                    {
                        "date": sw.get("prescribedDate"),
                        "workout_id": wid,
                        "workout_title": sw.get("title"),
                        "rpe": sw.get("rpe"),
                        "feel": sw.get("feel"),
                        "sets": flat_sets,
                        "max_weight_lb": max_weight,
                        "max_weight_reps": max_weight_reps,
                        "max_weight_set_count": max_weight_set_count,
                    }
                )

    # Sort each exercise's history most-recent first.
    for ex_title, entries in history.items():
        entries.sort(key=lambda e: e["date"] or "", reverse=True)

    return {
        "success": True,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "exercise_filter": exercise_name,
        "exercise_count": len(history),
        "history": history,
    }


async def tp_search_exercise(
    query: str,
    limit: int = 20,
) -> dict[str, Any]:
    """Search the TP exercise library for movements matching `query`.

    Returns up to `limit` matches with id, title, and primary muscle groups.
    Uses fuzzy substring matching on title and searchText.

    Args:
        query: Search term (e.g. "back squat", "bench press").
        limit: Max results to return (default 20, max 50).
    """
    if not query or not query.strip():
        return {"success": False, "message": "query must be non-empty"}
    limit = max(1, min(int(limit), 50))

    try:
        lib = await _load_library()
    except Exception as e:
        return {"success": False, "message": f"library load failed: {e}"}

    exercises = _exercises_from_library(lib)
    needle = _norm(query)
    tokens = needle.split()

    scored: list[tuple[int, dict[str, Any]]] = []
    for ex in exercises:
        title = _norm(ex.get("title", ""))
        search_text = _norm(ex.get("searchText") or "")
        haystack = f"{title} {search_text}"
        if not all(t in haystack for t in tokens):
            continue
        # Score: prefer exact title match, then leading title match, then any.
        score = 0
        if title == needle:
            score = 100
        elif title.startswith(needle):
            score = 80
        elif needle in title:
            score = 60
        else:
            score = 40
        # Boost shorter titles for ties (more specific).
        score -= min(len(title), 30) // 5
        scored.append((score, ex))

    scored.sort(key=lambda x: x[0], reverse=True)
    matches = [
        {
            "exerciseId": ex.get("exerciseId"),
            "title": ex.get("title"),
            "primaryMuscleGroups": (ex.get("searchAttributes") or {}).get(
                "primaryMuscleGroups", []
            ),
            "secondaryMuscleGroups": (ex.get("searchAttributes") or {}).get(
                "secondaryMuscleGroups", []
            ),
        }
        for _score, ex in scored[:limit]
    ]
    return {"success": True, "query": query, "count": len(matches), "matches": matches}


async def _resolve_exercise(name_or_id: str | int) -> dict[str, Any] | None:
    """Resolve an exercise reference to a library entry (with id and title).

    Accepts either an integer/string id or a name. For names, returns the
    top match by the same scoring as tp_search_exercise.
    """
    lib = await _load_library()
    exercises = _exercises_from_library(lib)

    # Numeric id path.
    s = str(name_or_id).strip()
    if s.isdigit():
        for ex in exercises:
            if str(ex.get("exerciseId")) == s:
                return ex
        return None

    # Name path — reuse the search ranking.
    needle = _norm(s)
    tokens = needle.split()
    best: tuple[int, dict[str, Any]] | None = None
    for ex in exercises:
        title = _norm(ex.get("title", ""))
        search_text = _norm(ex.get("searchText") or "")
        haystack = f"{title} {search_text}"
        if not all(t in haystack for t in tokens):
            continue
        if title == needle:
            score = 100
        elif title.startswith(needle):
            score = 80
        elif needle in title:
            score = 60
        else:
            score = 40
        score -= min(len(title), 30) // 5
        if best is None or score > best[0]:
            best = (score, ex)
    return best[1] if best else None


# ---------------------------------------------------------------------------
# Builder helpers — produce TP wire-format payloads from simplified input
# ---------------------------------------------------------------------------

# Block types accepted by TP (from /libraryContent).
BLOCK_TYPES = {"SingleExercise", "Circuit", "CoolDown", "WarmUp", "Superset"}


def _infer_parameters_for_exercise(exercise_title: str) -> list[dict[str, Any]]:
    """Heuristic: pick parameter types based on exercise title patterns.

    The TP exercise library doesn't expose a single canonical parameter list
    per exercise via /libraryContent (parameters live on exercise detail and
    are inferred at use). We approximate based on naming conventions.

    Returns a list of param specs in TP's wire format (without instance ids).
    """
    title_lower = exercise_title.lower()

    # Time-based: planks, holds, isometrics.
    if any(
        kw in title_lower
        for kw in ["plank", "hold", "iso ", " iso", "wall sit", "carry", "farmer"]
    ):
        return [_param_spec("Duration")]

    # Distance-based.
    if "walking lunge" in title_lower or "farmer carry" in title_lower:
        # Walking lunges: usually reps; farmer carry: distance. Default reps.
        return [_param_spec("Reps"), _param_spec("WeightLb")]

    # Unilateral: alternating, single-arm, single-leg, single-side.
    if any(
        kw in title_lower
        for kw in [
            "alternating",
            "single arm",
            "single-arm",
            "single leg",
            "single-leg",
            "one arm",
            "one-arm",
        ]
    ):
        # Bodyweight unilateral exercises (e.g. single-leg glute bridge BW)
        # are rare; default to RepsPerSide + WeightPerSideLb.
        return [_param_spec("RepsPerSide"), _param_spec("WeightPerSideLb")]

    # Bodyweight (no weight column).
    if any(
        kw in title_lower
        for kw in [
            "air squat",
            "body weight",
            "bodyweight",
            "push up",
            "push-up",
            "sit up",
            "sit-up",
            "burpee",
            "mountain climber",
            "jumping jack",
            "leg raise",
        ]
    ):
        return [_param_spec("Reps")]

    # Default: reps + weight.
    return [_param_spec("Reps"), _param_spec("WeightLb")]


_PARAM_CATALOG = {
    "Reps": {"title": "Reps", "unit": {"title": "Reps", "abbreviation": "", "unit": "Reps"}, "category": "Reps"},
    "RepsPerSide": {
        "title": "Reps/side",
        "unit": {"title": "Reps", "abbreviation": "", "unit": "Reps"},
        "category": "Reps/side",
    },
    "WeightLb": {
        "title": "Weight lb",
        "unit": {"title": "Pounds", "abbreviation": "lb", "unit": "Pounds"},
        "category": "Weight",
    },
    "WeightKg": {
        "title": "Weight kg",
        "unit": {"title": "Kilograms", "abbreviation": "kg", "unit": "Kilograms"},
        "category": "Weight",
    },
    "WeightPerSideLb": {
        "title": "Weight/side lb",
        "unit": {"title": "Pounds", "abbreviation": "lb", "unit": "Pounds"},
        "category": "Weight/side",
    },
    "WeightPerSideKg": {
        "title": "Weight/side kg",
        "unit": {"title": "Kilograms", "abbreviation": "kg", "unit": "Kilograms"},
        "category": "Weight/side",
    },
    # `Duration` is the exercise-level time parameter (in seconds). TP also
    # exposes `TimeSeconds` as a block-level total parameter; do not use it
    # on prescriptions.
    "Duration": {
        "title": "Duration",
        "unit": {"title": "Seconds", "abbreviation": "sec", "unit": "Seconds"},
        "category": "Duration",
    },
    "DistanceMeters": {
        "title": "Distance meters",
        "unit": {"title": "Meters", "abbreviation": "m", "unit": "Meters"},
        "category": "Distance",
    },
    "DistanceMiles": {
        "title": "Distance miles",
        "unit": {"title": "Miles", "abbreviation": "mi", "unit": "Miles"},
        "category": "Distance",
    },
}


def _param_spec(parameter: str) -> dict[str, Any]:
    """Return a TP parameter spec dict for the given parameter enum."""
    cat = _PARAM_CATALOG.get(parameter)
    if not cat:
        raise ValueError(f"Unknown parameter: {parameter}")
    return {
        "parameter": parameter,
        "title": cat["title"],
        "unit": cat["unit"],
        "category": cat["category"],
    }


def _input_format_for(parameter: str) -> str:
    """TP expects 'Integer' for reps/duration, 'Decimal' for weight/distance."""
    if parameter in {"Reps", "RepsPerSide", "Duration"}:
        return "Integer"
    return "Decimal"


def _set_summary_template(params: list[dict[str, Any]]) -> str:
    """Reproduce TP's display template like '{Reps} @ {WeightLb} lb'."""
    parts = []
    for p in params:
        name = p["parameter"]
        unit_abbr = (p.get("unit") or {}).get("abbreviation", "")
        if unit_abbr:
            parts.append(f"{{{name}}} {unit_abbr}")
        else:
            parts.append(f"{{{name}}}")
    return " @ ".join(parts)


def _build_set(
    set_input: dict[str, Any],
    param_specs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a single set from simplified input.

    set_input keys (any subset, must match param_specs by name):
      reps, reps_per_side, weight_lb, weight_kg, weight_per_side_lb,
      time_seconds, distance_meters
    """
    name_map = {
        "Reps": "reps",
        "RepsPerSide": "reps_per_side",
        "WeightLb": "weight_lb",
        "WeightKg": "weight_kg",
        "WeightPerSideLb": "weight_per_side_lb",
        "WeightPerSideKg": "weight_per_side_kg",
        # We accept either `duration_seconds` (canonical) or the legacy
        # `time_seconds` key for backward compat with early test code.
        "Duration": "duration_seconds",
        "DistanceMeters": "distance_meters",
        "DistanceMiles": "distance_miles",
    }
    # Backward compat: callers can still pass time_seconds; normalize it.
    if "time_seconds" in set_input and "duration_seconds" not in set_input:
        set_input = {**set_input, "duration_seconds": set_input["time_seconds"]}
    parameter_values = []
    for spec in param_specs:
        pkey = spec["parameter"]
        input_key = name_map[pkey]
        prescribed = set_input.get(input_key)
        prescribed_str = (
            None if prescribed is None or prescribed == "" else str(prescribed)
        )
        parameter_values.append(
            {
                "parameter": pkey,
                "inputFormat": _input_format_for(pkey),
                "prescribedValue": prescribed_str,
                "executedValue": None,
            }
        )
    return {
        "parameterValues": parameter_values,
        "isComplete": False,
        "setOrigin": "Prescribed",
    }


def _build_prescription(
    exercise: dict[str, Any],
    sets: list[dict[str, Any]],
    coach_notes: str | None = None,
    explicit_params: list[str] | None = None,
) -> dict[str, Any]:
    """Build a prescription block for a single exercise.

    `exercise` is the resolved library entry (must have exerciseId and title).
    `sets` is a list of dicts with reps/weight/etc.
    `explicit_params` overrides parameter inference if provided.
    """
    title = exercise.get("title", "")
    if explicit_params:
        param_specs = [_param_spec(p) for p in explicit_params]
    else:
        param_specs = _infer_parameters_for_exercise(title)

    return {
        "exercise": {
            "id": str(exercise.get("exerciseId")),
            "ownerId": exercise.get("ownerId") or 2000301,
            "title": title,
            "videoUrl": exercise.get("videoUrl"),
            "instructions": exercise.get("instructions"),
            "parameters": param_specs,
            "canEdit": False,
        },
        "parameters": [dict(p) for p in param_specs],
        "sets": [_build_set(s, param_specs) for s in sets],
        "coachNotes": coach_notes,
        "compliancePercent": 0,
        "setSummaryTemplate": _set_summary_template(param_specs),
    }


async def _build_block(block_input: dict[str, Any]) -> dict[str, Any]:
    """Build a block (with all its prescriptions) from simplified input.

    block_input keys:
      title (str, required)
      blockType (str, required, one of BLOCK_TYPES)
      coachNotes (str, optional)
      exercises: list[dict], each:
        - name (str) OR exerciseId (int|str)
        - sets: list[dict] (reps, weight_lb, ...)
        - parameters: list[str] (optional, override param inference)
        - coachNotes: str (optional)
    """
    title = block_input.get("title")
    block_type = block_input.get("blockType")
    if not title:
        raise ValueError("block.title is required")
    if block_type not in BLOCK_TYPES:
        raise ValueError(
            f"block.blockType must be one of {sorted(BLOCK_TYPES)}, got {block_type!r}"
        )

    prescriptions = []
    for ex_input in block_input.get("exercises", []):
        ref = ex_input.get("exerciseId") or ex_input.get("name")
        if ref is None:
            raise ValueError("each exercise needs `name` or `exerciseId`")
        exercise = await _resolve_exercise(ref)
        if exercise is None:
            raise ValueError(f"exercise not found in TP library: {ref!r}")
        sets = ex_input.get("sets") or []
        if not sets:
            raise ValueError(f"exercise {exercise.get('title')!r} needs at least one set")
        prescriptions.append(
            _build_prescription(
                exercise=exercise,
                sets=sets,
                coach_notes=ex_input.get("coachNotes"),
                explicit_params=ex_input.get("parameters"),
            )
        )

    return {
        "title": title,
        "blockType": block_type,
        "coachNotes": block_input.get("coachNotes"),
        "isComplete": False,
        "compliancePercent": 0,
        "parameters": [],
        "prescriptions": prescriptions,
    }


def _compute_snapshot(blocks: list[dict[str, Any]]) -> dict[str, int]:
    total_blocks = len(blocks)
    total_sets = 0
    total_prescriptions = 0
    for b in blocks:
        for p in b.get("prescriptions", []):
            total_prescriptions += 1
            total_sets += len(p.get("sets") or [])
    return {
        "totalBlocks": total_blocks,
        "completedBlocks": 0,
        "totalSets": total_sets,
        "completedSets": 0,
        "totalPrescriptions": total_prescriptions,
        "completedPrescriptions": 0,
    }


# ---------------------------------------------------------------------------
# Write tools
# ---------------------------------------------------------------------------


def _normalize_date(d: str) -> tuple[str, str | None]:
    """Split 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SS' into (date, start_time).

    TP's strength API expects `prescribedStartTime` to be time-only
    ('HH:MM:SS'), not a full ISO datetime. Returns (prescribedDate,
    prescribedStartTime). prescribedStartTime is None for all-day.
    """
    if "T" in d:
        try:
            dt = datetime.fromisoformat(d)
        except ValueError as e:
            raise ValueError(f"invalid date format {d!r}: {e}") from e
        return dt.date().isoformat(), dt.time().isoformat(timespec="seconds")
    # Validate the date alone.
    date_type.fromisoformat(d)
    return d, None


async def tp_create_strength_workout(
    date: str,
    title: str,
    blocks: list[dict[str, Any]],
    instructions: str | None = None,
    duration_minutes: int | None = None,
    tss_planned: float | None = None,
) -> dict[str, Any]:
    """Create a structured strength workout in TP.

    Args:
        date: 'YYYY-MM-DD' (all-day) or 'YYYY-MM-DDTHH:MM:SS' (planned start).
        title: Workout title.
        blocks: list of block dicts. See `_build_block` for the schema.
        instructions: Top-level workout instructions text.
        duration_minutes: Optional planned duration. Server may also compute.
        tss_planned: Optional TSS estimate.

    Returns dict with `success`, `workout_id`, and the persisted payload.
    """
    if not title:
        return {"success": False, "message": "title is required"}
    if not blocks:
        return {"success": False, "message": "at least one block is required"}

    try:
        prescribed_date, prescribed_start = _normalize_date(date)
    except ValueError as e:
        return {"success": False, "message": str(e)}

    try:
        wire_blocks = []
        for b in blocks:
            wire_blocks.append(await _build_block(b))
    except (ValueError, RuntimeError) as e:
        return {"success": False, "message": str(e)}

    snapshot = _compute_snapshot(wire_blocks)

    duration_seconds = (
        int(duration_minutes * 60) if duration_minutes is not None else None
    )

    async with StrengthClient() as c:
        # The athlete's calendarId equals their athlete_id in TP's data model.
        athlete_id = await c._tp_client.ensure_athlete_id()

        # Step 1: POST /workouts to create a draft shell.
        # TP's UI flow: POST creates an empty workout with a UUID id, then PUT
        # populates it, then POST /save commits. We mirror that here so a single
        # public function does the right thing.
        create_payload = {
            "workoutType": "StructuredStrength",
            "calendarId": athlete_id,
            "prescribedDate": prescribed_date,
        }
        create_r = await c.post("workouts", json=create_payload)
        if not create_r.success:
            return {
                "success": False,
                "error_code": create_r.error_code.name if create_r.error_code else "API_ERROR",
                "message": f"POST /workouts (create draft) failed: {create_r.message}",
            }
        draft = _unwrap(create_r.data) or {}
        draft_id = draft.get("id")
        if not draft_id:
            return {
                "success": False,
                "message": f"draft create returned no id: {draft}",
            }

        # Step 2: PUT /workouts with the full populated payload, including the
        # draft id and any server-assigned defaults from the create response.
        full_payload = dict(draft)  # carry forward server defaults (calendarId etc)
        full_payload.update(
            {
                "id": draft_id,
                "workoutType": "StructuredStrength",
                "workoutSubTypeId": None,
                "calendarId": athlete_id,
                "title": title,
                "instructions": instructions,
                "prescribedDate": prescribed_date,
                "prescribedStartTime": prescribed_start,
                "prescribedDurationInSeconds": duration_seconds,
                "prescribedTss": float(tss_planned) if tss_planned is not None else None,
                "prescribedIntensityFactor": None,
                "compliancePercent": 0,
                "rpe": None,
                "feel": None,
                "lastUpdatedAt": datetime.now().isoformat(timespec="seconds"),
                "orderOnDay": draft.get("orderOnDay", 0),
                "isLocked": False,
                "isHidden": False,
                "snapshot": snapshot,
                "blocks": wire_blocks,
            }
        )

        put_r = await c.put("workouts", json=full_payload)
        if not put_r.success:
            return {
                "success": False,
                "error_code": put_r.error_code.name if put_r.error_code else "API_ERROR",
                "message": f"PUT /workouts (populate) failed: {put_r.message}",
            }

        # Step 3: POST /workouts/save commits the draft into a persistent
        # workout. The response carries the new integer id and the full
        # populated workout. The PUT-only state has a UUID id that GET cannot
        # find, so save is required for persistence.
        save_payload = _unwrap(put_r.data) or full_payload
        save_r = await c.post("workouts/save", json=save_payload)

    if not save_r.success:
        return {
            "success": False,
            "error_code": save_r.error_code.name if save_r.error_code else "API_ERROR",
            "message": f"POST /workouts/save (commit) failed: {save_r.message}",
            "draft_id": draft_id,
        }

    persisted = _unwrap(save_r.data) or {}
    return {
        "success": True,
        "workout_id": persisted.get("id"),
        "title": persisted.get("title"),
        "prescribedDate": persisted.get("prescribedDate"),
        "totalSets": (persisted.get("snapshot") or {}).get("totalSets"),
        "totalPrescriptions": (persisted.get("snapshot") or {}).get("totalPrescriptions"),
    }


async def tp_update_strength_workout(
    workout_id: str | int,
    title: str | None = None,
    instructions: str | None = None,
    blocks: list[dict[str, Any]] | None = None,
    duration_minutes: int | None = None,
    tss_planned: float | None = None,
    date: str | None = None,
) -> dict[str, Any]:
    """Update an existing structured strength workout.

    Fetches the current workout, merges in the supplied fields, and PUTs the
    full payload back to TP, then POSTs to /save to commit. Mirrors the UI flow.
    """
    async with StrengthClient() as c:
        r = await c.get(f"workouts/{workout_id}")
        if not r.success:
            return {
                "success": False,
                "error_code": r.error_code.name if r.error_code else "API_ERROR",
                "message": r.message,
            }
        existing = _unwrap(r.data) or {}

        if title is not None:
            existing["title"] = title
        if instructions is not None:
            existing["instructions"] = instructions
        if duration_minutes is not None:
            existing["prescribedDurationInSeconds"] = int(duration_minutes * 60)
        if tss_planned is not None:
            existing["prescribedTss"] = float(tss_planned)
        if date is not None:
            try:
                d, t = _normalize_date(date)
            except ValueError as e:
                return {"success": False, "message": str(e)}
            existing["prescribedDate"] = d
            existing["prescribedStartTime"] = t

        if blocks is not None:
            try:
                wire_blocks = []
                for b in blocks:
                    wire_blocks.append(await _build_block(b))
            except (ValueError, RuntimeError) as e:
                return {"success": False, "message": str(e)}
            existing["blocks"] = wire_blocks
            existing["snapshot"] = _compute_snapshot(wire_blocks)

        existing["lastUpdatedAt"] = datetime.now().isoformat(timespec="seconds")

        # PUT then POST /save to mirror the UI's two-phase commit.
        put_r = await c.put("workouts", json=existing)
        if not put_r.success:
            return {
                "success": False,
                "error_code": put_r.error_code.name if put_r.error_code else "API_ERROR",
                "message": f"PUT failed: {put_r.message}",
            }
        save_r = await c.post("workouts/save", json=existing)

    if not save_r.success:
        return {
            "success": False,
            "error_code": save_r.error_code.name if save_r.error_code else "API_ERROR",
            "message": f"POST /save failed: {save_r.message}",
        }
    persisted = _unwrap(save_r.data) or {}
    return {
        "success": True,
        "workout_id": persisted.get("id"),
        "title": persisted.get("title"),
        "totalSets": (persisted.get("snapshot") or {}).get("totalSets"),
        "totalPrescriptions": (persisted.get("snapshot") or {}).get("totalPrescriptions"),
    }


async def tp_delete_strength_workout(workout_id: str | int) -> dict[str, Any]:
    """Delete a structured strength workout."""
    async with StrengthClient() as c:
        r = await c.delete(f"workouts/{workout_id}")
    if not r.success:
        return {
            "success": False,
            "error_code": r.error_code.name if r.error_code else "API_ERROR",
            "message": r.message,
        }
    return {"success": True, "message": f"Workout {workout_id} deleted."}
