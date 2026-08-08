from backend.weekly_report import render_people_list, render_page, extract_openai_text

# extract_openai_text handles both response shapes the Responses API can return
assert extract_openai_text({"output_text": " 요약 문장 "}) == "요약 문장"
assert (
    extract_openai_text({"output": [{"content": [{"text": "요약"}, {"text": "문장"}]}]})
    == "요약\n문장"
)
assert extract_openai_text({"output": []}) == ""

# no category parentheses — just "letter. name : summary"
html = render_people_list({"유세정": "API 리팩터링, CORS 설정 정리"})
assert '<p style="margin-left: 30.0px;">a. 유세정 : API 리팩터링, CORS 설정 정리</p>' in html

# missing summary renders a dash, not blank
assert render_people_list({}) == (
    '<p style="margin-left: 30.0px;">a. 유세정 : -</p>'
    '<p style="margin-left: 30.0px;">b. 박상혁 : -</p>'
)

# HTML-escapes the summary to avoid breaking the Confluence page
assert "&lt;script&gt;" in render_people_list({"유세정": "<script>bad</script>"})

# sections 1-4 are numbered inline labels, not headings
page = render_page("2026-07-27", {})
for label in ["1. 작업 공유", "2. 이후 작업 공유", "3. 공유/이슈/질문 공유", "4. 프론트 미팅 공유 사항"]:
    assert f"<strong>{label}</strong>" in page
for text in ["<h2><ac:emoticon", "날짜</h2>", "참여자</h2>", 'ac:emoji-id="1f5d3"', 'ac:emoji-id="1f465"']:
    assert text in page

# date renders as a native Confluence date element, not plain text
assert '<time datetime="2026-07-27" />' in page

print("ok")
