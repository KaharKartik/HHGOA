from .models import InvestigationContext, SARRecord, Verdict

def _sar_threshold_met(context: InvestigationContext) -> bool:
    """Return True when the SAR applicable threshold would be met (used by recommendation nodes)."""
    applicable = (
        context.exposure_usd > 1000
        or bool(context.shared_device_profile)
        or bool(context.shared_region_cluster)
        or context.another_customer_fraud
        or context.coordinated_pattern
        or not context.known_pattern
    )
    return context.verdict is Verdict.FRAUD and applicable

def decide_sar(context: InvestigationContext) -> SARRecord:
    applicable = (
        context.exposure_usd > 1000
        or bool(context.shared_device_profile)
        or bool(context.shared_region_cluster)
        or context.another_customer_fraud
        or context.coordinated_pattern
        or not context.known_pattern
    )
    file = context.verdict is Verdict.FRAUD and applicable
    if not file:
        return SARRecord(file=False, reason='No report trigger under R2/R6/R9', total_amount_usd=0)
    return SARRecord(
        file=True,
        reason='SAR threshold met under R2/R6/R9',
        narrative='Structured SAR narrative must be supplied by the investigation workflow.',
        subjects=[],
        total_amount_usd=context.exposure_usd,
        activity_dates=['', ''],
    )

