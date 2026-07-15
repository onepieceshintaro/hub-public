"""家族の価値観を可視化し、対話を支援する AI（MVP）。

構想の MVP を 1 画面に:
  ① 個人診断   … 価値観・強み・ストレスポイント・意思決定傾向を可視化
  ② 家族共有   … 家族全員の結果を並べる
  ③ AI 分析    … 違いを「対話の共通言語」に翻訳する
  ④ 対話支援   … 答えではなく「問い」を提案する

思想:
  診断アプリではない。相性診断でもない。
  “対話の共通言語” をつくり、家族が対話できる状態にするためのツール。
"""
import streamlit as st

import ai_engine
from profile import (
    RATING_MAX,
    RATING_MIN,
    build_profile,
    compare_profiles,
    default_ratings,
)
from value_cards import VALUE_CARDS, get_card

st.set_page_config(
    page_title="家族の価値観マップ",
    page_icon="🧭",
    layout="centered",
)

# ---------------- 状態 ----------------
if "members" not in st.session_state:
    # 保存済みプロファイルのリスト（家族メンバー）
    st.session_state["members"] = []  # list[Profile]
if "draft_ratings" not in st.session_state:
    st.session_state["draft_ratings"] = default_ratings()

_members = st.session_state["members"]


# ---------------- ヘッダー ----------------
st.markdown("### 🧭 家族の価値観マップ")
st.caption(
    "**どちらが正しいかを決めるツールではありません。**"
    "価値観の違いを可視化して、家族が対話できる状態をつくるためのものです。"
)

with st.expander("このアプリの考え方（はじめての方へ）", expanded=False):
    st.markdown(
        "- 価値観に **優劣はありません**。人によって優先順位が違うだけです。\n"
        "- 同じ出来事でも「挑戦しないことが怖い」人と"
        "「リスクを取ることが怖い」人がいて、どちらも自然です。\n"
        "- このアプリの AI は **答えを出さず、ジャッジしません**。"
        "「こういう見方もある」と *視点を増やす* 役割です。\n"
        "- ゴールは「相手は間違っている」ではなく、"
        "**「相手はこういう世界を生きていたんだ」** という理解です。"
    )
    if not ai_engine.is_available():
        st.info(
            "現在 AI キー未設定のため、AI 分析・対話支援は"
            "**簡易版（ルールベース）** で動作します。"
            "可視化と問いの提案はそのまま使えます。"
        )

st.markdown("---")

tab_diag, tab_family, tab_ai, tab_talk = st.tabs(
    ["① 個人診断", "② 家族共有", "③ AI 分析", "④ 対話支援"]
)


# ============================================================
# ① 個人診断
# ============================================================
with tab_diag:
    st.markdown("#### ① あなたの価値観を可視化する")
    st.caption(
        "12 個の価値観カードに、いまの自分にとっての大切さを付けてください。"
        "正解はありません。直感で大丈夫です。"
    )

    name = st.text_input(
        "お名前（ニックネーム可）",
        key="diag_name",
        placeholder="例：しんたろう",
    )

    st.write("")
    ratings = st.session_state["draft_ratings"]
    for card in VALUE_CARDS:
        col_l, col_r = st.columns([3, 2])
        with col_l:
            st.markdown(f"**{card.emoji} {card.label}**")
            st.caption(card.description)
        with col_r:
            ratings[card.key] = st.slider(
                f"{card.label}の大切さ",
                RATING_MIN,
                RATING_MAX,
                ratings.get(card.key, 3),
                key=f"slider_{card.key}",
                label_visibility="collapsed",
            )
    st.session_state["draft_ratings"] = ratings

    st.write("")
    if st.button("🔍 可視化する", use_container_width=True, key="do_diag"):
        st.session_state["current_profile"] = build_profile(name, ratings)

    prof = st.session_state.get("current_profile")
    if prof:
        st.markdown("---")
        st.markdown(f"##### 🪞 {prof.name} のプロファイル")

        st.markdown("**🎯 大切にしている価値観**")
        for c in prof.top_cards:
            st.markdown(f"- {c.emoji} **{c.label}** — {c.description}")

        st.markdown("**💪 発揮されやすい強み**")
        for s in prof.strengths:
            st.markdown(f"- {s}")

        st.markdown("**⚠️ ストレスを感じやすいポイント**")
        for s in prof.stresses:
            st.markdown(f"- {s}")

        st.markdown("**🧭 意思決定の傾向（あくまで傾き）**")
        st.markdown(f"- {prof.decision_label}")

        st.write("")
        if st.button(
            "➕ この結果を家族に追加",
            use_container_width=True,
            key="add_member",
        ):
            # 同名は上書き
            st.session_state["members"] = [
                m for m in _members if m.name != prof.name
            ] + [prof]
            st.success(
                f"「{prof.name}」を家族に追加しました。"
                "「② 家族共有」タブで並べて見られます。"
            )


