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
