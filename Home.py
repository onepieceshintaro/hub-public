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
st.write("")

CBT_URL = "https://cbt-bot-public-lxcmvrmdys9s3hfg6w2r7l.streamlit.app/"
MOOD_URL = "https://mood-tracker-public-exqvwdkagbgt3gk4mlmu6f.streamlit.app/"
ASSERTION_URL = "https://assertion-bot-public-7yjqhpnvshkdkj7avedrml.streamlit.app/"

# キーが設定されていれば各アプリURLに付与
u_query = f"?u={current_uid}" if current_uid else ""

st.link_button(
    "💭  CBT セルフヘルプ",
    CBT_URL + u_query,
    use_container_width=True,
)
st.caption("　　認知行動療法のワークを AI と一緒に進める")

st.write("")

st.link_button(
    "📊  気分トラッカー",
    MOOD_URL + u_query,
    use_container_width=True,
)
st.caption("　　毎日の気分・体調を記録してグラフで振り返る")

st.write("")

st.link_button(
    "🗣  アサーション練習",
    ASSERTION_URL + u_query,
    use_container_width=True,
)
st.caption("　　伝えにくい場面のコミュニケーション練習")

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
        **作者**: 奥田真太朗(適応障害当事者 / データサイエンス系)

        自身のセルフケアで使っているツールを公開しています。
        データは各アプリのブラウザ内ID単位で保存されます。
        """
    )