# ============================================================
# ② 家族共有
# ============================================================
with tab_family:
    st.markdown("#### ② 家族全員の結果を並べる")
    st.caption(
        "一人ずつ「① 個人診断」で作った結果を、ここで並べて見比べます。"
    )

    if not _members:
        st.info(
            "まだ誰も追加されていません。"
            "「① 個人診断」で診断し、「この結果を家族に追加」を押してください。"
        )
    else:
        cols = st.columns(min(len(_members), 3))
        for i, m in enumerate(_members):
            with cols[i % len(cols)]:
                with st.container(border=True):
                    st.markdown(f"**🪞 {m.name}**")
                    for c in m.top_cards:
                        st.markdown(f"{c.emoji} {c.label}")
                    st.caption(f"傾向：{m.decision_label}")

        st.write("")
        st.markdown("**登録メンバー**")
        for m in list(_members):
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(m.summary_line())
            with c2:
                if st.button("削除", key=f"del_{m.name}"):
                    st.session_state["members"] = [
                        x for x in _members if x.name != m.name
                    ]
                    st.rerun()


# ============================================================
# ③ AI 分析
# ============================================================
with tab_ai:
    st.markdown("#### ③ 違いを「対話の共通言語」に翻訳する")
    st.caption(
        "AI は答えを出しません。どちらが正しいかも決めません。"
        "「それぞれが何を守ろうとしているのか」を整理して、"
        "*視点を増やす* だけです。"
    )

    if len(_members) < 2:
        st.info(
            "AI 分析には **2 人以上** の登録が必要です。"
            "「① 個人診断 → 家族に追加」を 2 人ぶん行ってください。"
        )
    else:
        theme = st.text_area(
            "いま、すれ違っている具体的なテーマ（任意）",
            key="ai_theme",
            placeholder="例：将来のための自己投資の契約について",
            height=80,
        )
        if st.button("🧭 AI に整理してもらう", use_container_width=True, key="do_ai"):
            comp = compare_profiles(_members)
            with st.spinner("…違いを言葉にしています…"):
                st.session_state["ai_result"] = ai_engine.analyze(comp, theme)

        if st.session_state.get("ai_result"):
            st.markdown("---")
            st.markdown(st.session_state["ai_result"])
            st.caption(
                "※ これは “ひとつの見方” であって、答えではありません。"
            )


# ============================================================
# ④ 対話支援
# ============================================================
with tab_talk:
    st.markdown("#### ④ 答えではなく「問い」を持ち帰る")
    st.caption(
        "AI はアドバイスをしません。代わりに、"
        "お互いに聞き合うための問いを提案します。"
    )

    if len(_members) < 2:
        st.info(
            "対話支援には **2 人以上** の登録が必要です。"
            "「① 個人診断 → 家族に追加」を 2 人ぶん行ってください。"
        )
    else:
        theme2 = st.text_input(
            "話し合いたいテーマ（任意）",
            key="talk_theme",
            placeholder="例：これからのお金の使い方",
        )
        if st.button("💬 問いを提案してもらう", use_container_width=True, key="do_talk"):
            comp = compare_profiles(_members)
            with st.spinner("…問いを考えています…"):
                st.session_state["talk_result"] = ai_engine.suggest_dialogue(
                    comp, theme2
                )

        res = st.session_state.get("talk_result")
        if res:
            st.markdown("---")
            if res.get("ask_partner"):
                st.markdown("**🗣 相手に聞いてみたいこと**")
                for q in res["ask_partner"]:
                    st.markdown(f"- {q}")
            if res.get("reflect_self"):
                st.markdown("**🪞 自分の気持ちを整理する問い**")
                for q in res["reflect_self"]:
                    st.markdown(f"- {q}")
            if res.get("themes"):
                st.markdown("**🤝 一緒に話し合うテーマ**")
                for q in res["themes"]:
                    st.markdown(f"- {q}")
            st.caption(
                "※ 全部やる必要はありません。"
                "ひとつ持ち帰って、話してみるだけで十分です。"
            )


# ---------------- サイドバー ----------------
with st.sidebar:
    st.markdown("**🧭 家族の価値観マップ**")
    st.caption("価値観を可視化し、対話を支援する AI")
    st.divider()
    st.caption(
        "このアプリは診断でも相性判定でもありません。"
        "“対話の共通言語” をつくるための試作（MVP）です。"
    )
    st.divider()
    if st.button("🗑 データをリセット", use_container_width=True):
        for k in [
            "members",
            "current_profile",
            "ai_result",
            "talk_result",
            "draft_ratings",
        ]:
            st.session_state.pop(k, None)
        st.rerun()
