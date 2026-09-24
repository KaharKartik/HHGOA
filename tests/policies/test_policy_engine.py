import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'backend'))
from app.investigation.models import InvestigationContext, Verdict, Action, PolicyId
from app.investigation.policy_engine import PolicyEngine

def run(**kwargs):
 data={'case_id':'T','fraud_probability':.5,'verdict':Verdict.UNCERTAIN,'exposure_usd':10}; data.update(kwargs); return PolicyEngine().evaluate(InvestigationContext(**data))
def actions(r): return {x.action for x in r.actions}
def test_r1(): assert Action.VERIFY_WITH_CUSTOMER in actions(run(single_signal=True))
def test_r2(): assert {Action.BLOCK_CARD,Action.CREATE_CASE} <= actions(run(customer_response='denies'))
def test_r3(): assert Action.CLOSE_NO_FRAUD in actions(run(customer_response='confirms'))
def test_r4(): assert {Action.MONITOR_CARD,Action.DECLINE_TRANSACTION} <= actions(run(customer_response='no_reply',pending_authorizations=True))
def test_r5(): assert {Action.DECLINE_TRANSACTION,Action.STEP_UP_AUTH,Action.BLOCK_CARD} <= actions(run(small_online_authorizations=3,authorizations_within_hour=True,larger_purchase_followed=True,cleared_purchase_over_100=True))
def test_r6(): assert {Action.CREATE_CASE,Action.FILE_REPORT,Action.MONITOR_CONNECTED_CARDS} <= actions(run(shared_device_profile='device',another_customer_fraud=True))
def test_r7_no_block():
 r=run(customer_response='denies',recurring_match=True); assert {Action.CREATE_CASE,Action.VERIFY_WITH_CUSTOMER,Action.WARN_CUSTOMER} <= actions(r); assert Action.BLOCK_CARD not in actions(r)
def test_r8(): assert Action.ESCALATE_TO_ANALYST in actions(run(exposure_usd=501))
def test_r9(): assert {Action.CREATE_CASE,Action.FILE_REPORT,Action.ESCALATE_TO_ANALYST} <= actions(run(known_pattern=False,coordinated_pattern=True))
def test_r10(): assert Action.BLOCK_ALL_CARDS in actions(run(confirmed_fraud_cards=2))
