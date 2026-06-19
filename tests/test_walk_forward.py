from __future__ import annotations

from itertools import pairwise

from swing_rsi.research.walk_forward import expanding_splits


def test_expanding_splits_are_chronological_and_gapped() -> None:
    splits = expanding_splits(600, n_splits=5, test_size=60, gap=2, minimum_train_size=200)
    assert len(splits) == 5
    for split in splits:
        assert split.train_end < split.test_start
        assert split.test_start - split.train_end - 1 == 2
    assert all(current.train_end < following.train_end for current, following in pairwise(splits))
