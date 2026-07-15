"""AI エンジン：価値観の違いを「対話の共通言語」に翻訳する。

設計思想（構想「AIの役割」に忠実）:
- AI は答えを出さない。ジャッジしない。「あなたが正しい」と言わない。
- AI は “視点を増やす存在”。相手が何を守ろうとしているかを可視化する。
- 目的は「相手は間違っている」ではなく
  「相手はこういう世界で生きていたんだ」という理解を促すこと。

実装方針:
- ANTHROPIC_API_KEY があれば Claude で生成（analyze / dialogue）。
- 無ければ、プロファイル比較データからテンプレートで生成（fallback）。
  → API 未設定でもプロダクトの中心体験（可視化＋対話の問い）は動く。
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from profile import Comparison, Profile
from value_cards import get_card

ENV_PATH = Path(__file__).parent / ".env"
try:
    from dotenv import load_dotenv

    load_dotenv(ENV_PATH, override=False)
except Exception:
    pass

_api_key = None
try:
    import streamlit as st  # type: ignore

    _api_key = st.secrets.get("ANTHROPIC_API_KEY")
except Exception:
    pass
if not _api_key:
    _api_key = os.getenv("ANTHROPIC_API_KEY")

_client = None
MODEL = "claude-haiku-4-5"


def is_available() -> bool:
    return bool(_api_key)


def _get_client():
    global _client
    if _client is None:
        from anthropic import Anthropic

        if not _api_key:
            raise RuntimeError("ANTHROPIC_API_KEY が未設定です。")
        _client = Anthropic(api_key=_api_key)
    return _client


# ============================================================
# システムプロンプト（AI の立ち位置を強く固定する）
# ============================================================
SYSTEM_PROMPT = """\
あなたは「家族の価値観を可視化し、対話を支援する AI」です。

# 絶対に守る立ち位置
- あなたは答えを出さない。どちらが正しいかを決めない。
- あなたはジャッジしない。「あなたが正しい」とも「相手が正しい」とも言わない。
- あなたは説得しない。相手を変えさせようとしない。
- あなたの役割は “視点を増やすこと” だけ。
- 目的は「相手は間違っている」ではなく
  「相手はこういう世界を生きていたんだ」という理解を促すこと。

# 前提となる考え方
- 価値観に優劣はない。人によって優先順位が違うだけ。
- 同じ出来事でも「挑戦しないことが怖い」人と
  「リスクを取ることが怖い」人がいて、どちらも自然な価値観。
- すれ違いの多くは、性格や思いやりの問題ではなく、
  「大切にしているものが違う」だけのことが多い。

# トーン
- やわらかく、断定を避ける。「〜かもしれません」「〜という見方もできます」。
- 専門用語や診断ラベルで決めつけない。
- 短く。装飾しすぎない。
- 医療・心理の診断はしない。
"""


# ============================================================
# ① AI 分析：違いを共通言語に翻訳する
# ============================================================
def analyze(comparison: Comparison, theme: str = "") -> str:
    """家族の価値観比較から「共通言語」の説明文を返す。

    theme: 任意。今すれ違っている具体的なテーマ（例：自己投資の契約）。
    """
    if is_available():
        try:
            return _analyze_ai(comparison, theme)
        except Exception:
            pass
    return _analyze_fallback(comparison, theme)


def _members_context(comparison: Comparison) -> str:
    lines = []
    for p in comparison.members:
        cards = "、".join(f"{c.label}（{c.description}）" for c in p.top_cards)
        lines.append(
            f"- {p.name}：大切にしている＝{cards}／"
            f"意思決定の傾向＝{p.decision_label}"
        )
    return "\n".join(lines)


def _analyze_ai(comparison: Comparison, theme: str) -> str:
    shared = "、".join(
        c.label for k in comparison.shared_keys if (c := get_card(k))
    ) or "（明確な共通点は上位には出ていません）"
    diverge_lines = []
    for k, names in comparison.divergent.items():
        card = get_card(k)
        if card:
            diverge_lines.append(f"- {card.label}：{ '・'.join(names) } が特に大切にしている")
    diverge = "\n".join(diverge_lines) or "（際立った違いは上位には出ていません）"

    theme_line = f"\n今すれ違っている具体的なテーマ：{theme}" if theme.strip() else ""

    user_msg = f"""\
以下は、ある家族それぞれの価値観プロファイルです。

{_members_context(comparison)}

共通して大切にしていること：{shared}
一部の人だけが特に大切にしていること：
{diverge}{theme_line}

この情報をもとに、次の 3 つを日本語で整理してください。
どちらが正しいかは絶対に決めないでください。

1. 【それぞれが守ろうとしているもの】
   各メンバーが、その価値観の背景で “何を守ろうとしているのか” を、
   本人を責めない言葉で 1〜2 文ずつ。

2. 【なぜこのテーマですれ違いやすいか】
   価値観の違いが、どんな場面で衝突として現れやすいかを 2〜3 文で。
   「性格」ではなく「大切にしているものの違い」として説明する。

3. 【ひとつの見方として】
   「相手はこういう世界を生きていたのかもしれない」と気づけるような
   リフレーミングを 2〜3 文で。答えや結論は出さないこと。

