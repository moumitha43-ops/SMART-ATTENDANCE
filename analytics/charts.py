import io
import os
import sys
import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import query_all, query_one

COLOR_PRIMARY = "#2f5d8c"
COLOR_RISK = {"Low": "#2e7d32", "Medium": "#ef6c00", "High": "#c62828"}
COLOR_PURPLE = "#6a4c93"


def _fig_to_png_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _empty_state_figure(message, figsize=(7, 4)):
    fig, ax = plt.subplots(figsize=figsize)
    ax.axis("off")
    ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=13, color="#666")
    return fig


def attendance_trend_figure(days=7):
    trend = []
    for i in range(days - 1, -1, -1):
        day = (datetime.date.today() - datetime.timedelta(days=i)).isoformat()
        count = query_one("SELECT COUNT(DISTINCT student_id) AS c FROM attendance WHERE date = ?", (day,))["c"]
        trend.append((day, count))
    dates = [d for d, _ in trend]
    counts = [c for _, c in trend]

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(dates, counts, marker="o", color=COLOR_PRIMARY, linewidth=2)
    ax.fill_between(range(len(dates)), counts, alpha=0.15, color=COLOR_PRIMARY)
    ax.set_title(f"Attendance — last {days} days")
    ax.set_ylabel("Students present")
    ax.set_ylim(bottom=0)
    ax.set_xticks(range(len(dates)))
    ax.set_xticklabels(dates, rotation=40, ha="right")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    return fig


def risk_distribution_figure():
    rows = query_all(
"SELECT risk_level, COUNT(*) AS c FROM latest_predictions GROUP BY risk_level"
    )
    counts = {"Low": 0, "Medium": 0, "High": 0}
    for r in rows:
        counts[r["risk_level"]] = r["c"]
    total = sum(counts.values())
    if total == 0:
        return _empty_state_figure("No predictions yet.\nRun Performance Prediction for students first.", figsize=(5, 5))

    labels = [k for k, v in counts.items() if v > 0]
    values = [counts[k] for k in labels]
    colors = [COLOR_RISK[l] for l in labels]

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.pie(values, labels=labels, autopct="%1.0f%%", colors=colors, startangle=90,
           wedgeprops={"edgecolor": "white", "linewidth": 1.5})
    ax.set_title("Student Risk Distribution (latest prediction per student)")
    fig.tight_layout()
    return fig


def attendance_by_subject_figure():
    rows = query_all(
        """SELECT sub.subject_name, COUNT(a.id) AS total
           FROM subjects sub LEFT JOIN attendance a ON a.subject_id = sub.id
           GROUP BY sub.subject_name ORDER BY sub.subject_name"""
    )
    if not rows:
        return _empty_state_figure("No subjects found.", figsize=(8, 4.5))

    names = [r["subject_name"] for r in rows]
    totals = [r["total"] for r in rows]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(names, totals, color=COLOR_PRIMARY)
    ax.set_title("Attendance Sessions Marked per Subject")
    ax.set_ylabel("Sessions marked")
    plt.setp(ax.get_xticklabels(), rotation=40, ha="right")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    return fig


def feature_importance_figure():
    from ml import registry
    info = registry.get_current_version_info()
    if not info:
        return _empty_state_figure("No trained model yet.\nTrain a model under ML Training first.")

    if info.get("feature_importances"):
        items = sorted(info["feature_importances"].items(), key=lambda kv: kv[1])
        labels = [k.replace("_", " ").title() for k, _ in items]
        values = [v * 100 for _, v in items]
        xlabel = "Importance (%)"
        title_prefix = "Feature Importance"
    elif info.get("coefficients"):
        items = sorted(info["coefficients"].items(), key=lambda kv: abs(kv[1]))
        labels = [k.replace("_", " ").title() for k, _ in items]
        values = [v for _, v in items]
        xlabel = "Coefficient (standardized)"
        title_prefix = "Feature Coefficients"
    else:
        return _empty_state_figure("This model type doesn't expose per-feature weights.")

    fig, ax = plt.subplots(figsize=(7, 3.5))
    colors = [COLOR_PURPLE if v >= 0 else "#c62828" for v in values]
    ax.barh(labels, values, color=colors)
    ax.set_xlabel(xlabel)
    ax.axvline(0, color="#333", linewidth=0.8)
    ax.set_title(f"{title_prefix} — {info.get('selected_model', '').replace('_', ' ').title()} ({info['version']})")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    return fig


_CHART_GENERATORS = {
    "attendance_trend": attendance_trend_figure,
    "risk_distribution": risk_distribution_figure,
    "attendance_by_subject": attendance_by_subject_figure,
    "feature_importance": feature_importance_figure,
}


def png_bytes_for(chart_name):
    if chart_name not in _CHART_GENERATORS:
        raise ValueError(f"Unknown chart: {chart_name}")
    return _fig_to_png_bytes(_CHART_GENERATORS[chart_name]())


def _summary_page_figure():
    total_students = query_one("SELECT COUNT(*) AS c FROM students")["c"]
    today = datetime.date.today().isoformat()
    present_today = query_one("SELECT COUNT(DISTINCT student_id) AS c FROM attendance WHERE date = ?", (today,))["c"]
    total_predictions = query_one("SELECT COUNT(*) AS c FROM predictions")["c"]
    total_marks = query_one("SELECT COUNT(*) AS c FROM marks")["c"]

    fig, ax = plt.subplots(figsize=(8.5, 11))
    ax.axis("off")
    lines = [
        "Smart Attendance & Academic Performance Report",
        "",
        f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"Total students: {total_students}",
        f"Present today ({today}): {present_today}",
        f"Total marks entries recorded: {total_marks}",
        f"Total predictions made: {total_predictions}",
        "",
        "Generated directly from the live application database.",
    ]
    ax.text(0.05, 0.95, "\n".join(lines), va="top", ha="left", fontsize=13, family="monospace")
    return fig


def generate_pdf_report():
    buf = io.BytesIO()
    with PdfPages(buf) as pdf:
        pdf.savefig(_summary_page_figure())
        plt.close("all")
        for generator in _CHART_GENERATORS.values():
            fig = generator()
            pdf.savefig(fig)
            plt.close(fig)
    buf.seek(0)
    return buf.getvalue()
