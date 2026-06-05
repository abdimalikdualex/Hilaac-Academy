from django.contrib import messages

from django.contrib.auth.decorators import login_required

from django.db.models import Q

from django.shortcuts import get_object_or_404, redirect, render

from django.views.decorators.http import require_POST



from apps.core.permissions import student_required

from apps.core.utils import log_audit

from apps.notifications.services import notify_enrollment

from apps.payments.models import Payment



from .access import get_course_access, student_has_full_access

from .models import CourseReview, Enrollment, Language, Level, Lesson, Wishlist





def _lines(text):

    if not text:

        return []

    return [ln.strip() for ln in text.splitlines() if ln.strip()]





def catalog(request):

    languages = Language.objects.filter(is_active=True).prefetch_related("levels")

    query = request.GET.get("q", "").strip()

    language_filter = request.GET.get("language", "")

    level_filter = request.GET.get("level", "")



    levels = Level.objects.filter(is_published=True).select_related("language")

    if query:

        levels = levels.filter(

            Q(name__icontains=query)

            | Q(description__icontains=query)

            | Q(keywords__icontains=query)

            | Q(language__name__icontains=query)

        )

    if language_filter:

        levels = levels.filter(language__slug=language_filter)

    if level_filter:

        levels = levels.filter(slug=level_filter)



    course_cards = []

    wishlist_ids = set()
    if request.user.is_authenticated and getattr(request.user, "is_student", False):
        wishlist_ids = set(
            Wishlist.objects.filter(student=request.user).values_list("level_id", flat=True)
        )

    for level in levels:

        access = get_course_access(request.user, level)

        course_cards.append({"level": level, "access": access, "in_wishlist": level.id in wishlist_ids})



    return render(

        request,

        "courses/catalog.html",

        {

            "languages": languages,

            "course_cards": course_cards,

            "query": query,

            "language_filter": language_filter,

            "level_filter": level_filter,

        },

    )





def course_detail(request, language_slug, level_slug):

    level = get_object_or_404(

        Level.objects.select_related("language", "instructor").prefetch_related(

            "modules__lessons", "modules__quizzes", "modules__assignments", "quizzes"

        ),

        language__slug=language_slug,

        slug=level_slug,

        is_published=True,

    )



    access = get_course_access(request.user, level)

    in_wishlist = False

    user_review = None

    completed_lesson_ids = set()

    progress_pct = 0

    continue_lesson = None



    if request.user.is_authenticated and request.user.is_student:

        in_wishlist = Wishlist.objects.filter(student=request.user, level=level).exists()

        user_review = CourseReview.objects.filter(student=request.user, level=level).first()

        if access["has_full_access"]:

            from apps.learning.models import LessonProgress



            completed_lesson_ids = set(

                LessonProgress.objects.filter(

                    student=request.user, lesson__module__level=level, is_completed=True

                ).values_list("lesson_id", flat=True)

            )

            enrollment = Enrollment.objects.filter(student=request.user, level=level).first()

            progress_pct = enrollment.progress_percentage if enrollment else 0



    from .preview import get_enroll_or_checkout_url, get_first_preview_lesson

    sections = []
    lesson_counter = 0

    for module in level.modules.all():

        raw_lessons = [ls for ls in module.lessons.all() if ls.is_published]
        lessons = []
        for ls in raw_lessons:
            lesson_counter += 1
            lessons.append({"lesson": ls, "number": lesson_counter})

        total = len(lessons)

        completed = sum(1 for item in lessons if item["lesson"].id in completed_lesson_ids)

        duration = sum(item["lesson"].duration_minutes for item in lessons)

        if continue_lesson is None and access["has_full_access"]:

            for item in lessons:

                ls = item["lesson"]

                if ls.id not in completed_lesson_ids:

                    continue_lesson = ls

                    break

        sections.append(

            {

                "module": module,

                "lessons": lessons,

                "quizzes": list(module.quizzes.all()),

                "assignments": [a for a in module.assignments.all() if a.is_published],

                "total": total,

                "completed": completed,

                "pct": round(completed / total * 100) if total else 0,

                "duration": duration,

            }

        )



    reviews = level.reviews.select_related("student").all()[:30]



    context = {

        "level": level,

        "access": access,

        "is_enrolled": access["has_full_access"],

        "in_wishlist": in_wishlist,

        "sections": sections,

        "completed_lesson_ids": completed_lesson_ids,

        "progress_pct": progress_pct,

        "continue_lesson": continue_lesson,

        "final_quizzes": list(level.quizzes.all()),

        "objectives": _lines(level.learning_objectives),

        "skills": _lines(level.skills),

        "audience": _lines(level.target_audience),

        "requirements": _lines(level.requirements),

        "reviews": reviews,

        "user_review": user_review,

        "can_review": access["has_full_access"],

        "first_preview_lesson": get_first_preview_lesson(level),

        "enroll_url": get_enroll_or_checkout_url(level, request.user),

    }

    return render(request, "courses/detail.html", context)





