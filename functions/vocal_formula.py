"""
VOCAL FORMULA - Per-song difficulty scalar, computed from outputs of vocal_density

How much the pitch moves (P) times how far the voice reaches (R)
plus how fast the syllables come (S) (so talkie-heavy parts still count)
scaled by CoV (from P, S) & STAM

D = (P * R + S) * COV * STAM

    epsP = aPPS * 0.05
    P = ((medPPS + epsP) * aPPS * pPPS) ** (1 / 3)
    cvP = stdPPS / (medPPS + aPPS)

    R = Span ** 0.5

    epsS = aSPS * 0.05
    S = ((medSPS + epsS) * aSPS * pSPS) ** (1 / 3)
    cvS = stdSPS / (medSPS + aSPS)

    COV = 1 + (cvS * cvP) ** 0.5

    STAM = (DurationS / t_ref) ** s_stam

    # base scalar difficulty
    D = (P * R + S) * COV * STAM

P is pitch movement (folded, sqrt-compressed intervals) balancing peak windows against average and median
R is the song's sung range, sqrt-compressed the same way pitch movement and drum travel are
S is syllable rate (new sung syllables + talkies), same peak/average/median combination
COV is the same two-stream construction as 5 fret (N/V) and drums (hands/kick), across S and P

STAM: s_stam = 0.20, shared with 5 fret/drums

Vocals have no EMHX, so RemapDiff/CalcTier come straight from D

CalcTier: vocal D isn't log-normal - so the calc is now linear instead of log

LIMITATIONS:
This is probably the hardest one to get right since vocals relies so much on knowing a song
A song you know well can feel so much easier regardless of what the formula says
Not to mention the weirdness with talkies, huge variations between the same songs across charters, etc.
This may be a case where vibes tiering may be the correct path given enough playtesting...
"""

import math

# ---------------------------------
# Remap (0-6)
# ---------------------------------
DIFF_LABELS = [0, 1, 2, 3, 4, 5, 6]   # shared label set

# Bin edges calibrated so RemapDiff distribution matches diff_vocals' official distribution
VOCAL_REMAP_BINS = [0, 9.8, 16.5, 21.4, 26.7, 30.9, 35.0, math.inf]


# --------------------------------------------
# CalcTier (linear-scaled)
# --------------------------------------------
# BASE_D = RemapDiff's own tier 0/1 edge
# D_STEP = ~average gap between RemapDiff's calibrated edges (6.7, 4.9, 5.3, 4.2, 4.1 -> 5.0),
CALC_TIER_PARAMS = (9.8, 5.0)

# Formula params
T_REF = 230.0 # 3-4 min average song
S_STAM = 0.20 
R_GAMMA = 0.5 # range compression


# RB manual 0-6 fit
def remap_diff(D):
    if D <= 0:
        return 0
    bin_edges = VOCAL_REMAP_BINS
    lower = bin_edges[0]
    for label, upper in zip(DIFF_LABELS, bin_edges[1:]):
        if lower < D <= upper:
            return label
        lower = upper
    return None


# linear tier calculation
def calc_tier(D):
    base_d, d_step = CALC_TIER_PARAMS
    if D <= base_d:
        return 0
    return int(math.floor((D - base_d) / d_step) + 1)


# D Formula - P/R/S/COV/D, plus RemapDiff/CalcTier
def calc_vocal_d(metrics):
    pPPS, medPPS, aPPS, stdPPS = metrics['pPPS'], metrics['medPPS'], metrics['aPPS'], metrics['stdPPS']
    pSPS, medSPS, aSPS, stdSPS = metrics['pSPS'], metrics['medSPS'], metrics['aSPS'], metrics['stdSPS']
    Span = metrics['Span']
    DurationS = metrics.get('DurationS', 0.0)

    # PPS combo
    epsP = aPPS * 0.05
    P = ((medPPS + epsP) * aPPS * pPPS) ** (1 / 3)
    #cvP gets very large on talkie dominant charts, floored to limit impact
    P_FLOOR = 0.01
    cvP = stdPPS / (medPPS + aPPS + P_FLOOR)

    # range
    R = Span ** R_GAMMA if Span > 0 else 0.0

    # SPS combo
    epsS = aSPS * 0.05
    S = ((medSPS + epsS) * aSPS * pSPS) ** (1 / 3)
    cvS = stdSPS / (medSPS + aSPS) if (medSPS + aSPS) > 0 else 0.0

    # pitch work x reach, syllables added (saves rap songs from 0 D)
    BASE = P * R + S

    # CoV interaction across syllables & pitch movement
    COV = 1 + (cvS * cvP) ** 0.5

    # STAMINA!!! sublinear by duration / slowly building boost for long songs, discounts short songs
    # ~66% @ 30s, ~75% @ 60s / 1x @ t_ref / 1.1x @ ~6 mins, 1.2x @ 9.5 mins
    STAM = (DurationS / T_REF) ** S_STAM if DurationS > 0 else 0.0

    # base scalar difficulty
    D = BASE * COV * STAM

    return {
        'P': P,
        'R': R,
        'S': S,
        'Base': BASE,
        'CoV': COV,
        'STAM': STAM,
        'D': D,
        'RemapDiff': remap_diff(D),
        'CalcTier': calc_tier(D),
    }
