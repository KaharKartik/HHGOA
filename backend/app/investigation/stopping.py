from .models import InvestigationContext
def stop_investigation(context: InvestigationContext) -> tuple[bool, str]:
    if context.verification_settles_question: return True, 'verification response settles the question'
    if (context.fraud_probability >= .85 or context.fraud_probability <= .15) and len(context.evidence) >= 2: return True, 'calibrated probability is supported by at least two independent evidence items'
    if context.further_steps_unlikely_to_change: return True, 'further investigation is unlikely to change the decision'
    return False, ''
