from __future__ import annotations
from dataclasses import dataclass
from .actions import recommendation
from .models import Action, EvidenceRequest, EvidenceRequestType, InvestigationContext, PolicyId, Verdict

@dataclass
class PolicyEvaluation:
    matched_policies: list[PolicyId]; non_matched_policies: list[PolicyId]; actions: list; required_approval_routes: list; requested_evidence: list[EvidenceRequest]; explanations: list[str]; evidence: list

class PolicyEngine:
    def evaluate(self, context: InvestigationContext) -> PolicyEvaluation:
        matches=[]; actions=[]; requests=[]; explanations=[]
        def apply(rule, condition, actions_to_add, explanation):
            if condition:
                matches.append(rule); explanations.append(f'{rule.value}: {explanation}')
                for action in actions_to_add: actions.append(recommendation(action,context.exposure_usd,f'{rule.value}: {explanation}'))
        weak=context.single_signal and context.fraud_probability < .70
        apply(PolicyId.R1, weak, [Action.VERIFY_WITH_CUSTOMER], 'verify before any block on a weak signal')
        if weak: requests.append(EvidenceRequest(type=EvidenceRequestType.CUSTOMER_VALIDATION,asked_after_step=0,assumed_response='pending simulated customer validation'))
        denied=context.customer_response=='denies'
        r2report=context.exposure_usd>1000 or bool(context.shared_device_profile) or context.another_customer_fraud
        apply(PolicyId.R2, denied and not context.recurring_match, [Action.BLOCK_CARD,Action.CREATE_CASE]+([Action.FILE_REPORT] if r2report else []), 'customer denies the transaction')
        apply(PolicyId.R3, context.customer_response=='confirms', [Action.CLOSE_NO_FRAUD], 'customer confirms the transaction')
        r4=context.customer_response=='no_reply'
        apply(PolicyId.R4,r4,[Action.MONITOR_CARD]+([Action.DECLINE_TRANSACTION] if context.pending_authorizations else [])+([Action.ESCALATE_TO_ANALYST] if context.exposure_usd>500 else []),'no reply within 24 hours')
        testing=context.small_online_authorizations>=3 and context.authorizations_within_hour and context.larger_purchase_followed
        apply(PolicyId.R5,testing,[Action.DECLINE_TRANSACTION,Action.STEP_UP_AUTH]+([Action.BLOCK_CARD] if context.cleared_purchase_over_100 else []),'card-testing sequence')
        shared=bool(context.shared_device_profile or context.shared_region_cluster or context.shared_recipient_email) and context.another_customer_fraud
        apply(PolicyId.R6,shared,[Action.CREATE_CASE,Action.FILE_REPORT,Action.MONITOR_CONNECTED_CARDS],'several cards show fraud from a shared origin')
        apply(PolicyId.R7,context.customer_response=='denies' and context.recurring_match,[Action.CREATE_CASE,Action.VERIFY_WITH_CUSTOMER,Action.WARN_CUSTOMER],'disputed charge matches recurring customer pattern')
        apply(PolicyId.R8,(context.verdict is Verdict.UNCERTAIN and context.exposure_usd>500) or context.evidence_conflicts,[Action.ESCALATE_TO_ANALYST],'uncertain/exposed or conflicting evidence')
        undocumented=not context.known_pattern and (context.coordinated_pattern or context.another_customer_fraud)
        apply(PolicyId.R9,undocumented,[Action.CREATE_CASE,Action.FILE_REPORT,Action.ESCALATE_TO_ANALYST],'coordinated/repeated cross-customer abuse fits no known pattern')
        r10=context.confirmed_fraud_cards>=2 or context.credentials_confirmed_compromised
        apply(PolicyId.R10,r10,[Action.BLOCK_ALL_CARDS],'two confirmed customer-card frauds or confirmed credential compromise')
        unique=[]
        for item in actions:
            if item.action not in [entry.action for entry in unique]: unique.append(item)
        return PolicyEvaluation(matches,[p for p in PolicyId if p not in matches],unique,sorted({a.route.value for a in unique}),requests,explanations,context.evidence)
