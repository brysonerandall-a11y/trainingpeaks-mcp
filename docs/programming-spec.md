# TrainingPeaks Programming Skill — Spec

In-repo technical companion for the hybrid-lift programming skill. This is the durable record a future Claude session reads for the in-repo mechanics of writing a week of strength workouts via the strength MCP tools (`tp_create_strength_workout`, `tp_update_strength_workout`, `tp_search_exercise`): payload shape, the elbow-safe and front-rack bans, the equipment baseline, the alternatives convention, and the exercise-id discipline.

This file is NOT the plan authority. The plan is owned off-repo, in this order:

1. `~/.claude/projects/-Users-randall-Documents-AI---Projects-projects/memory/hybrid_lifting_program.md` (who the lifter is, the constraints, the current split).
2. `~/Documents/AI & Projects/projects/hybrid-strength-plan/Hybrid-Strength-Plan_2026-06-22_to_2026-09-20.xlsx` (the 13-week block macrocycle: phases, weekly template, exercise rotation pools, VO2 ramp, taper).

On any conflict about the PLAN (the split, the phase, exercise selection), the memory file and the workbook win. This spec governs only the in-repo HOW-to-write mechanics. Where this spec once described the plan itself (the periodization model in section 1 and the weekly split in section 1A), it now defers to those two sources and records only what is still mechanically true.

Last updated: 2026-06-22 (reconciled to the six-day plan and the 13-week macrocycle; added the front-rack ban, section 2A).

---

## 1. Periodization (owned by the workbook)

The periodization is NOT chosen here. It is the fixed 13-week block macrocycle in the workbook, running from 2026-06-22 to the 2026-09-20 A-race (IRONMAN 70.3 Michigan). Do not default to a generic mesocycle model. The retired 4-week DUP, linear, and block selection that this section used to prescribe no longer applies.

### Phases (read the workbook for the loading details)

| Weeks | Dates | Phase |
|---|---|---|
| Wk 1 | Jun 22-28 | Calibration: set estimated 1RM anchors, groove elbow-safe lifts, prime tendons, low-dose jumps. |
| Wk 2-4 | Jun 29-Jul 19 | Strength + lean-mass accumulation. Light deload end of Wk 4. |
| Wk 5-8 | Jul 20-Aug 16 | Maximal strength + power. Programmed deload Wk 8. |
| Wk 9-11 | Aug 17-Sep 6 | Conversion to race durability. |
| Wk 12-13 | Sep 7-20 | Taper. Cut volume 50-60%, hold load quality. Race Sun Sep 20. |

After 2026-09-20 the plan is exhausted; do not improvise past it. Pause and flag that a new macrocycle is needed.

### Microcycle progression (still the in-repo mechanic)

Within whatever phase the workbook dictates, record each main lift's week-over-week progression in the workout `instructions` field so a future session can read it back. Use one rule per main lift per week:

| Progression rule | Encoding | Example |
|---|---|---|
| `+load` | +2.5-5% on main lift, same reps | W1 Squat 4×6 @ 75% to W2 4×6 @ 77.5% |
| `+reps` | Same load, +1 rep per set | W1 RDL 3×8 to W2 3×9 |
| `+sets` | Same load × reps, add a working set | W1 Press 3×8 to W2 4×8 |
| `+density` | Same total work in less time (cut rest 15-30 sec, or add a paired exercise) | W1 90 sec rest to W2 75 sec rest |

**Rules:**

1. Pick **one** progression rule per main lift per week. Do not stack +load and +reps on the same lift in the same week.
2. Accessories progress on **+reps or +sets** preferentially; they take +load only when the rep ceiling for the prescribed range is hit.
3. Record the rule in the `instructions` field as `Progression: <rule>` (for example `Progression: +load 2.5%`). A future session reconstructs the next week by reading the prior week's `instructions` plus the executed weights, then advancing per the recorded rule and the current phase.
4. On a programmed deload week (the workbook marks them), cut volume by ~40-60% (cut sets first, hold top-set intensity) and mark the `instructions` with `Deload: volume cut, intensity held`.

The detailed loading targets (set, rep, and percent ranges per phase) live in the workbook, not here.

### Autoregulation mechanic (estimated 1RM + pre-filled targets, added 2026-06-22)

The Sunday routine closes the loop on Bryce's actual logged performance instead of inferring load from the workout-level RPE:

1. **Estimated 1RM** per main lift from `tp_get_strength_history`: take the heaviest logged set (weight W x reps R) and compute `eRM = W * (1 + R/30)` (Epley). This objective anchor replaces the old RPE-bracket guess.
2. **Target weight** = the phase %1RM band (from the workbook) x eRM, rounded to loads Bryce has (nearest available DB pair; nearest 5 lb on bars and machines).
3. **Double progression**: topped the rep range on all working sets last week -> advance weight (+5 lb upper / DB, +5-10 lb lower compound, +2.5-5 accessory). Missed the rep target -> hold, or drop to the eRM-implied weight for the target reps. Bodyweight progresses by reps/seconds (~10% if exceeded).
4. **Pre-fill** the suggested target into each working set's `weight_lb`. TrainingPeaks keeps planned vs. executed separate, so Bryce's phone-logged actuals still feed the next week's history honestly. Record the eRM and last-week reference in `coachNotes` as `Target Xlb (~Y% of est. 1RM Z lb; last week <load>x<reps>)`.

This supersedes the older RPE-bracket load bump (RPE 1-3 +10-15 lb, etc.). The recorded `Progression:` rule in the `instructions` field still notes which lever moved (+load / +reps / +sets / +density). Decided with Bryce 2026-06-22: pre-fill the number, standard double progression (bump the first week he tops the range).

