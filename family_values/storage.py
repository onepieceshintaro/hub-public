"""永続化層：家族の価値観プロファイルを保存／復元する。

既存 Hub（Home.py）と同じ思想:
- ログイン不要。ブラウザに紐づく「復元キー」（32桁hex）が家族の識別子。
- 家族 = 1 つの復元キー。その下に各メンバーの行がぶら下がる。
- DB(DATABASE_URL) 未設定でも動く（呼び出し側がセッションのみで動作）。

保存するのは name と ratings（12 カードの 1-5）だけ。
強み・ストレス・意思決定傾向は ratings から再計算できるため持たない。
"""
from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache

from profile import Profile, build_profile

TABLE = "family_value_profiles"


# ---------------- 復元キー（Home.py と同じ形式）----------------
def is_valid_hex(s: str) -> bool:
    if not isinstance(s, str) or len(s) != 32:
        return False
    return all(c in "0123456789abcdef" for c in s.lower())


def format_key(hex32: str) -> str:
    s = hex32.upper()
    return "-".join(s[i:i + 4] for i in range(0, 32, 4))


def parse_key(user_input: str) -> str | None:
    s = "".join(c for c in (user_input or "") if c.isalnum()).lower()
    return s if is_valid_hex(s) else None


# ---------------- DB 接続 ----------------
def _get_db_url() -> str | None:
    try:
        import streamlit as st  # type: ignore

        url = st.secrets.get("DATABASE_URL")
        if url:
            return url
    except Exception:
        pass
    import os

    return os.getenv("DATABASE_URL")


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
    from sqlalchemy import create_engine

    eng = create_engine(_normalize_url(url), pool_pre_ping=True, future=True)
    _ensure_table(eng)
    return eng


def _ensure_table(eng) -> None:
    """テーブルが無ければ作る（冪等）。手動マイグレーション不要。"""
    from sqlalchemy import text

    try:
        with eng.begin() as conn:
            conn.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS {TABLE} (
                        user_id     VARCHAR(32) NOT NULL,
                        member_name TEXT        NOT NULL,
                        ratings     JSONB       NOT NULL,
                        updated_at  TIMESTAMP   NOT NULL,
                        PRIMARY KEY (user_id, member_name)
                    )
                    """
                )
            )
    except Exception:
        pass


def is_available() -> bool:
    """DB が使えるか（＝永続化できるか）。"""
    return _get_engine() is not None


# ---------------- 読み書き ----------------
def load_members(uid: str) -> list[Profile]:
    """復元キー配下の全メンバーを Profile として復元。"""
    eng = _get_engine()
    if not eng or not is_valid_hex(uid):
        return []
    from sqlalchemy import text

    try:
        with eng.connect() as conn:
            rows = conn.execute(
                text(
                    f"SELECT member_name, ratings FROM {TABLE} "
                    f"WHERE user_id = :uid ORDER BY updated_at"
                ),
                {"uid": uid},
            ).fetchall()
    except Exception:
        return []

    members: list[Profile] = []
    for name, ratings in rows:
        if isinstance(ratings, str):
            try:
                ratings = json.loads(ratings)
            except Exception:
                ratings = {}
        members.append(build_profile(name, ratings or {}))
    return members


def save_member(uid: str, profile: Profile) -> bool:
    """メンバーを保存（同名は上書き）。成功で True。"""
    eng = _get_engine()
    if not eng or not is_valid_hex(uid):
        return False
    from sqlalchemy import text

    try:
        with eng.begin() as conn:
            conn.execute(
                text(
                    f"""
                    INSERT INTO {TABLE}
                        (user_id, member_name, ratings, updated_at)
                    VALUES
                        (:uid, :name, CAST(:ratings AS JSONB), :now)
                    ON CONFLICT (user_id, member_name) DO UPDATE
                    SET ratings = EXCLUDED.ratings,
                        updated_at = EXCLUDED.updated_at
                    """
                ),
                {
                    "uid": uid,
                    "name": profile.name,
                    "ratings": json.dumps(profile.ratings),
                    "now": datetime.now().isoformat(),
                },
            )
        return True
    except Exception:
        return False


def delete_member(uid: str, name: str) -> bool:
    eng = _get_engine()
    if not eng or not is_valid_hex(uid):
        return False
    from sqlalchemy import text

    try:
        with eng.begin() as conn:
            conn.execute(
                text(
                    f"DELETE FROM {TABLE} "
                    f"WHERE user_id = :uid AND member_name = :name"
                ),
                {"uid": uid, "name": name},
            )
        return True
    except Exception:
        return False
