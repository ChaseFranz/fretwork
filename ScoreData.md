# Clone Hero Score Data

Notes on Clone Hero's on-disk save format, written up so the scoring and ELO work
has something to build against. Everything here was reverse-engineered by reading
the files directly - none of it is documented by the game, and all of it can change
without warning when Clone Hero updates. Read the [Version safety](#version-safety)
section before trusting any of it in code.

Sample used throughout: one library whose cache holds 873 entries (843 of them
charts still on disk), 77 scored songs, 113 total plays. Findings are marked **confirmed** (the data proves it) or **inferred** (the
best reading, but a sample of one player cannot rule out alternatives).

## Where the files live

Clone Hero keeps save data in its Unity persistent-data path, *not* next to the
executable and *not* in the install directory:

```text
%USERPROFILE%\AppData\LocalLow\srylain Inc_\Clone Hero\
```

From WSL that is `/mnt/c/Users/<user>/AppData/LocalLow/srylain Inc_/Clone Hero/`.
Note the trailing underscore in `srylain Inc_` - Unity sanitises the `.` out of the
company name. Three files matter:

| File | Size (sample) | Contents |
|---|---|---|
| `scoredata.bin` | 2,780 B | Best score per song. The main table. |
| `scoresext.bin` | 2,164 B | Parallel table, same songs, extra integers. |
| `songcache.bin` | 406,748 B | Library scan: folder paths, metadata, chart hashes. |

`LeaderboardCache/` is a useful fourth source: 447 JSON files whose filenames begin
with a 32-hex **chart hash in the same namespace** (433 of its 444 distinct hashes
resolve in `songcache.bin`), each containing the song name and charter. It is the
only way to put a name to a score whose chart is no longer cached - see
[The join](#the-join). Note the filenames are **uppercase** hex. `Player.log`,
`icons.json` and `sources.txt` are irrelevant here.

All three are **read-only** as far as fretwork is concerned. Nothing should ever
write to them; a corrupt `scoredata.bin` costs the player their score history.

## `scoredata.bin`

Fixed-size records, no compression, no string data. **Confirmed** layout:

```text
offset  size  field
     0     4  magic            41 65 34 01   ("Ae4\x01")
     4     4  uint32 count     number of records
     8     -  count x 36-byte records
```

The arithmetic is exact and self-checking: `2780 = 8 + 77 * 36`, and 77 is what the
count field says. If that identity does not hold, the format has changed - see
[Version safety](#version-safety).

### Record (36 bytes)

```text
offset  size  field
     0    16  MD5 chart hash        join key, see The join
    16    20  payload               see below
```

### Payload (20 bytes)

| Off | Size | Field | Confidence | Observed |
|---:|---:|---|---|---|
| 0 | 1 | Entry count | inferred | always `1` |
| 1 | 1 | **Play count** | confirmed | 1, 2, 3, 5, 9 |
| 2 | 4 | *unknown* | - | always `0` |
| 6 | 1 | **Difficulty** | inferred | always `3` (Expert) |
| 7 | 1 | **Percent** | confirmed | 45-100 |
| 8 | 1 | **Full-combo flag** | confirmed | `1` on exactly the one 100% record |
| 9 | 1 | *unknown constant* | - | always `100` |
| 10 | 1 | *unknown* | - | always `0` |
| 11 | 1 | **Stars** | confirmed | 1-7 |
| 12 | 4 | *unknown* | - | `1` (65x) or `8` (12x) |
| 16 | 4 | **Score** (uint32 LE) | confirmed | 17,175 - 515,874 |

Little-endian throughout.

**Play count** is confirmed by the player against his own history: the record reading
9 is Through the Fire and Flames, which he has played nine times, and the 58 records
reading 1 are songs played once. Without that confirmation the field would be
ambiguous, since an instrument enum produces similarly small integers. It
cross-tabulates independently of byte 12, so the two are unrelated.

**Percent, the full-combo flag and score** validate against each other. Byte 8 is set
on exactly the set of records at 100% and no others, which is what a full-combo flag
must do. Byte 16 read as a uint32 gives a plausible score range whose top entry is
the most-played song.

**Stars are *not* a function of accuracy.** The bands overlap heavily, and across the
sample there are **71 record pairs where a higher percent earned fewer stars**:

| Stars | n | Percent range |
|---:|---:|---|
| 1 | 1 | 45 |
| 2 | 3 | 49-75 |
| 3 | 34 | 75-92 |
| 4 | 25 | 82-97 |
| 5 | 8 | 93-97 |
| 6 | 5 | 95-98 |
| 7 | 1 | 100 |

This is expected: Clone Hero derives stars from **score against a per-chart base
score**, not from accuracy, so an easy chart can reach 6 stars at 95% while a dense
one cannot. The field is still confidently stars - the range 1-7 matches five stars
plus a gold star plus the full-combo tier, and 7 occurs only on the 100% full combo -
but **do not treat stars as a skill signal**. Accuracy is the cleaner ELO input.

**Byte 6 is always 3** in this sample because this player only has Expert scores.
`3 = Expert` follows fretwork's own E/M/H/X ordering, but a library with lower
difficulty scores is needed to confirm 0/1/2.

## `scoresext.bin`

Same shape, different payload. **Confirmed:**

```text
     0     4  magic            83 01 35 01
     4     4  uint32 count     77 - matches scoredata.bin
     8     -  count x 28-byte records:  16-byte MD5 + 3 x uint32
```

The hashes and their order are **identical** to `scoredata.bin` (verified across all
77), so the two tables are row-aligned and can be zipped by index without matching on
hash.

| Int | Observed |
|---|---|
| 1st | `1` on 76 records; `16777217` (raw `01 00 00 01`) on the single 100% full-combo record |
| 2nd | score-like; **higher** than the same song's score on 68 records, equal on 1, zero on 8, lower on **none** |
| 3rd | always `0` |

The first integer is almost certainly **not a plain uint32** - the outlier's raw bytes
are `01 00 00 01`, a leading `1` plus a flag byte in the high position, and it lands
on the full-combo record.

The second integer exceeds the `scoredata.bin` score by 0 to 2,645 (at most 0.85%)
wherever it is non-zero - for example 337,789 against that song's 336,838. **Inferred:**
a score computed slightly differently, possibly before a modifier or rounding step.
Not needed for the join and not worth relying on until it is understood.

> An earlier draft of this document claimed the second integer was *lower* than the
> score, citing "240,795 against 336,838". Those two numbers came from **different
> records**. The direction is the opposite of what was written.

## `songcache.bin`

The library scan. Magic is `7b 25 35 01`. The file has two distinct regions:

```text
  0x00000   4  magic
  0x00004  16  unknown 16-byte value
  0x00014   -  seven string-interning tables, each: 1-byte marker (0-6),
               uint32 count, then that many 7-bit length-prefixed strings
               (titles, artists, albums, genres, years, charters, packs)
  0x13FC9   4  uint32 record count (873 in the sample)
  0x13FCD   -  variable-length song records
```

The string tables occupy the first ~20% of the file; song records do not begin until
roughly `0x13FCD`. Strings use .NET `BinaryWriter` convention - **length-prefixed
with a 7-bit encoded integer**, one byte under 128, two bytes above, low 7 bits first
with the high bit as a continuation flag.

Within a song record the folder path appears near the start, the chart file path
follows it, and the **16-byte MD5 sits at the end**, immediately before the next
record's length prefix. Paths are stored **lowercased** and in Windows form:

```text
c:\program files\clone hero\custom songs\s hero\s hero\[s] 12 - str-s free zone\...
```

**The chart file is `notes.chart` *or* `notes.mid`.** In this sample: 363 `.chart`
and 480 `.mid`. A parser keying on the literal string `notes.chart` would miss 57%
of the library.

**873 folders, 843 charts.** The count field says 873 and there are 873 folder paths,
but only 843 chart paths - so **30 cached folders carry no chart path** and are stale
entries for songs no longer on disk. Any parser must tolerate a record without one
rather than assuming the two counts match.

> The 363 / 480 split is an exact match for what `build.py` reports when parsing the
> same library ("Parsing charts: 363", "Parsing midis: 480"). Two independent parsers
> agreeing is good evidence both read the library correctly - and it confirms 843,
> not 873, is the live song count.

Fully parsing the record body is unnecessary and is the most version-fragile part of
the format. A parser only needs to associate each hash with the nearest preceding
folder path.

## The join

This is the part that makes the whole idea viable. Clone Hero keys scores by chart
hash; fretwork keys everything by resolved song folder path. They are bridged by the
song cache, so **fretwork never has to compute Clone Hero's hash itself** - which
matters, because reproducing that hash exactly would mean matching the game's byte
handling for every chart format.

```text
scoredata.bin   MD5 -> score, percent, stars, plays, FC
songcache.bin   MD5 -> song folder path
fretwork        song folder path -> D, RemapDiff, CalcTier, NPS/VPS metrics
```

**Measured:** 68 of 77 score hashes (88%) resolve to a folder through the cache.

The 9 that do not are **not** songs that left the library - they are scores stranded
on *chart files that were replaced*. Three were identified through `LeaderboardCache/`
as Through the Fire and Flames, Raining Blood and Stricken, all charted by "Buldy",
from a GH3 pack that was swapped for a different one. **All three songs are still in
the library and still in `songcache.bin`** - under different hashes, because the chart
files differ.

That is the single most important property of this data:

> **A score is bound to the exact chart file, not to the song.** Re-downloading a
> pack, or swapping one charter's version for another's, silently orphans every score
> on it. The song reappears with a fresh hash and no history.

For the rating this means measured coverage is a **floor, not a count** - a player may
have played far more than the resolved rows suggest. Orphans should be surfaced rather
than silently dropped, and `LeaderboardCache/` can name them.

### Two things that will bite

**Path form.** Cache paths are lowercased Windows paths (`c:\...`); fretwork stores
resolved absolute paths, which under WSL are `/mnt/c/...`. Any join has to normalise
case, separators and the drive prefix on both sides.

**Library location.** The join only lands if fretwork built its cache against the
*same* files Clone Hero scanned:

```bash
python build.py --search-path "/mnt/c/Program Files/Clone Hero/custom songs" --header Main
```

The repo's gitignored `songs/` folder is a *copy*, so its paths will not match the
game's cache. It appears to be a faithful copy - same 843 charts, same `.chart`/`.mid`
split - so matching on trailing path segments is a viable fallback, but it is fuzzy
and should not be the primary strategy.

### Expert anchoring lines up for free

Every score in the sample is Expert, and fretwork's `RemapDiff` and `CalcTier` are
already computed from the Expert chart only. The join therefore lands on exactly the
row that carries the tier, with no extra reconciliation.

## What this means for ELO

**Decision: the rating is an estimated skill level fitted from best attempts only.**
No play history is collected, and none is needed.

That follows from the data. Clone Hero keeps **no play history** - `scoredata.bin`
holds one aggregate record per song (best score, best percent, a play counter) with
no timestamps and no per-attempt rows. There is no way to reconstruct what a run
looked like before it was beaten.

Consequences for the design:

- The rating is a **function of a snapshot**, not a sequence. Classic ELO updates
  match-by-match in order; there is no order here, so nothing should pretend there is.
  Any "rating over time" chart would be fabricated.
- The natural formulation is a **static skill estimate**: fit one rating from all
  (difficulty, accuracy) pairs at once. Each song is an opponent of known strength
  `D` (or `CalcTier`); the outcome is the accuracy achieved. A logistic fit over the
  77 pairs gives a rating plus an honest confidence interval.
- **Use accuracy, not stars.** As shown above, stars come from score against a
  per-chart base and invert against accuracy on 71 pairs in this sample.
- Raw score is not comparable across songs either - it scales with note count - so it
  is a poor rating input on its own. Accuracy is the only directly comparable field.
- The sample is thin: 77 scored songs against 843 charts on disk, 113 plays, 58 songs
  played exactly once. Only 68 rows join, and that 8% is a floor rather than a
  measurement, since replaced charts orphan scores invisibly. Confidence bounds matter
  far more than the point estimate here.

**Considered and rejected:** snapshotting `scoredata.bin` over time and diffing
successive snapshots to synthesise a real match history. It would enable a true
sequential ELO, and the history cannot be recovered retroactively, but it adds a
background job and a store for a payoff the estimated rating does not need.

The interesting signal, and the reason the join is worth building at all, is accuracy
plotted against computed `D` - whether the formula actually predicts what a player
finds hard.

## Version safety

Every layout here is undocumented and specific to the build that produced the
sample (Clone Hero, files dated September 2026). The magic numbers appear to encode
a format version, and the game can change them in any update.

A parser must therefore:

1. **Check the magic bytes** and refuse to parse anything it does not recognise.
2. **Verify the size identity** (`filesize == 8 + count * record_size`) before
   reading records, since that catches a changed record width immediately.
3. **Degrade to "no scores"** rather than guessing. Wrong scores shown next to a
   difficulty rating are worse than no scores at all.
4. **Never write** to any of these files.

Treating an unrecognised magic as "no data" keeps the viewer working for players on
a different Clone Hero version instead of showing them nonsense.
