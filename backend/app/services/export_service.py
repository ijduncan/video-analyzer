import csv
import io
import json

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def export_json(job) -> str:
    data = {
        "filename": job.filename,
        "flash_analysis": job.flash_result,
        "deep_analysis": job.deep_results,
        "summary": job.summary,
        "cost_estimate": job.cost_estimate,
    }
    return json.dumps(data, indent=2)


def export_csv(job) -> str:
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Scene", "Scene Title", "Shot", "Start", "End",
        "Shot Type", "Camera Movement", "Visual Description",
        "Audio Notes", "Subjects", "Dominant Colors", "Mood",
    ])

    if job.flash_result and "scenes" in job.flash_result:
        for scene in job.flash_result["scenes"]:
            for shot in scene.get("shots", []):
                writer.writerow([
                    scene.get("scene_number", ""),
                    scene.get("scene_title", ""),
                    shot.get("shot_number", ""),
                    shot.get("start_time", ""),
                    shot.get("end_time", ""),
                    shot.get("shot_type", ""),
                    shot.get("camera_movement", ""),
                    shot.get("visual_description", ""),
                    shot.get("audio_notes", ""),
                    "; ".join(shot.get("subjects", [])),
                    "; ".join(shot.get("dominant_colors", [])),
                    shot.get("mood", ""),
                ])

    return output.getvalue()


def export_markdown(job) -> str:
    lines = [f"# Video Analysis: {job.filename}\n"]

    if job.summary:
        lines.append("## Summary\n")
        lines.append(f"{job.summary.get('executive_summary', '')}\n")
        lines.append(f"- **Genre:** {job.summary.get('genre_category', '')}")
        lines.append(f"- **Production Value:** {job.summary.get('production_value', '')}")
        lines.append(f"- **Target Audience:** {job.summary.get('target_audience', '')}")
        lines.append(f"- **Visual Style:** {job.summary.get('visual_style', '')}\n")

    if job.flash_result and "scenes" in job.flash_result:
        lines.append("## Scene Breakdown\n")
        for scene in job.flash_result["scenes"]:
            lines.append(f"### Scene {scene['scene_number']}: {scene.get('scene_title', '')}")
            lines.append(f"*{scene.get('start_time', '')} - {scene.get('end_time', '')}*\n")
            lines.append(f"{scene.get('scene_description', '')}\n")

            for shot in scene.get("shots", []):
                lines.append(
                    f"- **Shot {shot['shot_number']}** ({shot.get('start_time', '')}-{shot.get('end_time', '')}): "
                    f"{shot.get('shot_type', '')} | {shot.get('camera_movement', '')} — "
                    f"{shot.get('visual_description', '')}"
                )
            lines.append("")

    if job.deep_results:
        lines.append("## Deep Analysis\n")
        for deep in job.deep_results:
            lines.append(f"### Scene {deep.get('scene_number', '')}\n")
            va = deep.get("visual_analysis", {})
            if va:
                lines.append("**Visual Analysis:**")
                for key, val in va.items():
                    if val:
                        lines.append(f"- {key.replace('_', ' ').title()}: {val}")
                lines.append("")

            aa = deep.get("audio_analysis", {})
            if aa:
                lines.append("**Audio Analysis:**")
                for key, val in aa.items():
                    if val:
                        lines.append(f"- {key.replace('_', ' ').title()}: {val}")
                lines.append("")

    return "\n".join(lines)


def _time_to_timecode(time_str: str, fps: int = 24) -> str:
    """Convert MM:SS to HH:MM:SS:FF timecode."""
    parts = time_str.split(":")
    if len(parts) == 2:
        mins, secs = int(parts[0]), int(parts[1])
        hours = mins // 60
        mins = mins % 60
    elif len(parts) == 3:
        hours, mins, secs = int(parts[0]), int(parts[1]), int(parts[2])
    else:
        hours, mins, secs = 0, 0, 0
    return f"{hours:02d}:{mins:02d}:{secs:02d}:00"


def _time_to_seconds(time_str: str) -> int:
    parts = time_str.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0


