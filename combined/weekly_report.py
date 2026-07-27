"""Combined frontend+backend weekly meeting note.

Pulls the "백엔드 미팅 공유 사안" section out of this week's frontend report and
drops it into the combined page's "프론트 공유 사안" section. See
docs/combined-report-plan.md for the full design and open decisions.

NOT WIRED UP YET — no GitHub Actions workflow, no destination space/folder,
and no backend-side section (backend automation doesn't exist yet). Run
manually once COMBINED_SPACE_KEY / COMBINED_PARENT_PAGE_ID are set.
"""
import os
from datetime import datetime, timedelta, timezone
from html import escape

from dotenv import load_dotenv

from common.confluence_client import get_page_body, upsert_page

load_dotenv()

KST = timezone(timedelta(hours=9))

# (team label, [(display name, confluence accountId), ...])
PEOPLE_BY_TEAM = [
    ("프론트엔드", [
        ("서지권", "712020:25773487-905e-4738-be71-379ad5849157"),
        ("이수현", "712020:ac6478e7-a67c-4701-8552-e07d42f42f5d"),
        ("김준열", "712020:54c11aa3-6479-431d-875c-dca1c3506130"),
    ]),
    ("백엔드", [
        ("유세정", "712020:d5e6ae58-a92f-4c7a-9502-fe55e159428b"),
    ]),
]

# The marker paragraph that starts the section we pull out of the frontend
# report. It's currently the last section on that page, so everything after
# this marker belongs to it.
FRONTEND_SECTION_MARKER = "<p><strong>4. 백엔드 미팅 공유 사안</strong></p>"


def most_recent_monday(date):
    return date - timedelta(days=date.weekday())


def extract_frontend_backend_section(body_html):
    """Return the storage-format HTML after FRONTEND_SECTION_MARKER, or None if not found."""
    if body_html is None or FRONTEND_SECTION_MARKER not in body_html:
        return None
    return body_html.split(FRONTEND_SECTION_MARKER, 1)[1].strip()


def render_mention(account_id):
    return f'<ac:link><ri:user ri:account-id="{account_id}" /></ac:link>'


def render_participants():
    """Two-column table, one column per team, so they sit side by side."""
    cells = []
    for team, people in PEOPLE_BY_TEAM:
        mentions = " ".join(render_mention(account_id) for _, account_id in people)
        cells.append(f"<td><strong>{escape(team)}</strong><br/>{mentions}</td>")
    return f"<table><tbody><tr>{''.join(cells)}</tr></tbody></table>"


def render_page(iso_date, frontend_section_html):
    frontend_section = frontend_section_html or "<p>-</p>"
    return f"""
<h2>날짜</h2>
<p><time datetime="{escape(iso_date)}" /></p>
<h2>참가자</h2>
{render_participants()}
<p><strong>1. 프론트 공유 사안</strong></p>
{frontend_section}
<p><strong>2. 백엔드 공유 사안</strong></p>
<p>-</p>
<p><strong>3. 전체 회의 공유 사안</strong></p>
<p>-</p>
<p><strong>4. 공유/이슈/질문 공유</strong></p>
<p>-</p>
""".strip()


def main():
    now = datetime.now(KST)
    monday = most_recent_monday(now)
    iso_date = now.strftime("%Y-%m-%d")
    frontend_title = monday.strftime("%m월 %d일 미팅")
    title = now.strftime("%m월 %d일 통합 미팅")  # placeholder — title format not decided yet

    base_url = os.environ["CONFLUENCE_BASE_URL"]
    frontend_space_key = os.environ["FRONTEND_SPACE_KEY"]

    frontend_body = get_page_body(base_url, frontend_space_key, frontend_title)
    frontend_section = extract_frontend_backend_section(frontend_body)

    body_html = render_page(iso_date, frontend_section)

    result = upsert_page(
        base_url=base_url,
        space_key=os.environ["COMBINED_SPACE_KEY"],
        parent_id=os.environ["COMBINED_PARENT_PAGE_ID"],
        title=title,
        body_html=body_html,
    )
    print(f"Upserted page: {result['_links']['base']}{result['_links']['webui']}")


if __name__ == "__main__":
    main()
