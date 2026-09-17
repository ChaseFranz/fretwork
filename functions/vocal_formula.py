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

TODO Calibration for calctier - fit is bad right now
fix remap, not showing up on xlsx
"""

import math

# ---------------------------------
# Calibration fit selection
# ---------------------------------
REMAP_FIT = 'all'

# ---------------------------------
# Remap (0-6) params
# ---------------------------------
DIFF_LABELS = [0, 1, 2, 3, 4, 5, 6]   # shared label set

# Bin edges calibrated so RemapDiff distribution matches diff_vocals' official distribution
# fit at s_stam = 0.20
VOCAL_REMAP_BINS = [0, 9.8, 16.5, 21.4, 26.7, 30.9, 35.0, math.inf],


# --------------------------------------------
# CalcTier (log-scaled) params - PROVISIONAL, maybe needs a new method
# --------------------------------------------
# BASE_D = that fit's tier 0/1 remap edge, LN_INC = smallest step keeping most of songs under tier 7
# Vocal D is compressed at the top (p99 ~1.7x median), so log tiers bunch in the middle...
CALC_TIER_PARAMS = (8.7, 0.248)

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


# log tier calculation
def calc_tier(D):
    base_d, ln_inc = CALC_TIER_PARAMS
    if D < base_d:
        return 0
    return int(math.floor(math.log(D / base_d) / ln_inc) + 1)


# D Formula - P/R/S/COV/D, plus RemapDiff/CalcTier
def calc_vocal_d(metrics):
    pPPS, medPPS, aPPS, stdPPS = metrics['pPPS'], metrics['medPPS'], metrics['aPPS'], metrics['stdPPS']
    pSPS, medSPS, aSPS, stdSPS = metrics['pSPS'], metrics['medSPS'], metrics['aSPS'], metrics['stdSPS']
    Span = metrics['Span']
    DurationS = metrics.get('DurationS', 0.0)

    # PPS combo
    epsP = aPPS * 0.05
    P = ((medPPS + epsP) * aPPS * pPPS) ** (1 / 3)
    cvP = stdPPS / (medPPS + aPPS) if (medPPS + aPPS) > 0 else 0.0

    # range
    R = Span ** R_GAMMA if Span > 0 else 0.0

    # SPS combo
    epsS = aSPS * 0.05
    S = ((medSPS + epsS) * aSPS * pSPS) ** (1 / 3)
    cvS = stdSPS / (medSPS + aSPS) if (medSPS + aSPS) > 0 else 0.0

    # pitch work x reach, syllables added
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
