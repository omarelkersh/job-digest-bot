import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape


def build_note(scored_job):
    bits = []
    if scored_job.matched_role:
        bits.append(scored_job.matched_role)
    bits.extend(scored_job.matched_skills[:4])
    note = "Matches: " + ", ".join(bits) if bits else "General skills match"
    return note


def _render_html(market_label, scored_jobs):
    rows = []
    for sj in scored_jobs:
        j = sj.job
        rows.append(
            f"""
            <tr>
              <td style="padding:8px;border-bottom:1px solid #eee;">
                <a href="{escape(j.url)}" style="font-weight:600;text-decoration:none;color:#0b5fff;">
                  {escape(j.title)}
                </a><br>
                <span style="color:#555;">{escape(j.company)} — {escape(j.location)}</span><br>
                <span style="color:#888;font-size:12px;">Posted: {escape(j.date_posted or 'n/a')} · Source: {escape(j.source)} · Score: {sj.score}</span><br>
                <span style="color:#2a8a2a;font-size:13px;">{escape(build_note(sj))}</span>
              </td>
            </tr>"""
        )
    return f"""
    <html><body style="font-family:Arial,sans-serif;">
      <h2>{escape(market_label)} job digest — {len(scored_jobs)} new match(es)</h2>
      <table style="width:100%;border-collapse:collapse;">{''.join(rows)}</table>
    </body></html>
    """


def _render_text(market_label, scored_jobs):
    lines = [f"{market_label} job digest — {len(scored_jobs)} new match(es)", ""]
    for sj in scored_jobs:
        j = sj.job
        lines.append(f"- {j.title} @ {j.company} ({j.location})")
        lines.append(f"  Posted: {j.date_posted or 'n/a'} | Score: {sj.score} | {build_note(sj)}")
        lines.append(f"  {j.url}")
        lines.append("")
    return "\n".join(lines)


def send_digest(smtp_address, smtp_app_password, to_email, subject, market_label, scored_jobs):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_address
    msg["To"] = to_email
    msg.attach(MIMEText(_render_text(market_label, scored_jobs), "plain", "utf-8"))
    msg.attach(MIMEText(_render_html(market_label, scored_jobs), "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(smtp_address, smtp_app_password)
        server.sendmail(smtp_address, [to_email], msg.as_string())
