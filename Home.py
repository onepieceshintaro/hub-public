import uuid
from datetime import datetime
from functools import lru_cache

import streamlit as st
from sqlalchemy import create_engine, text

st.set_page_config(
    page_title="メンタルセルフケア",
    page_icon="🌱",
    layout="centered",
)


# ---------------- ユーティリティ ----------------
def _is_valid_hex(s: str) -> bool:
    if not isinstance(s, str) or len(s) != 32:
        return False
    return all(c in "0123456789abcdef" for c in s.lower())


def _format_key(hex32: str) -> str:
    s = hex32.upper()
    return "-".join(s[i:i + 4] for i in range(0, 32, 4))


def _parse_key(user_input: str) -> str | None:
    s = "".join(c for c in (user_input or "") if c.isalnum()).lower()
    if _is_valid_hex(s):
        return s
    return None


# ---------------- DB（ニックネーム用） ----------------
def _get_db_url() -> str | None:
    try:
        url = st.secrets.get("DATABASE_URL")
        if url:
            return url
    except Exception:
        pass
    return None


def _normalize_url(url: str) -> str:
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://") and "+psycopg2" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


@lru_cache(maxsize=1)
def _get_engine():
    url = _get_db_url()
    if not url:
        return None
    return create_engine(_normalize_url(url), pool_pre_ping=True, future=True)


def get_nickname(uid: str) -> str:
    eng = _get_engine()
    if not eng or not _is_valid_hex(uid):
        return ""
    try:
        with eng.connect() as conn:
            row = conn.execute(
                text("SELECT nickname FROM user_nicknames WHERE user_id = :uid"),
                {"uid": uid},
            ).fetchone()
            return (row[0] if row else "") or ""
    except Exception:
        return ""


def set_nickname(uid: str, nickname: str) -> None:
    eng = _get_engine()
    if not eng or not _is_valid_hex(uid):
        return
    nickname = (nickname or "").strip()
    try:
        with eng.begin() as conn:
            if not nickname:
                conn.execute(
                    text("DELETE FROM user_nicknames WHERE user_id = :uid"),
                    {"uid": uid},
                )
            else:
                conn.execute(
                    text("""
                        INSERT INTO user_nicknames (user_id, nickname, updated_at)
                        VALUES (:uid, :nick, :now)
                        ON CONFLICT (user_id) DO UPDATE
                        SET nickname = EXCLUDED.nickname,
                            updated_at = EXCLUDED.updated_at
                    """),
                    {
                        "uid": uid,
                        "nick": nickname,
                        "now": datetime.now().isoformat(),
                    },
                )
    except Exception:
        pass


# ---------------- 現在のUID取得 ----------------
try:
    _u = st.query_params.get("u")
except Exception:
    _u = None
current_uid = _u.lower() if (_u and _is_valid_hex(_u)) else None


# ---------------- ヘッダー ----------------
st.markdown("### 🌱 メンタルセルフケア")

# 名前を表示（設定済みの時）
if current_uid:
    _nick = get_nickname(current_uid)
    if _nick:
        st.caption(f"👤 {_nick}")

st.markdown("---")

# アプリ URL（ガイドとボタンで共通使用するためここで定義）
CBT_URL = "https://cbt-bot-public-lxcmvrmdys9s3hfg6w2r7l.streamlit.app/"
MOOD_URL = "https://mood-tracker-public-exqvwdkagbgt3gk4mlmu6f.streamlit.app/"
ASSERTION_URL = "https://assertion-bot-public-7yjqhpnvshkdkj7avedrml.streamlit.app/"
SELFMAP_URL = "https://self-map-public-cwdyf34nskswtaw2jwvylp.streamlit.app/"
u_query = f"?u={current_uid}" if current_uid else ""

# ---------------- 🧭 アプリ選びガイド（多ターン対話・初回展開）----------------
# AI チャット形式で「今気になっているテーマ」を 1-3 ターンで引き出し、
# 推薦アプリを返す。API 未設定時は radio fallback。
#
# 初回判定：ニックネーム未設定 = 新規ユーザーと見なす（Hub 初訪問の近似）
_has_nickname = bool(current_uid and get_nickname(current_uid))
_show_guide_state_key = "_show_guide"
if _show_guide_state_key not in st.session_state:
    st.session_state[_show_guide_state_key] = not _has_nickname