---

## 1A. Weekly split (microcycle layout) — HARD SCHEDULING RULE

**Six lift days, Monday through Saturday. Sunday is OFF.** Thursday IS a lift day. This replaces the 2026-05-17 five-day split (Thursday and Sunday off), which is retired. The week is built around Bryce's fixed weekend: Saturday long ride, Sunday long run. The exact intensities per phase live in the workbook; the table below is the durable layout.

| Day | Session focus | Time | TSS | Notes |
|---|---|---|---|---|
| Mon | Upper strength, push focus + trunk | 45 min | ~30 | Legs rest after Sunday's long run. |
| Tue | PRIMARY hard lower (squat and power) | 50 min | ~40 | On the freshest legs of the week. |
| Wed | Upper strength, pull focus (plus explosive later) | 45 min | ~30 | Bryce runs his own VO2 run this day; do not stack heavy legs around it. |
| Thu | Posterior chain and hamstring durability | 50 min | ~38 | The limiter day. Moderate, not maximal, to protect the weekend. |
| Fri | Light power, accessory, carries | 40 min | ~22 | Keep legs fresh for the weekend. |
| Sat | Low-fatigue durability (carries, isometrics, calf, trunk) | 35 min | ~15 | Before the long ride. Include "If Whoop is red the night before, swap this for 20 min mobility." |
| Sun | No strength | n/a | n/a | Natasha's long run. |

Only about two of the six lifts are truly hard (the Tuesday lower and one upper day); the rest are moderate or deliberately light. Do not make all six hard.

**Limiter bias (every week).** From the June 14 race, hamstrings edged toward cramping and run cadence and form collapsed after mile 6-7. Bias selection toward eccentric and fatigue-resistant hamstring work, calf and foot stiffness, hip and glute stability, and trunk endurance.

**No within-week movement repeats.** No movement may repeat anywhere in the Monday-to-Saturday week. Rotate within the workbook pattern pools; when a movement returns in a later week, it returns heavier, faster, or at a harder tempo.

**When the user asks for "the week", build exactly these six sessions (Mon through Sat).** Never program Sunday strength. The taper phase (workbook Wk 12-13) cuts volume on top of this; do not improvise other race-phase modulation that the workbook does not specify.

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

## 2A. Front-rack constraint (HARD RULE, added 2026-06-22)

**Reason:** the same elbow issue, plus wrist and shoulder loading, makes front-racked barbell positions a flare risk. This rule is medical, not preference, and overrides any movement table or library default.

### Banned (do not prescribe under any circumstance)

- Front Squat (TP id 143), front-rack lunge, Zercher squat or carry, any clean (power clean, hang clean, squat clean), and Olympic lifts generally (snatch, clean and jerk).
- Any variation that racks a barbell across the front of the shoulders.

### Substitutes (use any)

- Squat pattern: Back Squat, Paused Back Squat, Hack Squat, Leg Press, Belt Squat, Goblet Squat (DB held at the chest), Bulgarian Split Squat.
- Loaded carries or trunk work that would otherwise use a front rack: DB or kettlebell carries held at the sides or in a suitcase or farmer position, or a weighted plank.

### Audit checklist before writing a session

1. For every prescribed Block, verify no exercise title contains "Front Squat", "Front Rack", "Zercher", "Clean", or "Snatch".
2. If a movement-pattern pool would return one of those, swap to a substitute above.
3. If the lifter manually requests a banned movement, refuse and propose the substitute.

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

Default alternative ladder by pattern (pick 1-2). Every alternative must also respect the section 2 pressing ban and the section 2A front-rack ban:

| Pattern | Default | Alt 1 | Alt 2 |
|---|---|---|---|
| Squat | Back Squat (131) | Hack Squat / Leg Press | Goblet Squat (DB) / Bulgarian Split Squat |
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

Audit run 2026-06-22 (reconciliation to the six-day plan): updated section 1 (periodization now defers to the 13-week workbook), section 1A (six-day Mon-Sat split, Sunday off, Thursday a lift day), added section 2A (front-rack ban), and de-front-squatted the section 3 squat alternative ladder. Flagged Front Squat (143) BANNED in `BUILD-LOG.md`. Marked `scripts/program_week.py` SUPERSEDED (it builds the retired five-day split and listed a front-squat alternative); it now refuses to run by default. No active TrainingPeaks prescription required a swap (week 1 was written fresh under the new rules).

---

## 5. How a future session uses this file

1. Read the plan authority first: the memory file `hybrid_lifting_program.md`, then the 13-week workbook. They define who the lifter is, the constraints, the current split, and the phase. Read this spec for the in-repo mechanics, not the plan.
2. Read `BUILD-LOG.md` for the exercise id reference. Use section 1A above for the canonical six-day split (Mon through Sat; Sunday off; Thursday is a lift day).
3. Read the prior week's workouts via `tp_get_workouts` and parse the `instructions` field for the `Progression:` line on each main lift.
4. Determine the current phase from the workbook by the upcoming Monday's date (see section 1). Carry progression forward per section 1.
5. Build the new week's blocks. Pre-fill each working set's `weight_lb` with the autoregulation target (see the Autoregulation mechanic in section 1). For every main movement, attach an `Alt:` line to `coachNotes` per section 3, respecting both bans. Do not repeat any movement within the week.
6. Run the section 2 (elbow-safe) and section 2A (front-rack) audit checklists before calling `tp_create_strength_workout`.
7. Update the workout `instructions` with the current phase and the chosen progression rule.
