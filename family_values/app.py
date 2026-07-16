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
import storage
import topics
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

# ---------------- 復元キー（家族の識別子）----------------
# ?u=<32桁hex> をブラウザに紐づく家族キーとして扱う。既存 Hub と共通。
try:
    _u = st.query_params.get("u")
except Exception:
    _u = None
current_uid = _u.lower() if (_u and storage.is_valid_hex(_u)) else None

# 永続化が有効か = DB 設定あり かつ 復元キーあり
_persist = storage.is_available() and bool(current_uid)

# ---------------- 状態 ----------------
if "draft_ratings" not in st.session_state:
    st.session_state["draft_ratings"] = default_ratings()

# 復元キーが変わった／初回なら DB からメンバーを読み込む。
# （永続化が無効なときは session_state 内でのみ保持）
if _persist and st.session_state.get("_loaded_uid") != current_uid:
    st.session_state["members"] = storage.load_members(current_uid)
    st.session_state["_loaded_uid"] = current_uid
elif "members" not in st.session_state:
    st.session_state["members"] = []  # list[Profile]

_members = st.session_state["members"]


# ---------------- ヘッダー ----------------
st.markdown("### 🧭 家族の価値観マップ")
st.caption(
    "**一緒に暮らす前後の、二人の価値観のすり合わせに。**"
    "同棲・入籍・出産などの節目に、二人で 30 分。"
    "**どちらが正しいかを決めるツールではありません。**"
)

with st.expander("このアプリの考え方（はじめての方へ）", expanded=False):
    st.markdown(
        "- **暮らし始める前後に**、二人の価値観を前向きにすり合わせるための"
        "共同作業です。衝突してからではなく、その前に。\n"
        "- 価値観に **優劣はありません**。人によって優先順位が違うだけです。\n"
        "- 同じ出来事でも「挑戦しないことが怖い」人と"
        "「リスクを取ることが怖い」人がいて、どちらも自然です。\n"
        "- このアプリの AI は **答えを出さず、ジャッジしません**。"
        "「こういう見方もある」と *視点を増やす* 役割です。\n"
        "- ゴールは「相手は間違っている」ではなく、"
        "**「相手はこういう世界を生きているんだ」** という理解です。\n"
        "- もし今すでにすれ違っていて一人で来た場合は、"
        "「🫱 相手を想像する（ひとり）」から始められます。"
    )
    if not ai_engine.is_available():
        st.info(
            "現在 AI キー未設定のため、AI 分析・対話支援は"
            "**簡易版（ルールベース）** で動作します。"
            "可視化と問いの提案はそのまま使えます。"
        )

st.markdown("---")

st.caption(
    "💡 おすすめの流れ：**二人がそれぞれ「🪞 自分を知る」→「👨‍👩‍👧 家族で見る」で並べる"
    "→ 気になるテーマを「💬 対話支援」で話す**。"
    "相手がまだのときは、一人で「🫱 相手を想像する」から始めても OK です。"
)

