import io
import os

import anthropic
from flask import Flask, Response, jsonify, request
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (HRFlowable, Paragraph, SimpleDocTemplate,
                                 Spacer, Table, TableStyle)

from _shared import cors_headers, find_job, load_master_cv

app = Flask(__name__)

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")

SYSTEM_PROMPT = """You are tailoring Omar El Kersh's CV for one specific job posting.

HARD RULE — NEVER FABRICATE: you may only select, reorder, and rephrase facts
that already appear in the master CV data you're given (skills, bullets,
coursework, certifications, employers, dates, metrics). Never invent a skill,
tool, employer, metric, duration, or credential that isn't already there.
When in doubt, leave it out rather than guess.

STYLE: plain, direct, concrete language — matching the voice already in
Omar's real CV (e.g. "prevented over 500M EGP in financial losses",
"reduced data ingestion latency"). No AI-tell phrasing: avoid "leverage",
"delve", "robust", "seamless", "cutting-edge", "unlock", "elevate", generic
corporate triads ("innovative, scalable, and efficient"), excessive
em-dashes, hedgy "on one hand / on the other" constructions, or formal
transitions like "furthermore" / "moreover".

WORK TYPE: read the job posting and classify it.
- Werkstudent/Praktikum/part-time/student-job (typically Germany) →
  is_fulltime_role = false. relocation_country can be empty.
- Full-time role anywhere → is_fulltime_role = true, and set
  relocation_country to the job's country (used to build the work
  authorization line — Omar is an Egyptian citizen on a German student
  residence permit and will need visa sponsorship or a work permit for
  full-time employment elsewhere).

STRETCH / CAREER-PIVOT APPLICATIONS: if the job is in a field far from data
engineering/ML (e.g. sales, marketing, ops) — set include_strengths_section
to true and write a short "why this candidate" bullet list grounded ONLY in
real transferable facts from the master CV (e.g. quantified business impact,
McKinsey Forward Program business training, technical/product credibility,
language skills). Do not pretend the candidate has direct experience in the
target field if the master CV doesn't show it.

BULLET/COURSEWORK/CERTIFICATION ORDERING: you are given each experience
entry's bullets, the M.Sc. coursework list, and the certifications list as
zero-indexed arrays. Return arrays of indices selecting/reordering them by
relevance to this specific job — never write new bullet text for these,
only reorder the given indices (you may omit low-relevance certifications,
but keep at least 3)."""

TAILOR_TOOL = {
    "name": "tailor_cv",
    "description": "Tailoring decisions for Omar's CV against one job posting.",
    "input_schema": {
        "type": "object",
        "properties": {
            "subtitle": {
                "type": "string",
                "description": "Header tagline under the name, e.g. 'AI & Machine Learning M.Sc. Student | Data Engineer'. May add an honest framing clause for career-pivot roles.",
            },
            "is_fulltime_role": {"type": "boolean"},
            "relocation_country": {
                "type": "string",
                "description": "Country of the job location, for the full-time work-authorization line. Empty string if not a full-time role.",
            },
            "summary": {
                "type": "string",
                "description": "3-6 sentence professional summary tailored to this job. Must only state facts present in the master CV data.",
            },
            "experience_bullet_order": {
                "type": "array",
                "items": {"type": "array", "items": {"type": "integer"}},
                "description": "One array of 0-based bullet indices per experience entry (same order as the master CV's experience list), selecting/reordering existing bullets only.",
            },
            "coursework_order": {
                "type": "array", "items": {"type": "integer"},
                "description": "0-based indices into the M.Sc. coursework list, reordered by relevance to this job.",
            },
            "certifications_order": {
                "type": "array", "items": {"type": "integer"},
                "description": "0-based indices into the certifications list, reordered by relevance (keep at least 3).",
            },
            "include_strengths_section": {"type": "boolean"},
            "strengths_title": {"type": "string", "description": "e.g. 'STRENGTHS FOR THIS ROLE'. Only used if include_strengths_section is true."},
            "strengths_bullets": {
                "type": "array", "items": {"type": "string"},
                "description": "Only used if include_strengths_section is true. Must be grounded in real facts from the master CV.",
            },
        },
        "required": [
            "subtitle", "is_fulltime_role", "relocation_country", "summary",
            "experience_bullet_order", "coursework_order", "certifications_order",
            "include_strengths_section",
        ],
    },
}


