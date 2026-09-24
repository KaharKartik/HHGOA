import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'backend'))
from app.investigation.actions import route_action
from app.investigation.exposure import calculate_exposure
from app.investigation.models import *
from app.investigation.sar import decide_sar
from app.investigation.stopping import stop_investigation

def ctx(**kw):
 data={'case_id':'T','fraud_probability':.9,'verdict':Verdict.FRAUD,'exposure_usd':1001}; data.update(kw); return InvestigationContext(**data)
def test_routing():
 assert route_action(Action.BLOCK_CARD,2500) is ApprovalRoute.L1; assert route_action(Action.BLOCK_CARD,2500.01) is ApprovalRoute.L2; assert route_action(Action.FILE_REPORT,0) is ApprovalRoute.L2
def test_exposure(): assert calculate_exposure([('1',-3),('2',4)])==7
def test_stopping(): assert stop_investigation(ctx(evidence=[EvidenceItem(claim='a',source='graph',ref='q1',entity_ids=['1']),EvidenceItem(claim='b',source='document',ref='q2',entity_ids=['2'])]))[0]
def test_sar(): assert decide_sar(ctx()).file; assert not decide_sar(ctx(verdict=Verdict.UNCERTAIN)).file
def test_answer_contract():
 with pytest.raises(ValueError): CaseRecord(status=CaseStatus.CLOSED_LEGITIMATE,verdict=Verdict.LEGITIMATE,fraud_probability=0,pattern=Pattern.NONE,affected_txn_ids=['x'],connected_card_ids=[],connected_device_profiles=[],exposure_usd=0,evidence=[],similar_prior_cases=[],summary='x',written_to_graph=False)
