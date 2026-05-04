# TP Strength Builder API — Schema Reference

Captured 2026-04-28 from a live TP web session via Chrome MCP. This file is the source of truth for extending `trainingpeaks-mcp` with native strength workout support.

## Why this exists

The current MCP only knows `https://tpapi.trainingpeaks.com`, which serves endurance workouts under `/fitness/v6/`. TP's strength builder lives on a separate domain and namespace: `https://api.peakswaresb.com/rx/activity/v1/`. Strength workouts created in the web UI are invisible to the existing MCP, and the MCP cannot create structured strength workouts. This schema doc unblocks that gap.

## Authentication

The same OAuth bearer token used by `tpapi.trainingpeaks.com` works on `api.peakswaresb.com`. Verified by direct Python call. No separate auth flow needed; the existing `TPClient._token_cache.access_token` is reusable.

```python
async with TPClient() as client:
    await client._ensure_access_token()
    token = client._token_cache.access_token
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    # Now reach api.peakswaresb.com freely
```

## Endpoints discovered

| Method | Path | Use |
|---|---|---|
| GET | `/rx/activity/v1/workouts/{id}` | Read full structured strength workout |
| PUT | `/rx/activity/v1/workouts` | Update structured strength workout (body has `id`) |
| POST | `/rx/activity/v1/workouts/save` | Commit save (sent immediately after PUT) |
| GET | `/rx/activity/v1/parameters/exercise` | Catalogue of per-exercise parameter types (Reps, WeightLb, RepsPerSide, WeightPerSideLb, etc.) |
| GET | `/rx/activity/v1/parameters/block` | Catalogue of block-level parameter types (TimeSeconds, Reps total, WeightLb total, etc.) |
| GET | `/rx/activity/v1/libraryContent` | Full exercise library (955 exercises) plus the 5 supported block types |
| GET | `/rx/activity/v1/libraryContent/workoutLibrary/{libraryId}` | Items in a personal workout library (templates) |
| GET | `/rx/activity/v1/libraryContent/workoutLibrary/recentlyUsed` | Recently used templates |
| GET | `/rx/activity/v1/workouts/{id}/comments` | Comments on a workout |
| GET | `/rx/activity/v1/workouts/{id}/privateWorkoutNote` | Private athlete note on a workout |
| GET | `/rx/activity/v1/workouts/{id}/summary` | Computed totals (totalSets, totalPrescriptions, etc.) |

There is also a calendar listing endpoint TP uses to show all strength workouts in a date range. Not yet captured. Will discover during Phase 1 build by sniffing the calendar load.

## Workout JSON shape (top level)

The PUT body and the POST `/save` body are nearly identical and use this shape:

```json
{
  "id": "<int as string, the workout id>",
  "workoutType": "Strength",
  "workoutSubTypeId": null,
  "calendarId": "<athlete calendar id>",
  "title": "Example Title of Lifting Day TEST 2",
  "instructions": "This day is dedicated to high-intensity interval training and plyometric work...",
  "prescribedDate": "2026-04-29",
  "prescribedStartTime": null,
  "prescribedDurationInSeconds": 0,
  "prescribedTss": 0,
  "prescribedIntensityFactor": 0,
  "completedDateTime": null,
  "startDateTime": null,
  "completedTss": 0,
  "completedTssSource": null,
  "completedIntensityFactor": 0,
  "compliancePercent": 0,
  "rpe": null,
  "feel": null,
  "lastUpdatedAt": "2026-04-28T21:43:01",
  "orderOnDay": 0,
  "isLocked": false,
  "isHidden": false,
  "snapshot": {
    "totalBlocks": 2,
    "completedBlocks": 0,
    "totalSets": 10,
    "completedSets": 0,
    "totalPrescriptions": 4,
    "completedPrescriptions": 0
  },
  "blocks": [ ... see Block shape ... ]
}
```

## Block shape

A workout is an ordered list of blocks. Each block is one of the supported `blockType` values and contains one or more prescriptions (exercises).

```json
{
  "id": "<int as string>",
  "title": "Warm Up",
  "blockType": "WarmUp",
  "coachNotes": null,
  "isComplete": false,
  "compliancePercent": 0,
  "parameters": [
    {
      "parameter": "TimeSeconds",
      "title": "Total Time Seconds",
      "unit": {"title": "Seconds", "abbreviation": "sec", "unit": "Seconds"},
      "inputFormat": "Integer",
      "prescribedValue": "600",
      "executedValue": null,
      "id": "<int as string>"
    }
  ],
  "prescriptions": [ ... see Prescription shape ... ]
}
```

