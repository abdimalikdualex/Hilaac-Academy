from django.contrib import messages

from django.http import JsonResponse

from django.shortcuts import get_object_or_404, redirect, render

from django.views.decorators.http import require_POST



from apps.certificates.services import maybe_issue_certificate

from apps.core.permissions import student_required

from apps.courses.access import student_has_full_access

from apps.courses.models import Enrollment, Lesson, Level

from apps.notifications.services import notify_course_completion



from .models import LessonProgress





def _check_enrollment(user, level):

    return student_has_full_access(user, level)





@student_required

def course_view(request, level_id):

    level = get_object_or_404(

        Level.objects.select_related("language").prefetch_related(
            "modules__lessons", "modules__quizzes", "modules__assignments", "quizzes"
        ),

        pk=level_id,

    )

    if not _check_enrollment(request.user, level):

        if level.is_free:

            messages.error(request, "Please enroll in this course first.")

        else:

            messages.error(request, "Purchase and payment approval are required to access this course.")

        return redirect("courses:detail", language_slug=level.language.slug, level_slug=level.slug)



    progress_map = {

        p.lesson_id: p

        for p in LessonProgress.objects.filter(student=request.user, lesson__module__level=level)

    }

    completed_lesson_ids = {lid for lid, p in progress_map.items() if p.is_completed}



    return render(

        request,

        "learning/course_view.html",

        {

            "level": level,

            "progress_map": progress_map,

            "completed_lesson_ids": completed_lesson_ids,

            "progress_pct": Enrollment.objects.get(student=request.user, level=level).progress_percentage,

        },

    )





@student_required

def lesson_player(request, lesson_id):

    lesson = get_object_or_404(

        Lesson.objects.select_related("module__level__language").prefetch_related("resources"),

        pk=lesson_id,

    )

    level = lesson.module.level



    if not lesson.is_preview and not _check_enrollment(request.user, level):

        from apps.courses.preview import get_enroll_or_checkout_url

        messages.error(request, "This lesson is locked. Enroll to unlock full access.")

        return redirect(get_enroll_or_checkout_url(level, request.user))



    progress, _ = LessonProgress.objects.get_or_create(student=request.user, lesson=lesson)

    progress_map = {

        p.lesson_id: p

        for p in LessonProgress.objects.filter(student=request.user, lesson__module__level=level)

    }

    completed_lesson_ids = {lid for lid, p in progress_map.items() if p.is_completed}

    enrollment = Enrollment.objects.filter(student=request.user, level=level).first()

    progress_pct = enrollment.progress_percentage if enrollment else 0



    sections = []

    prev_lesson = next_lesson = None

    found_current = False

    for module in level.modules.prefetch_related("lessons", "quizzes", "assignments").all():

        lessons = [ls for ls in module.lessons.all() if ls.is_published]

        sections.append({

            "module": module,

            "lessons": lessons,

            "quizzes": list(module.quizzes.all()),

            "assignments": list(module.assignments.filter(is_published=True)),

        })

        for ls in lessons:

            if found_current and next_lesson is None:

                next_lesson = ls

            if ls.id == lesson.id:

                found_current = True

            elif not found_current:

                prev_lesson = ls



    return render(

        request,

        "learning/lesson_player.html",

        {

            "lesson": lesson,

            "level": level,

            "progress": progress,

            "sections": sections,

            "completed_lesson_ids": completed_lesson_ids,

            "progress_pct": progress_pct,

            "prev_lesson": prev_lesson,

            "next_lesson": next_lesson,

        },

    )





def _check_level_completion(user, level):

    enrollment = Enrollment.objects.filter(student=user, level=level).first()

    if not enrollment:

        return

    if enrollment.progress_percentage >= 100 and enrollment.status == Enrollment.Status.ACTIVE:

        notify_course_completion(user, level)

        final_quiz = level.quizzes.filter(is_final=True).first()

        if not final_quiz:

            maybe_issue_certificate(user, level)





@student_required

@require_POST

def update_progress(request, lesson_id):

    lesson = get_object_or_404(Lesson, pk=lesson_id)

    level = lesson.module.level

    if not _check_enrollment(request.user, level):

        return JsonResponse({"error": "Not enrolled"}, status=403)



    watched = int(request.POST.get("watched_seconds", 0))

    progress, _ = LessonProgress.objects.get_or_create(student=request.user, lesson=lesson)

    was_completed = progress.is_completed

    progress.watched_seconds = max(progress.watched_seconds, watched)



    duration_seconds = lesson.duration_minutes * 60

    if duration_seconds > 0 and progress.watched_seconds >= duration_seconds * 0.9:

        progress.is_completed = True



    progress.save()



    if progress.is_completed and not was_completed:

        _check_level_completion(request.user, level)



    return JsonResponse({"watched_seconds": progress.watched_seconds, "is_completed": progress.is_completed})

