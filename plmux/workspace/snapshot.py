from __future__ import annotations

from plmux.config.schema import PlmuxConfig
from plmux.session.models import SessionSnapshot
from plmux.session.store import load_session
from plmux.ui.geometry import Tree, pane_indices


def reindex_tree(tree: Tree, removed_indices: list[int]) -> Tree:
    if not removed_indices:
        return tree
    removed_set = set(removed_indices)
    all_idx = pane_indices(tree)
    max_idx = max(max(all_idx), max(removed_set)) if all_idx else 0
    mapping: dict[int, int] = {}
    shift = 0
    for i in range(max_idx + 2):
        if i in removed_set:
            shift += 1
        else:
            mapping[i] = i - shift
    if isinstance(tree, int):
        return mapping.get(tree, tree)
    d, r, a, b = tree
    return (d, r, reindex_tree(a, removed_indices), reindex_tree(b, removed_indices))


def try_load_snapshot(cfg: PlmuxConfig) -> SessionSnapshot | None:
    if not cfg.session.auto_save:
        return None
    return load_session(cfg)
