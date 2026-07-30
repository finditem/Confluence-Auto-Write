from combined.weekly_report import (
    extract_section_after_marker,
    render_page,
    render_participants,
    FRONTEND_SECTION_MARKER,
    BACKEND_SECTION_MARKER,
)

# extracts everything after the marker, trimmed
body = f"<p>intro</p>{FRONTEND_SECTION_MARKER}<p>the actual content</p>"
assert extract_section_after_marker(body, FRONTEND_SECTION_MARKER) == "<p>the actual content</p>"

# missing marker or missing page body both fall back to None (rendered as "-")
assert extract_section_after_marker("<p>no marker here</p>", FRONTEND_SECTION_MARKER) is None
assert extract_section_after_marker(None, BACKEND_SECTION_MARKER) is None

# two-column participants table, one column per team
participants_html = render_participants()
assert participants_html.startswith("<table>")
assert "프론트엔드" in participants_html
assert "백엔드" in participants_html

# both source sections land in their own numbered slot; missing ones render a dash
page = render_page("2026-07-27", "<p>프론트 내용</p>", None)
assert "1. 프론트 공유 사안" in page
assert "<p>프론트 내용</p>" in page
assert "2. 백엔드 공유 사안</strong></p>\n<p>-</p>" in page

# sections 3-5 are always blank manual-fill placeholders
for label in ["3. 최종 공유 사안", "4. 전체 회의 공유 사안", "5. 공유/이슈/질문 공유"]:
    assert f"<strong>{label}</strong>" in page

print("ok")
