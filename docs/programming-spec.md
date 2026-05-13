# TrainingPeaks Programming Skill — Spec

In-repo canonical spec for the hybrid-lift programming skill. This is the durable record a future Claude session reads before generating a week of strength workouts via the strength MCP tools (`tp_create_strength_workout`, `tp_update_strength_workout`, `tp_search_exercise`).

The full personal/lifter-profile spec lives outside this repo at
`~/.claude/projects/-Users-randall-Documents-AI---Projects-projects/memory/hybrid_lifting_program.md`.
Anything written here takes precedence on conflict — it is the in-repo source of truth for *how to program*, not *who the lifter is*.

Last updated: 2026-05-13.

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

## 2. Pressing constraint (HARD RULE — elbow-safe + equipment)

**Reason:** mild elbow tendonosis flares with bench-press patterns, AND the lifter has no incline pressing equipment at the home/travel setup. This rule overrides any movement table, library default, or athlete habit.

### Allowed

- **Barbell pressing is overhead press only.** Specifically: Barbell Overhead Press (TP id 11), Push Press, Z-Press.
- **Horizontal pressing must be machine chest press, cable chest press, DB Floor Press, push-up, or dip.** No bench press of any modality (barbell, DB, Smith).
- **No incline pressing of any kind.** The lifter has no incline bench or incline press machine. If a session needs an upper-chest emphasis, hit it with a low-to-high cable fly or a high-incline landmine press (standing); otherwise drop the incline slot and use a second horizontal or overhead variant.

### Banned (do not prescribe under any circumstance)

| Banned movement | TP id | Substitute (use any) |
|---|---|---|
| Barbell Bench Press (flat) | 16 | Machine Chest Press, Cable Chest Press, DB Floor Press (398), Push-up, Dip Machine |
| DB Bench Press (flat) | 30 | Machine Chest Press, Cable Chest Press, DB Floor Press (398), Push-up, Dip Machine |
| Barbell Incline Bench Press | (n/a — do not search) | DROP the slot; or low-to-high cable fly; or standing landmine press |
| Incline DB Press | 611 | DROP the slot; or low-to-high cable fly; or standing landmine press |
| Incline Machine Press | (varies) | DROP the slot; or low-to-high cable fly; or standing landmine press |
| Barbell Decline Bench Press | (n/a) | Dip Machine, Push-up (decline) |
| Close Grip Bench Press / Close Grip Incline Bench Press | 486 | Cable Triceps Pushdown (474), Cable Overhead Triceps Extension (471), DB Skullcrusher, Dip Machine |
| Smith-machine bench / incline | (varies) | Same machine / cable / floor / dip substitutes |

### Audit checklist before writing a session

1. For every prescribed Block, verify no exercise title contains "Bench Press" (any modality including DB), "Incline" (any pressing), "Decline Bench", "Close Grip Bench", or "Floor Press (barbell)".
2. If `tp_search_exercise` returns one of those banned ids, swap to the substitute in the table above. If the substitute is DROP, omit the slot rather than forcing a movement.
3. If the lifter manually requests a banned movement, refuse and propose the substitute. The constraint is medical + equipment, not preference.
4. Horizontal-press default for the week is **Machine Chest Press** (with Cable Chest Press / DB Floor Press as alternates). DB Bench Press (30) is no longer an allowed substitute — it goes in the banned table above.

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
| Horizontal press | Machine Chest Press | Cable Chest Press | DB Floor Press (398) / Push-up / Dip |
| Incline press | (slot removed — no equipment) | Low-to-high Cable Fly | Standing Landmine Press |
| Vertical press | Barbell Overhead Press (11) | Seated DB Press (771) | Machine Shoulder Press |
| Vertical pull | Lat Pulldown | Pull Up (73, bodyweight) | Assisted Pull Up Machine |
| Horizontal pull | Chest Supported Row (422793) | Bent Over Barbell Row (134) | Cable Row |
| Lunge / unilateral | DB Walking Lunge (47) | Reverse Lunge (DB) | Bulgarian Split Squat |
| Hamstring curl | Swiss Ball Leg Curl (897) | Seated Leg Curl Machine | Lying Leg Curl Machine |
| Calf | Rocking Standing Calf Raise (750) | Smith Calf Raise | Seated Calf Raise Machine |

**Notes on the vertical pull pattern:** the lifter has no rack or band setup for weighted pull-ups at the home setup but does have a lat pulldown machine. Weighted Pull Up (TP id 930) is therefore NOT a default prescription. Use Lat Pulldown as the heavy vertical-pull anchor; reserve bodyweight Pull Up (73) for higher-rep finishers or commercial-gym sessions only.

---

## 4. Rest times (REQUIRED on every prescription)

