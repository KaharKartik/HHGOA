from .models import EvidenceItem
def independent_evidence_count(items: list[EvidenceItem]) -> int:
    return len({(item.source.value,item.ref) for item in items})
