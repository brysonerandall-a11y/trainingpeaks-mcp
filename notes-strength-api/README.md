# Strength API reference and captured payloads

This folder is reference material for the structured-strength MCP tools added in `src/tp_mcp/tools/strength.py` and `src/tp_mcp/client/strength_http.py`.

## Why this exists

TrainingPeaks splits its API across two domains. The endurance side (workouts, fitness, calendar) lives on `tpapi.trainingpeaks.com` under `/fitness/v6/` and is what the rest of this MCP targets. The strength builder, where workouts have blocks, prescriptions, sets, and per-exercise parameters, lives on a different domain entirely: `api.peakswaresb.com/rx/activity/v1/`. The same OAuth bearer token works on both, so we share the existing `TPClient` token cache.

This folder captures live request and response payloads from the strength API plus a written schema reference, so future maintenance does not require re-reverse-engineering the wire format.

## Contents

| File | What it is |
|---|---|
| `SCHEMA.md` | Written reference: endpoint list, JSON shapes, block types, exercise library notes, save flow, four-phase implementation plan |
| `workout-19347189.json` | A single saved strength workout, full structured shape (blocks, prescriptions, sets, exercise refs, parameter values). The workout itself was a throwaway example built in the TP web UI during the reverse-engineering session |
| `library-content.json` | TP's full exercise library response, ~955 exercises plus the 5 supported block types (SingleExercise, Circuit, CoolDown, WarmUp, Superset). 234 KB |
| `parameters-exercise.json` | The per-exercise parameter catalog (Reps, RepsPerSide, WeightLb, WeightKg, WeightPerSideLb, WeightPerSideKg, Duration, DistanceMeters, DistanceMiles, etc.) |
| `parameters-block.json` | The block-level parameter catalog (TimeSeconds total, WeightLb total, etc.) |
| `library-3411174.json` | An empty user library, captured to confirm the response shape |
| `libraries-recently-used.json` | Recently used templates list, also empty for this account |

## Key learnings baked into `tools/strength.py`

- `workoutType` is the string `"StructuredStrength"`, not `"Strength"`.
- `calendarId` is the athlete's id.
- `prescribedStartTime` is time-only `HH:MM:SS`, never a full datetime.
- The exercise-level time parameter is `Duration` (in seconds), not `TimeSeconds`. `TimeSeconds` is block-level only.
- All API responses are wrapped in `{"data": ..., "errors": {}}`.
- Create flow is three steps: POST `/workouts` (returns a UUID-id draft), PUT `/workouts` (populates blocks on the draft), POST `/workouts/save` (commits the draft to a persistent integer id).
- Supersets must contain exercises with compatible parameter types. Reps + Duration cannot mix in one Superset; Plank goes in its own SingleExercise block.

## Refreshing the captures

If TP changes their API and the tools break, regenerate these captures with:

```python
import asyncio, httpx
from tp_mcp.client.http import TPClient

async def main():
    async with TPClient() as client:
        await client._ensure_access_token()
        token = client._token_cache.access_token
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        async with httpx.AsyncClient() as h:
            for path, name in [
                ("workouts/<id>", "workout-<id>"),
                ("parameters/exercise", "parameters-exercise"),
                ("parameters/block", "parameters-block"),
                ("libraryContent", "library-content"),
            ]:
                r = await h.get(f"https://api.peakswaresb.com/rx/activity/v1/{path}", headers=headers)
                with open(f"notes-strength-api/{name}.json", "w") as f:
                    f.write(r.text)

asyncio.run(main())
```

Replace `<id>` with a real strength workout id from the calendar UI to capture a sample structured workout.
