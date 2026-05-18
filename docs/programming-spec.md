# TrainingPeaks Programming Skill — Spec

In-repo canonical spec for the hybrid-lift programming skill. This is the durable record a future Claude session reads before generating a week of strength workouts via the strength MCP tools (`tp_create_strength_workout`, `tp_update_strength_workout`, `tp_search_exercise`).

The full personal/lifter-profile spec lives outside this repo at
`~/.claude/projects/-Users-randall-Documents-AI---Projects-projects/memory/hybrid_lifting_program.md`.
Anything written here takes precedence on conflict — it is the in-repo source of truth for *how to program*, not *who the lifter is*.

Last updated: 2026-05-17.

---

## 1. Periodization

### Mesocycle

- **Default mesocycle = 4 weeks**: 3 loading weeks with progressive overload, then 1 deload week.
- Pick the periodization model based on the **current goal**:

| Phase / goal | Model | What it means in practice |
|---|---|---|
| Strength block (off-season, peak strength focus) | **Linear** | One quality per week (intensity rises week to week), reps drop. Week 1 ~75% × 8, Week 2 ~80% × 6, Week 3 ~85% × 4-5, Week 4 deload. |
| Mixed / general phase (default when there is no race or pure-strength goal) | **DUP** (Daily Undulating Periodization) | Within a week, vary rep schemes across sessions: e.g. Mon heavy/low-rep, Wed moderate, Fri high-rep/hypertrophy. Loads on each session progress week-over-week independently. |
| Race build (≤ 12 weeks out from an A race) | **Block** | Sequential emphasis: accumulation block (volume) → transmutation (strength-endurance) → realization (taper/peaking). Strength volume drops as race approaches; see `BUILD-LOG.md` for the existing race-phase modulation rules (5+ weeks out full program, 2-3 weeks drop Sat lift, race week / post-race no strength). |

If the goal is unclear, default to **DUP**.

### Microcycle (week)

Each loading week must show **clear progression** versus the prior week on at least one of: load, reps, or density. Encode the rule as one of:

| Progression rule | Encoding | Example |
|---|---|---|
| `+load` | +2.5-5% on main lift, same reps | W1 Squat 4×6 @ 75% → W2 4×6 @ 77.5% |
| `+reps` | Same load, +1 rep per set | W1 RDL 3×8 → W2 3×9 |
| `+sets` | Same load × reps, add a working set | W1 Press 3×8 → W2 4×8 |
| `+density` | Same total work in less time (cut rest 15-30 sec, or add a paired exercise) | W1 90 sec rest → W2 75 sec rest |

**Rules:**

1. Pick **one** progression rule per main lift per week. Do not stack +load and +reps on the same lift in the same week.
2. Across the 3 loading weeks of a mesocycle, the cumulative progression should be ~5-10% more total work (load × reps × sets) on main lifts.
3. Accessories progress on **+reps or +sets** preferentially; they take +load only when the rep ceiling for the prescribed range is hit.
4. The progression rule for each main lift is recorded in the workout `instructions` field as `Progression: <rule>` so a future session can read it back. Example: `Progression: +load 2.5% (W2 of 4)`.
5. A future session reconstructs the next week's prescription by reading the prior week's `instructions` field plus the executed weights, then advancing per the recorded rule.

### Deload week (week 4)

- **Volume ~60% of the prior loading week.** Cut sets first (e.g. 4×6 → 2-3×6), not reps.
- **Intensity held**: keep top-set %1RM the same so neuromuscular pattern is preserved.
- Skip the high-rep / metabolic finishers and most supersets.
- Core volume cut by half.
- Mark the workout `instructions` with `Deload: ~60% volume, intensity held` so it is unambiguous on the calendar.

### Picking a model in practice

If the user asks for a generic "program me a week" without naming a phase, the assumption is:

- DUP, week N of a 4-week mesocycle, pick up from where the prior week left off.
- If no prior week exists, start at W1 of a fresh mesocycle.
- If the next race / A-event is within 12 weeks (`tp_get_focus_event`), switch to Block.

---

## 1A. Weekly split (microcycle layout) — HARD SCHEDULING RULE

**Five lift days per week. Thursday AND Sunday are non-strength recovery days.** This is a scheduling constraint, not optional. Sunday was a lift day until 2026-05-17; it was demoted to recovery because cumulative weekly CNS load left the athlete fried by Sunday and the endurance coach already programs every day, so the strength week needed a *net* reduction, not a redistribution.

