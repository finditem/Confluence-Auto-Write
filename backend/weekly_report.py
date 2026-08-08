"""Weekly meeting note generator for the backend team: pulls commits from GitHub, upserts a Confluence page."""
import os
from datetime import datetime, timedelta, timezone
from html import escape

import requests
from dotenv import load_dotenv

from common.confluence_client import get_or_create_folder, upsert_page

load_dotenv()

KST = timezone(timedelta(hours=9))

# (display name, github username, confluence accountId)
PEOPLE = [
    ("유세정", "Yoosejeong", "712020:d5e6ae58-a92f-4c7a-9502-fe55e159428b"),
    ("박상혁", "sangcci", "712020:d3304c0e-4c6a-4a1d-aa2f-9155d174a641"),
]

REPOS = ["finditem/FI-BE"]

GITHUB_API = "https://api.github.com"


def github_headers():
    return {
        "Authorization": f"Bearer {os.environ['BACKEND_GH_PAT']}",
        "Accept": "application/vnd.github+json",
    }


def fetch_commits(repo, author, since, until):
    params = {
        "author": author,
        "since": since.isoformat(),
        "until": until.isoformat(),
        "per_page": 100,
    }
    resp = requests.get(f"{GITHUB_API}/repos/{repo}/commits", headers=github_headers(), params=params)
    resp.raise_for_status()
    return resp.json()


def build_work_summary(since, until):
    """{person_name: [commit message, ...]} — no path/category split, single backend repo."""
    summary = {name: [] for name, _, _ in PEOPLE}
    for repo in REPOS:
        for name, username, _ in PEOPLE:
            for commit in fetch_commits(repo, username, since, until):
                summary[name].append(commit["commit"]["message"].splitlines()[0])
    return summary


def extract_openai_text(data):
    if data.get("output_text"):
        return data["output_text"].strip()
    texts = [
        content.get("text", "")
        for item in data.get("output", [])
        for content in item.get("content", [])
        if content.get("text")
    ]
    return "\n".join(texts).strip()


def summarize_commits(messages):
    """One-line Korean summary of a person's commit messages, via OpenAI Responses API."""
    if not messages:
        return ""
    prompt = (
        "다음은 한 사람이 이번 주에 작업한 Git 커밋 메시지 목록이다. "
        "회의록에 들어갈 한 줄 요약으로 압축해줘. 여러 작업이면 쉼표로 나열하고, "
        "설명 없이 요약 문장만 출력해.\n\n" + "\n".join(f"- {m}" for m in messages)
    )
    resp = requests.post(
        f"{os.environ['OPENAI_BASE_URL']}/responses",
        headers={
            "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
            "Content-Type": "application/json",
        },
        json={"model": os.environ["OPENAI_MODEL"], "input": prompt},
    )
    resp.raise_for_status()
    return extract_openai_text(resp.json())


def summarize_work_summary(work_summary):
    """{person: [commit message, ...]} -> {person: summary}"""
    return {name: summarize_commits(messages) for name, messages in work_summary.items()}


def render_mention(account_id):
    return f'<ac:link><ri:user ri:account-id="{account_id}" /></ac:link>'


LETTERS = "abcdefghijklmnopqrstuvwxyz"


def render_people_list(work_summary):
    """One line per person: 'a. 이름 : 요약' — no per-category breakdown (single-repo, no split)."""
    lines = []
    for i, (name, _, _) in enumerate(PEOPLE):
        summary = work_summary.get(name) or "-"
        lines.append(f'<p style="margin-left: 30.0px;">{LETTERS[i]}. {escape(name)} : {escape(summary)}</p>')
    return "".join(lines)


def render_emoji(name, shortname, emoji_id, fallback):
    return (
        f'<ac:emoticon ac:name="{name}" ac:emoji-shortname="{shortname}" '
        f'ac:emoji-id="{emoji_id}" ac:emoji-fallback="{fallback}" />'
    )


CALENDAR_EMOJI = render_emoji("spiral-calendar-pad", ":spiral_calendar_pad:", "1f5d3", "🗓️")
PEOPLE_EMOJI = render_emoji("busts-in-silhouette", ":busts_in_silhouette:", "1f465", "👥")


def render_page(iso_date, work_summary):
    work_html = render_people_list(work_summary)
    next_work_html = render_people_list({})
    participants_html = "".join(
        f"<li>{render_mention(account_id)}</li>" for _, _, account_id in PEOPLE
    )
    return f"""
<h2>{CALENDAR_EMOJI} 날짜</h2>
<p><time datetime="{escape(iso_date)}" /></p>
<h2>{PEOPLE_EMOJI} 참여자</h2>
<ul>{participants_html}</ul>
<p>&nbsp;</p>
<p><strong>1. 작업 공유</strong></p>
{work_html}
<p>&nbsp;</p>
<p><strong>2. 이후 작업 공유</strong></p>
{next_work_html}
<p>&nbsp;</p>
<p><strong>3. 공유/이슈/질문 공유</strong></p>
<p>-</p>
<p>&nbsp;</p>
<p><strong>4. 프론트 미팅 공유 사항</strong></p>
<p>-</p>
""".strip()


def main():
    now = datetime.now(KST)
    since = now - timedelta(days=7)
    iso_date = now.strftime("%Y-%m-%d")
    title = now.strftime("%m월 %d일 미팅")
    monthly_folder_title = f"통합 {now.strftime('%y')}년 {now.month}월"

    base_url = os.environ["CONFLUENCE_BASE_URL"]
    space_key = os.environ["BACKEND_SPACE_KEY"]

    monthly_folder_id = get_or_create_folder(
        base_url=base_url,
        space_key=space_key,
        parent_id=os.environ["BACKEND_PARENT_PAGE_ID"],
        title=monthly_folder_title,
    )

    work_summary = build_work_summary(since, now)
    work_summary = summarize_work_summary(work_summary)
    body_html = render_page(iso_date, work_summary)

    result = upsert_page(
        base_url=base_url,
        space_key=space_key,
        parent_id=monthly_folder_id,
        title=title,
        body_html=body_html,
    )
    print(f"Upserted page: {result['_links']['base']}{result['_links']['webui']}")


if __name__ == "__main__":
    main()
