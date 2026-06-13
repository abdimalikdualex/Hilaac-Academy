"""Central audit trail recording and metadata."""

from __future__ import annotations



from typing import Any, Optional



from django.http import HttpRequest



from .models import AuditLog



# Action code -> module name for dashboard filters

ACTION_MODULES: dict[str, str] = {

    "user_login": "Authentication",

    "user_logout": "Authentication",

    "user_login_failed": "Authentication",

    "user_register": "Users",

    "profile_update": "Users",

    "profile_photo_remove": "Users",

    "profile_password_change": "Users",

    "user_toggle_active": "Users",

    "student_delete": "Users",

    "instructor_delete": "Users",

    "course_create": "Courses",

    "course_update": "Courses",

    "course_soft_delete": "Courses",

    "course_publish_toggle": "Courses",

    "course_archive_toggle": "Courses",

    "module_create": "Courses",

    "module_update": "Courses",

    "module_soft_delete": "Courses",

    "lesson_create": "Courses",

    "lesson_update": "Courses",

    "lesson_soft_delete": "Courses",

    "course_enroll": "Courses",

    "assignment_create": "Assignments",

    "assignment_update": "Assignments",

    "assignment_delete": "Assignments",

    "assignment_extend_due": "Assignments",

    "assignment_submit": "Assignments",

    "assignment_grade": "Assignments",

    "quiz_create": "Quizzes",

    "quiz_update": "Quizzes",

    "quiz_delete": "Quizzes",

    "payment_approve": "Payments",

    "payment_refund": "Payments",

    "certificate_issue": "Certificates",

    "certificate_delete": "Certificates",

    "library_soft_delete": "Library",

    "notification_send": "Notifications",

    "platform_video_save": "Videos",

    "platform_video_toggle": "Videos",

    "platform_video_delete": "Videos",

    "site_settings_update": "Settings",

    "partner_school_save": "CMS",

    "partner_school_toggle": "CMS",

    "partner_school_delete": "CMS",

    "faq_delete": "CMS",

}



MODEL_MODULES: dict[str, str] = {

    "User": "Users",

    "Level": "Courses",

    "Module": "Courses",

    "Lesson": "Courses",

    "Assignment": "Assignments",

    "AssignmentSubmission": "Assignments",

    "Quiz": "Quizzes",

    "Payment": "Payments",

    "Certificate": "Certificates",

    "LibraryResource": "Library",

    "Notification": "Notifications",

    "PlatformIntroductionVideo": "Videos",

    "SiteSettings": "Settings",

    "PartnerSchool": "CMS",

    "FAQ": "CMS",

}



ACTION_LABELS: dict[str, str] = {

    "user_login": "User logged in",

    "user_logout": "User logged out",

    "user_login_failed": "Failed login attempt",

    "user_register": "Account created",

    "profile_update": "Profile updated",

    "profile_photo_remove": "Profile photo removed",

    "profile_password_change": "Password changed",

    "user_toggle_active": "User account status changed",

    "student_delete": "Student account deleted",

    "instructor_delete": "Instructor account deleted",

    "student_create": "Student account created",

    "instructor_create": "Instructor account created",

    "student_update": "Student profile updated",

    "instructor_update": "Instructor profile updated",

    "course_create": "Course created",

    "course_update": "Course updated",

    "course_soft_delete": "Course deleted",

    "course_publish_toggle": "Course publish status changed",

    "course_archive_toggle": "Course archive status changed",

    "module_create": "Module created",

    "module_update": "Module updated",

    "module_soft_delete": "Module deleted",

    "lesson_create": "Lesson created",

    "lesson_update": "Lesson updated",

    "lesson_soft_delete": "Lesson deleted",

    "course_enroll": "Course enrollment",

    "assignment_create": "Assignment created",

    "assignment_update": "Assignment updated",

    "assignment_delete": "Assignment deleted",

    "assignment_extend_due": "Assignment due date extended",

    "assignment_submit": "Assignment submitted",

    "assignment_grade": "Assignment graded",

    "quiz_create": "Quiz created",

    "quiz_update": "Quiz updated",

    "quiz_delete": "Quiz deleted",

    "payment_approve": "Payment approved",

    "payment_refund": "Payment refunded",

    "certificate_issue": "Certificate issued",

    "certificate_delete": "Certificate deleted",

    "library_soft_delete": "Library resource deleted",

    "notification_send": "Notification sent",

    "platform_video_save": "Platform video saved",

    "platform_video_toggle": "Platform video status changed",

    "platform_video_delete": "Platform video deleted",

    "site_settings_update": "System settings updated",

    "partner_school_save": "Partner school saved",

    "partner_school_toggle": "Partner school status changed",

    "partner_school_delete": "Partner school deleted",

    "faq_delete": "FAQ deleted",
}





def resolve_module(action: str, model_name: str = "") -> str:

    if action in ACTION_MODULES:

        return ACTION_MODULES[action]

    if model_name in MODEL_MODULES:

        return MODEL_MODULES[model_name]

    prefix = action.split("_")[0] if action else ""

    prefix_map = {

        "course": "Courses",

        "module": "Courses",

        "lesson": "Courses",

        "assignment": "Assignments",

        "quiz": "Quizzes",

        "payment": "Payments",

        "user": "Users",

        "profile": "Users",

        "student": "Users",

        "instructor": "Users",

        "certificate": "Certificates",

        "library": "Library",

        "notification": "Notifications",

        "platform": "Videos",

        "site": "Settings",

    }

    return prefix_map.get(prefix, "System")





def format_description(action: str, details: str = "", model_name: str = "", object_id: str = "") -> str:

    label = ACTION_LABELS.get(action, action.replace("_", " ").title())

    if details:

        return f"{label}: {details}"

    if model_name and object_id:

        return f"{label} ({model_name} #{object_id})"

    return label





def _user_snapshot(user) -> tuple[str, str]:

    if not user:

        return "", ""

    name = user.get_full_name() or user.username or ""

    role = getattr(user, "role", "") or ""

    return name, role





def record_audit(

    action: str,

    *,

    request: Optional[HttpRequest] = None,

    user=None,

    model_name: str = "",

    object_id: str = "",

    details: str = "",

    old_values: Optional[dict[str, Any]] = None,

    new_values: Optional[dict[str, Any]] = None,

    status: str = AuditLog.Status.SUCCESS,

    ip_address: Optional[str] = None,

    user_agent: str = "",

    user_display_name: str = "",

    user_role: str = "",

) -> AuditLog:

    from .utils import get_client_ip



    if request is not None:

        if user is None and request.user.is_authenticated:

            user = request.user

        if not ip_address:

            ip_address = get_client_ip(request)

        if not user_agent:

            user_agent = (request.META.get("HTTP_USER_AGENT") or "")[:500]



    display_name, role = _user_snapshot(user)

    if user_display_name:

        display_name = user_display_name

    if user_role:

        role = user_role



    module = resolve_module(action, model_name)

    description = format_description(action, details, model_name, object_id)



    return AuditLog.objects.create(

        user=user if getattr(user, "pk", None) else None,

        user_display_name=display_name,

        user_role=role,

        action=action,

        module=module,

        description=description,

        model_name=model_name,

        object_id=str(object_id) if object_id else "",

        details=details,

        old_values=old_values or {},

        new_values=new_values or {},

        ip_address=ip_address,

        user_agent=user_agent,

        status=status,

    )