| Day | Session | Time | TSS | Anchor |
|---|---|---|---|---|
| Mon | Lower — Squat focus + moderate hinge accessory | 50 min | ~40 | Back Squat (heavy); RDL 3×8 submax |
| Tue | Upper #1 — Heavy Push | 45 min | ~32 | OHP / DB or machine horizontal press |
| Wed | Upper #2 — Heavy Pull | 45 min | ~32 | Weighted pull-up / chest-supported row |
| Thu | **Recovery — no strength** | — | — | — |
| Fri | Hypertrophy + Hinge | 45 min | ~35 | Hip-dominant hinge at hypertrophy reps + upper hypertrophy |
| Sat | Arms + Calves + Core (light, before the long ride) | 35 min | ~15 | Isolation only, low CNS |
| Sun | **Recovery — no strength** | — | — | — |

**Hinge redistribution rule (do not undo this).** The pre-2026-05-17 split had two lower days: Mon (Squat) and Sun (Hinge). Sunday's hinge session was the single most CNS-expensive session in the week, so cutting *that* day specifically maximises CNS relief per day removed. The hinge **pattern** must still be trained — but sub-maximally, never as a max-strength day:

- Mon: a moderate bilateral hinge accessory after the squat (e.g. RDL 3×8 at submax load), `coachNotes` flagged "replaces the old Sunday hinge day at lower CNS cost".
- Fri: a hip-dominant hinge anchor at hypertrophy reps (e.g. Single-Leg RDL or RDL 3×10, submax), opening the Hypertrophy day.

Net effect: the posterior chain is trained twice weekly without a dedicated heavy hinge day. Weekly strength TSS lands ~154 (was ~194 on the 6-day split) — the ~20% reduction is the *point*, concentrated on the CNS axis. Do not "make up" the lost volume by adding sets elsewhere; that defeats the reason Sunday was cut.

**When the user asks for "the week", build exactly these five sessions (Mon, Tue, Wed, Fri, Sat).** Never program Thursday or Sunday strength. Race-phase modulation still applies on top of this (5+ weeks out full 5-day program; 2-3 weeks out drop the Sat lift; race week / post-race no strength).

---

## 2. Pressing constraint (HARD RULE — elbow-safe)

**Reason:** mild elbow tendonosis flares with barbell bench / incline pressing. This rule overrides any movement table, library default, or athlete habit.

### Allowed

- **Barbell pressing is overhead press only.** Specifically: Barbell Overhead Press (TP id 11), Push Press, Z-Press.
- **All horizontal and incline pressing must be dumbbell, machine, or cable.**

### Banned (do not prescribe under any circumstance)

| Banned movement | TP id | Substitute (use any) |
|---|---|---|
| Barbell Bench Press (flat) | 16 | DB Bench Press (30), Machine Chest Press, Cable Chest Press |
| Barbell Incline Bench Press | (n/a in BUILD-LOG; `tp_search_exercise "Incline Bench"` to confirm) | Incline DB Press (611), Incline Machine Press, Low-to-high Cable Fly + press |
| Barbell Decline Bench Press | (n/a) | DB Decline Press (or skip; not commonly programmed for hybrid lifters) |
| Close Grip Bench Press / Close Grip Incline Bench Press | 486 | Cable Triceps Pushdown (474), Cable Overhead Triceps Extension (471), DB Skullcrusher, Dip Machine |
| Floor Press (barbell) | (n/a) | Alternating DB Floor Press (398), DB Floor Press |
| Any Smith-machine flat/incline barbell-pattern press | (varies) | Same DB / machine substitutes |

### Audit checklist before writing a session

1. For every prescribed Block, verify no exercise title contains "Bench Press", "Incline Bench", "Decline Bench", "Close Grip Bench", "Floor Press" with a barbell modality.
2. If `tp_search_exercise` returns one of those banned ids, swap to the substitute in the table above.
3. If the lifter manually requests a banned movement, refuse and propose the substitute. The constraint is medical, not preference.

---

## 3. Equipment & alternatives

### Default training site: Trump Tower Chicago Fitness Club

Confirmed published equipment (commercial gym, ~23,000 sq ft, 24/7):

- **Free-weight room**: squat rack, smith machine, bench (note: bench available, but NOT used for barbell pressing per Section 2), multifunction workout station.
- **Cardio**: Technogym + Life Fitness treadmills, ellipticals, recumbent bikes, upright bikes, stair climbers, rowers; Peloton bikes.
- **Resistance machines**: Technogym + Life Fitness selectorized stations for major muscle groups.
- **Pilates**: Gratz reformer/Cadillac (not used in this program but available).

