from .models import Claim


def claim_alerts(request):
    """Adds the number of pending claims on the user's items to every template (navbar badge)."""
    if request.user.is_authenticated:
        count = Claim.objects.filter(item__user=request.user, status=Claim.PENDING).count()
        return {'pending_claim_alerts': count}
    return {'pending_claim_alerts': 0}