各見出しは上の【】をそのまま使ってください。"""

    resp = _get_client().messages.create(
        model=MODEL,
        max_tokens=900,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    return resp.content[0].text.strip()


def _analyze_fallback(comparison: Comparison, theme: str) -> str:
    """API 無しでも、比較データからテンプレートで整理を返す。"""
    parts: list[str] = []

    parts.append("### それぞれが守ろうとしているもの")
    for p in comparison.members:
        for c in p.top_cards[:2]:
            parts.append(
                f"- **{p.name}** は *{c.emoji}{c.label}* を大切にしています。"
                f"背景では「{c.stress}」を避けたい、"
                f"という願いがあるのかもしれません。"
            )

    parts.append("\n### なぜこのテーマですれ違いやすいか")
    if comparison.divergent:
        for k, names in list(comparison.divergent.items())[:3]:
            c = get_card(k)
            if not c:
                continue
            others = [
                p.name for p in comparison.members if p.name not in names
            ]
            others_txt = "・".join(others) if others else "他のメンバー"
            parts.append(
                f"- *{c.label}* を強く大切にする「{'・'.join(names)}」と、"
                f"そこは上位でない「{others_txt}」とでは、"
                f"同じ場面でも「{c.lean}」の度合いが違い、"
                f"すれ違いとして現れやすくなります。"
            )
    else:
        parts.append(
            "- 上位の価値観は近いようです。それでも、細かな優先順位の差が"
            "具体的な場面で摩擦になることがあります。"
        )

    parts.append("\n### ひとつの見方として")
    if len(comparison.members) >= 2:
        a, b = comparison.members[0], comparison.members[1]
        ca = a.top_cards[0] if a.top_cards else None
        cb = b.top_cards[0] if b.top_cards else None
        if ca and cb:
            parts.append(
                f"{a.name} にとっては「{ca.label}」が、"
                f"{b.name} にとっては「{cb.label}」が、"
                "世界の中心にあるのかもしれません。"
                "どちらかが間違っているのではなく、"
                "大切にしている場所が違うだけ、という見方もできます。"
            )
    if theme.strip():
        parts.append(
            f"\n※ 今回のテーマ「{theme}」も、この価値観の違いが"
            "背景にある可能性があります。"
        )
    parts.append(
        "\n> これは “ひとつの見方” です。答えではありません。"
        "ここから、お互いに聞き合ってみてください。"
    )
    return "\n".join(parts)


# ============================================================
# ② 対話支援：答えではなく「問い」を提案する
# ============================================================
def suggest_dialogue(comparison: Comparison, theme: str = "") -> dict:
    """対話のための問いを提案（答えは出さない）。

    返り値:
        {
          "ask_partner": [相手に聞いてみたいこと, ...],
          "reflect_self": [自分の気持ちを整理する問い, ...],
          "themes":       [一緒に話し合うテーマ, ...],
        }
    """
    if is_available():
        try:
            return _suggest_ai(comparison, theme)
        except Exception:
            pass
    return _suggest_fallback(comparison, theme)


def _suggest_ai(comparison: Comparison, theme: str) -> dict:
    theme_line = f"\n今すれ違っているテーマ：{theme}" if theme.strip() else ""
    user_msg = f"""\
以下は、ある家族の価値観プロファイルです。

{_members_context(comparison)}{theme_line}

この家族が “対話できる状態” になるための「問い」を提案してください。
アドバイスや答えは絶対に出さないでください。問いだけを出します。

次の JSON だけを返してください（前後に文章を付けない）:
{{
  "ask_partner": ["相手に聞いてみたいこと", ...],
  "reflect_self": ["自分の気持ちを整理するための問い", ...],
  "themes": ["二人／家族で話し合うと良さそうなテーマ", ...]
}}

- 各配列 2〜3 個。
- 誰かを責める前提の問いにしない。
- 「なぜ○○しなかったのか」ではなく
  「○○のとき、どんな気持ちだった？」のような、
  背景の価値観に触れられる問いにする。"""

    resp = _get_client().messages.create(
        model=MODEL,
        max_tokens=700,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    text = resp.content[0].text
    data = _extract_json(text)
    if data:
        return {
            "ask_partner": data.get("ask_partner", []),
            "reflect_self": data.get("reflect_self", []),
            "themes": data.get("themes", []),
        }
    return _suggest_fallback(comparison, theme)


def _suggest_fallback(comparison: Comparison, theme: str) -> dict:
    """API 無しでも、違いのある価値観から問いを組み立てる。"""
    ask, reflect, themes = [], [], []

    # 一部だけが大切にしている価値観 → 相手に聞いてみたいこと
    for k, names in list(comparison.divergent.items())[:3]:
        c = get_card(k)
        if not c:
            continue
        holder = names[0]
        ask.append(
            f"{holder} にとって「{c.label}」が大切なのは、"
            "どんな経験からなのか聞いてみる"
        )
        themes.append(
            f"「{c.label}」が脅かされそうな時、どうしてほしいか"
        )

    # 自分の気持ちを整理する問い（誰にでも効く定番）
    reflect.append("今回のことで、自分は本当は何を守りたかった？")
    reflect.append(
        "相手のどんな反応に、いちばん心が動いた？その裏にある"
        "自分の価値観は何だろう？"
    )
    if theme.strip():
        reflect.append(
            f"「{theme}」について、自分が譲れない一点と、"
            "実は譲れる部分はどこ？"
        )

    if not ask:
        ask.append("最近うれしかったこと・安心したことを聞いてみる")
    if not themes:
        themes.append("これからの1年で、家族として大切にしたいこと")
    themes.append("お互いの『これをされると不安になる』リストを見せ合う")

    return {
        "ask_partner": ask[:3],
        "reflect_self": reflect[:3],
        "themes": themes[:3],
    }


# ============================================================
# ユーティリティ
# ============================================================
def _extract_json(text: str) -> dict | None:
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
        return data if isinstance(data, dict) else None
    except Exception:
        return None
