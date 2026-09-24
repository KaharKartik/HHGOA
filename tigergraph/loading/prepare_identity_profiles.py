"""Stream identity.csv to a generated staging CSV; source data is never changed."""
import csv, hashlib, sys
from pathlib import Path
def main() -> int:
    root=Path(__file__).resolve().parents[2]; source=root/'data/raw/identity.csv'; target=root/'data/processed/identity_profiles_for_tigergraph.csv'
    with source.open(encoding='utf-8-sig',newline='') as inp,target.open('w',encoding='utf-8',newline='') as out:
        reader=csv.DictReader(inp); fields=['TransactionID','device_profile_id','DeviceInfo','id_30','id_31','id_33','DeviceType']; writer=csv.DictWriter(out,fieldnames=fields); writer.writeheader()
        for row in reader:
            parts=[row.get(k,'') or '' for k in ['DeviceInfo','id_30','id_31','id_33']]
            if any(parts): row['device_profile_id']='DP-'+hashlib.sha256('\x1f'.join(parts).encode()).hexdigest()[:24]; writer.writerow({k:row.get(k,'') for k in fields})
    return 0
if __name__=='__main__': raise SystemExit(main())