### Block types (5 total, from `/libraryContent`)

| `blockType` | UI title | Use |
|---|---|---|
| `SingleExercise` | Single Exercise | One exercise as a standalone block |
| `Circuit` | Circuit | Cycle through multiple exercises |
| `CoolDown` | Cool Down | Recovery block at the end |
| `WarmUp` | Warm Up | Optional opening block |
| `Superset` | Superset | Two or more exercises paired with shared rest |

Bryce's programming uses `WarmUp` (rare; he handles his own), `SingleExercise` (heavy compounds), and `Superset` (accessory pairing). `Circuit` may be useful for the Sat Arms+Calves+Core finisher.

## Prescription shape

A prescription is one exercise within a block, including the prescribed sets.

```json
{
  "id": "<int as string>",
  "exercise": { ... see Exercise shape ... },
  "parameters": [
    {
      "parameter": "Reps",
      "title": "Reps",
      "unit": {"title": "Reps", "abbreviation": "", "unit": "Reps"},
      "category": "Reps",
      "id": "<int as string, instance id distinct from the catalogue id>"
    }
  ],
  "sets": [ ... see Set shape ... ],
  "coachNotes": null,
  "compliancePercent": 0,
  "setSummaryTemplate": "{Reps}"
}
```

## Exercise shape

`exercise` references the TP exercise library. The catalogue of 955 exercises is in `library-content.json`. Each library entry has an `exerciseId` and `title` plus muscle group attributes.

```json
{
  "id": "1",
  "ownerId": 2000301,
  "title": "Air Squat",
  "videoUrl": "https://youtu.be/xPtIxrUwnxg",
  "instructions": "Stand tall with your feet shoulder-width apart...",
  "parameters": [
    {
      "parameter": "Reps",
      "title": "Reps",
      "unit": {"title": "Reps", "abbreviation": "", "unit": "Reps"},
      "category": "Reps",
      "id": "63"
    }
  ],
  "canEdit": false
}
```

`ownerId: 2000301` appears to be the TP-system library owner. User-created exercises probably carry the athlete's own ownerId; not yet observed.

## Set shape

Each set carries the prescribed values and the slots for executed values that the athlete fills in on the phone during the workout.

```json
{
  "id": "<int as string>",
  "isComplete": false,
  "setOrigin": "Prescribed",
  "parameterValues": [
    {
      "parameter": "Reps",
      "inputFormat": "Integer",
      "prescribedValue": "10",
      "executedValue": null,
      "id": "<int as string>"
    },
    {
      "parameter": "WeightPerSideLb",
      "inputFormat": "Decimal",
      "prescribedValue": null,
      "executedValue": null,
      "id": "<int as string>"
    }
  ]
}
```

`setOrigin` values seen: `Prescribed`. Other values likely include `Athlete` (sets the athlete added) and `Coach`.

## Parameter library

`/parameters/exercise` is the canonical list of values that can appear on a prescription. Each parameter has a `parameter` enum, a `unit`, and a `category`. The relevant ones for Bryce:

| `parameter` | Category | Unit | Notes |
|---|---|---|---|
| `Reps` | Reps | Reps (no abbr) | Standard reps |
| `RepsPerSide` | Reps/side | Reps | Unilateral exercises (alternating DB press, single-arm row) |
| `WeightLb` | Weight | Pounds (lb) | Standard weight |
| `WeightKg` | Weight | Kilograms (kg) | Metric weight |
| `WeightPerSideLb` | Weight/side | Pounds (lb) | Unilateral weight |
| `TimeSeconds` | (block-level) | Seconds (sec) | For timed sets like plank |
| `DistanceMeters` | (block-level) | Meters (m) | Walking lunges, farmer carry |

Block-level `parameters` can roll up totals (TotalReps, TotalWeightLb, etc.) for circuit/superset summary.

## Save flow

A save in the UI fires three calls in sequence:

1. `PUT /rx/activity/v1/workouts` with the full workout JSON. Returns 200.
2. `POST /rx/activity/v1/workouts/save` with the same JSON. Returns 200.
3. `GET /rx/activity/v1/workouts/{id}/summary` to refresh computed totals.

The MCP extension should mirror this: PUT the structured payload, POST to save, optionally GET the summary for verification.