# AI チャット利用可否
try:
    import chat_engine
    _CHAT_GUIDE_AVAILABLE = chat_engine.is_available()
except Exception:
    chat_engine = None
    _CHAT_GUIDE_AVAILABLE = False

# アプリ key → 表示名・URL マッピング
_APP_INFO = {
    "mood": ("📊  気分の記録", MOOD_URL),
    "cbt": ("💭  思考の整理ノート", CBT_URL),
    "selfmap": ("🗺️  自分マップ", SELFMAP_URL),
    "assertion": ("🗣  伝え方ノート", ASSERTION_URL),
}

# 上部右寄せの「🧭 ガイド」ボタン（returning users 向け）
if _has_nickname:
    _gcol1, _gcol2 = st.columns([4, 1])
    with _gcol2:
        if st.button(
            "🧭 ガイド",
            use_container_width=True,
            key="open_guide_button",
        ):
            st.session_state[_show_guide_state_key] = True
            st.rerun()

if st.session_state.get(_show_guide_state_key):
    # 推薦マッピング（URL は上で定義した変数を再利用）
    _GUIDE_RECOMMENDATIONS = {
        "💭 仕事のしんどさを言葉にできない": {
            "main": [
                ("🗺️  自分マップ「言葉にする」", SELFMAP_URL),
                ("💭  思考の整理ノート", CBT_URL),
            ],
            "also": [
                ("📊  気分の記録", MOOD_URL),
            ],
            "reason": (
                "「言葉にできない」状態の入口として、自分マップの「**言葉にする**」"
                "セクションが軽くて始めやすいです。"
                "話したい感じなら思考の整理ノート、まず日次記録なら気分の記録から。"
            ),
        },
        "🌀 思考が止まらない・考えすぎる": {
            "main": [("💭  思考の整理ノート", CBT_URL)],
            "also": [("📊  気分の記録", MOOD_URL)],
            "reason": (
                "考えすぎている時は、思考の整理ノートで AI と一緒に「考えを外側から眺める」"
                "のが効きやすいです。並行して気分の記録で日々のパターンを残すのも◯。"
            ),
        },
        "📊 体調や気分の変化が気になる": {
            "main": [("📊  気分の記録", MOOD_URL)],
            "also": [("🗺️  自分マップ「再発のサインリスト」", SELFMAP_URL)],
            "reason": (
                "気分・体調・気圧・睡眠などのパターンを見るなら気分の記録から。"
                "回復期に「サイン」を自分の言葉で書きたいなら自分マップの再発のサインリストも。"
            ),
        },
        "🌱 自分の強み・価値観を整理したい": {
            "main": [("🗺️  自分マップ", SELFMAP_URL)],
            "also": [("💭  思考の整理ノート", CBT_URL)],
            "reason": (
                "自分マップに **取扱説明書 / 強みインベントリ / 価値観カードソート / 働き方の条件** "
                "が揃っています。書く時は AI 対話補助のオプションもあります。"
            ),
        },
        "🗣 言えなかった場面の文案を考えたい": {
            "main": [("🗣  伝え方ノート", ASSERTION_URL)],
            "also": [("💭  思考の整理ノート", CBT_URL)],
            "reason": (
                "言えなかった場面の **3 パターンの文案** を伝え方ノートで考えられます。"
                "「そもそも何を伝えたいか」を整理したい時は思考の整理ノートから。"
            ),
        },
        "🤷 よくわからない・全部気になる": {
            "main": [("📊  気分の記録", MOOD_URL)],
            "also": [
                ("🗺️  自分マップ「言葉にする」", SELFMAP_URL),
                ("💭  思考の整理ノート", CBT_URL),
            ],
            "reason": (
                "迷ったら **気分の記録から** がおすすめ。1 日 30 秒、毎日の入口になります。"
                "並行で自分マップの「言葉にする」を眺めるのも軽い導線です。"
            ),
        },
    }

    with st.container(border=True):
        _c_head1, _c_head2 = st.columns([5, 1])
        with _c_head1:
            st.markdown("### 🧭 アプリ選びに迷ったら")
        with _c_head2:
            if st.button(
                "✕ 閉じる",
                use_container_width=True,
                key="close_guide_button",
            ):
                st.session_state[_show_guide_state_key] = False
                st.session_state.pop("hub_chat_messages", None)
                st.session_state.pop("hub_chat_recommendation", None)
                st.session_state.pop("guide_q1", None)
                st.rerun()

        if _CHAT_GUIDE_AVAILABLE:
            # ============ 多ターン対話モード ============
            st.caption(
                "**短い対話** で、まず試すアプリをご案内します。"
                "**推薦に従う必要はありません** — 他の候補もどうぞのスタンスです。"
                "話したくない時は下の「💬 選んで決める」を押せます。"
            )

            _hub_mkey = "hub_chat_messages"
            if _hub_mkey not in st.session_state:
                st.session_state[_hub_mkey] = []

            # オープニング AI メッセージ
            with st.chat_message("assistant"):
                st.markdown(chat_engine.OPENING_MESSAGE)

            # 過去の会話
            for _msg in st.session_state[_hub_mkey]:
                with st.chat_message(_msg["role"]):
                    _disp = (
                        chat_engine.strip_recommendation_block(_msg["content"])
                        if _msg["role"] == "assistant"
                        else _msg["content"]
                    )
                    st.markdown(_disp)

            # ユーザー入力
            _user_input = st.chat_input(
                "ここに書いてください（書きたい分だけで OK）",
                key="hub_chat_input",
            )
            if _user_input:
                st.session_state[_hub_mkey].append(
                    {"role": "user", "content": _user_input}
                )
                try:
                    with st.spinner("…考えています…"):
                        _ai_reply = chat_engine.chat_turn(
                            st.session_state[_hub_mkey]
                        )
                    st.session_state[_hub_mkey].append(
                        {"role": "assistant", "content": _ai_reply}
                    )
                    # 推薦が含まれていれば抽出
                    _rec = chat_engine.extract_recommendation(_ai_reply)
                    if _rec:
                        st.session_state["hub_chat_recommendation"] = _rec
                    st.rerun()
                except Exception as _e:
                    st.warning(f"AI 応答失敗：{_e}")
                    st.session_state[_hub_mkey].pop()

            # ボタン群（2 ターン以上書いた時に「おすすめを聞く」を表示）
            _user_turns = sum(
                1 for m in st.session_state[_hub_mkey]
                if m["role"] == "user"
            )
            _has_rec = st.session_state.get("hub_chat_recommendation")

            if _user_turns >= 1 and not _has_rec:
                if st.button(
                    "🎯 ここまでの話でおすすめを聞く",
                    use_container_width=True,
                    key="hub_chat_ask_rec",
                ):
                    # 推薦リクエストを送信
                    st.session_state[_hub_mkey].append(
                        {"role": "user", "content": "ここまでの話でおすすめを教えてください。"}
                    )
                    try:
                        with st.spinner("…おすすめを考えています…"):
                            _ai_reply = chat_engine.chat_turn(
                                st.session_state[_hub_mkey]
                            )
                        st.session_state[_hub_mkey].append(
                            {"role": "assistant", "content": _ai_reply}
                        )
                        _rec = chat_engine.extract_recommendation(_ai_reply)
                        if _rec:
                            st.session_state["hub_chat_recommendation"] = _rec
                        st.rerun()
                    except Exception as _e:
                        st.warning(f"AI 応答失敗：{_e}")
                        st.session_state[_hub_mkey].pop()

            # 推薦表示
            if _has_rec:
                _rec = st.session_state["hub_chat_recommendation"]
                st.markdown("---")
                if _rec.get("reason"):
                    st.markdown(f"💡 {_rec['reason']}")
                    st.write("")
                _main_keys = _rec.get("main") or []
                _also_keys = _rec.get("also") or []
                if _main_keys:
                    st.markdown("**🎯 まず試してみる**")
                    for _k in _main_keys:
                        if _k in _APP_INFO:
                            _name, _url = _APP_INFO[_k]
                            st.link_button(
                                _name, _url + u_query,
                                use_container_width=True,
                            )
                if _also_keys:
                    st.write("")
                    st.markdown("**🌱 もしくはこちらもどうぞ**")
                    for _k in _also_keys:
                        if _k in _APP_INFO:
                            _name, _url = _APP_INFO[_k]
                            st.link_button(
                                _name, _url + u_query,
                                use_container_width=True,
                            )

            # 補助ボタン
            _hb1, _hb2 = st.columns(2)
            with _hb1:
                if st.button(
                    "🗑️ チャットをリセット",
                    use_container_width=True,
                    key="hub_chat_reset",
                ):
                    st.session_state[_hub_mkey] = []
                    st.session_state.pop("hub_chat_recommendation", None)
                    st.rerun()
            with _hb2:
                if st.button(
                    "💬 選んで決める（対話なし）",
                    use_container_width=True,
                    key="hub_use_radio",
                ):
                    st.session_state["use_radio_fallback"] = True
                    st.rerun()

            # radio fallback への切替
            if st.session_state.get("use_radio_fallback"):
                st.markdown("---")
                st.caption("対話を使わずに 1 つの質問で選びます。")
                _q1 = st.radio(
                    "今、一番気になるのはどこですか？",
                    list(_GUIDE_RECOMMENDATIONS.keys()),
                    index=None,
                    key="guide_q1",
                )
                if _q1 and _q1 in _GUIDE_RECOMMENDATIONS:
                    _rec_radio = _GUIDE_RECOMMENDATIONS[_q1]
                    st.markdown(f"💡 {_rec_radio['reason']}")
                    st.write("")
                    st.markdown("**🎯 まず試してみる**")
                    for _name, _url in _rec_radio["main"]:
                        st.link_button(
                            _name, _url + u_query,
                            use_container_width=True,
                        )
                    if _rec_radio.get("also"):
                        st.write("")
                        st.markdown("**🌱 もしくはこちらもどうぞ**")
                        for _name, _url in _rec_radio["also"]:
                            st.link_button(
                                _name, _url + u_query,
                                use_container_width=True,
                            )

        else:
            # ============ Fallback: radio モード（API 未設定時）============
            st.caption(
                "1 つの質問で、**まず試すアプリ**をご案内します。"
                "推薦に従う必要はありません — **他の候補もどうぞ**のスタンスです。"
            )

            _q1 = st.radio(
                "今、一番気になるのはどこですか？",
                list(_GUIDE_RECOMMENDATIONS.keys()),
                index=None,
                key="guide_q1",
            )

            if _q1 and _q1 in _GUIDE_RECOMMENDATIONS:
                _rec = _GUIDE_RECOMMENDATIONS[_q1]
                st.markdown("---")
                st.markdown(f"💡 {_rec['reason']}")
                st.write("")
                st.markdown("**🎯 まず試してみる**")
                for _name, _url in _rec["main"]:
                    st.link_button(
                        _name, _url + u_query, use_container_width=True,
                    )
                if _rec.get("also"):
                    st.write("")
                    st.markdown("**🌱 もしくはこちらもどうぞ**")
                    for _name, _url in _rec["also"]:
                        st.link_button(
                            _name, _url + u_query, use_container_width=True,
                        )

    st.write("")

