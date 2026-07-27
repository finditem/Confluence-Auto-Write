"""Weekly meeting note generator: pulls commits from GitHub, upserts a Confluence page."""
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
    ("지권", "wlrnjs", "712020:25773487-905e-4738-be71-379ad5849157"),
    ("수현", "suhyeon0111", "712020:ac6478e7-a67c-4701-8552-e07d42f42f5d"),
    ("준열", "junye0l", "712020:54c11aa3-6479-431d-875c-dca1c3506130"),
]

# Categories always shown per person, in display order
PERSON_CATEGORIES = {
    "지권": ["운영", "모니터링"],
    "수현": ["운영", "일정관리"],
    "준열": ["운영", "모니터링"],
}

# (repo, [(paths, category)])  — empty paths list = whole repo
REPO_RULES = [
    ("finditem/infra-support", [
        (["apps/monitor-server", "apps/monitor-web"], "모니터링"),
        (["apps/schedule"], "일정관리"),
    ]),
    ("finditem/FI-FE", [
        ([], "운영"),
    ]),
]

GITHUB_API = "https://api.github.com"


def github_headers():
    return {
        "Authorization": f"Bearer {os.environ['GH_PAT']}",
        "Accept": "application/vnd.github+json",
    }


def fetch_commits(repo, author, since, until, path=None):
    params = {
        "author": author,
        "since": since.isoformat(),
        "until": until.isoformat(),
        "per_page": 100,
    }
    if path:
        params["path"] = path
    resp = requests.get(f"{GITHUB_API}/repos/{repo}/commits", headers=github_headers(), params=params)
    resp.raise_for_status()
    return resp.json()


def build_work_summary(since, until):
    """{person_name: {category: [commit message, ...]}}"""
    summary = {name: {} for name, _, _ in PEOPLE}
    for repo, rules in REPO_RULES:
        for name, username, _ in PEOPLE:
            for paths, category in rules:
                seen_shas = set()
                messages = []
                for path in (paths or [None]):
                    for commit in fetch_commits(repo, username, since, until, path=path):
                        sha = commit["sha"]
                        if sha in seen_shas:
                            continue
                        seen_shas.add(sha)
                        messages.append(commit["commit"]["message"].splitlines()[0])
                if messages:
                    summary[name].setdefault(category, []).extend(messages)
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
    """{person: {category: [commit message, ...]}} -> {person: {category: [summary]}}"""
    return {
        name: {category: [summarize_commits(messages)] for category, messages in categories.items()}
        for name, categories in work_summary.items()
    }


def render_category_line(category, messages):
    text = ", ".join(messages)
    suffix = f" {escape(text)}" if text else ""
    return f"({escape(category)}) :{suffix}"


def render_person_block(name, categories, letter):
    lines = [f'<p style="margin-left: 30.0px;">{letter}. {escape(name)}:</p>']
    for category in PERSON_CATEGORIES[name]:
        line = render_category_line(category, categories.get(category, []))
        lines.append(f'<p style="margin-left: 60.0px;">{line}</p>')
    return "".join(lines)


LETTERS = "abcdefghijklmnopqrstuvwxyz"


def render_people_list(work_summary):
    return "".join(
        render_person_block(name, work_summary.get(name, {}), LETTERS[i])
        for i, (name, _, _) in enumerate(PEOPLE)
    )


def render_mention(account_id):
    return f'<ac:link><ri:user ri:account-id="{account_id}" /></ac:link>'


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
<p><strong>1. 작업 공유</strong></p>
{work_html}
<p><strong>2. 이후 작업 공유</strong></p>
{next_work_html}
<p><strong>3. 공유/이슈/질문 공유</strong></p>
<p>-</p>
<p><strong>4. 백엔드 미팅 공유 사안</strong></p>
<p>-</p>
""".strip()


def main():
    now = datetime.now(KST)
    since = now - timedelta(days=7)
    iso_date = now.strftime("%Y-%m-%d")
    title = now.strftime("%m월 %d일 미팅")
    monthly_folder_title = f"통합 {now.strftime('%y')}년 {now.month}월"

    base_url = os.environ["CONFLUENCE_BASE_URL"]
    space_key = os.environ["CONFLUENCE_SPACE_KEY"]

    monthly_folder_id = get_or_create_folder(
        base_url=base_url,
        space_key=space_key,
        parent_id=os.environ["CONFLUENCE_PARENT_PAGE_ID"],
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