def _xml_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def export_edl(job) -> str:
    """Export as CMX 3600 EDL format."""
    lines = [
        f"TITLE: {job.filename}",
        "FCM: NON-DROP FRAME",
        "",
    ]
    event_num = 1
    if job.flash_result and "scenes" in job.flash_result:
        for scene in job.flash_result["scenes"]:
            for shot in scene.get("shots", []):
                src_in = _time_to_timecode(shot.get("start_time", "0:00"))
                src_out = _time_to_timecode(shot.get("end_time", "0:00"))
                lines.append(
                    f"{event_num:03d}  AX       V     C        "
                    f"{src_in} {src_out} {src_in} {src_out}"
                )
                lines.append(f"* SHOT TYPE: {shot.get('shot_type', '')}")
                lines.append(f"* CAMERA: {shot.get('camera_movement', '')}")
                lines.append(f"* FROM CLIP NAME: Scene {scene.get('scene_number', '')} - {scene.get('scene_title', '')}")
                desc = shot.get("visual_description", "")
                if desc:
                    lines.append(f"* COMMENT: {desc[:120]}")
                lines.append("")
                event_num += 1
    return "\n".join(lines)


def export_fcpxml(job) -> str:
    """Export as Final Cut Pro XML (FCPXML v1.11)."""
    filename = _xml_escape(job.filename or "Untitled")
    clips = []
    offset = 0
    if job.flash_result and "scenes" in job.flash_result:
        for scene in job.flash_result["scenes"]:
            for shot in scene.get("shots", []):
                start_s = _time_to_seconds(shot.get("start_time", "0:00"))
                end_s = _time_to_seconds(shot.get("end_time", "0:00"))
                dur = max(end_s - start_s, 1)
                name = _xml_escape(f"S{scene.get('scene_number','')}_Shot{shot.get('shot_number','')}")
                note = _xml_escape(f"{shot.get('shot_type','')} | {shot.get('camera_movement','')} — {shot.get('visual_description','')}")
                clips.append(
                    f'                        <clip name="{name}" offset="{offset * 24}/24s" '
                    f'duration="{dur * 24}/24s" start="{start_s * 24}/24s">\n'
                    f'                            <note>{note}</note>\n'
                    f'                        </clip>'
                )
                offset += dur
    total_dur = max(offset, 1)
    clips_str = "\n".join(clips)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.11">
    <resources>
        <format id="r1" frameDuration="1/24s" width="1920" height="1080"/>
    </resources>
    <library>
        <event name="{filename} Analysis">
            <project name="{filename} Shot List">
                <sequence format="r1" duration="{total_dur * 24}/24s">
                    <spine>
{clips_str}
                    </spine>
                </sequence>
            </project>
        </event>
    </library>
</fcpxml>"""


def export_pdf(job) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle(
        "CustomTitle", parent=styles["Title"], fontSize=18, spaceAfter=20
    )
    story.append(Paragraph(f"Video Analysis: {job.filename}", title_style))
    story.append(Spacer(1, 12))

    # Summary
    if job.summary:
        story.append(Paragraph("Executive Summary", styles["Heading2"]))
        story.append(Paragraph(job.summary.get("executive_summary", ""), styles["Normal"]))
        story.append(Spacer(1, 12))

        details = [
            ["Genre", job.summary.get("genre_category", "")],
            ["Production Value", job.summary.get("production_value", "")],
            ["Target Audience", job.summary.get("target_audience", "")],
            ["Visual Style", job.summary.get("visual_style", "")],
        ]
        t = Table(details, colWidths=[1.5 * inch, 4.5 * inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.Color(0.15, 0.15, 0.17)),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.Color(0.9, 0.9, 0.92)),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 20))

    # Scenes
    if job.flash_result and "scenes" in job.flash_result:
        story.append(Paragraph("Scene Breakdown", styles["Heading2"]))
        for scene in job.flash_result["scenes"]:
            story.append(Paragraph(
                f"Scene {scene['scene_number']}: {scene.get('scene_title', '')} "
                f"({scene.get('start_time', '')} - {scene.get('end_time', '')})",
                styles["Heading3"],
            ))
            story.append(Paragraph(scene.get("scene_description", ""), styles["Normal"]))

            if scene.get("shots"):
                shot_data = [["Shot", "Time", "Type", "Movement", "Description"]]
                for shot in scene["shots"]:
                    shot_data.append([
                        str(shot.get("shot_number", "")),
                        f"{shot.get('start_time', '')}-{shot.get('end_time', '')}",
                        shot.get("shot_type", ""),
                        shot.get("camera_movement", ""),
                        shot.get("visual_description", "")[:80],
                    ])
                t = Table(shot_data, colWidths=[0.4 * inch, 0.8 * inch, 1 * inch, 1 * inch, 2.8 * inch])
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.2, 0.2, 0.25)),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.Color(0.85, 0.85, 0.87)),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.3, 0.3, 0.35)),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                ]))
                story.append(t)
            story.append(Spacer(1, 12))

    doc.build(story)
    return buffer.getvalue()
