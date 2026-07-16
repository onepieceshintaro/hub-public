"""テーマパック：二人で最初にすり合わせておくと良い話題。

軸2（同棲・二人暮らしのスタート、入籍・出産などの節目）向けの入口。
「衝突してから」ではなく「暮らし始める前後」に、前向きな共同作業として
価値観をすり合わせるための定番テーマを用意する。

各テーマは “正解を決める” ものではなく、
「ここは人によって基準が違いやすいね」と気づくための足場。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Topic:
    emoji: str
    label: str
    hint: str  # なぜ話しておくと良いか（一言）


# 同棲・二人暮らしスタートの定番テーマ
STARTER_TOPICS: list[Topic] = [
    Topic("💰", "お金の使い方・貯金", "どこまで共有する？何にいくらまでなら相談なし？"),
    Topic("🧹", "家事の分担", "「きれい」の基準も、やる頻度も人それぞれ"),
    Topic("⏰", "生活リズム（朝型／夜型）", "起きる・寝る・食べる時間が合うか"),
    Topic("🛋", "一人の時間・距離感", "どのくらい一緒／別々でいたい？"),
    Topic("🍽", "休日の過ごし方", "予定を詰めたい／家でゆっくりしたい"),
    Topic("👪", "親・親戚とのつき合い", "帰省や連絡の頻度、どこまで関わる？"),
    Topic("🎉", "友人を家に呼ぶ・来客", "家というプライベート空間の感覚の違い"),
    Topic("🧭", "大きな決め方（買い物・引越し）", "いくらから／どのタイミングで相談する？"),
    Topic("🌱", "これからの将来設計", "仕事・住む場所・子ども観 など"),
]

# 自由入力を選ぶための番兵ラベル
CUSTOM_LABEL = "✍️ 自分で書く（自由入力）"


def topic_choices() -> list[str]:
    """selectbox 用のラベル一覧（先頭に「選ばない」、末尾に自由入力）。"""
    return (
        ["—（テーマを選ばない）"]
        + [f"{t.emoji} {t.label}" for t in STARTER_TOPICS]
        + [CUSTOM_LABEL]
    )


def topic_hint(choice: str) -> str:
    """選択中の定番テーマの「なぜ話すと良いか」を返す。無ければ空。"""
    for t in STARTER_TOPICS:
        if choice == f"{t.emoji} {t.label}":
            return t.hint
    return ""


def resolve_theme(choice: str, custom_text: str) -> str:
    """selectbox の選択と自由入力から、AI へ渡すテーマ文字列を決める。"""
    if not choice or choice.startswith("—"):
        return (custom_text or "").strip()
    if choice == CUSTOM_LABEL:
        return (custom_text or "").strip()
    # 絵文字を除いたラベル本体をテーマにする
    for t in STARTER_TOPICS:
        if choice == f"{t.emoji} {t.label}":
            return t.label
    return choice.strip()
