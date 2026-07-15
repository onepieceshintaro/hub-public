"""個人プロファイルの組み立て：レーティング → 可視化用データ。

ここは外部依存なしの純粋ロジック（AI も DB も使わない）。
「診断で当てる」のではなく、本人が付けた重みづけを
そのまま構造化して見せ返すだけ、という思想。

出力する 4 つの軸（構想の MVP ①個人診断に対応）:
- values    : 大切にしている価値観（上位）
- strengths : その価値観から発揮されやすい強み
- stresses  : その価値観が脅かされた時のストレスポイント
- decision  : 意思決定で傾きやすい方向（判定ではなく傾向）
"""
from __future__ import annotations

from dataclasses import dataclass, field

from value_cards import (
    CATEGORY_LABELS,
    VALUE_CARDS,
    ValueCard,
    get_card,
)

# 上位いくつを「大切にしている価値観」として扱うか
TOP_N = 4
# レーティングの範囲（Streamlit 側の slider と揃える）
RATING_MIN = 1
RATING_MAX = 5


@dataclass
class Profile:
    name: str
    ratings: dict[str, int]
    top_keys: list[str] = field(default_factory=list)
    decision_category: str = ""
    decision_label: str = ""

    # ---- 表示用ヘルパ ----
    @property
    def top_cards(self) -> list[ValueCard]:
        return [c for k in self.top_keys if (c := get_card(k))]

    @property
    def strengths(self) -> list[str]:
        return [c.strength for c in self.top_cards]

    @property
    def stresses(self) -> list[str]:
        return [c.stress for c in self.top_cards]

    def summary_line(self) -> str:
        """AI へ渡す・家族共有で並べる用の 1 行サマリ。"""
        vals = "／".join(f"{c.emoji}{c.label}" for c in self.top_cards)
        return f"{self.name}：{vals}（傾向：{self.decision_label}）"


def default_ratings() -> dict[str, int]:
    """全カードを中央値で初期化。"""
    mid = (RATING_MIN + RATING_MAX) // 2 + 1  # 1-5 なら 3
    return {c.key: mid for c in VALUE_CARDS}


def _rank_keys(ratings: dict[str, int]) -> list[str]:
    """レーティング降順。同点はカード定義順で安定ソート。"""
    order = {c.key: i for i, c in enumerate(VALUE_CARDS)}
    return sorted(
        ratings.keys(),
        key=lambda k: (-ratings.get(k, 0), order.get(k, 999)),
    )


def _decision_tendency(top_keys: list[str]) -> tuple[str, str]:
    """上位カードのカテゴリ分布から意思決定傾向を推定。

    「あなたは○○タイプ」と断定しないため、最頻カテゴリを
    “傾きやすい方向” として 1 つだけ返す。同数なら上位ほど優先。
    """
    weights: dict[str, float] = {}
    for i, key in enumerate(top_keys):
        card = get_card(key)
        if not card:
            continue
        # 上位ほど重く（1位: 4, 2位: 3, ...）
        weights[card.category] = weights.get(card.category, 0.0) + (
            len(top_keys) - i
        )
    if not weights:
        return "", "まだ傾向はわかりません"
    best = max(weights, key=lambda c: weights[c])
    return best, CATEGORY_LABELS.get(best, best)


def build_profile(name: str, ratings: dict[str, int]) -> Profile:
    """レーティングからプロファイルを構築。"""
    name = (name or "").strip() or "名前未設定"
    clean = {
        c.key: int(ratings.get(c.key, RATING_MIN))
        for c in VALUE_CARDS
    }
    top_keys = _rank_keys(clean)[:TOP_N]
    cat, label = _decision_tendency(top_keys)
    return Profile(
        name=name,
        ratings=clean,
        top_keys=top_keys,
        decision_category=cat,
        decision_label=label,
    )


# ============================================================
# 家族比較：2 人以上のプロファイルの重なり／違いを整理
# ============================================================
@dataclass
class Comparison:
    members: list[Profile]
    shared_keys: list[str]        # 上位に共通して現れた価値観
    divergent: dict[str, list[str]]  # value_key -> それを上位に持つ人の名前


def compare_profiles(profiles: list[Profile]) -> Comparison:
    """家族のプロファイルを比べ、共通点と違いを抽出。

    - shared_keys : 全員が上位に挙げた価値観（対話の足場になりやすい）
    - divergent   : 一部の人だけが上位に挙げた価値観（すれ違いの芽）
    """
    if not profiles:
        return Comparison([], [], {})

    top_sets = [set(p.top_keys) for p in profiles]
    shared = set.intersection(*top_sets) if top_sets else set()

    # value_key -> その価値観を上位に持つ人の名前リスト
    holders: dict[str, list[str]] = {}
    for p in profiles:
        for k in p.top_keys:
            holders.setdefault(k, []).append(p.name)

    # 全員が持っていない＝一部だけが大切にしている価値観
    divergent = {
        k: names
        for k, names in holders.items()
        if len(names) < len(profiles)
    }

    # カード定義順で安定させる
    order = {c.key: i for i, c in enumerate(VALUE_CARDS)}
    shared_keys = sorted(shared, key=lambda k: order.get(k, 999))
    divergent = dict(
        sorted(divergent.items(), key=lambda kv: order.get(kv[0], 999))
    )
    return Comparison(list(profiles), shared_keys, divergent)
