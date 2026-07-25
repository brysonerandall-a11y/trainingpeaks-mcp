---
name: fueling-plan
description: Tell Bryce exactly what to eat and drink during today's training - grams of carbohydrate per hour, converted into a count of the specific products he actually owns. Trigger whenever he asks "what nutrition do I need today", "what should I fuel with", "how many carbs today", "fueling plan", "what do I take on the bike", "what gels do I need", "nutrition for my long ride", "how much should I eat on this ride", "what's my fueling", or pairs any training session with eat/drink/fuel/carbs/gels/nutrition intent. Also trigger for race-day and specific future-date fueling ("what do I take for Michigan 70.3", "fueling for Saturday's ride"). Pulls today's sessions from the TrainingPeaks MCP, computes carb, sodium, fluid and caffeine targets, then maps them onto the pantry of products from his Gmail nutrition receipts. Do not answer a fueling question from general knowledge without running this skill - the point is the specific product counts.
---

# fueling-plan

## Purpose

Bryce opens TrainingPeaks, sees a four-hour ride and a run, and does not want to
do arithmetic about it. He wants: *two scoops of this, three of those gels, one
bar at the ninety-minute mark.* This skill closes the gap between "60 g/hr" and
"here is what to put in the jersey pocket."

The deliverable is a **count of physical objects**, not a rate. A plan that ends
at "aim for 60-80 g/hr" has failed.

## Where the session data comes from

Three sources, in order. **Never stop at the first one being unavailable** —
the second works in any session with Bryce's Google account, including cloud
sessions where the MCP cannot run.

### 1. TrainingPeaks MCP (best)

`tp_get_workouts` and `tp_get_athlete_settings`. Gives planned duration, TSS,
IF, and body mass. Available from local Claude Code in the `trainingpeaks-mcp`
repo, or Claude Desktop.

### 2. TrainingPeaks iCal feed in Google Calendar (works almost anywhere)

Bryce's TrainingPeaks calendar is subscribed to his Google Calendar as
`jn1icru68l14ijcurr87i1uq245bqe2u@import.calendar.google.com`. Query it with
`list_events` for the target date.

Each event's `description` carries the **full structured workout** — warm-up,
main set, intervals with target percentages, and `Planned Time:`. The `summary`
is the workout title. This is genuinely enough to build a fueling plan.

What it does *not* carry: TSS, IF, or body mass. Infer intensity from the
interval targets in the description rather than guessing a number, and fall
back to the 400 mg caffeine ceiling instead of 6 mg/kg.

### 3. The TrainingPeaks daily schedule email

`from:messages-no-reply@trainingpeaks.com`, subject `Schedule for <date>`,
delivered around 05:15 UTC daily. Covers the same sessions plus strength work,
with coach notes. Often lands in TRASH, so search `in:anywhere`. Some of these
threads return "caller does not have permission" on fetch — if so, the search
snippet still carries the session titles and durations, and the calendar is the
better source anyway.

### If all three fail

Say so plainly and ask Bryce for sport and planned duration. Run the same math
on his numbers, labelled as his input rather than TrainingPeaks data. Never
invent a session, and never fall back on "a typical long ride."

## Workflow

### 1. Get the sessions

Pull the target date (default today) from the best available source above. For
each session capture sport type, planned duration, and whatever intensity
information exists. Get body mass from `tp_get_athlete_settings` when the MCP
is available.

Skip anything already completed unless Bryce asks about it. Strength and
mobility sessions do not get a fueling plan; mention them in one clause and
move on.

### 2. Compute targets per session

Follow `reference/fueling-math.md`. Read it before computing — do not work from
memory, the ceilings there are load-bearing.

Per session: carb g/hr, sodium mg/hr, fluid mL/hr. Then total carbohydrate,
total sodium, total fluid, and **total caffeine across the whole day**.

The 60 g/hr glucose-only ceiling in that reference will bind on most long
sessions with the current pantry. When it does, say so in one line — Bryce
should know his fuelling is capped by what is in the cupboard, not by his gut.

### 3. Map onto the pantry

Read `pantry.json`. Solve for whole units — packets, scoops, bars. Nobody
carries 1.4 gels.

Selection order:

1. **Drink mix first** for the bike. It carries carbs, sodium and fluid at once.
   But G.1.M Sport+ is 150 mg caffeine per scoop, so it is rarely right to
   build a whole long ride on it. Usually one scoop early, then gels.
2. **Gels** for the bulk of the carbohydrate, and for all of a run.
3. **Bars** on the bike only, and only in the first two-thirds — solid food
   late in a long session sits badly.
4. **Raw Replenish** to top up sodium *after* counting what the carb products
   already contribute. It has no carbohydrate; never count it as fuel.

Round toward whole units and state the resulting g/hr, rather than presenting a
target Bryce cannot actually hit with what he owns.