# ---------------- 5 フェーズ俯瞰（expander・初見の人向け）----------------
with st.expander("🗺️ 5 フェーズの全体像", expanded=False):
    st.caption(
        "「仕事のしんどさ」は、人によって今どこにいるかが違います。"
        "5 段階の流れで眺めると、自分の今と次の一歩が見えやすくなります。"
    )
    st.markdown(
        "1. **🌱 気づき** — 何がつらいのか言葉にする段階\n"
        "2. **🧭 整理** — 症状・状況を整理して、次の判断をする段階\n"
        "3. **🛌 回復** — 休むことに罪悪感を持たずに過ごす段階\n"
        "4. **🔍 再選択** — 自分に合う働き方を考え直す段階\n"
        "5. **🚪 分岐** — 具体的な次の一歩を選ぶ段階"
    )
    st.caption(
        "**判定ではなく並走するスタンス**。順番通りに進むとも限らず、"
        "行ったり来たりしながら、自分のペースで。"
    )
    st.caption(
        "**Phase 2 はアプリで扱いません**（医療機関・公的相談窓口に繋ぐ範囲）。"
        "緊急時の窓口は各アプリ内（CRISIS_RESPONSE）に案内があります。"
    )

st.write("")

# (URL と u_query はガイドブロック上部で定義済)