def preview_lesson(request, lesson_id):

    lesson = get_object_or_404(

        Lesson.objects.select_related("module__level__language", "module__level__instructor"),

        pk=lesson_id,

        is_published=True,

    )

    level = lesson.module.level

    from .preview import get_enroll_or_checkout_url

    if not lesson.is_preview:

        messages.info(request, "This lesson is locked. Enroll to unlock full access.")

        return redirect(get_enroll_or_checkout_url(level, request.user))

    Lesson.objects.filter(pk=lesson.pk).update(preview_views=lesson.preview_views + 1)

    has_access = student_has_full_access(request.user, level) if request.user.is_authenticated else False

    preview_lessons = Lesson.objects.filter(

        module__level=level, is_preview=True, is_published=True

    ).select_related("module").order_by("module__order", "order")



    return render(

        request,

        "courses/preview_player.html",

        {
            "lesson": lesson,
            "level": level,
            "is_enrolled": has_access,
            "preview_lessons": preview_lessons,
            "enroll_url": get_enroll_or_checkout_url(level, request.user),
        },

    )





@login_required

@require_POST

def submit_review(request, level_id):

    level = get_object_or_404(Level, pk=level_id, is_published=True)

    if not student_has_full_access(request.user, level):

        messages.error(request, "Only enrolled students can review this course.")

        return redirect("courses:detail", language_slug=level.language.slug, level_slug=level.slug)



    try:

        rating = int(request.POST.get("rating", 5))

    except (TypeError, ValueError):

        rating = 5

    rating = max(1, min(5, rating))

    comment = request.POST.get("comment", "").strip()



    CourseReview.objects.update_or_create(

        student=request.user, level=level, defaults={"rating": rating, "comment": comment}

    )

    messages.success(request, "Thank you! Your review has been saved.")

    return redirect(level.get_absolute_url() + "#reviews")





@student_required

def toggle_wishlist(request, level_id):

    level = get_object_or_404(Level, pk=level_id, is_published=True)

    if level.is_free:

        messages.info(request, "Free courses don't need to be wishlisted — enroll directly.")

        return redirect(level.get_absolute_url())



    access = get_course_access(request.user, level)

    if access["has_full_access"]:

        messages.info(request, "You're already enrolled in this course.")

        return redirect(level.get_absolute_url())



    item = Wishlist.objects.filter(student=request.user, level=level).first()

    if item:

        item.delete()

        messages.info(request, "Removed from your wishlist.")

    else:

        Wishlist.objects.create(student=request.user, level=level)

        messages.success(request, "Added to your wishlist.")

    return redirect(request.META.get("HTTP_REFERER", level.get_absolute_url()))





@student_required

def enroll(request, level_id):

    level = get_object_or_404(Level, pk=level_id, is_published=True)

    access = get_course_access(request.user, level)



    if access["has_full_access"]:

        messages.info(request, "You already have access to this course.")

        return redirect("learning:course_view", level_id=level.id)



    if access["pending_payment"]:

        messages.info(request, "Your payment is pending verification.")

        return redirect("payments:pending", payment_id=access["pending_payment"].pk)



    if level.is_free:

        Enrollment.objects.create(student=request.user, level=level)

        notify_enrollment(request.user, level)

        log_audit(request, "course_enroll", "Level", level.pk, level.name)

        messages.success(request, f"Successfully enrolled in {level.name}!")

        return redirect("learning:course_view", level_id=level.id)



    return redirect("payments:checkout", level_id=level.id)


