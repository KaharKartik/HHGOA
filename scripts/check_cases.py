import sys, csv, json
from urllib.request import Request, urlopen
sys.path.insert(0, "backend")
from app.integrations.tigergraph import TigerGraphAdapter

adapter = TigerGraphAdapter.from_environment()

with open("data/raw/case_pack.csv", encoding="utf-8") as f:
    cases = list(csv.DictReader(f))

print(f"Checking {len(cases)} cases...")
found = 0
for row in cases:
    tid = row["flagged_txn_id"]
    url = adapter._restpp_url(f"graph/HHGOA_FRAUD/vertices/Transaction/{tid}")
    req = Request(url, headers=adapter._headers())
    try:
        with urlopen(req, timeout=5) as r:
            res = json.load(r).get("results", [])
            if res:
                found += 1
                v = res[0]["attributes"]
                print(f"{row['case_id']}: Txn {tid} found! Amt={v.get('amount')}, Channel={v.get('channel')}, Region={v.get('billing_region')}")
            else:
                print(f"{row['case_id']}: Txn {tid} not found in graph")
    except Exception as e:
        print(f"{row['case_id']}: Error {e}")

print(f"Total found: {found}/{len(cases)}")