st.link_button(
    "📊  気分の記録",
    MOOD_URL + u_query,
    use_container_width=True,
)
st.caption("　　1 日の終わりに、気分を記録する")

st.write("")

st.link_button(
    "💭  思考の整理ノート",
    CBT_URL + u_query,
    use_container_width=True,
)
st.caption("　　考えすぎてしまう時に、AI と整える")

st.write("")

st.link_button(
    "🗺️  自分マップ",
    SELFMAP_URL + u_query,
    use_container_width=True,
)
st.caption("　　自己理解を整理する（取扱説明書・働き方・強み・価値観）")

st.write("")

st.link_button(
    "🗣  伝え方ノート",
    ASSERTION_URL + u_query,
    use_container_width=True,
)
st.caption("　　言えなかった場面の文案を考える")

st.markdown("---")

# ---------------- 各フェーズで使う機能 マトリクス（常時表示）----------------
st.markdown("##### 📍 各フェーズで使う機能")
st.markdown(
    "| フェーズ | 主に使うアプリ・機能 |\n"
    "|---|---|\n"
    "| 🌱 **1. 気づき** | 📊 気分の記録 ／ 💭 思考の整理ノート ／ 🗺️ 自分マップ「言葉にする」 |\n"
    "| 🧭 **2. 整理** | アプリで扱わず、**医療機関・公的相談窓口**に繋ぐ |\n"
    "| 🛌 **3. 回復** | 📊 気分の記録（生活リズム）／ 💭 思考の整理ノート ／ 🗺️ 自分マップ「再発のサインリスト」|\n"
    "| 🔍 **4. 再選択** | 🗺️ 自分マップ（取扱説明書・働き方条件・強み・価値観）／ 🗣 伝え方ノート |\n"
    "| 🚪 **5. 分岐** | （準備中） |"
)

