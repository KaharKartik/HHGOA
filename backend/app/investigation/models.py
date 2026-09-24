from __future__ import annotations
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field, model_validator

class PolicyId(str, Enum): R1='R1'; R2='R2'; R3='R3'; R4='R4'; R5='R5'; R6='R6'; R7='R7'; R8='R8'; R9='R9'; R10='R10'
class Action(str, Enum):
    ALLOW_TRANSACTION='ALLOW_TRANSACTION'; DECLINE_TRANSACTION='DECLINE_TRANSACTION'; MONITOR_CARD='MONITOR_CARD'; MONITOR_CONNECTED_CARDS='MONITOR_CONNECTED_CARDS'; WARN_CUSTOMER='WARN_CUSTOMER'; VERIFY_WITH_CUSTOMER='VERIFY_WITH_CUSTOMER'; STEP_UP_AUTH='STEP_UP_AUTH'; BLOCK_CARD='BLOCK_CARD'; BLOCK_ALL_CARDS='BLOCK_ALL_CARDS'; GENERATE_REPORT='GENERATE_REPORT'; CREATE_CASE='CREATE_CASE'; FILE_REPORT='FILE_REPORT'; ESCALATE_TO_ANALYST='ESCALATE_TO_ANALYST'; CLOSE_NO_FRAUD='CLOSE_NO_FRAUD'
class ApprovalRoute(str, Enum): AUTO='auto'; L1='L1'; L2='L2'
class Pattern(str, Enum): CARD_TESTING='card_testing'; CARD_NOT_PRESENT='card_not_present_fraud'; CARD_NOT_PRESENT_NEW_DEVICE='card_not_present_new_device'; OUT_OF_REGION='out_of_region_use'; ACCOUNT_TAKEOVER='account_takeover'; UNDOCUMENTED='undocumented'; NONE='none'
class CaseStatus(str, Enum): OPEN='open'; CLOSED_FRAUD='closed_fraud'; CLOSED_LEGITIMATE='closed_legitimate'; ESCALATED='escalated'
class Verdict(str, Enum): FRAUD='fraud'; LEGITIMATE='legitimate'; UNCERTAIN='uncertain'
class EvidenceSource(str, Enum): GRAPH='graph'; DOCUMENT='document'; CUSTOMER='customer'; EXTERNAL='external'
class EvidenceRequestType(str, Enum): CUSTOMER_VALIDATION='customer_validation'; STEP_UP_AUTH='step_up_auth'; ANALYST_INFO='analyst_info'

class EvidenceItem(BaseModel):
    claim: str = Field(min_length=1); source: EvidenceSource; ref: str = Field(min_length=1); entity_ids: list[str]
    @model_validator(mode='after')
    def traceable(self):
        if not self.entity_ids and not self.ref: raise ValueError('evidence needs an entity ID or source reference')
        return self
class EvidenceRequest(BaseModel): type: EvidenceRequestType; asked_after_step: int = Field(ge=0); assumed_response: str = Field(min_length=1)
class ActionRecommendation(BaseModel): action: Action; route: ApprovalRoute; reason: str = Field(min_length=1); executable_by_agent: bool = False
class ActionSet(BaseModel): initial: list[ActionRecommendation]; final: list[ActionRecommendation]; what_changed: str
class CaseRecord(BaseModel):
    status: CaseStatus; verdict: Verdict; fraud_probability: float = Field(ge=0, le=1); pattern: Pattern; pattern_description: str = ''; affected_txn_ids: list[str]; first_suspicious_txn_id: str = ''; connected_card_ids: list[str]; connected_device_profiles: list[str]; exposure_usd: float = Field(ge=0); evidence: list[EvidenceItem]; similar_prior_cases: list[str]; summary: str; written_to_graph: bool; graph_case_id: str = ''
    @model_validator(mode='after')
    def case_invariants(self):
        if self.pattern is Pattern.UNDOCUMENTED and not self.pattern_description: raise ValueError('undocumented pattern requires description')
        if self.pattern is not Pattern.UNDOCUMENTED and self.pattern_description: raise ValueError('pattern description is only for undocumented patterns')
        if self.verdict is Verdict.LEGITIMATE and (self.affected_txn_ids or self.exposure_usd): raise ValueError('legitimate case has no affected transactions or exposure')
        return self
class SARRecord(BaseModel):
    file: bool; reason: str; narrative: str = ''; subjects: list[str] = []; total_amount_usd: float = Field(ge=0); activity_dates: list[str] = []
    @model_validator(mode='after')
    def sar_invariants(self):
        if not self.file and (self.narrative or self.subjects or self.total_amount_usd or self.activity_dates): raise ValueError('non-filed SAR must use empty/zero fields')
        if self.file and (not self.narrative or len(self.activity_dates) != 2): raise ValueError('filed SAR needs narrative and two activity dates')
        return self
class InvestigationResult(BaseModel): case_id: str; case: CaseRecord; evidence_requests: list[EvidenceRequest]; next_best_actions: ActionSet; sar: SARRecord; stop_reason: str; tool_calls: int = Field(ge=0); tokens: int = Field(ge=0); latency_s: float = Field(ge=0)

class InvestigationContext(BaseModel):
    case_id: str; fraud_probability: float = Field(ge=0, le=1); verdict: Verdict; exposure_usd: float = Field(ge=0); evidence: list[EvidenceItem] = []; affected_transactions: list[tuple[str, float]] = []; customer_response: Literal['denies','confirms','no_reply'] | None = None; verification_settles_question: bool = False; single_signal: bool = False; pending_authorizations: bool = False; small_online_authorizations: int = 0; authorizations_within_hour: bool = False; larger_purchase_followed: bool = False; cleared_purchase_over_100: bool = False; shared_device_profile: str = ''; shared_region_cluster: str = ''; shared_recipient_email: str = ''; another_customer_fraud: bool = False; coordinated_pattern: bool = False; recurring_match: bool = False; evidence_conflicts: bool = False; credentials_confirmed_compromised: bool = False; confirmed_fraud_cards: int = 0; known_pattern: bool = True; pattern: Pattern = Pattern.NONE; pattern_description: str = ''; connected_card_ids: list[str] = []; further_steps_unlikely_to_change: bool = False; simulated_requests: list[EvidenceRequest] = []
