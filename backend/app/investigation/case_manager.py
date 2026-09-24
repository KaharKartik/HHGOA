from .models import CaseRecord, CaseStatus, InvestigationResult
def create_case(result: InvestigationResult) -> CaseRecord | None:
    case=result.case
    disputed=any(request.type.value=='customer_validation' for request in result.evidence_requests)
    if case.fraud_probability >= .30 or result.evidence_requests or disputed:
        return case.model_copy(update={'written_to_graph':False,'graph_case_id':''})
    return None
