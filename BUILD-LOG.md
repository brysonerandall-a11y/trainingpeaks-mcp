# Build Log

This file is the durable record of why this fork exists and how the structured strength extension was built. If something breaks, or a future Claude session needs to understand the history without re-deriving it, start here.

## What this fork is

`brysonerandall-a11y/trainingpeaks-mcp` is a fork of `JamsusMaximus/trainingpeaks-mcp` extended with five new MCP tools that target TrainingPeaks's strength builder API. Upstream covers endurance only.

| | |
|---|---|
| Local clone | `~/Documents/AI & Projects/mcp-servers/trainingpeaks-mcp/` |
| Origin remote | `https://github.com/brysonerandall-a11y/trainingpeaks-mcp.git` |
| Upstream remote | `https://github.com/JamsusMaximus/trainingpeaks-mcp.git` |
| Branch | `main` |
| Registered in | `~/.claude.json` under `mcpServers.trainingpeaks` |
| Auth | OAuth bearer token, exchanged from a TrainingPeaks session cookie stored in macOS Keychain |
| Powers | `hybrid-lift-programmer` Routine (Sunday 6 PM Central) and `hybrid-lift-reprogrammer` Routine (ad-hoc) |

## Why we extended it

The hybrid-lift Routine originally wrote text descriptions into the workout body of `sport=Strength` workouts, because the existing MCP only spoke the `tpapi.trainingpeaks.com/fitness/v6/` API. That gave Bryce the prescription but no native weight logging.

Reverse-engineering the TP web UI revealed the strength builder lives on a completely separate domain: `api.peakswaresb.com/rx/activity/v1/`. The same OAuth bearer token works on both. Once that was clear, the path forward was an extension, not a workaround.

End state achieved 2026-05-03: the Routine writes structured workouts directly into TP, Bryce logs actual weights set-by-set on his phone during the workout, and the data is queryable for trend analysis.

## The five new tools

| Tool | Purpose |
|---|---|
| `tp_get_strength_workout(workout_id)` | Read a structured strength workout by id |
| `tp_search_exercise(query, limit)` | Search TP's 955-exercise library by name fragment |
| `tp_create_strength_workout(date, title, blocks, instructions, duration_minutes, tss_planned)` | Create a structured strength workout with native weight logging |
| `tp_update_strength_workout(workout_id, ...)` | Partial update of an existing structured workout |
| `tp_delete_strength_workout(workout_id)` | Delete a structured workout |

Total tool count after extension: 63 (was 58 in upstream).

## How a workout payload is shaped

The simplified Python dict format the LLM produces:

```python
tp_create_strength_workout(
    date="2026-05-04T06:00:00",
    title="Lower #1 (Squat focus)",
    instructions="Heavy squat day. If Whoop is red the night before, swap for 20 min mobility.",
    duration_minutes=50,
    tss_planned=40,
    blocks=[
        {
            "title": "Back Squat",
            "blockType": "SingleExercise",
            "exercises": [
                {"name": "Back Squat", "sets": [{"reps": 6}, {"reps": 6}, {"reps": 6}, {"reps": 6}]},
            ],
        },
        {
            "title": "Walking Lunge + Leg Raise",
            "blockType": "Superset",
            "exercises": [
                {"name": "DB Walking Lunge", "sets": [{"reps": 10}, {"reps": 10}, {"reps": 10}]},
                {"name": "Hanging Leg Raise", "sets": [{"reps": 12}, {"reps": 12}, {"reps": 12}]},
            ],
        },
        {
            "title": "Plank Finisher",
            "blockType": "SingleExercise",
            "exercises": [
                {"name": "Plank", "sets": [{"duration_seconds": 45}, {"duration_seconds": 45}, {"duration_seconds": 45}]},
            ],
        },
    ],
)
```

Block types: `SingleExercise`, `Superset`, `Circuit`, `WarmUp`, `CoolDown`.

Set parameters accepted: `reps`, `reps_per_side`, `weight_lb`, `weight_kg`, `weight_per_side_lb`, `weight_per_side_kg`, `duration_seconds`, `distance_meters`, `distance_miles`. Always leave weight columns blank — the athlete fills those in on the phone during the session.

## Critical constraints baked into the code

These are the gotchas that took multiple debug iterations to find. If you hit a 400 from TP, check this list first.

