# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "polars",
#     "altair",
#     "pydantic",
#     "pandas",
# ]
# ///
"""
Dormant Users Analysis

Identify organization members with low or no activity:
- Cross-reference audit logs with org member list
- Analyze Copilot usage patterns
- Identify users who may need follow-up or license reallocation
"""

import marimo


__generated_with = "0.18.4"
app = marimo.App(width="medium")


# ============================================================
# Cell 1: Imports
# ============================================================
@app.cell(hide_code=True)
def _():
    import json
    from datetime import datetime, timedelta, timezone

    import altair as alt
    import marimo as mo
    import polars as pl

    # JST (UTC+9) タイムゾーン
    JST = timezone(timedelta(hours=9))

    return JST, alt, datetime, json, mo, pl, timedelta, timezone


# ============================================================
# Cell 2: Title
# ============================================================
@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 💤 休眠ユーザー分析

    Organization メンバーのアクティビティを分析し、休眠状態のユーザーを特定します。

    **分析対象:**
    - 監査ログ上のアクティビティ
    - GitHub Copilot の利用状況

    **データソース:**
    1. **監査ログ** (JSON/NDJSON) - GitHubのアクティビティログ
    2. **Org Members** (JSON) - 現在のOrganizationメンバーリスト
    3. **Copilot Seats** (JSON) - Copilotシート割り当てデータ（オプション）
    """)


# ============================================================
# Cell 3: File Uploads
# ============================================================
@app.cell(hide_code=True)
def _(mo):
    audit_log_upload = mo.ui.file(
        filetypes=[".json", ".ndjson"],
        multiple=True,
        label="📋 監査ログファイル（複数選択可）",
    )

    members_upload = mo.ui.file(
        filetypes=[".json"],
        multiple=False,
        label="👥 Org Membersファイル（/orgs/{org}/members）",
    )

    copilot_upload = mo.ui.file(
        filetypes=[".json"],
        multiple=True,
        label="🤖 Copilot Seatsファイル（複数Org対応、オプション）",
    )

    mo.vstack(
        [
            mo.md("## 📁 データファイルのアップロード"),
            mo.md("### 必須ファイル"),
            audit_log_upload,
            members_upload,
            mo.md("### オプション"),
            copilot_upload,
        ],
        gap=1,
    )
    return audit_log_upload, copilot_upload, members_upload


# ============================================================
# Cell 4: Parse Audit Logs
# ============================================================
@app.cell(hide_code=True)
def _(JST, audit_log_upload, datetime, json, mo, pl, timezone):
    def parse_audit_log_file(file_info) -> list[dict]:
        """単一の監査ログファイルをパースしてレコードリストを返す"""
        content = file_info.contents.decode("utf-8").strip()

        if file_info.name.endswith(".ndjson") or not content.startswith("["):
            lines = [json.loads(line) for line in content.split("\n") if line.strip()]
        else:
            lines = json.loads(content)

        records = []
        for entry in lines:
            ts = entry.get("@timestamp", entry.get("timestamp"))
            if isinstance(ts, (int, float)):
                if ts > 1e12:
                    dt_jst = datetime.fromtimestamp(ts / 1000, tz=JST)
                else:
                    dt_jst = datetime.fromtimestamp(ts, tz=JST)
            else:
                dt_jst = datetime.fromisoformat(str(ts))
                if dt_jst.tzinfo is None:
                    dt_jst = dt_jst.replace(tzinfo=timezone.utc).astimezone(JST)
                else:
                    dt_jst = dt_jst.astimezone(JST)

            # JSTの日時をnaive datetimeとして保存
            date_jst = dt_jst.replace(tzinfo=None)

            records.append(
                {
                    "date_jst": date_jst,
                    "action": entry.get("action", "unknown"),
                    "actor": entry.get("actor", "unknown"),
                    "org": entry.get("org", "unknown"),
                    "repo": entry.get("repo"),
                    "_source_file": file_info.name,
                }
            )
        return records

    # 監査ログ読み込み
    audit_df = None
    audit_status = mo.md("⏳ 監査ログファイルをアップロードしてください")

    if audit_log_upload.value:
        _all_records = []
        _file_summaries = []

        for _audit_file in audit_log_upload.value:
            _records = parse_audit_log_file(_audit_file)
            _all_records.extend(_records)
            _file_summaries.append(
                f"- `{_audit_file.name}`: {len(_records):,} イベント"
            )

        audit_df = pl.DataFrame(_all_records)
        _files_info = "\n".join(_file_summaries)
        audit_status = mo.md(f"""