**Rule:** every exercise in every block gets a rest prescription on the `coachNotes` field of that exercise. Rest belongs on the prescription, not buried in the top-level workout `instructions`, so the lifter sees it in the phone UI next to the sets while resting.

### Format

Use the same `coachNotes` line that carries the `Alt:` clause. Rest comes first, alt comes second, separated by a period:

```
Rest 2:00. Alt: <alt 1>; <alt 2>.
```

For paired work (Superset / Circuit), put the rest note on the FIRST exercise of the block and describe the pair rhythm:

```
A1 then A2 back-to-back. Rest 75s after A2.
```

### Defaults (use these unless the session note says otherwise)

| Slot | Default rest | Range |
|---|---|---|
| Main heavy compound (Squat, Deadlift, OHP, Lat Pulldown anchor) | **2:30-3:00** | 2:00 floor; 3:00 ceiling for top sets ≤5 reps |
| Secondary compound (CSR, RDL, machine press, lunge) | **1:30-2:00** | 90s floor |
| Accessory paired in Superset | **60-75s after the pair** | 45s floor for short-cycle hypertrophy weeks |
| Core movement | **45-60s** | usually paired with an accessory so this rolls with the superset rest |
| Plyometric / power block | **full recovery, 1:30-2:00 between sets** | never compress plyometric rest for density |
| Cardio interval work | per the interval protocol — see Section 7 | |

### Audit checklist before writing a session

1. Every `exercises[*].coachNotes` for a main movement starts with `Rest <X>` where X is one of the values above (or a session-specific override).
2. Every Superset block has a rest note on its first exercise that describes pair rhythm AND the post-pair rest.
3. The top-level workout `instructions` field still carries the `Progression:` and `Deload:` lines but does NOT carry the per-exercise rest — that lives on the prescription so the lifter can see it during the set.

---

## 5. Core movement variety (anti-monotony rule)

**Rule:** within any 7-day microcycle, do not repeat the same core movement on more than two days. Cycle through at least three of the five core patterns each week. Plank and Hanging Leg Raise are NOT the default — they are one option each in their respective patterns.

### The five core patterns

| Pattern | What it trains | Example movements |
|---|---|---|
| **Anti-extension** | Resists lumbar extension under load | Plank (71), Ab Wheel Rollout, Hollow Body Hold, Dead Bug, Stir-the-Pot (Swiss ball) |
| **Anti-rotation** | Resists transverse-plane rotation | Pallof Press (cable, substitute for the missing library entry), Bird Dog, Half-Kneeling Cable Chop, Renegade Row |
| **Anti-lateral-flexion** | Resists lateral spine flexion | Suitcase Carry (DB), Side Plank, Single-Arm Farmer Carry, Copenhagen Plank |
| **Flexion / dynamic** | Trunk flexion under load | Cable Crunch (464), Hanging Leg Raise (590), Hanging Knee Raise, Toes-to-Bar, V-Up, Decline Sit-Up |
| **Rotation (controlled)** | Active rotation under load | Cable Wood Chop (high-to-low / low-to-high), Russian Twist (DB or plate), Landmine Rotation, Medicine Ball Rotational Throw |

### Programming the core block

- 2-3 core movements per session, slotted into the back-half supersets per the existing rule.
- Across the week, hit **at least 3 of the 5 patterns**; ideally all 5.
- No single movement repeats more than 2× in a week.
- A finisher block of carries (Farmer / Suitcase) counts as core for that day.
- Movements not in the TP library (Pallof Press, Hollow Body Hold, Ab Wheel Rollout, Copenhagen Plank, Dead Bug, Bird Dog, Stir-the-Pot, Cable Wood Chop, Russian Twist, Landmine Rotation, Toes-to-Bar, V-Up, Decline Sit-Up, Renegade Row, Farmer Carry, Suitcase Carry): use the closest library entry (see BUILD-LOG.md substitutes), or fall back to a generic library entry and put the actual movement name in `coachNotes`.

### Audit checklist before writing a session

1. Count the distinct core movements across the week. ≥3 distinct patterns, ≥4 distinct movements.
2. Plank appears at most 2× per week. Same for Hanging Leg Raise.
3. At least one anti-rotation OR anti-lateral-flexion movement per week (the patterns most often missed).

---

## 6. Plyometric / power work

**Rule:** include a short plyometric block on appropriate strength days. Plyo goes at the **start of the session, after the warm-up, before the heavy compound**. Never tack plyo onto the end of a session when the CNS is fatigued — it loses its training effect and becomes injury risk.

### When to program plyo

