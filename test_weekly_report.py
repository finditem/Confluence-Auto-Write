from weekly_report import render_person_block, render_people_list, render_page, extract_openai_text

# extract_openai_text handles both response shapes the Responses API can return
assert extract_openai_text({"output_text": " 요약 문장 "}) == "요약 문장"
assert (
    extract_openai_text({"output": [{"content": [{"text": "요약"}, {"text": "문장"}]}]})
    == "요약\n문장"
)
assert extract_openai_text({"output": []}) == ""

# person with commits renders each fixed category on its own line, colon-prefixed
html = render_person_block("준열", {"운영": ["fix bug"], "모니터링": ["add alert"]}, "c")
assert "(운영) : fix bug" in html
assert "(모니터링) : add alert" in html

# name sits on its own line; every category line (including the first) gets the
# same deeper indent, so they align with each other instead of the "a." label
assert render_person_block("지권", {}, "a") == (
    '<p style="margin-left: 30.0px;">a. 지권:</p>'
    '<p style="margin-left: 60.0px;">(운영) :</p>'
    '<p style="margin-left: 60.0px;">(모니터링) :</p>'
)

# person's fixed category list differs (수현 gets 일정관리, not 모니터링)
assert "(일정관리) :" in render_person_block("수현", {}, "b")

# HTML-escapes commit messages to avoid breaking the Confluence page
assert "&lt;script&gt;" in render_person_block("수현", {"운영": ["<script>bad</script>"]}, "b")

# people are rendered as literal a./b./c.-prefixed, indented paragraphs
people_html = render_people_list({})
assert "margin-left" in people_html
assert "a. 지권:" in people_html
assert "b. 수현:" in people_html
assert "c. 준열:" in people_html

# sections 1-4 are numbered inline labels, not headings
page = render_page("2026-07-27", {"지권": {}, "수현": {}, "준열": {}})
for label in ["1. 작업 공유", "2. 이후 작업 공유", "3. 공유/이슈/질문 공유", "4. 전체 회의 공유 사안"]:
    assert f"<strong>{label}</strong>" in page
for text in ["<h2><ac:emoticon", "날짜</h2>", "참여자</h2>", 'ac:emoji-id="1f5d3"', 'ac:emoji-id="1f465"']:
    assert text in page

# date renders as a native Confluence date element, not plain text
assert '<time datetime="2026-07-27" />' in page

print("ok")
