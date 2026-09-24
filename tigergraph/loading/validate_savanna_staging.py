from __future__ import annotations
import csv,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'data/processed/tigergraph_staging'
def ids(name,column):
 with (OUT/name).open(encoding='utf-8',newline='') as f:return {r[column] for r in csv.DictReader(f) if r[column]}
def main():
 manifest=json.loads((OUT/'manifest.json').read_text()); errors=[]
 for name,info in manifest['files'].items():
  if next(csv.reader((OUT/name).open(encoding='utf-8',newline=''))) != info['header']: errors.append(f'header mismatch: {name}')
 tx=ids('transactions.csv','transaction_id'); customers=ids('customers.csv','customer_id'); cards=ids('cards.csv','card_id'); devices=ids('device_profiles.csv','device_profile_id'); emails=ids('email_domains.csv','email_domain'); regions=ids('billing_regions.csv','billing_region'); closed=ids('closed_cases.csv','case_id')
 checks=[('owns.csv','from_customer_id',customers),('owns.csv','to_card_id',cards),('from_device.csv','from_transaction_id',tx),('from_device.csv','to_device_profile_id',devices),('purchaser_email.csv','from_transaction_id',tx),('purchaser_email.csv','to_email_domain',emails),('billed_in.csv','from_transaction_id',tx),('billed_in.csv','to_billing_region',regions),('involves.csv','from_closed_case_id',closed),('involves.csv','to_transaction_id',tx),('on_card.csv','from_closed_case_id',closed),('on_card.csv','to_card_id',cards),('connected_to.csv','from_closed_case_id',closed),('connected_to.csv','to_card_id',cards)]
 for file,column,valid in checks:
  with (OUT/file).open(encoding='utf-8',newline='') as f:
   if any(r[column] not in valid for r in csv.DictReader(f)): errors.append(f'reference mismatch: {file}.{column}')
 expected={f'HHG-{n:03d}' for n in range(1,21)}
 if not expected <= set(manifest['benchmark_cases']): errors.append('benchmark cases missing')
 print('PASS' if not errors else 'FAIL: '+'; '.join(errors)); return 0 if not errors else 1
if __name__=='__main__': raise SystemExit(main())
