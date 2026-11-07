from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.models import AccountStatus
from apps.notifications.models import Notification, NotificationChannel


@login_required
def notification_list(request):
    if request.user.account_status != AccountStatus.ACTIVE:
        raise PermissionDenied("An active account is required.")
    notifications = Notification.objects.filter(
        recipient=request.user,
        channel=NotificationChannel.IN_APP,
    ).order_by(
        "-created_at", "-id"
    )[:100]
    return render(request, "notifications/list.html", {"notifications": notifications})


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    if request.user.account_status != AccountStatus.ACTIVE:
        raise PermissionDenied("An active account is required.")
    notification = Notification.objects.filter(
        pk=notification_id,
        recipient=request.user,
    ).first()
    if notification is None:
        raise Http404
    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at"])
    return redirect("notifications:list")
