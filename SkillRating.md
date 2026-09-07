# Player Skill Rating

Design for a skill rating derived from a player's Clone Hero scores and fretwork's
chart difficulty. This is a design document, not an implementation: the rating is
specified, fitted on real data, and stress-tested, but nothing in the repo computes
it yet. Read `ScoreData.md` first for where the scores come from and what they can
and cannot say.

The rating in one sentence: **the CalcTier at which a chart you have never played is
expected to land at 90% accuracy on the first try.** For the player whose data
produced this document, that is **tier 6.8** (95% interval 6.5 to 7.2).

## Decisions this design rests on

These were settled before the design work and are not revisited here.

- **Best attempts only.** Clone Hero stores one aggregate record per chart - best
  score, best accuracy, play count - with no timestamps and no per-attempt history.
  The rating is an estimated skill level fitted from that snapshot. There is no
  snapshotting over time and no synthetic timeline.
- **Accuracy is the signal.** Stars derive from score against a per-chart base and
  invert against accuracy on 71 pairs in the sample; raw score scales with note count.
  Neither is used. See `ScoreData.md`.
- **Stunt charts are excluded**, for now, by a mechanical rule: `CalcTier >= 10`.
  These are trill and arpeggio exercise charts rather than songs (8 of 843 in the
  library). The cutoff is a named parameter, not a hard-coded filter or a name list,
  and is expected to be revisited.
- **The rating is a separate surface.** It lives in its own package with its own
  entry point and never touches `serve.py` or `web/`. The base fretwork site may be
  hosted publicly; personal performance data is local-only by construction, not by
  convention.

## The data

Fifty-six rows: one player's scored charts joined to fretwork's Expert Guitar
metrics, after the stunt-chart rule removed three. Every row is a best attempt.

| Property | Value |
|---|---|
| Rows | 56, tiers 3 to 8 (continuous 3.4 to 9.0) |
| Accuracy | mean 90.0%, median 91%, range 75 to 100 |
| Correlation with D / ln D | -0.67 / -0.69 |
| Slope | about 2.5 accuracy points per tier |
| Within-tier spread | 1.8 pts at tier 3, rising to 5.3 at tier 8 |
| Plays | 45 songs once, 8 twice, 3 three times, 2 five, 1 nine |
| Full combos | 1 (Castle, tier 8, 100%) |

Three features of the data shape the design directly.

**The grind bonus is real and measurable.** After removing difficulty, the accuracy
residual runs -1.1 points at one play, +2.6 at two or three, +6.6 at four or more.
A best-of-k record is biased upward, and the bias grows with k. This is a fittable
term, and the design fits it.

**Selection skews toward hard charts.** The player attempts a median tier of 6
against a library median of 4; tiers 6 to 8 are 66% of the plays but 24% of the
library. Good for estimation - the data are dense where the curve bends - but it
means the easy end is thin.

**Coverage is a floor.** 77 scored charts of 843, and scores bind to chart files, so
replaced or deleted charts silently orphan their scores. Nothing in this design
reattaches orphans; they are surfaced, never used.

## The rating

A player has one rating per instrument, expressed in **continuous CalcTier units**
so it reads directly against the tier label on every chart. `floor(rating)` is a
CalcTier band; 6.8 is "a tier-6 chart near the top of the band."

**Why 90%.** The rating is the difficulty at which a fitted accuracy curve crosses
a chosen threshold, and the precision of that crossing depends on where it falls
relative to the data. Sweeping the threshold on this player's rows, the standard
error of the crossing is 0.35 tiers at 95%, 0.17 at 90%, 0.17 at 87.5%, and 0.28 at
80%. The crossing is best determined at the centre of the data, and 90% is where
this player's data are centred. It is also a threshold a player understands: "the
hardest thing I can play cleanly."

Two companion lines are reported alongside: a **comfort line** at 95% and a **wall**
at 80%. Both are less precise than the rating - the comfort line sits on the flat
part of the curve, the wall on the thin end - and are shown as context, not as
ratings.

## The model

One fit per instrument, on Expert scores only - `D` and the tier constants are
Expert-anchored, so lower-difficulty records are dropped rather than mis-rated.
Every quantity is in continuous CalcTier units.

