"""Create CSV staging files from HHGOA sources without changing raw data or graph state."""
from __future__ import annotations
import csv, hashlib, json, shutil
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]; RAW=ROOT/'data/raw'; OUT=ROOT/'data/processed/tigergraph_staging'
FILES={
 'customers.csv':['customer_id'], 'cards.csv':['card_id','customer_id'],
 'transactions.csv':['transaction_id','customer_id','ts','amount','channel','product_cd','billing_region','purchaser_email'],
 'device_profiles.csv':['device_profile_id','device_info','os','browser','screen','device_type'],
 'email_domains.csv':['email_domain'], 'billing_regions.csv':['billing_region'],
 'closed_cases.csv':['case_id','customer_id','card_id','outcome','pattern','exposure_usd','actions_taken','report_filed','analyst_notes'],
 'case_pack_records.csv':['case_id','opened_at','trigger_type','trigger_text','flagged_txn_id','card_id','customer_id','risk_score'],
 'owns.csv':['from_customer_id','to_card_id'], 'made.csv':['from_card_id','to_transaction_id'],
 'from_device.csv':['from_transaction_id','to_device_profile_id'], 'purchaser_email.csv':['from_transaction_id','to_email_domain'],
 'billed_in.csv':['from_transaction_id','to_billing_region'], 'next.csv':['from_transaction_id','to_transaction_id','delta_seconds'],
 'involves.csv':['from_closed_case_id','to_transaction_id'], 'on_card.csv':['from_closed_case_id','to_card_id'],
 'connected_to.csv':['from_closed_case_id','to_card_id'], 'related_device.csv':['from_investigation_case_id','to_device_profile_id'], 'similar_to.csv':['from_investigation_case_id','to_closed_case_id'],
}
def open_writers():
 OUT.mkdir(parents=True,exist_ok=True); handles={}; writers={}
 for name,fields in FILES.items():
  f=(OUT/name).open('w',encoding='utf-8',newline=''); handles[name]=f; writers[name]=csv.DictWriter(f,fieldnames=fields); writers[name].writeheader()
 return handles,writers
def profile_id(row):
 values=[row.get(k,'') or '' for k in ('DeviceInfo','id_30','id_31','id_33')]
 return 'DP-'+hashlib.sha256('\x1f'.join(values).encode()).hexdigest()[:24] if any(values) else ''
def rows(path):
 with path.open(encoding='utf-8-sig',newline='') as f: yield from csv.DictReader(f)
def main():
 if OUT.exists(): shutil.rmtree(OUT)
 handles,w=open_writers(); customers=set(); cards={}; emails=set(); regions=set(); tx_ids=set(); selected_ts={}; closed=[]; case_pack=[]
 for r in rows(RAW/'closed_cases_history.csv'):
  closed.append(r); cards[r['card_id']]=r['customer_id']; customers.add(r['customer_id'])
  for card in filter(None,r['connected_card_ids'].split('|')): cards.setdefault(card,'')
  for tid in filter(None,r['txn_ids'].split('|')): selected_ts[tid]=None
  if r['first_fraud_txn_id']: selected_ts[r['first_fraud_txn_id']]=None
 for r in rows(RAW/'case_pack.csv'):
  case_pack.append(r); customers.add(r['customer_id']); cards.setdefault(r['card_id'],r['customer_id']); selected_ts[r['flagged_txn_id']]=None
  w['case_pack_records.csv'].writerow(r)
 for r in rows(RAW/'transactions.csv'):
  tid=r['TransactionID']; tx_ids.add(tid); customer=r['customer_id']; customers.add(customer)
  email=r['P_emaildomain'] or ''; region=r['addr1'] or ''
  w['transactions.csv'].writerow({'transaction_id':tid,'customer_id':customer,'ts':r['ts'],'amount':r['TransactionAmt'],'channel':r['channel'],'product_cd':r['ProductCD'],'billing_region':region,'purchaser_email':email})
  if email: emails.add(email); w['purchaser_email.csv'].writerow({'from_transaction_id':tid,'to_email_domain':email})
  if region: regions.add(region); w['billed_in.csv'].writerow({'from_transaction_id':tid,'to_billing_region':region})
  if tid in selected_ts: selected_ts[tid]=r['ts']
 for customer in sorted(customers): w['customers.csv'].writerow({'customer_id':customer})
 for card,customer in sorted(cards.items()):
  w['cards.csv'].writerow({'card_id':card,'customer_id':customer})
  if customer: w['owns.csv'].writerow({'from_customer_id':customer,'to_card_id':card})
 for email in sorted(emails): w['email_domains.csv'].writerow({'email_domain':email})
 for region in sorted(regions): w['billing_regions.csv'].writerow({'billing_region':region})
 devices=set()
 for r in rows(RAW/'identity.csv'):
  did=profile_id(r)
  if not did: continue
  if did not in devices:
   devices.add(did); w['device_profiles.csv'].writerow({'device_profile_id':did,'device_info':r['DeviceInfo'] or '','os':r['id_30'] or '','browser':r['id_31'] or '','screen':r['id_33'] or '','device_type':r['DeviceType'] or ''})
  w['from_device.csv'].writerow({'from_transaction_id':r['TransactionID'],'to_device_profile_id':did})
 for r in closed:
  w['closed_cases.csv'].writerow({k:r[k] for k in FILES['closed_cases.csv']})
  w['on_card.csv'].writerow({'from_closed_case_id':r['case_id'],'to_card_id':r['card_id']})
  tids=[tid for tid in r['txn_ids'].split('|') if tid]
  for tid in tids:
   if tid in tx_ids: w['involves.csv'].writerow({'from_closed_case_id':r['case_id'],'to_transaction_id':tid})
  for card in filter(None,r['connected_card_ids'].split('|')): w['connected_to.csv'].writerow({'from_closed_case_id':r['case_id'],'to_card_id':card})
  ordered=sorted((selected_ts[tid],tid) for tid in tids if selected_ts.get(tid))
  for (before,first),(after,second) in zip(ordered,ordered[1:]):
   from datetime import datetime
   delta=int((datetime.fromisoformat(after)-datetime.fromisoformat(before)).total_seconds())
   w['next.csv'].writerow({'from_transaction_id':first,'to_transaction_id':second,'delta_seconds':delta})
 for h in handles.values(): h.close()
 manifest={'files':{},'benchmark_cases':[r['case_id'] for r in case_pack],'unpopulated_edges':['MADE','RELATED_DEVICE','SIMILAR_TO'],'reason':'No transaction-to-card source key; InvestigationCase records are not fabricated.'}
 for name in FILES:
  path=OUT/name
  with path.open(encoding='utf-8',newline='') as f: manifest['files'][name]={'rows':sum(1 for _ in f)-1,'bytes':path.stat().st_size,'header':next(csv.reader(path.open(encoding='utf-8',newline='')))}
 (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
 print(OUT/'manifest.json')
if __name__=='__main__': main()