✅ **監査ログ: {len(audit_df):,} イベント** ({len(audit_log_upload.value)} ファイル)

{_files_info}
        """)

    audit_status
    return audit_df, audit_status, parse_audit_log_file


# ============================================================
# Cell 5: Parse Org Members
# ============================================================
@app.cell(hide_code=True)
def _(json, members_upload, mo, pl):
    members_df = None
    members_status = mo.md("⏳ Org Membersファイルをアップロードしてください")

    if members_upload.value:
        _content = members_upload.value[0].contents.decode("utf-8").strip()
        _members_data = json.loads(_content)

        # GitHub API形式のメンバーリストをパース
        _member_records = []
        for _member in _members_data:
            _member_records.append(
                {
                    "login": _member.get("login"),
                    "id": _member.get("id"),
                    "type": _member.get("type", "User"),
                    "site_admin": _member.get("site_admin", False),
                }
            )

        members_df = pl.DataFrame(_member_records)
        members_status = mo.md(f"""
✅ **Org Members: {len(members_df):,} メンバー**

- ファイル: `{members_upload.value[0].name}`
        """)

    members_status
    return members_df, members_status


# ============================================================
# Cell 6: Parse Copilot Seats
# ============================================================
@app.cell(hide_code=True)
def _(JST, copilot_upload, datetime, json, mo, pl, timezone):
    def parse_copilot_timestamp(ts_str: str | None) -> datetime | None:
        """ISO形式のタイムスタンプをJSTのnaive datetimeに変換"""
        if not ts_str:
            return None
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        dt_jst = dt.astimezone(JST)
        return dt_jst.replace(tzinfo=None)

    copilot_df = None
    copilot_status = mo.md("ℹ️ Copilot Seatsファイルは未アップロード（オプション）")

    if copilot_upload.value:
        _all_seats = []
        _org_summaries = []

        for _copilot_file in copilot_upload.value:
            _content = _copilot_file.contents.decode("utf-8").strip()
            _data = json.loads(_content)
            _seats = _data.get("seats", [])

            for _seat in _seats:
                _assignee = _seat.get("assignee", {})
                _org = _seat.get("organization", {})
                _all_seats.append(
                    {
                        "login": _assignee.get("login"),
                        "user_id": _assignee.get("id"),
                        "org_name": _org.get("login"),
                        "created_at": parse_copilot_timestamp(_seat.get("created_at")),
                        "last_activity_at": parse_copilot_timestamp(
                            _seat.get("last_activity_at")
                        ),
                        "last_activity_editor": _seat.get("last_activity_editor"),
                        "pending_cancellation_date": _seat.get(
                            "pending_cancellation_date"
                        ),
                    }
                )

            _org_name = (
                _data.get("seats", [{}])[0]
                .get("organization", {})
                .get("login", "unknown")
                if _data.get("seats")
                else "unknown"
            )
            _org_summaries.append(
                f"- `{_copilot_file.name}` ({_org_name}): {len(_seats)} シート"
            )

        if _all_seats:
            copilot_df = pl.DataFrame(_all_seats)

            # 同一ユーザーが複数Orgにいる場合、最新のlast_activity_atを使用
            copilot_df = (
                copilot_df.sort("last_activity_at", descending=True, nulls_last=True)
                .group_by("login")
                .first()
            )

            _orgs_info = "\n".join(_org_summaries)
            copilot_status = mo.md(f"""
✅ **Copilot Seats: {len(copilot_df):,} ユーザー**

{_orgs_info}
            """)

    copilot_status
    return copilot_df, copilot_status, parse_copilot_timestamp


# ============================================================
# Cell 7: Validation Check
# ============================================================
@app.cell(hide_code=True)
def _(audit_df, members_df, mo):
    mo.stop(
        audit_df is None or members_df is None,
        mo.md("""
⚠️ **必須ファイルをアップロードしてください**