st.markdown("---")

# ---------------- 名前設定 ----------------
if current_uid:
    _nick_current = get_nickname(current_uid)
    _label = _nick_current if _nick_current else "名前未設定"
    with st.expander(f"👤 {_label}", expanded=False):
        st.caption("名前（任意・3アプリで共有）")
        new_nick = st.text_input(
            "名前",
            value=_nick_current,
            label_visibility="collapsed",
            placeholder="例：しんたろう",
            key="nick_input_hub",
        )
        if new_nick != _nick_current:
            set_nickname(current_uid, new_nick)
            st.success("保存しました。")
            st.rerun()

# ---------------- 復元キー設定 ----------------
with st.expander("🔑 復元キー（3アプリ共通）", expanded=(current_uid is None)):
    if current_uid:
        st.caption("現在の復元キー（スクショ等で保管してください）")
        st.code(_format_key(current_uid), language=None)
        st.info(
            "💡 このページを**ブックマーク**すれば、次回は開くだけで"
            "同じキーで3アプリにアクセスできます。"
        )
    else:
        st.info(
            "まだキーが設定されていません。既存のキーを入力するか、"
            "新規作成してください。"
        )

    st.markdown("---")
    st.caption("別のキーに切り替え")
    key_input = st.text_input(
        "復元キー",
        label_visibility="collapsed",
        placeholder="XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX",
    )
    if st.button("このキーを使う", use_container_width=True):
        parsed = _parse_key(key_input)
        if parsed:
            st.query_params["u"] = parsed
            st.rerun()
        else:
            st.error("キーの形式が正しくありません（32文字のhex）")

    st.write("")
    st.caption("新しいキーを作る(新規ユーザーとして開始)")
    if st.button("➕ 新規作成", use_container_width=True):
        new_uid = uuid.uuid4().hex
        st.query_params["u"] = new_uid
        st.rerun()

with st.expander("ℹ️ このツールについて"):
    st.markdown(
        """
        **作者**: 奥田真太朗(適応障害当事者)

        自身のセルフケアで使っているツールを公開しています。
        データは各アプリのブラウザ内ID単位で保存されます。
        """
    )

# ---------------- サイドバー（ご意見・感想・補足）----------------
# 4 アプリの sidebar とトーンを揃える。メインフローを軽くする。
with st.sidebar:
    st.markdown("**🌱 メンタルセルフケア**")
    st.caption("4 アプリ共通の入口（Hub）")
    st.divider()
    st.link_button(
        "💬 ご意見・感想",
        "https://docs.google.com/forms/d/e/1FAIpQLSetCb_dHG6JFsUzhK9ZYxydgh5cP8w07Q6NRO4ouEM7BvSTRw/viewform",
        use_container_width=True,
    )