| Gotcha | Why it matters | Where it is handled |
|---|---|---|
| `workoutType` must be `"StructuredStrength"`, not `"Strength"` | TP rejects "Strength" silently with 400 "Invalid workout" | Hardcoded in `tp_create_strength_workout` |
| `calendarId` equals the athlete's id | Required, no default | Pulled via `TPClient.ensure_athlete_id()` |
| `prescribedStartTime` is time-only `HH:MM:SS`, never a full ISO datetime | Sending `2026-05-04T06:00:00` to that field returns 400 | `_normalize_date` strips date portion |
| Per-exercise time parameter is `Duration` (in seconds), NOT `TimeSeconds` | `TimeSeconds` is block-level only; using it on a prescription returns 400 | `_PARAM_CATALOG` and `_infer_parameters_for_exercise` |
| API responses are wrapped in `{"data": ..., "errors": {}}` | Unwrap before reading workout fields | `_unwrap` helper |
| Create flow is three steps, not one | POST `/workouts` returns a UUID-id draft, PUT `/workouts` populates blocks, POST `/workouts/save` commits to a persistent integer id | Implemented inside `tp_create_strength_workout` |
| Supersets need parameter compatibility | All exercises in a Superset must share parameter types (all reps-based, OR all duration-based, never mixed) | Documented in tool description; LLM has to honor this |
| Plank in a Superset with reps exercises will 400 | Same root cause as above | Plank goes in its own SingleExercise block |
| TP exercise names must match the library | Free-form names produce a closest-match silently | Use `tp_search_exercise` first to confirm the exact title |

## Common Bryce movements with their TP exercise IDs

Confirmed via `tp_search_exercise` during build. Use these to cross-check on future builds.