- 監査ログファイル（JSON/NDJSON）
- Org Membersファイル（JSON）
        """),
    )


# ============================================================
# Cell 8: Analysis Parameters
# ============================================================
@app.cell(hide_code=True)
def _(mo):
    period_slider = mo.ui.slider(
        start=1,
        stop=12,
        value=3,
        step=1,
        label="分析期間（月）",
        show_value=True,
    )

    threshold_slider = mo.ui.slider(
        start=0,
        stop=50,
        value=5,
        step=1,
        label="休眠判定の閾値（イベント数以下）",
        show_value=True,
    )

    mo.vstack(
        [
            mo.md("## ⚙️ 分析パラメータ"),
            mo.hstack([period_slider, threshold_slider], gap=2),
        ],
        gap=1,
    )
    return period_slider, threshold_slider


# ============================================================
# Cell 9: Calculate User Activity
# ============================================================
@app.cell(hide_code=True)
def _(audit_df, copilot_df, datetime, members_df, period_slider, pl, timedelta):
    # 分析期間の計算
    now = datetime.now()
    period_months = period_slider.value
    period_start = now - timedelta(days=period_months * 30)

    # 現在のOrg Membersのみをフィルタリング
    member_logins = members_df["login"].to_list()

    # Filter audit logs for current org members within the analysis period
    audit_period_df = audit_df.filter(
        (pl.col("date_jst") >= period_start) & (pl.col("actor").is_in(member_logins))
    )

    # ユーザー別アクティビティ集計
    user_activity = (
        audit_period_df.group_by("actor")
        .agg(
            pl.len().alias("audit_event_count"),
            pl.col("date_jst").max().alias("last_audit_activity"),
            pl.col("action").n_unique().alias("unique_actions"),
        )
        .rename({"actor": "login"})
    )

    # Join with all members to include those with no activity
    user_summary = (
        members_df.select(["login", "id", "type"])
        .join(user_activity, on="login", how="left")
        .with_columns(
            pl.col("audit_event_count").fill_null(0),
            pl.col("unique_actions").fill_null(0),
        )
    )

    # Copilotデータがあれば結合
    if copilot_df is not None:
        copilot_summary = copilot_df.select(
            [
                "login",
                "last_activity_at",
                "last_activity_editor",
                "pending_cancellation_date",
            ]
        ).rename({"last_activity_at": "copilot_last_activity"})

        user_summary = user_summary.join(copilot_summary, on="login", how="left")
    else:
        user_summary = user_summary.with_columns(
            pl.lit(None).cast(pl.Datetime).alias("copilot_last_activity"),
            pl.lit(None).cast(pl.Utf8).alias("last_activity_editor"),
            pl.lit(None).cast(pl.Utf8).alias("pending_cancellation_date"),
        )

    # Use most recent activity between audit log and Copilot
    user_summary = user_summary.with_columns(
        pl.max_horizontal("last_audit_activity", "copilot_last_activity").alias(
            "last_activity"
        )
    )

    # 非アクティブ日数を計算
    user_summary = user_summary.with_columns(
        pl.when(pl.col("last_activity").is_not_null())
        .then((pl.lit(now) - pl.col("last_activity")).dt.total_days())
        .otherwise(pl.lit(None))
        .alias("days_inactive")
    )
    return (
        audit_period_df,
        member_logins,
        now,
        period_months,
        period_start,
        user_activity,
        user_summary,
    )


# ============================================================
# Cell 10: Identify Dormant Users
# ============================================================
@app.cell(hide_code=True)
def _(period_months, pl, threshold_slider, user_summary):
    threshold = threshold_slider.value

    # 休眠ユーザーの判定
    dormant_users = user_summary.filter(pl.col("audit_event_count") <= threshold).sort(
        "audit_event_count"
    )

    # カテゴリ分類
    dormant_users = dormant_users.with_columns(
        pl.when(pl.col("audit_event_count") == 0)
        .then(pl.lit("完全休眠"))
        .when(pl.col("audit_event_count") <= threshold // 2)
        .then(pl.lit("低活動"))
        .otherwise(pl.lit("要観察"))
        .alias("status")
    )

    # 統計サマリー
    total_members = user_summary.height
    dormant_count = dormant_users.height
    dormant_ratio = dormant_count / total_members * 100 if total_members > 0 else 0

    complete_dormant = dormant_users.filter(pl.col("status") == "完全休眠").height
    low_activity = dormant_users.filter(pl.col("status") == "低活動").height
    watch_needed = dormant_users.filter(pl.col("status") == "要観察").height

    dormant_stats = {
        "total_members": total_members,
        "dormant_count": dormant_count,
        "dormant_ratio": dormant_ratio,
        "complete_dormant": complete_dormant,
        "low_activity": low_activity,
        "watch_needed": watch_needed,
        "period_months": period_months,
        "threshold": threshold,
    }
    return (
        complete_dormant,
        dormant_count,
        dormant_ratio,
        dormant_stats,
        dormant_users,
        low_activity,
        threshold,
        total_members,
        watch_needed,
    )


# ============================================================
# Cell 11: Summary Statistics
# ============================================================
@app.cell(hide_code=True)
def _(dormant_stats, mo):
    stats = dormant_stats

    summary_md = mo.md(f"""
