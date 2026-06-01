import json
import os
import time
import requests
import xml.etree.ElementTree as ET

# 시크릿에서 가져오기
NTS_COOKIE = os.environ.get("NTS_COOKIE")
LAW_OC = "hongjeyeon"  # 법제처 API OC값

# 출력 폴더
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

print("🎯 세법해석례 수집 시작\n")

# ===== 1. 국세청 세법해석례 =====
print("📂 [1/2] 국세청 세법해석례 수집 시작")

NTS_URL = "https://taxlaw.nts.go.kr/action.do"
NTS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/json;charset=UTF-8",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://taxlaw.nts.go.kr",
    "Referer": "https://taxlaw.nts.go.kr/",
    "Cookie": NTS_COOKIE,
}

TAX_CATEGORIES = [
    "법인세법", "소득세법", "부가가치세법",
    "상속세 및 증여세법", "조세특례제한법",
    "국세기본법", "국세징수법",
]

nts_file = f"{output_dir}/국세청_세법해석례.md"
with open(nts_file, "w", encoding="utf-8") as f:
    f.write(f"# 국세청 세법해석례\n- 수집: {time.strftime('%Y-%m-%d %H:%M:%S')}\n---\n\n")

    for idx, tax_name in enumerate(TAX_CATEGORIES, 1):
        print(f"  [{idx}/{len(TAX_CATEGORIES)}] {tax_name}")
        page = 0
        saved = 0

        while True:
            payload = {
                "actionId": "ASIPDI002PR01",
                "paramData": json.dumps({
                    "qstnPrdcOrgnClCtl": [],
                    "rltnStttCtl": [],
                    "schDtBase": "FRS_RGT_DTM",
                    "bltnStrtDt": "",
                    "bltnEndDt": "",
                    "dcmClCdCtl": ["001_01", "001_02", "001_03", "001_04"],
                    "collectionName": "question,question_gr",
                    "sortField": "DCM_RGT_DTM/DESC",
                    "startCount": 1 + (page * 50),
                    "viewCount": 50,
                    "nowCnt": 0,
                    "searchWord": tax_name,
                }, ensure_ascii=False),
            }

            try:
                res = requests.post(NTS_URL, headers=NTS_HEADERS, json=payload, timeout=15)
                res.raise_for_status()
                body_list = res.json().get("data", {}).get("ASIPDI002PR01", {}).get("body", [])

                if not body_list:
                    print(f"    ✅ {tax_name} 완료 ({saved}건)")
                    break

                for item in body_list:
                    dcm = item.get("dcm", {})
                    if not dcm:
                        continue
                    title = dcm.get("TTL", "제목없음")
                    doc_no = dcm.get("NTST_DCM_DSCM_CNTN") or dcm.get("DOCU_NO_STR1", "")
                    tax_type = dcm.get("NTST_TLAW_CL_NM", tax_name)
                    reg_date = dcm.get("NTST_DCM_RGT_DT", "")[:8]
                    gist = dcm.get("GIST_CNTN", "").strip()
                    content = dcm.get("CNTN", "").strip()

                    f.write(f"## {title}\n")
                    f.write(f"| 세목 | {tax_type} | 문서번호 | {doc_no} | 일자 | {reg_date} |\n")
                    f.write(f"|---|---|---|---|---|---|\n\n")
                    f.write(f"### 요약\n> {gist}\n\n")
                    f.write(f"### 본문\n```\n{content}\n```\n\n---\n\n")
                    saved += 1

                time.sleep(3)
                page += 1

            except Exception as e:
                print(f"    ❌ {tax_name} 에러: {e}")
                break

print(f"✅ 국세청 완료 → {nts_file}\n")

# ===== 2. 기재부 세법해석례 (법제처 API) =====
print("📂 [2/2] 기재부 세법해석례 수집 시작")

MOEF_KEYWORDS = [
    "법인세", "소득세", "부가가치세",
    "상속세", "증여세", "조세특례",
    "국세기본", "양도소득",
]

moef_file = f"{output_dir}/기재부_세법해석례.md"
with open(moef_file, "w", encoding="utf-8") as f:
    f.write(f"# 기재부 세법해석례\n- 수집: {time.strftime('%Y-%m-%d %H:%M:%S')}\n---\n\n")

    for idx, keyword in enumerate(MOEF_KEYWORDS, 1):
        print(f"  [{idx}/{len(MOEF_KEYWORDS)}] {keyword}")

        page = 1
        saved = 0

        while True:
            list_url = (
                f"http://www.law.go.kr/DRF/lawSearch.do"
                f"?OC={LAW_OC}&target=expc&type=JSON"
                f"&query={keyword}&display=100&page={page}"
                f"&sort=ddes"
            )

            try:
                res = requests.get(list_url, timeout=15)
                data = res.json()
                expc_list = data.get("Expc", {}).get("expc", [])
                total = int(data.get("Expc", {}).get("totalCnt", 0))

                if not expc_list:
                    break

                for item in expc_list:
                    # 기재부 회신만 필터
                    if "기획재정부" not in item.get("회신기관명", "") and \
                       "기획재정부" not in item.get("질의기관명", ""):
                        continue

                    serial = item.get("법령해석례일련번호")
                    title = item.get("안건명", "")
                    case_no = item.get("안건번호", "")
                    reply_org = item.get("회신기관명", "")
                    inq_org = item.get("질의기관명", "")
                    reply_date = item.get("회신일자", "")

                    # 본문 조회
                    detail_url = (
                        f"http://www.law.go.kr/DRF/lawService.do"
                        f"?OC={LAW_OC}&target=expc&ID={serial}&type=XML"
                    )
                    try:
                        det_res = requests.get(detail_url, timeout=15)
                        tree = ET.fromstring(det_res.content)

                        질의요지 = tree.findtext("질의요지", "").strip()
                        회답 = tree.findtext("회답", "").strip()
                        이유 = tree.findtext("이유", "").strip()

                        f.write(f"## {title}\n")
                        f.write(f"| 안건번호 | {case_no} | 질의 | {inq_org} | 회신 | {reply_org} | 일자 | {reply_date} |\n")
                        f.write(f"|---|---|---|---|---|---|---|---|\n\n")
                        if 질의요지:
                            f.write(f"### 질의요지\n> {질의요지}\n\n")
                        if 회답:
                            f.write(f"### 회답\n{회답}\n\n")
                        if 이유:
                            f.write(f"### 이유\n{이유}\n\n")
                        f.write("---\n\n")
                        saved += 1

                    except Exception as e:
                        print(f"    ⚠️ 본문 조회 실패 {serial}: {e}")

                    time.sleep(1)

                print(f"    page {page} 완료 ({saved}건 누적)")

                if page * 100 >= total:
                    break
                page += 1
                time.sleep(2)

            except Exception as e:
                print(f"    ❌ {keyword} 에러: {e}")
                break

        print(f"    ✅ {keyword} 완료 ({saved}건)")

print(f"✅ 기재부 완료 → {moef_file}\n")
print("🎉 전체 수집 완료!")