```text
b_i    = ln(D_i / BASE_D) / LN_INC + 1          chart difficulty; floor(b_i) is fretwork's CalcTier
m(k)   = E[ max of k iid N(0,1) ]               best-of-k lift;  m(1) = 0,  m(2) = 0.564,  m(9) = 1.485

eta_i  = logit(T / u)  -  beta * (b_i - r)  +  gamma * m(plays_i)
p_i    = u * sigmoid(eta_i)                     expected best-of-k accuracy

y_i    = logit(percent_i / 100)
y_i  ~  StudentT(nu = 4,  loc = logit(p_i),  scale = sigma)        if percent_i < 100
P( y_i >= logit(1 - 0.5 / notes_i) )                               if percent_i == 100
```

with `T = 0.90` and `BASE_D, LN_INC` taken from `functions/formula.CALCTIER_PARAMS`
for the instrument's calibration group - imported, never copied.

Five parameters:

| Parameter | Meaning | Fitted (this player) |
|---|---|---|
| `r` | **the rating**: tier at which a first play lands at 90% | 6.81 |
| `beta` | accuracy fall-off per tier, on the logit scale | 0.485 |
| `gamma` | best-of-k lift per unit of expected order statistic | 0.417 |
| `u` | accuracy plateau on easy charts | 0.979 |
| `sigma` | song-to-song scatter, logit scale | 0.352 |

Each term is there for a measured reason.

- **`r` is the rating itself**, parameterised directly so its interval comes straight
  from the fit rather than from a transform of other parameters.
- **`gamma * m(plays)`** is the grind bonus. `m(k)` is the expected best of `k`
  standard normal draws, so the model treats a best-of-9 record as the maximum of
  nine attempts around a true level. The rating is evaluated at `k = 1`: it is a
  **first-try** rating, and a score reached after many retries counts for less than
  the same score first try. On this data one retry is worth about +1.5 accuracy
  points at the 90% line. Play count is a covariate, never a weight - weighting by
  plays would upweight exactly the rows with the largest upward bias.
- **`u`** is a ceiling below 100%. Accuracy on easy charts plateaus near 98%, not at
  100%, and forcing the curve through 100% distorts the slope. The plateau is fitted,
  bounded to `(T, 1)`.
- **Student-t with 4 degrees of freedom** bounds any single row's pull. A 100% full
  combo on a tier-8 chart (Castle, +12 points against prediction) would dominate a
  Gaussian fit; under the t it carries 3% of a normal row's weight. No tuning
  constant, no manual outlier removal.
- **Full combos are right-censored** at "better than half a miss" - `logit(1 - 0.5 /
  notes)` - rather than clipped to an arbitrary 99.5%. A 100% is evidence that the
  true level is at least that high, not a measurement of exactly that.

### Priors

Fixed population defaults, never derived from the player being rated - a prior
centred on the player's own data is circular and quietly overstates confidence.

```text
r          ~ N(6, 3^2)                          tiers
ln beta    ~ N(ln 0.40, 0.5^2)
gamma      = |g|,  g ~ N(0.4, 0.3^2)            folded normal, mode at 0.4
u          = T + (1 - T) * sigmoid(a_u),  a_u ~ N(logit 0.7, 1^2)     u centred 0.97
ln sigma   ~ N(ln 0.40, 0.5^2)
```

At 56 rows the data dominate: doubling any prior's width, or moving the `r` prior
centre, changes the rating by 0.01 or less. The priors exist for the player with five
rows, where they keep the fit finite and the interval honest.

### Estimator and interval

**Maximum a posteriori by Nelder-Mead**, three starts plus a restart. Deterministic,
about 30 ms at 59 rows, numpy and pandas only - no scipy, no sampling. The panel's
winning design used MCMC; the maintainer-lens judge's graft replaced it with this,
which reproduces the same rating to 0.01 with no random seed and no convergence
diagnostics.

**The interval is a profile interval on `r`**: the range over which re-optimising
every other parameter keeps the log-posterior within 1.92 of its maximum (95%) or
0.82 (80%). It is open-ended when the data do not close it, and that is reported as
a bound rather than a number. A Laplace standard error from the numerical Hessian is
computed as a cross-check; on this player the two agree (SE 0.167, profile half-width
about 0.35).

