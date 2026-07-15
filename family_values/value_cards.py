"""価値観カード定義：このプロダクトの「共通言語」の語彙。

設計思想（最重要）:
- ここで定義するカードは、診断のための「タイプ」ではない。
- 家族が同じ言葉で自分と相手を語れるようにするための、
  “対話の共通言語” の単語帳である。
- どのカードも優劣はない。人によって優先順位が違うだけ。

各カードが持つ情報:
- key         : 内部識別子
- emoji/label : 表示用
- description : 「この価値観を大切にしている人にとっての世界」の説明
- strength    : その価値観が満たされている時に発揮されやすい強み
- stress      : その価値観が脅かされた時に生まれやすいストレス／不安
- lean        : 意思決定で傾きやすい方向（判定ではなく傾向）
- category    : 意思決定傾向を推定するための緩いグルーピング
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ValueCard:
    key: str
    emoji: str
    label: str
    description: str
    strength: str
    stress: str
    lean: str
    category: str


# 意思決定傾向を推定するための緩いカテゴリ
# stability : 守り・確かさを重視
# growth    : 攻め・変化を重視
# relation  : 人・関係を重視
# autonomy  : 自分・自由を重視
CATEGORY_LABELS = {
    "stability": "確かさ・安心を土台にする",
    "growth": "変化・挑戦に向かう",
    "relation": "人とのつながりを大切にする",
    "autonomy": "自分らしさ・自由を守る",
}


VALUE_CARDS: list[ValueCard] = [
    ValueCard(
        key="security",
        emoji="🛡",
        label="安心・安全",
        description=(
            "見通しが立ち、脅かされない状態が何より大切。"
            "「これで大丈夫」と思えることが、動くための前提になる。"
        ),
        strength="リスクに早く気づき、家族を守る備えができる",
        stress="予測できない出来事や、相談なく物事が決まること",
        lean="決める前に「本当に大丈夫か」を確かめたくなる",
        category="stability",
    ),
    ValueCard(
        key="challenge",
        emoji="🚀",
        label="挑戦・成長",
        description=(
            "同じ場所に留まることの方が怖い。"
            "新しいことに踏み出し、昨日より前に進んでいる感覚が大切。"
        ),
        strength="現状に甘えず、家族の未来のために動ける",
        stress="変化のない停滞や、挑戦を止められること",
        lean="迷ったら「やってみる」方に踏み出したくなる",
        category="growth",
    ),
    ValueCard(
        key="family_time",
        emoji="🏠",
        label="家族との時間",
        description=(
            "一緒に過ごす時間そのものが目的。"
            "何をするかより、誰といるかが心の栄養になる。"
        ),
        strength="家族の小さな変化に気づき、場をあたためられる",
        stress="すれ違いや、家族が後回しにされること",
        lean="「家族の時間が減らないか」を基準に考えたくなる",
        category="relation",
    ),
    ValueCard(
        key="freedom",
        emoji="🕊",
        label="自由",
        description=(
            "自分で選び、自分で決められることが大切。"
            "縛られる感覚があると、息苦しくなる。"
        ),
        strength="固定観念に縛られず、しなやかに動ける",
        stress="選択肢を狭められること、細かく管理されること",
        lean="「自分で決められる余白があるか」を大事にする",
        category="autonomy",
    ),
    ValueCard(
        key="financial",
        emoji="💰",
        label="経済的安定",
        description=(
            "お金の見通しが立っていることが安心の土台。"
            "数字で確かめられると、落ち着いて考えられる。"
        ),
        strength="家計を現実的に見て、地に足のついた判断ができる",
        stress="収支の見えない大きな出費や、将来の不確かさ",
        lean="「数字で見て無理がないか」を先に確かめたくなる",
        category="stability",
    ),
    ValueCard(
        key="self_actualization",
        emoji="🌱",
        label="自己実現",
        description=(
            "自分の可能性を活かし、なりたい自分に近づきたい。"
            "「これが自分の人生だ」と感じられることが大切。"
        ),
        strength="目的に向かって粘り強く自分を育てられる",
        stress="自分を押し殺すこと、可能性を諦めさせられること",
        lean="「自分の成長につながるか」を基準に考えたくなる",
        category="growth",
    ),
    ValueCard(
        key="connection",
        emoji="🤝",
        label="つながり・関係",
        description=(
            "分かり合えている感覚が大切。"
            "気持ちが通じているとき、いちばん安心できる。"
        ),
        strength="相手の気持ちを汲み、関係を結び直せる",
        stress="無視されること、気持ちがすれ違ったままになること",
        lean="「お互い納得できているか」をまず確かめたくなる",
        category="relation",
    ),
    ValueCard(
        key="integrity",
        emoji="🤲",
        label="誠実・信頼",
        description=(
            "嘘がなく、約束が守られていることが大切。"
            "信頼が土台にあるから、安心して任せ合える。"
        ),
        strength="約束を守り、言動を一致させて信頼を積む",
        stress="隠しごとや、相談なく事が進むこと",
        lean="「透明に共有できているか」を大事にする",
        category="stability",
    ),
    ValueCard(
        key="contribution",
        emoji="🌍",
        label="貢献・役立ち",
        description=(
            "誰かの役に立てている実感が原動力。"
            "自分の行いが誰かを支えていると感じられると満たされる。"
        ),
        strength="家族や周りのために自分を差し出せる",
        stress="努力が誰にも届かない・報われないと感じること",
        lean="「これは誰かのためになるか」を基準に考えたくなる",
        category="relation",
    ),
    ValueCard(
        key="curiosity",
        emoji="📚",
        label="学び・好奇心",
        description=(
            "知らないことを知るのが楽しい。"
            "学び続けている状態そのものが、生きている感覚につながる。"
        ),
        strength="新しい知識を取り入れ、選択肢を増やせる",
        stress="学ぶ機会を奪われること、思考停止を求められること",
        lean="「もっと良いやり方はないか」を探したくなる",
        category="growth",
    ),
    ValueCard(
        key="order",
        emoji="🗂",
        label="秩序・計画",
        description=(
            "段取りが整い、見通しが立っていることが心地よい。"
            "計画どおりに進むと、安心して次に集中できる。"
        ),
        strength="先を見て段取りし、破綻を防げる",
        stress="行き当たりばったり、計画が崩されること",
        lean="「順番と段取りが立っているか」を確かめたくなる",
        category="stability",
    ),
    ValueCard(
        key="playfulness",
        emoji="🎈",
        label="楽しさ・遊び",
        description=(
            "日々に笑いや遊びがあることが大切。"
            "深刻になりすぎず、軽やかでいられることを大事にする。"
        ),
        strength="場を和ませ、重い空気をほぐせる",
        stress="ずっと張り詰めていること、楽しさを否定されること",
        lean="「これは楽しめるか・軽くできないか」を大事にする",
        category="autonomy",
    ),
]


CARDS_BY_KEY: dict[str, ValueCard] = {c.key: c for c in VALUE_CARDS}


def get_card(key: str) -> ValueCard | None:
    return CARDS_BY_KEY.get(key)
