import streamlit as st

st.set_page_config(
    page_title="メンタルケア Hub",
    page_icon="🌱",
    layout="centered",
)

st.markdown("### 🌱 メンタルケア Hub")
st.caption("当事者エンジニアが作るセルフヘルプツール集")

st.markdown("---")
st.write("")

CBT_URL = "https://cbt-bot-public-lxcmvrmdys9s3hfg6w2r7l.streamlit.app/"
MOOD_URL = "https://mood-tracker-public-exqvwdkagbgt3gk4mlmu6f.streamlit.app/"
ASSERTION_URL = "https://assertion-bot-public-7yjqhpnvshkdkj7avedrml.streamlit.app/"

st.link_button(
    "🧠  CBT セルフヘルプ",
    CBT_URL,
    use_container_width=True,
)
st.caption("　　認知行動療法のワークを AI と一緒に進める")

st.write("")

st.link_button(
    "📊  気分トラッカー",
    MOOD_URL,
    use_container_width=True,
)
st.caption("　　毎日の気分・体調を記録してグラフで振り返る")

st.write("")

st.link_button(
    "🗣  アサーション練習",
    ASSERTION_URL,
    use_container_width=True,
)
st.caption("　　伝えにくい場面のコミュニケーション練習")

st.markdown("---")

with st.expander("ℹ️ このツールについて"):
    st.markdown(
        """
        **作者**: 奥田真太朗（適応障害当事者 / 異常検知エンジニア）

        自身のセルフケアで使っているツールを公開しています。
        データは各アプリのブラウザ内ID単位で保存されます。
        """
    )
