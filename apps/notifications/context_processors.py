"""Expose the current user's unread in-app notification count to the app shell."""

from apps.notifications.models import Notification, NotificationChannel


def unread_in_app_count(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"unread_notification_count": 0}
    return {
        "unread_notification_count": Notification.objects.filter(
            recipient_id=user.pk,
            channel=NotificationChannel.IN_APP,
            read_at__isnull=True,
        ).count()
    }
