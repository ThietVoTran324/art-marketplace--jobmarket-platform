"""Home feed personalization constants (Feed_Sprint1 Plan #2)."""

from __future__ import annotations

# AC-18 — single place to tune interaction weights
INTERACTION_WEIGHTS: dict[str, float] = {
    "save": 3.0,
    "like": 2.0,
    "view": 1.0,
}

# Q2 — pool share of each page (must sum ~1.0)
FEED_POOL_RATIOS: dict[str, float] = {
    "following": 0.30,
    "affinity": 0.35,
    "explore": 0.15,
    "trending": 0.10,
    "fresh": 0.10,
}

# Guest: no following/affinity
FEED_GUEST_POOL_RATIOS: dict[str, float] = {
    "trending": 0.45,
    "explore": 0.35,
    "fresh": 0.20,
}

FEED_DIVERSITY_MAX_AUTHOR_STREAK = 2
FEED_DIVERSITY_MAX_TAG_STREAK = 3

FEED_RECENT_DAYS = 7
FEED_CANDIDATE_CAP = 300
FEED_FRESH_DAYS = 7
FEED_TRENDING_DAYS = 7

# Guest home (no auth): popularity only — weights decrease like → view → comment → save.
# Applied as weight * log1p(count) so extremes do not dominate.
GUEST_POPULARITY_WEIGHTS: dict[str, float] = {
    "like": 8.0,
    "view": 3.0,
    "comment": 1.5,
    "save": 0.5,
}
