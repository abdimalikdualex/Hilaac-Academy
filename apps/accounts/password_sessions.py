"""Session helpers for password changes."""
from django.contrib.auth import SESSION_KEY
from django.contrib.sessions.models import Session
from django.utils import timezone


def logout_other_sessions(user, current_session_key=None):
    """End other active sessions for this user after a password change."""
    if not user or not user.pk:
        return 0
    user_key = str(user.pk)
    removed = 0
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        if current_session_key and session.session_key == current_session_key:
            continue
        try:
            data = session.get_decoded()
        except Exception:
            continue
        if data.get(SESSION_KEY) == user_key:
            session.delete()
            removed += 1
    return removed