**Not explicitly published** (assume present per "well-equipped commercial gym"): full dumbbell rack to ~100 lb, cable crossover / dual-stack cable column, leg press, hack squat, lat pulldown, seated row, hip-thrust pad/bench, GHD or hyperextension, plate-loaded chest-supported row.

If the lifter reports a missing piece, fall back to the per-movement alternatives below.

### Alternatives convention (REQUIRED for every main movement)

For every "main movement" in a prescribed workout, include **1-2 alternative movements directly in the note/description field** — same place rest times go (`coachNotes` on the prescription, or the block `instructions`). Format:

```
Rest 90s. Alt: <alt 1>; <alt 2>.
```

Example:

```python
{
    "title": "Back Squat",
    "blockType": "SingleExercise",
    "exercises": [
        {
            "name": "Back Squat",
            "coachNotes": "Rest 2:00. Alt: Hack Squat; Goblet Squat (DB) high-bar tempo.",
            "sets": [{"reps": 6}, {"reps": 6}, {"reps": 6}, {"reps": 6}],
        },
    ],
},
```

What counts as a "main movement":

- The first heavy compound of any session (squat, deadlift, hinge, overhead press, weighted pull-up, chest-supported row, etc.).
- Any movement listed in the BUILD-LOG.md "Common Bryce movements" table that is being used as the day's anchor.
- Accessories paired into supersets do **not** require alternatives unless they are the only representative of a movement pattern that day.

Default alternative ladder by pattern (pick 1-2):

| Pattern | Default | Alt 1 | Alt 2 |
|---|---|---|---|
| Squat | Back Squat (131) | Front Squat (143) | Hack Squat / Leg Press |
| Hinge | Conventional Deadlift (141) | Trap Bar Deadlift (903) | Romanian Deadlift (154) |
| Horizontal press | DB Bench Press (30) | Machine Chest Press | Cable Chest Press |
| Incline press | Incline DB Press (611) | Incline Machine Press | Low-to-high Cable Press |
| Vertical press | Barbell Overhead Press (11) | Seated DB Press (771) | Machine Shoulder Press |
| Vertical pull | Weighted Pull Up (930) | Lat Pulldown | Assisted Pull Up Machine |
| Horizontal pull | Chest Supported Row (422793) | Bent Over Barbell Row (134) | Cable Row |
| Lunge / unilateral | DB Walking Lunge (47) | Reverse Lunge (DB) | Bulgarian Split Squat |
| Hamstring curl | Swiss Ball Leg Curl (897) | Seated Leg Curl Machine | Lying Leg Curl Machine |
| Calf | Rocking Standing Calf Raise (750) | Smith Calf Raise | Seated Calf Raise Machine |

---

## 4. Audit log (existing plans/templates)

Audit run 2026-05-09 against the `claude/training-peaks-periodization-pressing-hTFUU` branch:

| File | Status | Notes |
|---|---|---|
| `notes-strength-api/workout-19347189.json` | Clean | Air Squat, Alternating Incline DB Curl, Alternating DB Press. No banned movements. |
| `notes-strength-api/library-content.json` | N/A | This is TP's master exercise catalog (reference data), not a prescribed plan. No audit needed. |
| `BUILD-LOG.md` "Common Bryce movements" table | Updated | Bench Press (16) and Close Grip Incline Bench Press (486) flagged as BANNED with substitute pointers. See BUILD-LOG.md for the marked rows. |
| `BUILD-LOG.md` example payload (Lower #1, Squat focus) | Clean | Back Squat, DB Walking Lunge, Hanging Leg Raise, Plank. No banned movements. |
| `BUILD-LOG.md` "Programming spec snapshot" | Updated | Cross-references this file for periodization and pressing rules. |

**Swaps performed:** none required in active prescription files. The two banned movements only appear as references in the `BUILD-LOG.md` reference table; they have been marked `BANNED — see programming-spec.md §2` with substitute suggestions in place.

---

## 5. How a future session uses this file

1. Read this file first when prompted to program or reprogram a strength week.
2. Read `BUILD-LOG.md` for the exercise id reference, then §1A above for the canonical five-day split (Mon/Tue/Wed/Fri/Sat; Thu+Sun recovery).
3. Read the prior week's workouts via `tp_get_workouts` and parse the `instructions` field for the `Progression:` line on each main lift.
4. Decide the current mesocycle week (W1-W4) and the periodization model (linear / DUP / block) per Section 1.
5. Build the new week's blocks. For every main movement, attach an `Alt:` line to `coachNotes` per Section 3.
6. Run the Section 2 audit checklist before calling `tp_create_strength_workout`.
7. Update the workout `instructions` with the explicit week-of-mesocycle and the chosen progression rule.