def call_claude(master_cv, job):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    user_prompt = (
        f"JOB POSTING\nTitle: {job.get('title')}\nCompany: {job.get('company')}\n"
        f"Location: {job.get('location')}\nMarket: {job.get('market_label')}\n"
        f"Description:\n{job.get('description', '')}\n\n"
        f"MASTER CV DATA (JSON — the only facts you may draw from):\n{master_cv}\n\n"
        "Call tailor_cv with your tailoring decisions."
    )
    resp = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        tools=[TAILOR_TOOL],
        tool_choice={"type": "tool", "name": "tailor_cv"},
        messages=[{"role": "user", "content": user_prompt}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            return block.input
    raise RuntimeError("Claude did not return a tailor_cv tool call")


BLUE = colors.HexColor("#1F4E79")
DARK = colors.HexColor("#1A1A1A")
GRAY = colors.HexColor("#444444")

STYLES = {
    "name": ParagraphStyle("name", fontName="Helvetica-Bold", fontSize=19, textColor=BLUE, spaceAfter=5),
    "subtitle": ParagraphStyle("subtitle", fontName="Helvetica", fontSize=11.5, textColor=DARK, spaceAfter=4),
    "contact": ParagraphStyle("contact", fontName="Helvetica", fontSize=9, textColor=GRAY, spaceAfter=2, leading=12),
    "italicline": ParagraphStyle("italicline", fontName="Helvetica-Oblique", fontSize=8.7, textColor=GRAY, spaceAfter=1.5, leading=11),
    "heading": ParagraphStyle("heading", fontName="Helvetica-Bold", fontSize=11, textColor=BLUE, spaceBefore=4, spaceAfter=1.5),
    "jobtitle": ParagraphStyle("jobtitle", fontName="Helvetica-Bold", fontSize=10, textColor=DARK),
    "jobdate": ParagraphStyle("jobdate", fontName="Helvetica", fontSize=9, textColor=GRAY, alignment=TA_RIGHT),
    "company": ParagraphStyle("company", fontName="Helvetica-Oblique", fontSize=9.5, textColor=GRAY, spaceAfter=2),
    "bullet": ParagraphStyle("bullet", fontName="Helvetica", fontSize=9, textColor=DARK, leftIndent=12, firstLineIndent=-12, spaceAfter=1.5, leading=11.2),
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=9, textColor=DARK, spaceAfter=2, leading=11.4),
    "skillline": ParagraphStyle("skillline", fontName="Helvetica", fontSize=9, textColor=DARK, spaceAfter=2, leading=11.4),
}


def _hr():
    return HRFlowable(width="100%", thickness=0.9, color=BLUE, spaceAfter=4, spaceBefore=0)


def _section(title):
    return [Paragraph(title, STYLES["heading"]), _hr()]


def _job_row(title, dates):
    t = Table(
        [[Paragraph(title, STYLES["jobtitle"]), Paragraph(dates, STYLES["jobdate"])]],
        colWidths=[108 * mm, 66 * mm],
    )
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    return t


def _bullets(items):
    return [Paragraph("&bull;&nbsp;&nbsp;" + b, STYLES["bullet"]) for b in items]


