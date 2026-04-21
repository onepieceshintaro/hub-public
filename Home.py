import uuid

import streamlit as st

st.set_page_config(
    page_title="メンタルセルフケア",
    page_icon="🌱",
    layout="centered",
)

# ---------------- 復元キー（3アプリ共通のユーザーID） ----------------
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


# URL クエリパラメータから現在のキーを取得
try:
    _u = st.query_params.get("u")
except Exception:
    _u = None
current_uid = _u.lower() if (_u and _is_valid_hex(_u)) else None


# ---------------- ヘッダー ----------------
st.markdown("### 🌱 メンタルセルフケア")

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
    st.caption("新しいキーを作る（新規ユーザーとして開始）")
    if st.button("➕ 新規作成", use_container_width=True):
        new_uid = uuid.uuid4().hex
        st.query_params["u"] = new_uid
        st.rerun()

with st.expander("ℹ️ このツールについて"):
    st.markdown(
        """
        **作者**: 奥田真太朗（適応障害当事者 / データサイエンス系）

        自身のセルフケアで使っているツールを公開しています。
        データは各アプリのブラウザ内ID単位で保存されます。
        """
    )
