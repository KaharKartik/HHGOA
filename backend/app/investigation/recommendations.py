from .models import ActionSet, InvestigationContext
from .policy_engine import PolicyEngine
def recommend_actions(context: InvestigationContext) -> ActionSet:
    initial=PolicyEngine().evaluate(context)
    final_context=context.model_copy(update={'simulated_requests': context.simulated_requests})
    final=PolicyEngine().evaluate(final_context)
    changed='nothing' if [x.action for x in initial.actions]==[x.action for x in final.actions] else 'simulated evidence changed the policy recommendation'
    return ActionSet(initial=initial.actions,final=final.actions,what_changed=changed)
