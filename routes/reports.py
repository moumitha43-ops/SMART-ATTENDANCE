import csv, io
from flask import Blueprint, render_template, Response
from database.db import query_all
from routes.auth import login_required
from analytics import charts

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/reports")
@login_required
def reports_page():
    at_risk = query_all(
        """
        SELECT p.student_id, st.name, p.predicted_score, p.risk_level, p.created_at
        FROM latest_predictions p JOIN students st ON p.student_id = st.student_id
        WHERE p.risk_level IN ('High', 'Medium') ORDER BY p.predicted_score ASC
        """
    )
    attendance_by_student = query_all(
        """SELECT st.student_id, st.name, COUNT(a.id) AS sessions_attended
           FROM students st LEFT JOIN attendance a ON a.student_id = st.student_id
           GROUP BY st.student_id, st.name ORDER BY st.name"""
    )
    attendance_by_subject = query_all(
        """SELECT sub.subject_name, COUNT(a.id) AS total_marked
           FROM subjects sub LEFT JOIN attendance a ON a.subject_id = sub.id
           GROUP BY sub.subject_name ORDER BY sub.subject_name"""
    )
    return render_template("reports.html", at_risk=at_risk, attendance_by_student=attendance_by_student,
                            attendance_by_subject=attendance_by_subject)


@reports_bp.route("/reports/at_risk.csv")
@login_required
def export_at_risk_csv():
    rows = query_all(
        """
        SELECT p.student_id, st.name, p.predicted_score, p.risk_level, p.created_at
        FROM latest_predictions p JOIN students st ON p.student_id = st.student_id
        WHERE p.risk_level IN ('High', 'Medium') ORDER BY p.predicted_score ASC
        """
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Student ID", "Name", "Predicted Score", "Risk Level", "Predicted On"])
    for r in rows:
        writer.writerow([r["student_id"], r["name"], r["predicted_score"], r["risk_level"], r["created_at"]])
    return Response(buf.getvalue(), mimetype="text/csv",
                     headers={"Content-Disposition": "attachment; filename=at_risk_students.csv"})


@reports_bp.route("/reports/chart/<chart_name>.png")
@login_required
def chart_png(chart_name):
    try:
        png = charts.png_bytes_for(chart_name)
    except ValueError:
        return "Unknown chart", 404
    return Response(png, mimetype="image/png", headers={"Cache-Control": "no-store"})


@reports_bp.route("/reports/pdf")
@login_required
def download_pdf():
    pdf_bytes = charts.generate_pdf_report()
    return Response(pdf_bytes, mimetype="application/pdf",
                     headers={"Content-Disposition": "attachment; filename=attendance_performance_report.pdf"})