## 📊 分析結果サマリー

| 項目 | 値 |
|------|-----|
| **分析期間** | 過去 {stats["period_months"]} ヶ月 |
| **休眠判定閾値** | {stats["threshold"]} イベント以下 |
| **総メンバー数** | {stats["total_members"]:,} 人 |
| **休眠ユーザー数** | {stats["dormant_count"]:,} 人 ({stats["dormant_ratio"]:.1f}%) |

### 休眠ユーザー内訳

| ステータス | 人数 | 説明 |
|-----------|------|------|
| 🔴 完全休眠 | {stats["complete_dormant"]} 人 | 期間内アクティビティなし |
| 🟡 低活動 | {stats["low_activity"]} 人 | 閾値の半分以下 |
| 🟢 要観察 | {stats["watch_needed"]} 人 | 閾値以下だが活動あり |
    """)

    summary_md
    return stats, summary_md


# ============================================================
# Cell 12: Dormant Users Table
# ============================================================
@app.cell(hide_code=True)
def _(dormant_users, mo, pl):
    # 表示用にフォーマット
    display_df = dormant_users.select(
        [
            pl.col("login").alias("ユーザー名"),
            pl.col("status").alias("ステータス"),
            pl.col("audit_event_count").alias("監査ログイベント数"),
            pl.col("unique_actions").alias("ユニークアクション数"),
            pl.col("last_audit_activity")
            .dt.strftime("%Y-%m-%d")
            .fill_null("-")
            .alias("最終監査ログ"),
            pl.col("copilot_last_activity")
            .dt.strftime("%Y-%m-%d")
            .fill_null("-")
            .alias("最終Copilot利用"),
            pl.col("last_activity_editor").fill_null("-").alias("エディタ"),
            pl.col("days_inactive")
            .cast(pl.Int64)
            .fill_null(pl.lit("N/A"))
            .cast(pl.Utf8)
            .alias("非アクティブ日数"),
        ]
    )

    mo.vstack(
        [
            mo.md("## 📋 休眠ユーザー一覧"),
            mo.ui.table(display_df.to_dicts(), selection=None),
        ],
        gap=1,
    )
    return (display_df,)


# ============================================================
# Cell 13: Activity Distribution Chart
# ============================================================
@app.cell(hide_code=True)
def _(alt, mo, pl, threshold, user_summary):
    # アクティビティ分布のヒストグラム
    activity_data = user_summary.select(
        [
            pl.col("login"),
            pl.col("audit_event_count"),
            pl.when(pl.col("audit_event_count") <= threshold)
            .then(pl.lit("休眠"))
            .otherwise(pl.lit("アクティブ"))
            .alias("category"),
        ]
    )

    histogram_chart = (
        alt.Chart(alt.Data(values=activity_data.to_dicts()))
        .mark_bar()
        .encode(
            x=alt.X(
                "audit_event_count:Q",
                bin=alt.Bin(maxbins=30),
                title="監査ログイベント数",
            ),
            y=alt.Y("count():Q", title="ユーザー数"),
            color=alt.Color(
                "category:N",
                scale=alt.Scale(
                    domain=["休眠", "アクティブ"],
                    range=["#e74c3c", "#27ae60"],
                ),
                title="ステータス",
            ),
            tooltip=[
                alt.Tooltip("audit_event_count:Q", title="イベント数", bin=True),
                alt.Tooltip("count():Q", title="ユーザー数"),
            ],
        )
        .properties(width=600, height=300, title="ユーザーアクティビティ分布")
    )

    # 閾値ラインを追加
    threshold_rule = (
        alt.Chart(alt.Data(values=[{"threshold": threshold}]))
        .mark_rule(color="red", strokeDash=[5, 5], strokeWidth=2)
        .encode(x=alt.X("threshold:Q"))
    )

    combined_chart = histogram_chart + threshold_rule

    mo.vstack(
        [
            mo.md("## 📈 アクティビティ分布"),
            mo.md(f"赤い点線は休眠判定の閾値（{threshold}イベント）を示します"),
            combined_chart,
        ],
        gap=1,
    )
    return activity_data, combined_chart, histogram_chart, threshold_rule


# ============================================================
# Cell 14: Dormant Users by Status Chart
# ============================================================
@app.cell(hide_code=True)
def _(alt, dormant_users, mo, pl):
    # ステータス別の休眠ユーザー数
    status_counts = (
        dormant_users.group_by("status")
        .agg(pl.len().alias("count"))
        .sort("count", descending=True)
    )

    status_chart = (
        alt.Chart(alt.Data(values=status_counts.to_dicts()))
        .mark_bar()
        .encode(
            x=alt.X("status:N", title="ステータス", sort="-y"),
            y=alt.Y("count:Q", title="ユーザー数"),
            color=alt.Color(
                "status:N",
                scale=alt.Scale(
                    domain=["完全休眠", "低活動", "要観察"],
                    range=["#e74c3c", "#f39c12", "#27ae60"],
                ),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("status:N", title="ステータス"),
                alt.Tooltip("count:Q", title="ユーザー数"),
            ],
        )
        .properties(width=400, height=250, title="休眠ユーザーステータス別分布")
    )

    mo.vstack(
        [
            mo.md("## 📊 ステータス別分布"),
            status_chart,
        ],
        gap=1,
    )
    return status_chart, status_counts


# ============================================================
# Cell 15: Monthly Activity Trend
# ============================================================
@app.cell(hide_code=True)
def _(alt, audit_period_df, dormant_users, mo, pl):
    # 休眠ユーザーのリスト
    dormant_logins = dormant_users["login"].to_list()

    # Monthly activity trend: all users vs dormant users
    monthly_trend = (
        audit_period_df.with_columns(
            pl.col("date_jst").dt.truncate("1mo").alias("month")
        )
        .group_by("month")
        .agg(
            pl.len().alias("total_events"),
            pl.col("actor")
            .filter(pl.col("actor").is_in(dormant_logins))
            .len()
            .alias("dormant_events"),
        )
        .sort("month")
    )

    # 長形式に変換
    trend_long = pl.concat(
        [
            monthly_trend.select(
                pl.col("month"),
                pl.col("total_events").alias("events"),
                pl.lit("全ユーザー").alias("category"),
            ),
            monthly_trend.select(
                pl.col("month"),
                pl.col("dormant_events").alias("events"),
                pl.lit("休眠ユーザー").alias("category"),
            ),
        ]
    )

    trend_chart = (
        alt.Chart(alt.Data(values=trend_long.to_dicts()))
        .mark_line(point=True)
        .encode(
            x=alt.X("month:T", title="月"),
            y=alt.Y("events:Q", title="イベント数"),
            color=alt.Color(
                "category:N",
                scale=alt.Scale(
                    domain=["全ユーザー", "休眠ユーザー"],
                    range=["#3498db", "#e74c3c"],
                ),
                title="カテゴリ",
            ),
            tooltip=[
                alt.Tooltip("month:T", title="月", format="%Y-%m"),
                alt.Tooltip("category:N", title="カテゴリ"),
                alt.Tooltip("events:Q", title="イベント数"),
            ],
        )
        .properties(width=600, height=300, title="月別アクティビティトレンド")
    )

    mo.vstack(
        [
            mo.md("## 📅 月別アクティビティトレンド"),
            trend_chart,
        ],
        gap=1,
    )
    return dormant_logins, monthly_trend, trend_chart, trend_long


# ============================================================
# Cell 16: Copilot Analysis (if available)
# ============================================================
@app.cell(hide_code=True)
def _(alt, copilot_df, dormant_users, mo, pl):
    copilot_analysis = None

    if copilot_df is not None:
        dormant_logins_set = set(dormant_users["login"].to_list())

        # 休眠ユーザーのCopilot利用状況
        dormant_copilot = copilot_df.filter(pl.col("login").is_in(dormant_logins_set))

        if dormant_copilot.height > 0:
            # Copilot利用状況のサマリー
            copilot_active = dormant_copilot.filter(
                pl.col("last_activity_at").is_not_null()
            ).height
            copilot_never_used = dormant_copilot.filter(
                pl.col("last_activity_at").is_null()
            ).height
            copilot_pending = dormant_copilot.filter(
                pl.col("pending_cancellation_date").is_not_null()
            ).height

            # エディタ別利用分布
            editor_dist = (
                dormant_copilot.filter(pl.col("last_activity_editor").is_not_null())
                .group_by("last_activity_editor")
                .agg(pl.len().alias("count"))
                .sort("count", descending=True)
            )

            editor_chart = (
                alt.Chart(alt.Data(values=editor_dist.to_dicts()))
                .mark_bar()
                .encode(
                    x=alt.X("count:Q", title="ユーザー数"),
                    y=alt.Y(
                        "last_activity_editor:N",
                        title="エディタ",
                        sort="-x",
                    ),
                    tooltip=[
                        alt.Tooltip("last_activity_editor:N", title="エディタ"),
                        alt.Tooltip("count:Q", title="ユーザー数"),
                    ],
                )
                .properties(width=500, height=200)
            )

            copilot_analysis = mo.vstack(
                [
                    mo.md("## 🤖 休眠ユーザーのCopilot利用状況"),
                    mo.md(f"""