| Movement | TP id | Notes |
|---|---|---|
| Back Squat | 131 | Quad-dominant primary |
| Front Squat | 143 | Trunk-honest accessory |
| Paused Back Squat | 5356 | Variation |
| Deadlift | 141 | "Conventional Deadlift" maps here |
| Romanian Deadlift | 154 | |
| Single Leg Romanian Deadlift | 156 | Search "Single-Leg RDL" hits this too |
| TrapBar Deadlift | 903 | |
| DB Walking Lunge | 47 | Beware: bare "Walking Lunge" returns id 924 (overhead) |
| Bench Press | 16 | **BANNED** (all bench-press patterns) — see `docs/programming-spec.md` §2. Substitute: Machine Chest Press, Cable Chest Press, DB Floor Press (398), Push-up, or Dip. |
| DB Bench Press | 30 | **BANNED** (athlete avoiding all bench-press patterns 2026-05-13 forward) — see `docs/programming-spec.md` §2. Substitute: Machine Chest Press, Cable Chest Press, DB Floor Press (398), Push-up, or Dip. |
| Incline DB Press | 611 | **BANNED** (no incline equipment at athlete's setup) — see `docs/programming-spec.md` §2. No direct substitute; drop the slot, or use a low-to-high cable fly / standing landmine press for upper-chest emphasis. |
| Barbell Overhead Press | 11 | The ONLY allowed barbell pressing pattern. |
| DB Floor Press | 398 | Default heavy horizontal-press alternate. Confirmed via `tp_search_exercise "Floor Press"`. |
| Lat Pulldown | (search to confirm) | New default for the vertical-pull heavy slot (replaces Weighted Pull Up 930). |
| Seated DB Press | 771 | |
| Weighted Pull Up | 930 | **NOT PROGRAMMED** (athlete has no rack/band setup for weighted pull-ups 2026-05-13 forward) — see `docs/programming-spec.md` §3. Default vertical-pull anchor is now Lat Pulldown. Pull Up (73) is allowed for higher-rep finishers only. |
| Pull Up | 73 | Bodyweight. Use for higher-rep finishers; not the heavy vertical-pull anchor. |
| Bent Over Barbell Row | 134 | |
| Chest Supported Row | 422793 | |
| Face Pulls | 422794 | |
| Cable Lateral Raise | 470 | |
| DB Lateral Raise | 37 | |
| Cable Triceps Pushdown | 474 | |
| Cable Overhead Triceps Extension | 471 | "Overhead Cable Triceps Extension" maps here |
| Close Grip Incline Bench Press | 486 | **BANNED** (barbell close-grip bench/incline) — see `docs/programming-spec.md` §2. Substitute: Cable Triceps Pushdown (474), Cable Overhead Triceps Extension (471), DB Skullcrusher, or Dip Machine. |
| Barbell Bicep Curl | 9 | Bare "Barbell Curl" returns 737 (Reverse) |
| EZ Bar Curl | 564 | |
| DB Hammer Curls | 428966 | |
| Cross Body Hammer Curl | 492 | |
| Cable Hammer Curl | 467 | |
| DB Fly | 34 | "DB Chest Fly" maps here |
| Plank | 71 | Duration parameter, not Reps. Cap at 2× per week (core variety rule, programming-spec.md §5). |
| Hanging Leg Raise | 590 | Cap at 2× per week (core variety rule, programming-spec.md §5). |
| Cable Crunch | 464 | Flexion / dynamic pattern. |
| Side Plank | (search) | Anti-lateral-flexion pattern. |
| Bird Dog | (search) | Anti-rotation pattern. |
| Dead Bug | (search) | Anti-extension pattern. |
| Suitcase Carry | (search) | Anti-lateral-flexion pattern; DB unilateral. |
| Cable Wood Chop | (search) | Controlled rotation; high-to-low or low-to-high. |
| Russian Twist | (search) | Controlled rotation; DB or plate. |
| Pallof Press | (NOT in library) | Anti-rotation; substitute by logging Cable Crunch as the closest entry and putting "Pallof Press" in `coachNotes`. |
| Ab Wheel Rollout | (search; may not be in library) | Anti-extension; substitute as for Pallof Press if missing. |
| Rocking Standing Calf Raise | 750 | "Standing Calf Raise" maps here |
| Swiss Ball Leg Curl | 897 | "Lying Leg Curl" not in library; this is the closest |

Movements NOT in the library (substitute with above): Pallof Press, Lying Leg Curl (literal), Donkey Calf Raise, Pec Deck.

## Programming spec snapshot

The in-repo canonical programming spec is `docs/programming-spec.md`. Read it first for periodization rules, the elbow-safe pressing constraint, equipment baseline, and the alternatives convention. The personal/lifter-profile spec (off-repo) lives in `~/.claude/projects/-Users-randall-Documents-AI---Projects-projects/memory/hybrid_lifting_program.md`. On conflict, `docs/programming-spec.md` wins.

Headlines:

- Six lift days per week, Thursday off (scheduling constraint, not optional).
- Standard split: Mon Lower #1 (Squat), Tue Upper #1 (Heavy Push), Wed Upper #2 (Heavy Pull), Fri Upper #3 (Hypertrophy), Sat Arms+Calves+Core (light, before long ride), Sun Lower #2 (Hinge).
- Time targets: Mon/Sun 50 min @ 40 TSS, Tue/Wed/Fri 45 min @ 30-35 TSS, Sat 35 min @ 15 TSS.
- Main lifts get full rest (90 sec to 3:00). Accessories paired into supersets to cut idle time.
- 2-3 core movements every session, slotted into back-half supersets so they do not bloat session time.
- Movement variation week-to-week within the same pattern.
- **Periodization (see programming-spec.md §1):** default 4-week mesocycle = 3 loading weeks + 1 deload (~60% volume, intensity held). Linear for strength blocks, DUP for mixed/general phases, Block for race builds (≤12 weeks out). Each loading week shows a single explicit progression rule (`+load`, `+reps`, `+sets`, or `+density`), recorded in the workout `instructions` field as `Progression: <rule> (W<n> of 4)` so a future session can read it back.
- **Pressing constraint (see programming-spec.md §2, HARD RULE — updated 2026-05-13):** barbell pressing is overhead press only. ALL bench-press patterns are banned, including DB Bench Press — horizontal-press default is now Machine Chest Press (alternates: Cable Chest Press, DB Floor Press, push-up, dip). NO incline pressing of any kind (no incline equipment at athlete's setup); drop the slot or substitute a low-to-high cable fly / standing landmine press. Banned ids include Bench Press (16), DB Bench Press (30), Incline DB Press (611), and Close Grip Incline Bench Press (486).
- **Vertical pull (see programming-spec.md §3 — updated 2026-05-13):** Lat Pulldown is the heavy vertical-pull default. Weighted Pull Up (930) is NOT programmed (no rack/band at athlete's setup). Pull Up (73) is allowed only for higher-rep finishers.
- **Rest times (see programming-spec.md §4 — NEW 2026-05-13):** every prescription's `coachNotes` field starts with `Rest <X>. Alt: <a>; <b>.` Defaults: main compound 2:30-3:00, secondary 1:30-2:00, accessory in superset 60-75s, core 45-60s, plyo 1:30-2:00. Rest must live on the prescription, not the top-level `instructions`, so the lifter sees it in the phone UI during the set.
- **Core variety (see programming-spec.md §5 — NEW 2026-05-13):** five patterns — anti-extension, anti-rotation, anti-lateral-flexion, flexion/dynamic, controlled rotation. Hit ≥3 patterns per week, ≥4 distinct movements. Plank and Hanging Leg Raise each cap at 2× per week.
- **Plyometrics (see programming-spec.md §6 — NEW 2026-05-13):** plyo block goes FIRST after warm-up, before the heavy compound. 2-4 sets × 3-5 reps with 1:30-2:00 rest. Day-specific bias: Mon vertical jumps, Sun horizontal jumps + KB swings, Tue plyo push-up / MB chest pass, Wed MB rotational throws. Skip on Fri (hypertrophy) and Sat (pre-long-ride). Skip during deload.
- **Cardio intervals (see programming-spec.md §7 — NEW 2026-05-13):** VO2 Max, MAP, and sprint protocols via the WODWAY curved treadmill. 1× VO2 Max OR MAP per week (Wed default) + optionally 1× sprint session (Tue/Fri). Logged as endurance Run workouts via `tp_create_workout`, NOT as strength. Never stack against Natasha's quality run days.
- **Equipment & alternatives (see programming-spec.md §3):** default site is Trump Tower Chicago Fitness Club (assume well-equipped commercial gym). Every "main movement" must include 1-2 alternative movements in the `coachNotes` field on the same prescription where rest times go, so there is a fallback if equipment is missing.
- Race-phase modulation: 5+ weeks out full program, 2-3 weeks out drop Sat lift, race week and post-race deload have no strength.
- Weight columns always blank in the prescription; Bryce logs actual loads on his phone during the session.

## Operational details

### How a future session loads context

Open this file. Then check:

1. `notes-strength-api/SCHEMA.md` for full API reference.
2. `notes-strength-api/README.md` for the captures folder explanation.
3. `~/.claude/projects/-Users-randall-Documents-AI---Projects-projects/memory/hybrid_lifting_program.md` for the programming spec.
4. `git log -- src/tp_mcp/tools/strength.py src/tp_mcp/client/strength_http.py` for change history.

### How to invoke the new tools

Three paths:

1. **Native MCP tools after Claude Code restart:** `mcp__trainingpeaks__tp_create_strength_workout`, `mcp__trainingpeaks__tp_search_exercise`, etc. Available once Claude Code spawns a fresh tp-mcp server.
2. **Python wrapper from any session:**
   ```bash
   "/Users/randall/Documents/AI & Projects/mcp-servers/trainingpeaks-mcp/.venv/bin/python" - <<'PY'
   import asyncio
   from tp_mcp.tools.strength import tp_create_strength_workout
   asyncio.run(tp_create_strength_workout(...))
   PY
   ```
3. **Inside the Sunday Routine:** the Routine body lists the tool calls in its Steps to Execute. The Routine fires Sunday 6 PM Central from a fresh Claude Code session and picks up whatever the MCP server exposes.

### How to apply code changes

The package is installed as a regular (non-editable) install, NOT editable. Reason: macOS Python's `.pth` file processing did not honor a path containing spaces and `&` characters, so the editable install pointed at `src/` was silently ignored at import time. Symptom was the MCP server failing to start with `ModuleNotFoundError: No module named 'tp_mcp'`.

Workflow when you change code in `src/`:

```bash
cd "/Users/randall/Documents/AI & Projects/mcp-servers/trainingpeaks-mcp"
./.venv/bin/pip install ".[browser]" 2>&1 | tail -5
./.venv/bin/tp-mcp auth-status   # smoke test
```

Then quit Claude Code and relaunch so it spawns a fresh MCP server with your new code.

### How to refresh authentication

The TP cookie lasts roughly two weeks. When it expires:

```bash
"/Users/randall/Documents/AI & Projects/mcp-servers/trainingpeaks-mcp/.venv/bin/tp-mcp" auth --from-browser chrome
```

May trigger macOS Keychain or Full Disk Access prompts. Approve them. Cookie gets exchanged for a fresh OAuth token and stored in the system keyring.

### How to refresh the captures (if TP changes their API)

See `notes-strength-api/README.md` for the script. Re-run captures, diff against the saved files, update `_PARAM_CATALOG` or schema if needed.

## Session-by-session history

### Session 1 (2026-04-27, Mon evening)

Installed upstream `JamsusMaximus/trainingpeaks-mcp`. Authenticated via Chrome cookie auto-extract. Registered in `~/.claude.json`. Verified via `tp_auth_status` and `tp_get_workouts`. First manual hybrid-lift programming pass for week of 4/27-5/3 using text descriptions (3 sessions: Tue Upper Push, Fri Upper Pull, Sun Lower combined). Memory file `hybrid_lifting_program.md` created with the lifter profile and constraints.

### Session 2 (2026-04-27, late evening)

Refined the programming to a six-day split (Mon-Tue-Wed-Fri-Sat-Sun). Updated this week's plan to add Wed Heavy Pull and Sat Arms+Calves+Core, repurposed Friday from Pull to Hypertrophy. Built two Routines via the build-routine skill: `hybrid-lift-programmer` (Sunday 6 PM Central recurring) and `hybrid-lift-reprogrammer` (ad-hoc, manual trigger when Natasha changes the endurance plan). Test-fired the recurring Routine with an HTML email summary. Added supersets and a 2-3 core movement rule per session.

### Session 3 (2026-04-28)

Mid-week, Natasha updated her endurance plan: removed Friday's run, added Sunday aerobic run, moved Train Heroic strength placeholder to Wednesday. Ran the reprogrammer logic inline: deleted the Wed Heavy Pull (would double-stack with Train Heroic), trimmed Sunday Lower volume to account for the new Sunday run. Then captured TP's strength builder API via Chrome MCP network sniffing, parsed the schema, and wrote `notes-strength-api/SCHEMA.md` as the build reference.

### Session 4 (2026-05-03, evening)

Built the strength MCP extension. New file `tp_mcp/client/strength_http.py` (`StrengthClient` reusing `TPClient` token cache, targeting `api.peakswaresb.com`). New file `tp_mcp/tools/strength.py` (the five tools, builder helpers, library cache). Registered in `tp_mcp/tools/__init__.py` and `tp_mcp/server.py`. Round-trip test passed (create -> read -> update -> delete a fake workout). Migrated next week's 6 lifts from text descriptions to structured workouts (135 prescribed sets, all with empty weight columns). Updated both Routines to call the new tools instead of text-format. Updated memory file with the new programming format.

### Session 5 (2026-05-03, late evening)

GitHub fork created at `brysonerandall-a11y/trainingpeaks-mcp`. Renamed previous `origin` to `upstream`, added the fork as new `origin`. Committed and pushed our changes (12 files, 1562 insertions, commit `0327563`). Updated `skill-audit.md` with the new MCP entry. Discovered the editable install was silently broken (path with spaces and `&`); reinstalled as a regular non-editable package. Wrote this build log.

### Session 6 (2026-05-09)

Created in-repo programming spec at `docs/programming-spec.md` covering: 4-week mesocycle (3 loading + 1 deload), model selection (linear / DUP / block), microcycle progression rules (`+load`, `+reps`, `+sets`, `+density`) encoded in the workout `instructions` field, deload semantics (~60% volume, intensity held), the elbow-safe pressing constraint (barbell pressing = overhead press only), Trump Tower Chicago equipment baseline, and the alternatives-in-coachNotes convention for every main movement. Audited existing repo files for banned barbell pressing: `notes-strength-api/workout-19347189.json` was clean (DB/bodyweight only); the BUILD-LOG.md exercise reference table had Bench Press (16) and Close Grip Incline Bench Press (486) listed as available — both flagged BANNED with substitute pointers in place. No active prescription file required a movement swap.

### Session 7 (2026-05-13)

Athlete feedback on the week-of-2026-05-11 prescription triggered five spec changes for the week-of-2026-05-18 Sunday Routine to apply:

1. **Pressing constraint tightened (programming-spec.md §2):** DB Bench Press (id 30) and all incline pressing (Incline DB Press 611, Incline Machine Press) are now BANNED. DB Bench was previously the default substitute for the banned barbell bench; the athlete now avoids all bench-press patterns, not just barbell. Incline pressing is removed entirely because the athlete has no incline equipment. Horizontal-press default is now Machine Chest Press (alternates: Cable Chest Press, DB Floor Press 398, push-up, dip). Incline slot drops or substitutes a low-to-high cable fly / standing landmine press.
2. **Vertical-pull default rewritten (programming-spec.md §3):** Lat Pulldown replaces Weighted Pull Up (930) as the heavy vertical-pull anchor. The athlete has no rack/band setup for weighted pull-ups. Pull Up (73, bodyweight) is allowed for higher-rep finishers only.
3. **Rest times made mandatory and discoverable (programming-spec.md §4, NEW):** every `exercises[*].coachNotes` must start with `Rest <X>. Alt: <a>; <b>.` so the lifter sees rest in the phone UI during the set. Defaults table added. The Mon 2026-05-11 lift had no per-exercise rest visible — root cause was that the rest convention lived in §3 prose without an audit gate, so it was silently dropped.
4. **Core variety rule added (programming-spec.md §5, NEW):** five core patterns (anti-extension, anti-rotation, anti-lateral-flexion, flexion, controlled rotation). Hit ≥3 patterns per week, ≥4 distinct movements. Plank and Hanging Leg Raise cap at 2× per week each. Triggered by the prior week's overuse of Plank and Hanging Leg Raise.
5. **Plyometrics added (programming-spec.md §6, NEW):** plyo block goes FIRST after warm-up, 2-4 sets × 3-5 reps, 1:30-2:00 rest. Day-specific bias table. Skip Fri/Sat and deload weeks.
6. **Cardio intervals added (programming-spec.md §7, NEW):** VO2 Max, MAP, and sprint protocols for the WODWAY curved treadmill. 1× VO2 Max OR MAP per week (Wed default) + optionally 1× sprint session (Tue/Fri). Logged as endurance Run workouts via `tp_create_workout`. Never stack against Natasha's quality run days.

BUILD-LOG.md exercise table updated: DB Bench Press (30), Incline DB Press (611), and Weighted Pull Up (930) marked BANNED / NOT PROGRAMMED with substitute pointers. Added DB Floor Press (398) and a starter set of core-variety movements (Side Plank, Bird Dog, Dead Bug, Suitcase Carry, Cable Wood Chop, Russian Twist) to the movements table — most need `tp_search_exercise` confirmation at programming time.

No code changes; spec-only update. The Sunday Routine running 2026-05-17 will read the updated spec when it programs the week of 2026-05-18.

## Known issues and gotchas

1. **Editable installs are broken on this filesystem.** The `.pth` mechanism does not honor the `~/Documents/AI & Projects/mcp-servers/trainingpeaks-mcp/src` path. Stay on regular installs (`pip install .`).

2. **Native MCP tools require a Claude Code quit-and-relaunch after any code change.** A `/clear` or in-session reset does not respawn the MCP server.

3. **TP cookie expires every ~2 weeks.** Bryce will need to re-run `tp-mcp auth --from-browser chrome` periodically. Both Routines detect auth failure and send a `[ACTION REQUIRED]` email instead of writing workouts.

4. **Some movements are not in the TP library.** Pallof Press, literal Lying Leg Curl, Donkey Calf Raise. Substitute with closest matches (see exercise table above) or fall back to instructions text for those movements.

5. **TP exercise library matches are scored by title fuzziness.** Bare "Barbell Curl" returns "Reverse Barbell Curl" because of how the scoring breaks ties. Use precise names ("Barbell Bicep Curl", id 9) to avoid surprises.

6. **The Sunday Routine fires from a fresh Claude Code session.** Whatever code is installed at that moment is what runs. After any code change, reinstall + relaunch before the next Sunday at 6 PM.

## Quick reference: re-running the migration

If the structured workouts get out of sync with the spec, the path to rebuild a week from scratch:

```python
import asyncio
from tp_mcp.tools.workouts import tp_get_workouts, tp_delete_workout
from tp_mcp.tools.strength import tp_delete_strength_workout, tp_create_strength_workout

async def main():
    # 1. Find existing strength sessions
    plan = await tp_get_workouts(start_date="YYYY-MM-DD", end_date="YYYY-MM-DD", workout_filter="planned")
    # filter for sport=Strength and titles starting with "Upper", "Lower", "Arms +"
    # 2. Delete via tp_delete_workout (text-format) or tp_delete_strength_workout (structured)
    # 3. Build new sessions per the spec
    # 4. Write via tp_create_strength_workout

asyncio.run(main())
```

The full migration script that ran in Session 4 is in the conversation transcript and can be regenerated from the programming spec.
