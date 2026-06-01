import json
import os
import time
import requests
import xml.etree.ElementTree as ET

NTS_COOKIE = os.environ.get("NTS_COOKIE")
LAW_OC = "hongjeyeon"

output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

print("🎯 세법해석례 수집 시작\n")

# ===== 1. 국세청 세법해석례 (세목별 개별 파일) =====
print("📂 [1/2] 국세청 세법해석례 수집 시작")

NTS_URL = "https://taxlaw.nts.go.kr/action.do"
NTS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/json;charset=UTF-8",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Origin": "https://taxlaw.nts.go.kr",
    "Referer": "https://taxlaw.nts.go.kr/",
    "Cookie": NTS_COOKIE,
}

TAX_CATEGORIES = [
    "법인세법", "소득세법", "부가가치세법",
    "상속세 및 증여세법", "조세특례제한법",
    "국제조세조정에관한법률", "국세기본법",
    "국세징수법", "종합부동산세", "개별소비세",
    "주세", "교육세법", "농어촌특별세법", "조세범처벌법",
]

for idx, tax_name in enumerate(TAX_CATEGORIES, 1):
    print(f"  [{idx}/{len(TAX_CATEGORIES)}] {tax_name}")
    file_name = f"{output_dir}/국세청_{idx:02d}_{tax_name}.md"
    page = 0
    saved = 0

    with open(file_name, "w", encoding="utf-8") as f:
        f.write(f"# 국세청 세법해석례 - {tax_name}\n")
        f.write(f"- 수집: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n\n")

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
                res = requests.post(
                    NTS_URL, headers=NTS_HEADERS,
                    data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                    timeout=15, verify=False
                )
                res.raise_for_status()
                body_list = res.json().get("data", {}).get("ASIPDI002PR01", {}).get("body", [])

                if not body_list:
                    print(f"    ✅ 완료 ({saved}건)")
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
                    facts = dcm.get("FILE_CN", "").strip()

                    f.write(f"## {title}\n\n")
                    f.write(f"| 항목 | 내용 |\n|---|---|\n")
                    f.write(f"| 세목 | {tax_type} |\n")
                    f.write(f"| 문서번호 | {doc_no} |\n")
                    f.write(f"| 생산일자 | {reg_date} |\n\n")
                    if gist:
                        f.write(f"### 요약\n> {gist}\n\n")
                    if content:
                        f.write(f"### 본문\n```\n{content}\n```\n\n")
                    if facts:
                        f.write(f"### 사실관계\n{facts}\n\n")
                    f.write("---\n\n")
                    saved += 1

                time.sleep(3)
                page += 1

            except Exception as e:
                print(f"    ❌ 에러: {e}")
                try:
                    print(f"    응답내용: {res.text[:200]}")
                except:
                    pass
                break

print("✅ 국세청 완료\n")

# ===== 2. 기재부 세법해석례 (세목별 개별 파일) =====
print("📂 [2/2] 기재부 세법해석례 수집 시작")

MOEF_CATEGORIES = [
    ("법인세", "기재부_법인세법"),
    ("소득세", "기재부_소득세법"),
    ("부가가치세", "기재부_부가가치세법"),
    ("상속세", "기재부_상속세법"),
    ("증여세", "기재부_증여세법"),
    ("조세특례", "기재부_조세특례제한법"),
    ("양도소득", "기재부_양도소득세"),
    ("국제조세", "기재부_국제조세"),
    ("종합부동산세", "기재부_종합부동산세"),
]

for idx, (keyword, fname) in enumerate(MOEF_CATEGORIES, 1):
    print(f"  [{idx}/{len(MOEF_CATEGORIES)}] {keyword}")
    file_name = f"{output_dir}/{idx:02d}_{fname}.md"
    page = 1
    saved = 0

    with open(file_name, "w", encoding="utf-8") as f:
        f.write(f"# 기재부 세법해석례 - {keyword}\n")
        f.write(f"- 수집: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n\n")

        while True:
            list_url = (
                f"http://www.law.go.kr/DRF/lawSearch.do"
                f"?OC={LAW_OC}&target=expc&type=JSON"
                f"&query={keyword}&display=100&page={page}&sort=ddes"
            )

            try:
                res = requests.get(list_url, timeout=15)
                data = res.json()
                expc_data = data.get("Expc", {})
                expc_list = expc_data.get("expc", [])
                total = int(expc_data.get("totalCnt", 0))

                if not expc_list:
                    break

                for item in expc_list:
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

                        f.write(f"## {title}\n\n")
                        f.write(f"| 항목 | 내용 |\n|---|---|\n")
                        f.write(f"| 안건번호 | {case_no} |\n")
                        f.write(f"| 질의기관 | {inq_org} |\n")
                        f.write(f"| 회신기관 | {reply_org} |\n")
                        f.write(f"| 회신일자 | {reply_date} |\n\n")
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

                print(f"    page {page} 완료 ({saved}건 누적, 전체 {total}건)")

                if page * 100 >= total:
                    break
                page += 1
                time.sleep(2)

            except Exception as e:
                print(f"    ❌ {keyword} 에러: {e}")
                break

    print(f"    ✅ {keyword} 완료 ({saved}건)")

print("\n🎉 전체 수집 완료!")
