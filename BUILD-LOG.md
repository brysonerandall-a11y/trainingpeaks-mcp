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
| Bench Press | 16 | **BANNED** (barbell flat bench) — see `docs/programming-spec.md` §2. Substitute: DB Bench Press (30) or machine/cable chest press. |
| DB Bench Press | 30 | Use this for "Flat DB Press" intent. Default substitute for Bench Press (16). |
| Incline DB Press | 611 | Default for incline pressing. Barbell incline is BANNED — see programming-spec.md §2. |
| Barbell Overhead Press | 11 | The ONLY allowed barbell pressing pattern. |
| Seated DB Press | 771 | |
| Weighted Pull Up | 930 | |
| Pull Up | 73 | Bodyweight |
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
| Plank | 71 | Duration parameter, not Reps |
| Hanging Leg Raise | 590 | |
| Cable Crunch | 464 | |
| Rocking Standing Calf Raise | 750 | "Standing Calf Raise" maps here |
| Swiss Ball Leg Curl | 897 | "Lying Leg Curl" not in library; this is the closest |

Movements NOT in the library (substitute with above): Pallof Press, Lying Leg Curl (literal), Donkey Calf Raise, Pec Deck.

## Programming spec snapshot

The in-repo canonical programming spec is `docs/programming-spec.md`. Read it first for periodization rules, the elbow-safe pressing constraint, equipment baseline, and the alternatives convention. The personal/lifter-profile spec (off-repo) lives in `~/.claude/projects/-Users-randall-Documents-AI---Projects-projects/memory/hybrid_lifting_program.md`. On conflict, `docs/programming-spec.md` wins.

Headlines:

- Five lift days per week (Mon, Tue, Wed, Fri, Sat). **Thursday AND Sunday are non-strength recovery days** (scheduling constraint, not optional). Sunday was demoted from a lift day to recovery on 2026-05-17 because cumulative weekly CNS load was leaving the athlete fried by Sunday; the coach already programs endurance every day, so the strength week needed a net reduction, not a redistribution.
- Standard split: Mon Lower (Squat focus + moderate hinge accessory), Tue Upper #1 (Heavy Push), Wed Upper #2 (Heavy Pull), Fri Hypertrophy + Hinge (hip-dominant at hypertrophy reps), Sat Arms+Calves+Core (light, before long ride).
- Hinge redistribution: the old Sunday "Lower #2 (Hinge)" was the single most CNS-expensive session in the week. Removing it gives the largest CNS relief per day cut. The hinge **pattern** is preserved sub-maximally — a moderate RDL accessory on Mon (3×8, after the squat) and a hypertrophy-rep hinge anchor on Fri (3×10, submax). Trained twice weekly, never at the max-strength cost that was the problem. Weekly strength TSS drops ~194 → ~154 (~20%, concentrated on the CNS axis), which is the intended net reduction.
- Time targets: Mon 50 min @ 40 TSS, Tue/Wed 45 min @ 30-35 TSS, Fri 45 min @ 35 TSS, Sat 35 min @ 15 TSS.
- Main lifts get full rest (90 sec to 3:00). Accessories paired into supersets to cut idle time.
- 2-3 core movements every session, slotted into back-half supersets so they do not bloat session time.
- Movement variation week-to-week within the same pattern.
- **Periodization (see programming-spec.md §1):** default 4-week mesocycle = 3 loading weeks + 1 deload (~60% volume, intensity held). Linear for strength blocks, DUP for mixed/general phases, Block for race builds (≤12 weeks out). Each loading week shows a single explicit progression rule (`+load`, `+reps`, `+sets`, or `+density`), recorded in the workout `instructions` field as `Progression: <rule> (W<n> of 4)` so a future session can read it back.
- **Pressing constraint (see programming-spec.md §2, HARD RULE):** barbell pressing is overhead press only. All horizontal/incline pressing must be DB, machine, or cable. Reason: mild elbow tendonosis flares with barbell bench/incline. Banned ids include Bench Press (16) and Close Grip Incline Bench Press (486); substitutes are flagged in the movements table above.
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

### Writing the week to TrainingPeaks — run it from the Mac, not a cloud session

`scripts/program_week.py` (added Session 7) is the canonical next-week builder. From the Mac:

```bash
cd "/Users/randall/Documents/AI & Projects/mcp-servers/trainingpeaks-mcp"
git checkout main && git pull origin main           # get the latest plan/spec
./.venv/bin/python scripts/program_week.py           # preview (dry run, no auth needed)
./.venv/bin/python scripts/program_week.py --write   # create the 5 sessions in TP
```

If the write reports an auth error, refresh the cookie (`tp-mcp auth --from-browser chrome`, see below) and re-run the `--write` line.

