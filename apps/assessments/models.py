from django.db import models

from apps.core.models import TimeStampedModel


class Quiz(TimeStampedModel):
    module = models.ForeignKey(
        "courses.Module",
        on_delete=models.CASCADE,
        related_name="quizzes",
        null=True,
        blank=True,
    )
    level = models.ForeignKey(
        "courses.Level",
        on_delete=models.CASCADE,
        related_name="quizzes",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=200)
    pass_mark = models.PositiveIntegerField(default=70, help_text="Minimum percentage to pass")
    time_limit_minutes = models.PositiveIntegerField(null=True, blank=True)
    is_final = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_final", "title"]

    def __str__(self):
        return self.title


class Question(TimeStampedModel):
    class QuestionType(models.TextChoices):
        MULTIPLE_CHOICE = "mcq", "Multiple Choice"
        TRUE_FALSE = "true_false", "True/False"
        FILL_BLANK = "fill_blank", "Fill in the Blank"
        READING = "reading", "Reading Comprehension"
        LISTENING = "listening", "Listening"

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    question_type = models.CharField(max_length=20, choices=QuestionType.choices, default=QuestionType.MULTIPLE_CHOICE)
    text = models.TextField()
    passage = models.TextField(blank=True, help_text="Reading passage if applicable")
    audio_url = models.URLField(blank=True)
    correct_answer = models.CharField(max_length=500, blank=True, help_text="For fill-in-the-blank")
    order = models.PositiveIntegerField(default=0)
    points = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.text[:80]


class AnswerOption(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text[:50]


class QuizAttempt(TimeStampedModel):
    student = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="quiz_attempts")
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    passed = models.BooleanField(default=False)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.student} - {self.quiz.title} ({self.score}%)"


class Assignment(TimeStampedModel):
    module = models.ForeignKey("courses.Module", on_delete=models.CASCADE, related_name="assignments")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    max_score = models.PositiveIntegerField(default=100)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["module", "title"]

    def __str__(self):
        return self.title


class AssignmentSubmission(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending Review"
        APPROVED = "approved", "Approved"
        RESUBMIT = "resubmit", "Resubmit Required"
        GRADED = "graded", "Graded"

    student = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="assignment_submissions")
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")
    file = models.FileField(upload_to="assignments/submissions/")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    grade = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "assignment")
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.student} - {self.assignment.title}"