**A model-form band is shown beside the sampling interval.** Refitting under three
reasonable alternative choices - no retry correction, no ceiling, flat priors - gives
6.95, 6.73 and 6.79. That 6.7 to 7.0 band is misspecification uncertainty; the
sampling interval does not contain it, and the player-facing output says so.

### Reliability flags

Every output carries one flag, and the display rules follow from it. Two derived
quantities drive them: `n_near`, the number of scored charts within one tier of the
rating, and `n_eff`, the sum of the t-weights (how many full-weight rows the fit
effectively saw).

| Flag | Condition | What is shown |
|---|---|---|
| `unrated` | no rows on this instrument | "unrated - no scores yet" |
| `censored` | the 90% line falls outside the tiers played | a bound only: "at least 4.8" or "at most 8.1", with the hardest or easiest chart played |
| `provisional` | fewer than 10 rows, or 95% interval wider than 1.5 tiers | the number, labelled provisional |
| `extrapolated` | `n_near` below 3 | the number, labelled extrapolated |
| `established` | 10 or more rows, interval within 1.5 tiers, `n_near` at least 3 | the number |

The judges tightened these from the winning design's original `n < 5`: no fit on
five rows is ever labelled established, whatever its interval says. On this player's
random subsets, 0% of 5-row fits, 22% of 10-row fits and 72% of 20-row fits earn
the label.

The censored rule matters most. A player who has only played easy charts will
produce a numerically identified crossing above everything they have played; that is
an extrapolation, and it is never printed as a point. On ten easy-only charts from
this player the fit says "at least 4.8 - nothing you have played is that hard yet."

### Update rule

**Refit from the whole snapshot**, warm-started from the previous fit. There is no
sequential update, for a concrete reason: Clone Hero overwrites a chart's record in
place when its best is beaten, so a "new" row is usually a changed row, and a
Bayesian update that used yesterday's posterior as today's prior would count the old
version of that row twice.

After a refit, a **session delta** decomposes the change: for each new or changed
row, expected accuracy, achieved accuracy, and that row's contribution in tiers. The
contributions sum to the total change (to 0.001 on this data). This is the one useful
thing the Elo design contributed - the per-match "this moved you +0.02" is a good
explanation even when the underlying estimator is a refit.

Scale of movement, from leave-one-out on this player: no single song shifts the
rating by more than 0.04 tiers; the mean shift is 0.016. Grinding TTFAF from 9 plays
to 20 with no improvement moves the rating by 0.00. The same 88% on a new tier-7
chart is worth +0.008 first try and +0.031 after twenty tries - less, not more,
because `gamma` discounts it.

### Per instrument

Identical model, separate fit, on the instrument's own `D` and its own calibration
constants. Nothing is shared between guitar and bass except code. Guitar, Co-op and
Rhythm share fretwork's guitar calibration group and are rated together. The bass
path is implemented and returns `unrated` today because the sample holds no bass
scores; it has been exercised only with synthetic rows.

## What the player sees

The rating's own page or report - never a column in the base viewer.

```text
GUITAR rating: 6.8   (95% interval 6.5 to 7.2; 80%: 6.6 to 7.0)   from 56 songs   [established]
  A chart you have never played at tier 6.8 is one you would land at about 90% first try.
  CalcTier band 6 (upper end): charts fretwork labels tier 6 are at your 90% line.
  With retries: best-of-3 ~ tier 7.5; as your records show it ~ tier 7.0.
  Comfort line (95%): tier 4.6     Wall (80%): tier 8.7     Plateau on easy charts: 97.9%

  Expected first-try accuracy by CalcTier:
        3     4     5     6     7     8     9    10
       97    96    94    92    89    85    78    69
  Tested on tiers 3.4 to 9.0; 25 songs within a tier of the rating pin it down.

  Songs you beat the model on most:     Castle (+12), Sagittarius A* (+5), OG Pattern Practice (+5)
  Songs the model expected more from:   Sloppy Seconds (-10), Sleep (-9), Scissor Fuck Paper Doll (-7)
  Charts fretwork's difficulty does not describe for you:  Castle (tier 8.0, 100% vs 88% expected)

  Other reasonable model choices give 6.7 to 7.0; the interval above does not include that.
  Every score is your best attempt. Songs you failed, quit, or replaced the chart for are invisible.
```