**Cloud sessions (Claude Code on the web) cannot do the `--write` step — and it is not an auth problem.** The cloud sandbox's network policy denies all `*.trainingpeaks.com` and `api.peakswaresb.com` egress (proxy returns `403 host_not_allowed`; `api.peakswaresb.com` is TLS-blocked). The cookie→token exchange, the athlete-id lookup, and the workout write all need those hosts, so even a valid cookie supplied via `TP_AUTH_COOKIE` cannot complete a write there. A cloud session CAN build and verify the plan (the dry run is offline-safe), but the live write must run from the Mac or the Sunday Routine (which also runs on the Mac). Note: merging to `main` on GitHub does NOT push code to the Mac — someone must `git pull` on the Mac before the new plan is what the routine runs.

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

### Session 7 (2026-05-17, Sunday)

Demoted Sunday from a lift day to a non-strength recovery day at the athlete's request (CNS fried by Sunday; coach programs endurance daily, so the strength week needed a net cut). Split went 6-day → 5-day: Mon/Tue/Wed/Fri/Sat lift, Thu+Sun recovery. The old Sunday "Lower #2 (Hinge)" was the highest-CNS session, so cutting it specifically maximised relief; the hinge pattern was preserved sub-maximally (moderate RDL accessory Mon, hypertrophy-rep hinge Fri) rather than dropped or crammed in heavy. Updated `docs/programming-spec.md` (new "Weekly split" section, `Last updated` bump, "six-day" → "five-day") and the BUILD-LOG headlines. Added `scripts/program_week.py` — a self-contained, idempotent next-week builder that reads the prior week's `instructions` for the DUP mesocycle/progression state, builds the 5 sessions per the new split with the elbow-safe audit and `Alt:` lines, and writes via `tp_create_strength_workout`. This cloud session could not write to live TP (no MCP server / no keyring auth / TP API blocked 403), so the live calendar write must run from the local box or the Sunday Routine via that script.

### Session 8 (2026-05-17, Sunday — cloud session)

Ran from Claude Code on the web (a cloud sandbox, not the Mac). Verified next week's plan via `scripts/program_week.py`: W1 of a fresh DUP mesocycle (the prior-week lookup hit `AUTH_INVALID` and fell back to W1 by design; athlete confirmed W1 is correct), 5 sessions Mon 5/18–Sat 5/23, Thu/Sun empty, elbow-safe audit clean, hinge redistributed sub-maximally, weekly TSS 154. Investigated whether the live write could happen from the cloud and root-caused why it can't: the environment's network allowlist, not auth — every TP host returns `403 host_not_allowed` and `api.peakswaresb.com` is TLS-blocked; `TP_AUTH_COOKIE` would load a cookie but the blocked hosts still defeat the write. Merged PR #3 (`feat(programming): make Sunday a non-strength recovery day (#3)`, squash `6e779a2`), so the 5-day split is now canonical on `main`. Documented the cloud-vs-Mac write procedure and the network-block gotcha (above). The live calendar write for the week of 5/18 still needs to run from the Mac (`git pull` then `program_week.py --write`), or be left to the Sunday Routine once the Mac has pulled `main`.

## Known issues and gotchas

1. **Editable installs are broken on this filesystem.** The `.pth` mechanism does not honor the `~/Documents/AI & Projects/mcp-servers/trainingpeaks-mcp/src` path. Stay on regular installs (`pip install .`).

2. **Native MCP tools require a Claude Code quit-and-relaunch after any code change.** A `/clear` or in-session reset does not respawn the MCP server.

3. **TP cookie expires every ~2 weeks.** Bryce will need to re-run `tp-mcp auth --from-browser chrome` periodically. Both Routines detect auth failure and send a `[ACTION REQUIRED]` email instead of writing workouts.

4. **Some movements are not in the TP library.** Pallof Press, literal Lying Leg Curl, Donkey Calf Raise. Substitute with closest matches (see exercise table above) or fall back to instructions text for those movements.

5. **TP exercise library matches are scored by title fuzziness.** Bare "Barbell Curl" returns "Reverse Barbell Curl" because of how the scoring breaks ties. Use precise names ("Barbell Bicep Curl", id 9) to avoid surprises.

6. **The Sunday Routine fires from a fresh Claude Code session.** Whatever code is installed at that moment is what runs. After any code change, reinstall + relaunch before the next Sunday at 6 PM.

7. **Cloud sessions are network-blocked from TrainingPeaks.** Claude Code on the web runs in a sandbox whose egress allowlist excludes every TP host (`403 host_not_allowed`; `api.peakswaresb.com` TLS-blocked). This is NOT an auth issue — `TP_AUTH_COOKIE` would load a cookie, but the cookie→token exchange and the write still hit blocked hosts. A cloud session can build and verify a week (the dry run is offline-safe) but never `--write`; that runs from the Mac or the Sunday Routine. Merging to `main` does not propagate to the Mac — `git pull` there first.

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