### 4. Check the caffeine budget

Total every caffeinated item. Ceiling is ~400 mg, or 6 mg/kg, whichever is lower.

If the plan exceeds it, **rebalance before presenting** — swap CAF gels for
plain, or drop the Sport+ scoop. Present the fixed plan and note the swap in
one line. Do not present an over-budget plan with a warning attached and leave
Bryce to solve it.

On evening sessions, flag anything caffeinated within ~6 hr of bedtime.

### 5. Present it

Lead with the shopping-list answer. Bryce is often reading this while getting
dressed.

```
Today: 3h30 endurance ride + 40min run

RIDE - 3h30, target 60 g/hr (capped, see note)
  1 scoop G.1.M Sport+ in bottle 1        20g carb / 350mg Na / 150mg caf
  7 x Go Gel (5 plain, 2 CAF)            168g carb / 770mg Na / 150mg caf
  1 x Go Bar Maple Cinnamon @ 60min       36g carb
  1 scoop Raw Replenish in bottle 2        0g carb / 1000mg Na
  -> 224g carb over 3h30 = 64 g/hr

RUN - 40min
  Nothing needed.

Day total caffeine: 300mg - under the 400mg ceiling, but all of it
before noon. Skip coffee this afternoon.

Note: capped at 60 g/hr because every carb source you own is glucose-only.
A fructose-blend product would unlock 90 g/hr on rides this long.
```

Then a short timeline — when to take what. Then anything worth flagging.

Keep it tight. Tables and a timeline, not paragraphs.

## Guardrails

**Never invent a nutrition number.** If a product's carbs, sodium or caffeine is
`null` or flagged low-confidence in `pantry.json`, say it is unverified and ask
Bryce to check the label. A confidently wrong caffeine figure is the worst
output this skill can produce.

**Quantities are what he bought, not what he has.** The pantry is built from
order confirmations; nothing tracks consumption. If a plan needs 7 gels, add a
half-line to confirm he still has them. Do not belabour it.

**Raw Replenish is not a carb drink.** It is ~1000 mg sodium and no meaningful
carbohydrate. This is the single most likely product to be mis-mapped, because
it looks and mixes like a fuel drink. Guard it every time.

**Don't overhaul race-day nutrition on a training day.** If Bryce is inside two
weeks of an A race, say so and keep the plan close to what he has been training
with. New products on race week is how races end early.

This is general sports-nutrition guidance for a trained athlete, tuned to
duration and intensity. It is not medical advice. Say that once if the plan
touches something unusual — heat, illness, a very long day — and not otherwise.

## Refreshing the pantry

The pantry is a cache, not a live feed. Rebuild it when Bryce mentions a new
order, or when it is more than ~2 months stale.

To rebuild, search Gmail across these labels:

| Label | ID |
|---|---|
| Personal/Shopping/Bare Performance Nutrition | `Label_115` |
| Personal/Shopping/Raw Nutrition | `Label_116` |
| Personal/Nutrition | `Label_395879413984535837` |
| Personal/Shopping/Other | `Label_125` |
| Personal/Training/Training Gear | `Label_8837642864833150998` |

Querying by label ID returns nothing; use the label *name* with `in:anywhere`,
e.g. `label:"Personal/Shopping/Bare Performance Nutrition" in:anywhere`. Many
of these receipts sit in TRASH, so `in:anywhere` is required, not optional.

Order-confirmation emails are large HTML. Fetching one whole blows the context
window — pull the thread, then extract only the region between "Items ordered"
/ "Order summary" and "Subtotal".

Receipts give product *names*, never nutrition facts. Get carbs, sodium and
caffeine from the manufacturer's label. The BPN and Raw Nutrition Shopify sites
return 403 to automated fetches, so web search against retailer listings is the
working route. Record `confidence` and `data_source` for anything not read off
a physical label.

Note that Gmail only proves a purchase happened. It cannot tell you what is
still in the cupboard.

## Worked example

Real numbers from the July 2026 pantry, for a 3h30 ride:

- Target from duration: 90 g/hr → **capped to 60 g/hr**, glucose-only pantry
- 3h30 × 60 g/hr = 210 g carbohydrate
- 1 scoop Sport+ (20 g) + 7 gels (168 g) + 1 bar (36 g) = 224 g → 64 g/hr
- Sodium: 350 + 770 = 1120 mg, ≈320 mg/hr → light, add 1 Replenish
- Caffeine: 150 (Sport+) + 150 (2 CAF gels) = 300 mg → under ceiling

The binding constraint is caffeine, not carbohydrate. Two scoops of Sport+ —
which is the intuitive "just use more drink mix" move — is 300 mg before a
single gel, and forces every gel to be caffeine-free. Usually better to spend
the caffeine on gels, where it comes in 75 mg increments.