tab_diag, tab_solo, tab_family, tab_ai, tab_talk = st.tabs(
    [
        "🪞 自分を知る",
        "🫱 相手を想像する（ひとり）",
        "👨‍👩‍👧 家族で見る",
        "🧭 AI 分析",
        "💬 対話支援",
    ]
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
            saved = storage.save_member(current_uid, prof) if _persist else False
            if saved:
                st.success(
                    f"「{prof.name}」を家族に追加し、**復元キーに保存** しました。"
                    "「👨‍👩‍👧 家族で見る」タブで並べて見られます。"
                )
            else:
                st.success(
                    f"「{prof.name}」を家族に追加しました。"
                    "「👨‍👩‍👧 家族で見る」タブで並べて見られます。"
                )
                if storage.is_available() and not current_uid:
                    st.info(
                        "💡 このままだとリロードで消えます。下の"
                        "「🔑 復元キー」で保存先を作ると、次回も復元できます。"
                    )


# ============================================================
# ①.5 ソロ起点：相手の視点を「仮説として」想像する
# ============================================================
with tab_solo:
    st.markdown("#### 🫱 一人で、相手の視点を想像してみる")
    st.caption(
        "相手がいなくても、ここから始められます。"
        "AI は相手の気持ちを **決めつけません**。"
        "「こうだったのかもしれない」という *仮説* を出し、"
        "最後は **相手に確かめる問い** に変えます。"
    )

    prof_solo = st.session_state.get("current_profile")
    if not prof_solo:
        st.info(
            "先に「🪞 自分を知る」で、あなた自身の価値観を可視化してください。"
            "（相手の登録は要りません）"
        )
    else:
        st.markdown(
            f"あなたが大切にしていること："
            + "／".join(f"{c.emoji}{c.label}" for c in prof_solo.top_cards)
        )
        st.write("")
        situation = st.text_area(
            "すれ違った具体的な状況（任意）",
            key="solo_situation",
            placeholder="例：相談せずに自己投資の契約をして、相手が強く不安がった",
            height=80,
        )
        partner_hint = st.text_input(
            "相手について、思い当たることメモ（任意）",
            key="solo_partner_hint",
            placeholder="例：将来のお金の話にいつも慎重",
        )
        if st.button(
            "🫱 相手の視点を想像してもらう",
            use_container_width=True,
            key="do_solo",
        ):
            with st.spinner("…別の見方を探しています…"):
                st.session_state["solo_result"] = ai_engine.imagine_partner(
                    prof_solo, situation, partner_hint
                )

        res = st.session_state.get("solo_result")
        if res:
            st.markdown("---")
            st.warning(
                "以下は **仮説** です。相手の気持ちの正解ではありません。"
                "本当のところは、相手に聞いてみないとわかりません。",
                icon="🫧",
            )
            if res.get("partner_maybe"):
                st.markdown("**🤔 相手が守ろうとしていた *かもしれない* こと**")
                for q in res["partner_maybe"]:
                    st.markdown(f"- {q}")
            if res.get("why_gap"):
                st.markdown("**🔀 なぜ、すれ違いやすいのか**")
                st.markdown(res["why_gap"])
            if res.get("reflect_self"):
                st.markdown("**🪞 自分の気持ちを整理する問い**")
                for q in res["reflect_self"]:
                    st.markdown(f"- {q}")
            if res.get("ask_partner"):
                st.markdown("**🗣 相手に確かめてみたい問い**")
                for q in res["ask_partner"]:
                    st.markdown(f"- {q}")
            st.write("")
            st.success(
                "手応えがあれば、次は相手にも「🪞 自分を知る」を試してもらい、"
                "「👨‍👩‍👧 家族で見る」で二人ぶんを並べてみてください。",
                icon="🌱",
            )


# ============================================================
# ② 家族共有
# ============================================================
with tab_family:
    st.markdown("#### ② 家族全員の結果を並べる")
    st.caption(
        "一人ずつ「🪞 自分を知る」で作った結果を、ここで並べて見比べます。"
    )

    if not _members:
        st.info(
            "まだ誰も追加されていません。"
            "「🪞 自分を知る」で診断し、「この結果を家族に追加」を押してください。"
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
                    if _persist:
                        storage.delete_member(current_uid, m.name)
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
            "「🪞 自分を知る → 家族に追加」を 2 人ぶん行ってください。"
        )
    else:
        _pick_ai = st.selectbox(
            "テーマを選ぶ（同棲・二人暮らしの定番から）",
            topics.topic_choices(),
            key="ai_topic_pick",
        )
        if topics.topic_hint(_pick_ai):
            st.caption(f"　{topics.topic_hint(_pick_ai)}")
        _custom_ai = st.text_area(
            "自分で書く場合はこちら（任意）",
            key="ai_theme",
            placeholder="例：将来のための自己投資の契約について",
            height=68,
        )
        theme = topics.resolve_theme(_pick_ai, _custom_ai)
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
            "「🪞 自分を知る → 家族に追加」を 2 人ぶん行ってください。"
        )
    else:
        _pick_talk = st.selectbox(
            "話し合いたいテーマ（同棲・二人暮らしの定番から）",
            topics.topic_choices(),
            key="talk_topic_pick",
        )
        if topics.topic_hint(_pick_talk):
            st.caption(f"　{topics.topic_hint(_pick_talk)}")
        _custom_talk = st.text_input(
            "自分で書く場合はこちら（任意）",
            key="talk_theme",
            placeholder="例：これからのお金の使い方",
        )
        theme2 = topics.resolve_theme(_pick_talk, _custom_talk)
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

    # ---- 復元キー（家族の保存先）----
    if storage.is_available():
        with st.expander("🔑 復元キー（家族の保存先）", expanded=(current_uid is None)):
            if current_uid:
                st.caption("現在の復元キー（スクショ等で保管してください）")
                st.code(storage.format_key(current_uid), language=None)
                st.caption(
                    "このページを **ブックマーク** すれば、次回は開くだけで"
                    "同じ家族の記録に戻れます。"
                )
            else:
                st.info(
                    "まだ保存先がありません。キーを入力するか、新規作成すると"
                    "家族の記録が次回も復元できます。"
                )
            st.divider()
            st.caption("別のキーに切り替え")
            _key_in = st.text_input(
                "復元キー",
                label_visibility="collapsed",
                placeholder="XXXX-XXXX-…（32桁）",
                key="key_input",
            )
            if st.button("このキーを使う", use_container_width=True):
                _parsed = storage.parse_key(_key_in)
                if _parsed:
                    st.query_params["u"] = _parsed
                    st.session_state.pop("_loaded_uid", None)
                    st.rerun()
                else:
                    st.error("キーの形式が正しくありません（32桁hex）")
            st.caption("新しい家族の記録を作る")
            if st.button("➕ 新規作成", use_container_width=True):
                import uuid

                st.query_params["u"] = uuid.uuid4().hex
                st.session_state.pop("_loaded_uid", None)
                st.rerun()
    else:
        st.caption(
            "※ この環境ではデータ保存（DB）が未設定のため、"
            "記録はセッション内のみで、リロードで消えます。"
        )

    st.divider()
    st.caption(
        "このアプリは診断でも相性判定でもありません。"
        "“対話の共通言語” をつくるための試作（MVP）です。"
    )
    st.divider()
    # 作業中のスクラッチだけを消す（保存済みの家族はキー配下に残る）
    if st.button("🗑 入力をクリア", use_container_width=True):
        for k in [
            "current_profile",
            "solo_result",
            "ai_result",
            "talk_result",
            "draft_ratings",
        ]:
            st.session_state.pop(k, None)
        st.rerun()
