import datetime
from flask import Blueprint, render_template
from database.db import query_all, query_one
from routes.auth import login_required

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
@login_required
def index():
    today = datetime.date.today().isoformat()
    total_students = query_one("SELECT COUNT(*) AS c FROM students")["c"]
    present_today = query_one("SELECT COUNT(DISTINCT student_id) AS c FROM attendance WHERE date = ?", (today,))["c"]
    absent_today = max(total_students - present_today, 0)
    attendance_pct = round((present_today / total_students) * 100, 1) if total_students else 0

    risk_rows = query_all("SELECT risk_level, COUNT(*) AS c FROM latest_predictions GROUP BY risk_level")
    risk_counts = {"Low": 0, "Medium": 0, "High": 0}
    for row in risk_rows:
        risk_counts[row["risk_level"]] = row["c"]

    trend = []
    for i in range(6, -1, -1):
        day = (datetime.date.today() - datetime.timedelta(days=i)).isoformat()
        count = query_one("SELECT COUNT(DISTINCT student_id) AS c FROM attendance WHERE date = ?", (day,))["c"]
        trend.append({"date": day, "count": count})

    at_risk = query_all(
        """SELECT p.student_id, s.name, s.section, p.predicted_score, p.risk_level
           FROM latest_predictions p JOIN students s ON s.student_id = p.student_id
           WHERE p.risk_level IN ('High', 'Medium') ORDER BY p.predicted_score ASC LIMIT 6"""
    )
    from ml import registry
    model_info = registry.get_current_version_info()

    return render_template("dashboard.html", at_risk=at_risk, model_info=model_info, total_students=total_students, present_today=present_today,
                            absent_today=absent_today, attendance_pct=attendance_pct,
                            risk_counts=risk_counts, trend=trend)