## Exercise library

`library-content.json` is 234 KB and contains the full exercise catalogue plus the 5 block types. Sample entries (Bryce-relevant):

| Movement | TP `exerciseId` |
|---|---|
| Back Squat | 131 |
| Paused Back Squat | 5356 |
| Heel Elevated Back Squat | 5302 |
| Barbell Overhead Press | 11 |
| Romanian Deadlift | 154 |
| Romanian Deadlift with DB | 752 |
| Bent Over Barbell Row | 134 |
| Barbell Bent Over Row | 427 |
| Hanging Leg Raise | 590 |
| Wide Grip Barbell Bench Press | 933 |
| Barbell Bulgarian Split Squat | 24 |
| DB Bulgarian Split Squat | 500 |
| DB Deadlift | 32 |
| Wide Grip Standing Barbell Curl | 938 |
| Reverse Barbell Curl | 737 |

The full catalogue includes 30 deadlift variants, 20 pull-up variants, 42 plank variants, 6 OHP variants. The MCP extension will need a name-to-ID lookup helper. Bryce's six-day standard split needs ~30 unique exercise IDs; we will hard-code those in the MCP and fall back to a search call for anything else.

Movements not found by exact match (need targeted search during build): Pallof Press, Lying Leg Curl, Standing Calf Raise (only "Rocking Standing Calf Raise" hit), Weighted Dip. Likely present under different naming. Resolve by searching `searchText` field of each library entry.

## Implementation plan for `trainingpeaks-mcp` extension

### Phase 1 — Read-only tools

New file: `tp_mcp/client/strength_http.py` — thin client targeting `api.peakswaresb.com`, reusing the existing `TPClient._token_cache`.

New file: `tp_mcp/tools/strength.py` with these tools:
- `tp_get_strength_workout(workout_id)` — GET, parse, return Pydantic model
- `tp_list_strength_workouts(start_date, end_date)` — discover the calendar listing endpoint
- `tp_search_exercise(query)` — search the local library cache for an exercise by name fragment

Local cache: pull `library-content.json` once on first use, persist to `~/.tp-mcp-cache/library.json`, refresh weekly.

### Phase 2 — Write tools

Extend `tp_mcp/tools/strength.py`:
- `tp_create_strength_workout(date, title, instructions, blocks, ...)` — accept simplified Python dict, build TP wire format, do PUT then POST
- `tp_update_strength_workout(workout_id, ...)` — same but with existing id
- `tp_delete_strength_workout(workout_id)` — DELETE

Builder helpers in `tp_mcp/tools/_strength_builder.py`:
- `build_block(title, block_type, prescriptions)` — wraps prescriptions, computes block parameters
- `build_prescription(exercise_name_or_id, sets, params=["Reps"], rest=None)` — looks up exercise id from cache, builds parameters and sets
- `build_set(reps=None, reps_per_side=None, weight_lb=None, weight_per_side_lb=None, time_seconds=None)` — produces parameterValues entries
- `compute_snapshot(blocks)` — calculates totalBlocks, totalSets, totalPrescriptions

### Phase 3 — Routine integration

Update `~/.claude/scheduled-tasks/hybrid-lift-programmer/SKILL.md` and `hybrid-lift-reprogrammer/SKILL.md`:
- Replace the "write text description via tp_create_workout" path with "build structured payload via tp_create_strength_workout"
- Update the email template to acknowledge native weight logging
- Document the simplified Python dict format the LLM should produce

### Phase 4 — Test, install, document

- Unit tests against captured payloads in this directory
- Round-trip test: create a strength workout for May 11, fetch it back, verify match, delete
- `pip install -e ".[browser]"` to refresh the venv binding
- Update `~/.claude/projects/-Users-randall-Documents-AI---Projects-projects/memory/hybrid_lifting_program.md` with the new programming format (TP exercise library names, block types, set/rep format)

## Decisions captured

- Auth: reuse the existing TPClient bearer token. No separate auth flow.
- Repo strategy: local-only edits to `~/Documents/AI & Projects/mcp-servers/trainingpeaks-mcp/`. No GitHub fork, no upstream PR for now. May reconsider once the extension is stable.
- Pacing: schema doc tonight, full implementation Saturday or Sunday.
- Sunday Routine fallback: if the build is not done by 5/3, the recurring Routine fires with the current text-description format. The strength format ships for the 5/10 fire.