def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_pdf(master_cv, tailored):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=8, bottomMargin=6,
        title=f"{master_cv['name']} - CV",
    )
    story = []

    story.append(Paragraph(_esc(master_cv["name"]), STYLES["name"]))
    story.append(Paragraph(_esc(tailored.get("subtitle") or master_cv["default_subtitle"]), STYLES["subtitle"]))
    story.append(Paragraph(
        f"{_esc(master_cv['location'])} &nbsp;|&nbsp; {_esc(master_cv['phone'])} &nbsp;|&nbsp; "
        f"{_esc(master_cv['email'])} &nbsp;|&nbsp; {_esc(master_cv['linkedin'])}",
        STYLES["contact"],
    ))
    story.append(Paragraph(_esc(master_cv["availability_line"]), STYLES["italicline"]))

    if tailored.get("is_fulltime_role") and tailored.get("relocation_country"):
        work_auth = master_cv["work_auth_fulltime_template"].format(country=tailored["relocation_country"])
    else:
        work_auth = master_cv["work_auth_werkstudent"]
    story.append(Paragraph(_esc(work_auth), STYLES["italicline"]))
    story.append(Spacer(1, 2))

    story.extend(_section("PROFESSIONAL SUMMARY"))
    story.append(Paragraph(_esc(tailored["summary"]), STYLES["body"]))

    story.extend(_section("EXPERIENCE"))
    bullet_orders = tailored.get("experience_bullet_order") or []
    for idx, exp in enumerate(master_cv["experience"]):
        story.append(_job_row(_esc(exp["title"]), _esc(exp["dates"])))
        story.append(Paragraph(_esc(exp["company"]), STYLES["company"]))
        order = bullet_orders[idx] if idx < len(bullet_orders) and bullet_orders[idx] else range(len(exp["bullets"]))
        chosen = [exp["bullets"][i] for i in order if 0 <= i < len(exp["bullets"])]
        story.extend(_bullets([_esc(b) for b in chosen]))
        story.append(Spacer(1, 2))

    story.extend(_section("EDUCATION"))
    for edu in master_cv["education"]:
        story.append(_job_row(_esc(edu["title"]), _esc(edu["dates"])))
        story.append(Paragraph(_esc(edu["company"]), STYLES["company"]))
        if edu.get("coursework"):
            order = tailored.get("coursework_order") or range(len(edu["coursework"]))
            chosen = [edu["coursework"][i] for i in order if 0 <= i < len(edu["coursework"])]
            story.extend(_bullets(["Relevant coursework: " + _esc(", ".join(chosen)) + "."]))
        if edu.get("bullets"):
            story.extend(_bullets([_esc(b) for b in edu["bullets"]]))
        story.append(Spacer(1, 2))

    if tailored.get("include_strengths_section") and tailored.get("strengths_bullets"):
        story.extend(_section(_esc(tailored.get("strengths_title") or "STRENGTHS FOR THIS ROLE")))
        story.extend(_bullets([_esc(b) for b in tailored["strengths_bullets"]]))

    story.extend(_section("TECHNICAL SKILLS"))
    for category, items in master_cv["skills"].items():
        story.append(Paragraph(f"<b>{_esc(category)}:</b> {_esc(', '.join(items))}", STYLES["skillline"]))

    story.extend(_section("CERTIFICATIONS"))
    cert_order = tailored.get("certifications_order") or range(len(master_cv["certifications"]))
    chosen_certs = [master_cv["certifications"][i] for i in cert_order if 0 <= i < len(master_cv["certifications"])]
    story.extend(_bullets([_esc(c) for c in chosen_certs]))

    story.extend(_section("LANGUAGES"))
    story.append(Paragraph(_esc(master_cv["languages"]), STYLES["body"]))

    doc.build(story)
    buf.seek(0)
    return buf.read()


@app.route("/", defaults={"path": ""}, methods=["POST", "OPTIONS"])
@app.route("/<path:path>", methods=["POST", "OPTIONS"])
def generate_cv(path):
    if request.method == "OPTIONS":
        return ("", 204, cors_headers())

    body = request.get_json(force=True, silent=True) or {}
    job_id = body.get("job_id")
    if not job_id:
        return jsonify({"error": "job_id is required"}), 400, cors_headers()

    job = find_job(job_id)
    if not job:
        return jsonify({"error": f"job {job_id} not found in docs/jobs.json"}), 404, cors_headers()

    try:
        master_cv = load_master_cv()
        tailored = call_claude(master_cv, job)
        pdf_bytes = build_pdf(master_cv, tailored)
    except Exception as exc:  # noqa: BLE001 — surface any failure to the portal, not a blank 500
        return jsonify({"error": str(exc)}), 500, cors_headers()

    filename = "CV_" + "".join(c if c.isalnum() else "_" for c in job.get("company", "job")) + ".pdf"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        **cors_headers(),
    }
    return Response(pdf_bytes, mimetype="application/pdf", headers=headers)