| 項目 | 値 |
|------|-----|
| Copilotシート保有者 | {dormant_copilot.height} 人 |
| Copilot利用あり | {copilot_active} 人 |
| Copilot未利用 | {copilot_never_used} 人 |
| キャンセル予定 | {copilot_pending} 人 |

**💡 推奨アクション**: Copilotシートを保有しているが監査ログ上で休眠状態のユーザーは、
ライセンスの再割り当て候補となる可能性があります。
                    """),
                    mo.md("### エディタ別利用分布") if editor_dist.height > 0 else None,
                    editor_chart if editor_dist.height > 0 else None,
                ],
                gap=1,
            )
        else:
            copilot_analysis = mo.md("""
## 🤖 休眠ユーザーのCopilot利用状況

休眠ユーザーの中にCopilotシートを保有しているユーザーはいません。
            """)
    else:
        copilot_analysis = mo.md("""
## 🤖 Copilot利用状況

Copilot Seatsデータがアップロードされていないため、分析をスキップします。
        """)

    copilot_analysis
    return (copilot_analysis,)


# ============================================================
# Cell 17: Export Data
# ============================================================
@app.cell(hide_code=True)
def _(dormant_users, mo, pl):
    # CSVエクスポート用データ
    export_df = dormant_users.select(
        [
            pl.col("login"),
            pl.col("status"),
            pl.col("audit_event_count"),
            pl.col("unique_actions"),
            pl.col("last_audit_activity").dt.strftime("%Y-%m-%d").fill_null(""),
            pl.col("copilot_last_activity").dt.strftime("%Y-%m-%d").fill_null(""),
            pl.col("last_activity_editor").fill_null(""),
            pl.col("days_inactive").cast(pl.Int64).fill_null(-1),
        ]
    )

    csv_data = export_df.write_csv()

    download_button = mo.download(
        data=csv_data.encode("utf-8"),
        filename="dormant_users.csv",
        mimetype="text/csv",
        label="📥 休眠ユーザーリストをダウンロード (CSV)",
    )

    mo.vstack(
        [
            mo.md("## 📥 データエクスポート"),
            download_button,
        ],
        gap=1,
    )
    return csv_data, download_button, export_df


if __name__ == "__main__":
    app.run()
