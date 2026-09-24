from .models import Action, ApprovalRoute, ActionRecommendation
AUTO={Action.ALLOW_TRANSACTION,Action.MONITOR_CARD,Action.MONITOR_CONNECTED_CARDS,Action.WARN_CUSTOMER,Action.VERIFY_WITH_CUSTOMER,Action.STEP_UP_AUTH,Action.GENERATE_REPORT,Action.CREATE_CASE,Action.ESCALATE_TO_ANALYST,Action.CLOSE_NO_FRAUD}
def route_action(action: Action, exposure: float) -> ApprovalRoute:
    if action in AUTO:return ApprovalRoute.AUTO
    if action is Action.BLOCK_CARD:return ApprovalRoute.L1 if exposure <= 2500 else ApprovalRoute.L2
    return ApprovalRoute.L2 if action in {Action.BLOCK_ALL_CARDS,Action.FILE_REPORT} else ApprovalRoute.L1
def recommendation(action: Action, exposure: float, reason: str) -> ActionRecommendation:
    route=route_action(action, exposure); return ActionRecommendation(action=action,route=route,reason=reason,executable_by_agent=route is ApprovalRoute.AUTO)