| Day | Plyo bias | Examples |
|---|---|---|
| Mon (Lower #1, Squat) | Vertical / triple-extension | Box Jump (24-30"), Squat Jump, Depth Drop-to-Stick |
| Sun (Lower #2, Hinge) | Horizontal / posterior-chain | Broad Jump, Kettlebell Swing (heavy, treat as plyo if hinge-bias), Medicine Ball Slam |
| Tue (Upper Push) | Upper-body explosive | Plyo Push-up, Medicine Ball Chest Pass, MB Overhead Slam |
| Wed (Upper Pull) | Rotational / pulling explosive | MB Rotational Throw, MB Scoop Toss, Band Pull-Apart Fast |
| Fri (Hypertrophy) | Skip or low-intensity priming only — body is mid-mesocycle accumulation, plyo here adds CNS load without payoff |
| Sat (Arms / Calves / Core) | Skip — pre-long-ride day, no CNS stress |

### Dose

- **2-4 sets × 3-5 reps** (or 3-6 throws / jumps). Never train plyo for "reps until fatigue".
- Full rest between sets: **1:30-2:00**.
- Total plyo block time: **5-8 minutes**, not more.
- During deload weeks (W4): cut plyo to 1 working set or skip entirely.
- During race build, transmutation / realization blocks: skip plyo on the day before a hard endurance session.

### Inclusion criteria (think before adding)

1. Has the lifter slept ≥6 hours and Whoop recovery is yellow/green? If red, skip plyo.
2. Is this a deload week? If yes, skip or reduce.
3. Is there a hard endurance session in the next 24 hours? If yes, downgrade volume.
4. Is the lifter mid-injury or returning from one? If yes, skip until cleared.

### Audit checklist before writing a session

1. Plyo block (if present) is the FIRST working block after the WarmUp.
2. Block is labeled clearly — title like "Power: Box Jump" so the lifter does not confuse it with a metcon.
3. `coachNotes` reads `Rest 1:30-2:00. Quality over quantity — stop the set if jump height or speed drops.`

---

## 7. Cardiovascular conditioning — VO2 Max / MAP intervals + sprints

The lifter has a **WODWAY curved manual treadmill** at the home setup. A curved manual treadmill is ideal for max-effort work because there is no preset speed cap — the belt accelerates to whatever the runner produces, and decelerates the moment the runner backs off. This makes it well-suited for VO2 Max intervals, Maximal Aerobic Power (MAP) intervals, and short sprints.

This work goes on the calendar as an **endurance Run workout** (not a Strength workout) — use the existing `tp_create_workout` endurance path, not the strength tools. Coordinate with Natasha's plan: never stack a hard cardio interval session against one of her quality run days.

### The three interval flavors

| Flavor | Target intensity | Work | Recovery | Sets | Total session |
|---|---|---|---|---|---|
| **VO2 Max intervals** | ~95-100% VO2 Max (≈ 5K race effort, RPE 9) | 3-5 min | 2-3 min easy walk/jog | 4-6 | 35-50 min incl. warm-up + cool-down |
| **MAP intervals** | ~100-110% VO2 Max (just above all-out sustainable, RPE 9-10) | 30 sec - 2 min | 1:1 to 1:2 work:rest | 6-10 | 30-40 min |
| **Sprints / neuromuscular** | All-out, ATP-PC dominant | 10-30 sec | 2-3 min full rest | 6-10 | 25-35 min |

### Weekly placement

- **1× VO2 Max OR MAP** per week, plus optionally **1× sprint session**. Never both VO2 Max AND MAP in the same week (too much glycolytic load on top of the lift schedule).
- Default day for VO2 Max / MAP: **Wednesday** (slots between Tue Heavy Push and Fri Hypertrophy, 24+ hours from the Mon squat and the Sun hinge).
- Default day for sprints: **Tuesday or Friday** (Upper days — minimal interference with strength). Sprints are short and CNS-priming, not glycolytic-heavy, so they pair OK with an Upper lift if done first or separated by ≥4 hours.
- Never put VO2 Max / MAP on Monday or Sunday — the heavy leg day is the priority.
- Skip ALL of this work during a deload week (W4).

### Sample protocols

```
VO2 Max — Wed
  Warm-up: 10 min easy + 4×30s strides
  Main:    5 × 3:00 @ 5K effort / 2:00 walk recovery
  Cool-down: 8 min easy
  Total: ~43 min

MAP — Wed
  Warm-up: 10 min easy + 4×30s strides
  Main:    8 × 1:00 hard (RPE 9-10) / 1:00 walk
  Cool-down: 8 min easy
  Total: ~35 min

Sprints — Tue or Fri (before the lift, or ≥4h after)
  Warm-up: 10 min easy + drills + 3×20s build-ups
  Main:    8 × 20 sec all-out / 2:30 walk recovery
  Cool-down: 8 min easy
  Total: ~30 min
```

### Curve-treadmill notes (WODWAY)

- No motor — belt is driven by the runner. Effort scales naturally.
- Hand on the front rail to push off the start of each interval; ride momentum into the rep.
- Step OFF the belt during recovery (straddle the side rails), don't try to slow-walk a curved belt at low speed.
- Cap top-end heart rate via RPE, not pace — the curved belt is ~10-15% harder for the same perceived speed than a motorized belt.

### Audit checklist before writing a session

1. Workout `sport` is Run (not Strength). Use `tp_create_workout`, not `tp_create_strength_workout`.
2. Session title is unambiguous: "VO2 Max Intervals", "MAP Intervals", or "Sprints (WODWAY)".
3. Per-interval pace / effort is in the workout description; total TSS_planned reflects the interval load (typically 50-80 for VO2 Max, 40-60 for sprints).
4. Not stacked against Natasha's quality run day in the same week — read her plan via `tp_get_workouts` first.

---

## 8. Audit log (existing plans/templates)

Audit run 2026-05-09 against the `claude/training-peaks-periodization-pressing-hTFUU` branch:

| File | Status | Notes |
|---|---|---|
| `notes-strength-api/workout-19347189.json` | Clean | Air Squat, Alternating Incline DB Curl, Alternating DB Press. No banned movements. |
| `notes-strength-api/library-content.json` | N/A | This is TP's master exercise catalog (reference data), not a prescribed plan. No audit needed. |
| `BUILD-LOG.md` "Common Bryce movements" table | Updated | Bench Press (16) and Close Grip Incline Bench Press (486) flagged as BANNED with substitute pointers. See BUILD-LOG.md for the marked rows. |
| `BUILD-LOG.md` example payload (Lower #1, Squat focus) | Clean | Back Squat, DB Walking Lunge, Hanging Leg Raise, Plank. No banned movements. |
| `BUILD-LOG.md` "Programming spec snapshot" | Updated | Cross-references this file for periodization and pressing rules. |

**Swaps performed:** none required in active prescription files. The two banned movements only appear as references in the `BUILD-LOG.md` reference table; they have been marked `BANNED — see programming-spec.md §2` with substitute suggestions in place.

### Audit run 2026-05-13 (this branch, `claude/update-training-program-Y76ry`)

Triggered by athlete feedback on the week-of-2026-05-11 programming. Findings:

| Item | Finding | Resolution |
|---|---|---|
| DB Bench Press (id 30) still in the alternatives ladder | Athlete avoiding all bench-press patterns going forward, not just barbell | Banned in §2; horizontal-press default rewritten to Machine Chest Press. |
| Incline DB Press (id 611) still in the alternatives ladder | Athlete has no incline equipment | Banned in §2; incline slot is dropped (no substitute movement, just remove the slot). |
| Weighted Pull Up (id 930) as vertical-pull default | Athlete has no rack/band for weighted pull-ups | Vertical-pull default rewritten to Lat Pulldown in §3. |
| Mon 2026-05-11 lift had no per-exercise rest visible on the phone | Rest convention was buried in §3 prose, not enforced | New §4 makes rest mandatory on every `exercises[*].coachNotes`, with defaults table. |
| Core block was Plank + Hanging Leg Raise both repeating across the week | No variety rule existed | New §5 introduces the five core patterns and the weekly variety audit. |
| No plyometric / explosive work programmed | Athlete requested it | New §6 introduces plyo block placement, day-by-day bias, and dose. |
| No VO2 Max / MAP / sprint sessions programmed | Athlete requested it; has a WODWAY curved treadmill | New §7 introduces the three interval flavors, weekly placement, and sample protocols. |

**Swaps required in next week's prescription (week of 2026-05-18):** the Sunday Routine writing 2026-05-17 must apply all of the above.

---

## 9. How a future session uses this file

1. Read this file first when prompted to program or reprogram a strength week.
2. Read `BUILD-LOG.md` for the exercise id reference and the six-day split structure.
3. Read the prior week's workouts via `tp_get_workouts` and parse the `instructions` field for the `Progression:` line on each main lift.
4. Decide the current mesocycle week (W1-W4) and the periodization model (linear / DUP / block) per Section 1.
5. Build the new week's blocks:
   - For every main movement, attach a `Rest <X>. Alt: <a>; <b>.` line to `coachNotes` per Sections 3 and 4.
   - Apply the core-variety rule from Section 5 — count patterns across the week before finalizing.
   - Add a plyometric block where appropriate per Section 6 — first working block, after warm-up.
   - If the week includes VO2 Max / MAP / sprint work, write those as endurance Run workouts via `tp_create_workout`, NOT as strength blocks. See Section 7.
6. Run the Section 2 audit checklist (no bench, no incline, no weighted pull-up) before calling `tp_create_strength_workout`.
7. Run the Section 4 audit checklist (rest on every prescription).
8. Run the Section 5 audit checklist (core variety) and the Section 6 audit checklist (plyo placement) if applicable.
9. Update the workout `instructions` with the explicit week-of-mesocycle and the chosen progression rule.
