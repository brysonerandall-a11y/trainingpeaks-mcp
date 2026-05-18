#!/usr/bin/env python3
"""Build next week's hybrid-lift strength block per docs/programming-spec.md.

Canonical split (spec §1A, set 2026-05-17): five lift days — Mon, Tue, Wed,
Fri, Sat. Thursday AND Sunday are non-strength recovery days. The old Sunday
"Lower #2 (Hinge)" was the highest-CNS session; it was cut and the hinge
pattern redistributed sub-maximally (moderate RDL Mon, hypertrophy-rep hinge
Fri). This script is what the Sunday Routine runs to materialise that week.

Usage:
    python scripts/program_week.py                 # dry run, prints the plan
    python scripts/program_week.py --write          # create the workouts in TP
    python scripts/program_week.py --week-start 2026-05-18 [--write]

Default is a dry run so it is always safe to inspect "what's ahead" without
touching the live calendar. --write requires a working tp-mcp auth context.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import re
import sys

# DUP mesocycle: one progression rule per main lift per loading week. Deload
# (W4) cuts sets to ~60%, intensity held. Recorded in `instructions` so a
# future run reads it back (spec §1).
PROGRESSION = {
    1: "baseline (W1 of 4)",
    2: "+load 2.5% on main lifts (W2 of 4)",
    3: "+load ~5% / -1 rep on main lifts (W3 of 4)",
    4: "Deload: ~60% volume, intensity held (W4 of 4)",
}

# Elbow-safe (spec §2): barbell pressing is overhead only. Audit guardrail so
# a future edit cannot silently introduce a banned barbell press.
_BANNED_PHRASES = (
    "barbell bench",
    "incline barbell",
    "barbell incline",
    "decline barbell",
    "barbell decline",
    "close grip bench",
    "barbell floor press",
)
_ALLOWED_MODALITY = ("db ", "dumbbell", "machine", "cable", "smith ")


def _reps(*counts: int) -> list[dict]:
    return [{"reps": c} for c in counts]


def _secs(*durations: int) -> list[dict]:
    return [{"duration_seconds": d} for d in durations]


def build_sessions() -> list[dict]:
    """The five canonical sessions. Loads stay blank — logged on the phone."""
    return [
        {
            "weekday": 0,  # Monday
            "title": "Lower — Squat + Hinge",
            "duration_minutes": 50,
            "tss_planned": 40,
            "instructions": (
                "Heaviest day of the week; you come in fresh off Sunday "
                "recovery. Back Squat is the anchor. The RDL is the "
                "submax hinge that replaced the old Sunday hinge day — "
                "keep it well short of a max-strength deadlift. If Whoop "
                "is red, drop to 2 squat sets and skip the lunge superset."
            ),
            "blocks": [
                {
                    "title": "Back Squat",
                    "blockType": "SingleExercise",
                    "exercises": [
                        {
                            "name": "Back Squat",
                            "coachNotes": "Rest 2:30. Alt: Hack Squat; Front Squat.",
                            "sets": _reps(6, 6, 6, 6),
                        }
                    ],
                },
                {
                    "title": "Romanian Deadlift",
                    "blockType": "SingleExercise",
                    "exercises": [
                        {
                            "name": "Romanian Deadlift",
                            "coachNotes": (
                                "Rest 2:00. SUBMAX — this is the redistributed "
                                "Sunday hinge, not a max pull. Alt: Trap Bar "
                                "Deadlift; Single Leg Romanian Deadlift."
                            ),
                            "sets": _reps(8, 8, 8),
                        }
                    ],
                },
                {
                    "title": "Walking Lunge + Leg Raise",
                    "blockType": "Superset",
                    "exercises": [
                        {
                            "name": "DB Walking Lunge",
                            "coachNotes": "Rest 90s. Alt: Reverse Lunge (DB); Bulgarian Split Squat.",
                            "sets": _reps(10, 10, 10),
                        },
                        {"name": "Hanging Leg Raise", "sets": _reps(12, 12, 12)},
                    ],
                },
                {
                    "title": "Plank",
                    "blockType": "SingleExercise",
                    "exercises": [{"name": "Plank", "sets": _secs(45, 45, 45)}],
                },
            ],
        },
        {
            "weekday": 1,  # Tuesday
            "title": "Upper Push (Heavy)",
            "duration_minutes": 45,
            "tss_planned": 32,
            "instructions": (
                "Heavy vertical + horizontal press. Barbell pressing is "
                "overhead ONLY (elbow-safe rule). Horizontal press stays "
                "DB/machine/cable."
            ),
            "blocks": [
                {
                    "title": "Barbell Overhead Press",
                    "blockType": "SingleExercise",
                    "exercises": [
                        {
                            "name": "Barbell Overhead Press",
                            "coachNotes": "Rest 2:00. Alt: Seated DB Press; Machine Shoulder Press.",
                            "sets": _reps(6, 6, 6, 6),
                        }
                    ],
                },
                {
                    "title": "DB Bench Press",
                    "blockType": "SingleExercise",
                    "exercises": [
                        {
                            "name": "DB Bench Press",
                            "coachNotes": "Rest 2:00. Alt: Machine Chest Press; Cable Chest Press.",
                            "sets": _reps(8, 8, 8),
                        }
                    ],
                },
                {
                    "title": "Lateral Raise + Pushdown",
                    "blockType": "Superset",
                    "exercises": [
                        {"name": "DB Lateral Raise", "sets": _reps(12, 12, 12)},
                        {"name": "Cable Triceps Pushdown", "sets": _reps(12, 12, 12)},
                    ],
                },
                {
                    "title": "Core",
                    "blockType": "Superset",
                    "exercises": [
                        {"name": "Hanging Leg Raise", "sets": _reps(12, 12, 12)},
                        {"name": "Cable Crunch", "sets": _reps(15, 15, 15)},
                    ],
                },
            ],
        },
        {
            "weekday": 2,  # Wednesday
            "title": "Upper Pull (Heavy)",
            "duration_minutes": 45,
            "tss_planned": 32,
            "instructions": "Heavy vertical + horizontal pull. Full rest on the two anchors.",
            "blocks": [
                {
                    "title": "Weighted Pull Up",
                    "blockType": "SingleExercise",
                    "exercises": [
                        {
                            "name": "Weighted Pull Up",
                            "coachNotes": "Rest 2:00. Alt: Lat Pulldown; Assisted Pull Up Machine.",
                            "sets": _reps(6, 6, 6, 6),
                        }
                    ],
                },
                {
                    "title": "Chest Supported Row",
                    "blockType": "SingleExercise",
                    "exercises": [
                        {
                            "name": "Chest Supported Row",
                            "coachNotes": "Rest 2:00. Alt: Bent Over Barbell Row; Cable Row.",
                            "sets": _reps(8, 8, 8),
                        }
                    ],
                },
                {
                    "title": "Face Pulls + Hammer Curls",
                    "blockType": "Superset",
                    "exercises": [
                        {"name": "Face Pulls", "sets": _reps(15, 15, 15)},
                        {"name": "DB Hammer Curls", "sets": _reps(10, 10, 10)},
                    ],
                },
                {
                    "title": "Core",
                    "blockType": "Superset",
                    "exercises": [
                        {"name": "Hanging Leg Raise", "sets": _reps(12, 12, 12)},
                        {"name": "Cable Crunch", "sets": _reps(15, 15, 15)},
                    ],
                },
            ],
        },
        {
            "weekday": 4,  # Friday
            "title": "Hypertrophy + Hinge",
            "duration_minutes": 45,
            "tss_planned": 35,
            "instructions": (
                "Second posterior-chain exposure of the week, at "
                "hypertrophy reps and submax load (low CNS by design — "
                "this is why Sunday could be cut). Single-Leg RDL leads, "
                "then upper hypertrophy supersets."
            ),
            "blocks": [
                {
                    "title": "Single Leg Romanian Deadlift",
                    "blockType": "SingleExercise",
                    "exercises": [
                        {
                            "name": "Single Leg Romanian Deadlift",
                            "coachNotes": (
                                "10 per side. Rest 90s. SUBMAX hypertrophy "
                                "hinge. Alt: Romanian Deadlift (bilateral); "
                                "Swiss Ball Leg Curl."
                            ),
                            "sets": _reps(10, 10, 10),
                        }
                    ],
                },
                {
                    "title": "Incline Press + Row",
                    "blockType": "Superset",
                    "exercises": [
                        {"name": "Incline DB Press", "sets": _reps(10, 10, 10)},
                        {"name": "Chest Supported Row", "sets": _reps(10, 10, 10)},
                    ],
                },
                {
                    "title": "Lateral Raise + Hammer Curl",
                    "blockType": "Superset",
                    "exercises": [
                        {"name": "DB Lateral Raise", "sets": _reps(15, 15, 15)},
                        {"name": "DB Hammer Curls", "sets": _reps(12, 12, 12)},
                    ],
                },
                {
                    "title": "Hamstring + Core",
                    "blockType": "Superset",
                    "exercises": [
                        {"name": "Swiss Ball Leg Curl", "sets": _reps(12, 12, 12)},
                        {"name": "Cable Crunch", "sets": _reps(15, 15, 15)},
                    ],
                },
                {
                    "title": "Plank",
                    "blockType": "SingleExercise",
                    "exercises": [{"name": "Plank", "sets": _secs(45, 45, 45)}],
                },
            ],
        },
        {
            "weekday": 5,  # Saturday
            "title": "Arms + Calves + Core (light)",
            "duration_minutes": 35,
            "tss_planned": 15,
            "instructions": (
                "Deliberately light and isolation-only — it sits before "
                "the long ride and the now-protected Sunday recovery. Do "
                "NOT add load here to 'make up' for the cut Sunday."
            ),
            "blocks": [
                {
                    "title": "Curl + Pushdown",
                    "blockType": "Superset",
                    "exercises": [
                        {"name": "EZ Bar Curl", "sets": _reps(12, 12, 12)},
                        {"name": "Cable Triceps Pushdown", "sets": _reps(12, 12, 12)},
                    ],
                },
                {
                    "title": "Hammer Curl + Overhead Extension",
                    "blockType": "Superset",
                    "exercises": [
                        {"name": "Cross Body Hammer Curl", "sets": _reps(12, 12, 12)},
                        {"name": "Cable Overhead Triceps Extension", "sets": _reps(12, 12, 12)},
                    ],
                },
                {
                    "title": "Calves",
                    "blockType": "SingleExercise",
                    "exercises": [
                        {
                            "name": "Rocking Standing Calf Raise",
                            "coachNotes": "Rest 60s. Alt: Smith Calf Raise; Seated Calf Raise Machine.",
                            "sets": _reps(15, 15, 15, 15),
                        }
                    ],
                },
                {
                    "title": "Core",
                    "blockType": "Superset",
                    "exercises": [
                        {"name": "Hanging Leg Raise", "sets": _reps(15, 15, 15)},
                        {"name": "Cable Crunch", "sets": _reps(15, 15, 15)},
                    ],
                },
            ],
        },
    ]


def audit_elbow_safe(sessions: list[dict]) -> list[str]:
    """Return a list of violations of the elbow-safe pressing rule (spec §2)."""
    violations: list[str] = []
    for s in sessions:
        for block in s["blocks"]:
            for ex in block["exercises"]:
                name = ex["name"].lower()
                if any(p in name for p in _BANNED_PHRASES):
                    violations.append(f"{s['title']}: {ex['name']} (banned phrase)")
                elif "bench press" in name and not any(
                    m in name for m in _ALLOWED_MODALITY
                ):
                    violations.append(
                        f"{s['title']}: {ex['name']} (bench press w/o DB/machine/cable)"
                    )
    return violations


def apply_deload(sessions: list[dict]) -> None:
    """W4: cut working sets to ~60% (intensity held). Mutates in place."""
    for s in sessions:
        for block in s["blocks"]:
            for ex in block["exercises"]:
                n = len(ex["sets"])
                keep = max(2, round(n * 0.6))
                ex["sets"] = ex["sets"][:keep]
        s["tss_planned"] = round(s["tss_planned"] * 0.65)


def next_monday(today: dt.date) -> dt.date:
    """The Monday that starts next week (strictly after today's week)."""
    return today + dt.timedelta(days=(7 - today.weekday()) % 7 or 7)


async def detect_meso_week(week_start: dt.date) -> int:
    """Best-effort: read the prior week's strength workouts and parse the
    `W<n> of 4` marker out of their instructions. Default to W1 on any miss."""
    try:
        from tp_mcp.tools.workouts import tp_get_workouts  # noqa: PLC0415

        prior_start = (week_start - dt.timedelta(days=7)).isoformat()
        prior_end = (week_start - dt.timedelta(days=1)).isoformat()
        res = await tp_get_workouts(prior_start, prior_end, "planned")
        blob = json.dumps(res)
        m = re.search(r"W(\d)\s*of\s*4", blob)
        if m:
            prior = int(m.group(1))
            nxt = prior % 4 + 1
            print(f"  prior week detected as W{prior} of 4 → next week is W{nxt}")
            return nxt
        print("  no prior-week mesocycle marker found → defaulting to W1")
    except Exception as e:  # noqa: BLE001 - degrade gracefully, never block the week
        print(f"  prior-week lookup unavailable ({type(e).__name__}) → defaulting to W1")
    return 1


def render(sessions: list[dict], dates: dict[int, dt.date], meso: int) -> str:
    out = [f"\n=== Next week — DUP {PROGRESSION[meso]} ===\n"]
    for s in sessions:
        d = dates[s["weekday"]]
        out.append(f"{d.strftime('%a %Y-%m-%d')}  {s['title']}  "
                   f"({s['duration_minutes']} min / ~{s['tss_planned']} TSS)")
        for b in s["blocks"]:
            tag = "" if b["blockType"] == "SingleExercise" else f" [{b['blockType']}]"
            for ex in b["exercises"]:
                sets = ex["sets"]
                if "reps" in sets[0]:
                    scheme = f"{len(sets)}x{sets[0]['reps']}"
                else:
                    scheme = f"{len(sets)}x{sets[0]['duration_seconds']}s"
                note = f"  — {ex['coachNotes']}" if ex.get("coachNotes") else ""
                out.append(f"    {ex['name']}: {scheme}{tag}{note}")
        out.append("")
    return "\n".join(out)


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--week-start", help="YYYY-MM-DD Monday; default = next Monday")
    ap.add_argument("--write", action="store_true",
                    help="actually create the workouts in TrainingPeaks")
    args = ap.parse_args()

    if args.week_start:
        monday = dt.date.fromisoformat(args.week_start)
        if monday.weekday() != 0:
            print(f"error: {monday} is not a Monday", file=sys.stderr)
            return 2
    else:
        monday = next_monday(dt.date.today())

    dates = {wd: monday + dt.timedelta(days=wd) for wd in (0, 1, 2, 4, 5)}
    print(f"Week of {monday} (Thu {monday + dt.timedelta(days=3)} and "
          f"Sun {monday + dt.timedelta(days=6)} are recovery — no strength)")

    meso = await detect_meso_week(monday)
    sessions = build_sessions()
    if meso == 4:
        apply_deload(sessions)

    violations = audit_elbow_safe(sessions)
    if violations:
        print("ELBOW-SAFE AUDIT FAILED:", file=sys.stderr)
        for v in violations:
            print(f"  - {v}", file=sys.stderr)
        return 1
    print("  elbow-safe audit: clean")

    print(render(sessions, dates, meso))

    if not args.write:
        print("Dry run. Re-run with --write to create these in TrainingPeaks.")
        return 0

    from tp_mcp.tools.strength import tp_create_strength_workout  # noqa: PLC0415

    rule = PROGRESSION[meso]
    for s in sessions:
        d = dates[s["weekday"]]
        instructions = f"{s['instructions']}\n\nProgression: {rule}"
        res = await tp_create_strength_workout(
            date=f"{d.isoformat()}T06:00:00",
            title=s["title"],
            blocks=s["blocks"],
            instructions=instructions,
            duration_minutes=s["duration_minutes"],
            tss_planned=s["tss_planned"],
        )
        ok = res.get("success")
        print(f"  {d} {s['title']}: "
              f"{'created id=' + str(res.get('workout_id')) if ok else 'FAILED ' + str(res.get('message'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