The per-song residual lines are the most useful thing on the card. "Songs the model
expected more from" is where to practise; "charts fretwork's difficulty does not
describe" flags rows where `|z| > 3` - either the player has a specific strength or
weakness there, or `D` mis-rates the chart. Both are worth knowing.

## Evidence the design holds

All numbers from the reference implementation on this player's 56 core rows.

**Fit.** RMSE 3.67 accuracy points, MAE 2.67. Per-tier residuals are within a point
through tier 6; tier 7 sits 2.6 points under the curve and tier 8 two points over,
which is the raw data's plateau at 86% across those two tiers and the one place a
smooth curve visibly compromises. Effective n is 44.9 of 56.

**Robustness.**

| Perturbation | Rating |
|---|---|
| Core set (56 rows) | 6.81 [6.5, 7.2] |
| Full set including the 3 stunt charts (59) | 6.81 [6.5, 7.1] |
| Without Castle, the full combo | 6.81 |
| Plus one bad run: 40% on a tier-5 chart | 6.80 |
| Leave-one-out, worst case | shift 0.038 |

The stunt charts moved the rating by 0.00 while they were in the data - they sat on
the fitted curve rather than pulling it - but they controlled the slope past tier 8
and the wall. Removing them is why the wall (8.7) now sits at the very edge of the
data rather than inside it, and it should be read that way.

**Low n.** Random subsets of this player's rows, refit with intervals:

| n | Median rating | Median 95% width | Interval covers full-data rating |
|---:|---:|---:|---:|
| 5 | 6.90 | 2.66 tiers | 95% |
| 10 | 6.90 | 1.88 | 98% |
| 20 | 6.93 | 1.26 | 92% |

Synthetic recovery from the fitted model at n = 500 gives sd 0.05 and a 0.28-tier
interval, so the design tightens correctly as data accrue.

**Edge cases.** One chart: "at least 3.8." Two charts: "at least 5.4." Ten charts all
at 100%: "at least 4.8." A beginner at 55-75% on tiers 2-5: "at most 2.0." The ten
hardest charts only: "at most 8.1." Zero rows: unrated. None of these prints a point.

## How the design was chosen

Four designs were built independently, each fitted on the same data, then scored by
three judges - one weighting statistics, one the player's view, one maintainability -
who re-ran every prototype and confirmed every claimed number.

| Design | Rating | Total score | Fate |
|---|---:|---:|---|
| Robust Bayesian logit line, Student-t, retry covariate | 6.67 | 215 | **Winner** - the model above |
| Threshold crossing, fractional logit | 6.74 | 212 | Grafted: the 90% justification, the censored display rule, profile intervals in place of MCMC |
| Item-response with ceiling, censoring, mixture | 6.85 | 191 | Grafted: the ceiling `u`, FC right-censoring, the misfit flag |
| Snapshot Elo, chart as opponent | "even-match tier 11.6" | 174 | Rejected; grafted: session deltas, the model-form band |

Three of the four converged on 6.67 to 6.85 from different assumptions, which is the
strongest evidence that the number is a property of the data rather than of a model.

Elo was rejected on the merits, not on taste. Mechanically it was sound - a unique
fixed point, order-free by construction - but it is a one-parameter logistic with two
frozen constants (Elo per tier, ceiling) that a regression fits instead of assumes,
and its output scale means nothing to a player. Its per-match delta and its
information diagnostic were worth keeping; its rating was not.

## Architecture

- A `scores/` namespace package beside `web/` and `parsers/`, matching the repo's
  no-`__init__.py` convention: readers for the three Clone Hero files, the join, the
  rating. Its own entry point in the root, in the same shape as the other four.
- **Nothing in `web/` changes.** The rating's page or report is its own surface.
- Inputs are read-only: fretwork's cache and metrics, and the Clone Hero save files,
  which are never written to. The rating never modifies any of them.
- `T`, `NU`, `STUNT_TIER`, and every prior are named constants at the top of one
  module. `BASE_D` and `LN_INC` are imported from `functions/formula.py`, not copied.
