import os
import time
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.kasb.or.kr"
LIST_URL = f"{BASE_URL}/front/board/allReplySummaryList.do"

output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/x-www-form-urlencoded",
    "Referer": "https://www.kasb.or.kr/front/board/allReplySummaryList.do",
}

# 분류별 파일 핸들러
category_files = {}
category_counts = {}

def get_file(category):
    if category not in category_files:
        safe_name = category.replace("/", "_").replace(" ", "_")
        f = open(f"{output_dir}/회계기준원_{safe_name}.md", "w", encoding="utf-8")
        f.write(f"# 한국회계기준원 질의회신 - {category}\n")
        f.write(f"- 수집: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n\n")
        category_files[category] = f
        category_counts[category] = 0
    return category_files[category]

def get_detail(seq, ctg_cd):
    url = f"{BASE_URL}/front/board/View{ctg_cd}.do"
    payload = {
        "siteCd": "002000000000000",
        "seq": seq,
        "ctgCd": ctg_cd,
        "replySummary": "Y",
    }
    try:
        res = requests.post(url, headers=HEADERS, data=payload, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")

        # 제목
        title_tag = soup.select_one(".view_tit, h3.tit, .board_view_tit")
        title = title_tag.get_text(strip=True) if title_tag else ""

        # 본문 내용
        content_tag = soup.select_one(".view_cont, .board_view_cont, .content_area")
        content = content_tag.get_text(separator="\n", strip=True) if content_tag else ""

        return title, content
    except Exception as e:
        return "", f"본문 조회 실패: {e}"

print("🎯 한국회계기준원 질의회신 수집 시작\n")

# 총 페이지 먼저 확인
res = requests.post(LIST_URL, headers=HEADERS, data={
    "siteCd": "002000000000000",
    "replySummary": "Y",
    "searchfield": "ALL",
    "page": "1",
}, timeout=15)
soup = BeautifulSoup(res.text, "html.parser")
paging = soup.select_one(".paging_wrap")
total_pages = 1
if paging:
    last_link = paging.find("a", string="Last")
    if last_link and "G_MovePage" in last_link.get("href", ""):
        import re
        m = re.search(r"G_MovePage\((\d+)\)", last_link["href"])
        if m:
            total_pages = int(m.group(1))

print(f"총 {total_pages}페이지 수집 시작\n")

total_saved = 0

for page in range(1, total_pages + 1):
    print(f"  [{page}/{total_pages}] 페이지 수집 중...")

    payload = {
        "siteCd": "002000000000000",
        "replySummary": "Y",
        "searchfield": "ALL",
        "page": str(page),
    }

    try:
        res = requests.post(LIST_URL, headers=HEADERS, data=payload, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        rows = soup.select(".board_sty01 tbody tr")

        for row in rows:
            # 공지 스킵
            if row.select_one("strong"):
                continue

            tds = row.select("td")
            if len(tds) < 3:
                continue

            # 분류
            category = tds[1].get_text(strip=True) if len(tds) > 1 else "기타"
            if not category:
                category = "기타"

            # 제목 + seq, ctgCd
            title_td = tds[2]
            a_tag = title_td.select_one("a")
            if not a_tag:
                continue

            title = a_tag.get_text(strip=True)
            onclick = a_tag.get("onclick", "")

            import re
            m = re.search(r"fn_Detail\('(\d+)','(\w+)'\)", onclick)
            if not m:
                continue

            seq = m.group(1)
            ctg_cd = m.group(2)

            # 회신일
            date_tag = row.select_one(".board_date")
            reply_date = date_tag.get_text(strip=True) if date_tag else ""

            # 상세 본문 조회
            _, content = get_detail(seq, ctg_cd)

            # 파일에 저장
            f = get_file(category)
            f.write(f"## {title}\n\n")
            f.write(f"| 분류 | {category} | 회신일 | {reply_date} |\n")
            f.write(f"|---|---|---|---|\n\n")
            if content:
                f.write(f"### 내용\n{content}\n\n")
            f.write("---\n\n")
            f.flush()

            category_counts[category] = category_counts.get(category, 0) + 1
            total_saved += 1

            time.sleep(1)

        print(f"    누적 {total_saved}건")
        time.sleep(2)

    except Exception as e:
        print(f"    ❌ 페이지 {page} 에러: {e}")
        continue

# 파일 닫기
for f in category_files.values():
    f.close()

print("\n📊 분류별 수집 결과:")
for cat, cnt in category_counts.items():
    print(f"  {cat}: {cnt}건")

print(f"\n🎉 전체 {total_saved}건 수집 완료!")
