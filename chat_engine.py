"""Hub のアプリ選びガイド：多ターン対話エンジン。

設計原則:
- 1-3 ターンで推薦に到達する短い対話
- 1 回に 2 つ以上質問しない
- 「本人の言葉が主・AI は案内役」スタンス
- 危機的内容が出たら対話停止＋専門窓口案内
- API 未設定時は graceful degrade（呼び出し側で fallback）
"""
import os
import json
import re
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH, override=False)

api_key = None
try:
    import streamlit as st  # type: ignore
    api_key = st.secrets.get("ANTHROPIC_API_KEY")
except Exception:
    pass
if not api_key:
    api_key = os.getenv("ANTHROPIC_API_KEY")

_client: Anthropic | None = None
MODEL = "claude-haiku-4-5"


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY が未設定です。secrets を確認してください。"
            )
        _client = Anthropic(api_key=api_key)
    return _client


def is_available() -> bool:
    return bool(api_key)


# ============================================================
# 対話用システムプロンプト
# ============================================================
GUIDE_SYSTEM_PROMPT = """\
あなたは「メンタルセルフケア」4 アプリの入口で、ユーザーがどのアプリから
始めると良いかを案内する AI です。

# 立ち位置
- 奥田真太朗（適応障害経験のあるデータサイエンティスト）が作ったツール群
- 「判定しない・並走する」がスタンス
- 押し付けない。「他のもどうぞ」のトーン

# 4 アプリの守備範囲
- 📊 **気分の記録**（mood）: 日々の気分・体調・睡眠・気圧などを記録してパターンを見る
- 💭 **思考の整理ノート**（cbt）: 考えすぎ・反芻思考を AI と整理する。話したい時
- 🗺️ **自分マップ**（selfmap）: 自己理解の整理ツール群
   （言葉にする / 取扱説明書 / 強み / 価値観 / 働き方の条件 / 再発のサイン）
- 🗣 **伝え方ノート**（assertion）: 言えなかった場面の文案を 3 パターン考える

# あなたのタスク
ユーザーから **1-3 ターン** の自然な対話で「今気になっているテーマ」を引き出し、
適切なアプリを案内する準備をする。

# 大事なルール
- **1 回に 2 つ以上質問しない**。短く。
- 返答は **2-4 文以内**。長く書かない
- 「うまく書けなくても、絵文字 1 つでも OK」を冒頭で 1 回伝える
- 「自分なんて」など否定的になっても、そのまま受け止める
- 押し付けない。決めつけない。
- 医療的アドバイス・診断はしない
- **危機的内容**（死にたい・消えたい・自傷の直接表現）が出たら、
  対話を続けずに専門窓口（よりそいホットライン 0120-279-338 等）を
  案内し、アプリの推薦には進まない

# 推薦のタイミング
- ユーザーが 2 回以上書いて、テーマが見えてきたら推薦に進める
- ユーザーが明示的に「推薦して」と言ったら即推薦
- 不明瞭なまま 3 ターン超えたら、「気分の記録」「自分マップ言葉にする」を
  軽い入口として案内（迷ったらここから）

# 推薦時のフォーマット
推薦を返す時は、対話文章の **末尾に必ず**次の JSON コードブロックを
付けてください（マーカーとしてシステム側で抽出します）。
ユーザーには文章のみ見えます。

```json
{
  "main": ["selfmap", "cbt"],
  "also": ["mood"],
  "reason": "短い理由（1-2 文）"
}
```

- main: 1-2 個。最も推奨するアプリの key
- also: 0-2 個。他の候補
- key は mood / cbt / selfmap / assertion のいずれか
- reason: 推薦理由を 1-2 文で（ユーザー向けの言葉）

推薦しない（対話継続）時は、JSON ブロックを **入れない** こと。
"""


# ============================================================
# 推薦判定用キーワード（フェイルセーフ用）
# ============================================================
# AI が JSON を返さなかった時の最終的な fallback
FALLBACK_RECOMMENDATIONS = {
    "main": ["mood", "selfmap"],
    "also": ["cbt"],
    "reason": "迷ったら、気分の記録か自分マップから軽く始めるのがおすすめです。",
}


# ============================================================
# 対話呼び出し
# ============================================================
def chat_turn(messages: list[dict]) -> str:
    """1 ターン応答を返す。

    Args:
        messages: [{"role": "user"/"assistant", "content": "..."}]
    Returns:
        AI の応答テキスト（推薦時は末尾に JSON ブロック含む）
    """
    client = _get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=GUIDE_SYSTEM_PROMPT,
        messages=messages,
    )
    return response.content[0].text


# ============================================================
# 推薦 JSON 抽出
# ============================================================
def extract_recommendation(text: str) -> dict | None:
    """AI 応答から推薦 JSON を抽出。無ければ None。"""
    m = re.search(
        r"```(?:json)?\s*(\{[\s\S]*?\})\s*```",
        text,
        flags=re.DOTALL,
    )
    if not m:
        return None
    try:
        data = json.loads(m.group(1))
        if isinstance(data, dict) and ("main" in data or "also" in data):
            return data
    except Exception:
        pass
    return None


def strip_recommendation_block(text: str) -> str:
    """応答テキストから JSON ブロックを除いた表示用テキストを返す。"""
    cleaned = re.sub(
        r"```(?:json)?\s*\{[\s\S]*?\}\s*```",
        "",
        text,
        flags=re.DOTALL,
    )
    return cleaned.strip()


# ============================================================
# 初期メッセージ（AI 側からの最初の語りかけ）
# ============================================================
OPENING_MESSAGE = (
    "こんにちは。"
    "今、どんな感じですか？\n\n"
    "仕事のしんどさ／思考の整理／体調や気分／自分の整理／"
    "言えなかった場面 など、気になっていることがあれば、"
    "書きたい分だけ教えてください。"
    "**うまく書けなくても、絵文字 1 つでも OK** です。"
)