- The last rated snapshot per instrument - rows, fitted parameters, constants - is
  persisted under `caches/` (gitignored) so the next refit can warm-start and the
  session delta has something to diff against.
- No new dependencies. numpy and pandas only; the closed-form t(4) CDF and the
  order-statistic table are a few lines each.
- matplotlib stays off the import path unless a plot is requested, as in the viewer.

## Open questions

- **Byte 12 of the score record** (always 1 or 8; see `ScoreData.md`) is unidentified.
  Until the instrument field is decoded, every record is assumed to be guitar - every
  observed record is Expert guitar - and the card must say so. If byte 12 encodes
  the instrument, twelve of the guitar rows may belong elsewhere. The design is
  unaffected; the join is.
- **The bass path has no real data** and has only been run on synthetic rows.
- **The priors were set by judgment** from this one player and the CalcTier design
  intent. They should be revisited once a second player's data exist, and `gamma`
  in particular is a population quantity that would be better pooled than re-fitted
  per player.
- **The wall now sits at the data's edge.** With stunt charts excluded, nothing above
  tier 9 informs the curve, and the 80% line is barely inside the played range.
- **A cliff cannot be distinguished from a line** past tier 8 with this data. The
  model-form band is the only misspecification signal.
- **Play-count semantics.** The retry correction assumes `plays` counts completed
  attempts. If a failed or quit run also increments Clone Hero's counter, `m(k)`
  overstates the lift and the first-try rating sits slightly low. Testable in a
  few minutes with a deliberate failed run.
- **Guitar, Co-op and Rhythm** share tier constants but are different charts. They
  are specified as three separate ratings; pooling them into one 5-fret rating is
  the alternative, and nothing in the data yet says which is right.
- **Lower difficulties.** Hard, Medium and Easy scores are dropped because the tier
  scale is Expert-anchored. fretwork computes `D` per level, so a per-level rating
  is possible once a per-level tier calibration exists.
- **Integer accuracy is treated as exact.** Interval-censoring each percent to
  `[p - 0.5, p + 0.5]` is the correct refinement if the plateau rows turn out to
  drive the ceiling; it is worth about 0.17 logit at 97%, against `sigma` of 0.35.
- **Ratings below tier 1.** The beginner case fits `r = -1.8` and is shown only as a
  bound. Whether a non-censored display should floor at 0 needs deciding before
  anything ships.

## Validation plan

- **The prospective first-play check** is the one true out-of-sample test this data
  allows. Every new row that appears with `plays = 1` was predicted before it
  existed. At each refit, log the chart, its tier, the expected first-try accuracy
  with its 80% predictive interval, and the observed result. Over time the mean
  residual should sit near zero and about 80% should fall inside. A drift that is
  the same at every tier is skill change and the rating should follow it; a drift
  that depends on tier is miscalibration.
- Recompute after every session and log the rating, interval, flag, `n_near` and
  `n_eff`. The rating should drift slowly and the interval should narrow.
- Track leave-one-out predictive RMSE against the two built-in variants (no
  ceiling, no retry correction) on every refit. The full model must stay at or
  below both, or a graft is doing harm on this player's data.
- Check posterior-predictive coverage as rows accrue: about 80% of new results should
  fall inside the 80% predictive interval for their tier. Sustained miscoverage
  means the curve shape is wrong, not the data.
- Track the per-tier residuals. The tier 7-8 plateau is the thing most likely to
  become a real shape problem as those tiers fill in.
- When a second player's data exist, compare fitted `beta`, `gamma`, `u` and `sigma`
  across players. If they agree, fix them as population constants and fit only `r`,
  which would make the rating usable from a handful of songs.
- Revisit `STUNT_TIER` once tier-9 charts have been played. The rule exists to keep
  exercise charts out of a rating about songs, not to cap difficulty.

## Not doing

- Snapshotting `scoredata.bin` over time to build a history. Considered and
  rejected; the estimated rating does not need it.
- Sequential Elo updates. Ratings are refit, and the reasons are above.
- Using stars, raw score, or the unidentified byte 12.
- Reattaching orphaned scores by song title. The replaced chart is a different chart.
- Weighting rows by play count.
- Showing any of this in the base viewer.
