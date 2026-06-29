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
    description = models.TextField(blank=True)
    pass_mark = models.PositiveIntegerField(default=70, help_text="Minimum percentage to pass")
    time_limit_minutes = models.PositiveIntegerField(null=True, blank=True)
    max_attempts = models.PositiveIntegerField(default=3, help_text="Maximum attempts per student")
    randomize_questions = models.BooleanField(
        default=False,
        help_text="Shuffle question order for each attempt.",
    )
    questions_per_attempt = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="If set, only this many random questions are shown per attempt.",
    )
    is_published = models.BooleanField(default=False)
    show_correct_answers = models.BooleanField(default=False)
    is_final = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_final", "title"]

    def __str__(self):
        return self.title


class Question(TimeStampedModel):
    class QuestionType(models.TextChoices):
        MULTIPLE_CHOICE = "mcq", "Multiple Choice"
        TRUE_FALSE = "true_false", "True/False"
        MULTIPLE_ANSWER = "multi_answer", "Multiple Answers"
        FILL_BLANK = "fill_blank", "Short Answer"
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
    instructions = models.TextField(blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    max_score = models.PositiveIntegerField(default=100)
    attachment = models.FileField(upload_to="assignments/attachments/", blank=True, null=True)
    allow_resubmit = models.BooleanField(default=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ["module", "title"]

    def __str__(self):
        return self.title

    @property
    def level(self):
        return self.module.level

    @property
    def attachment_url(self):
        if not self.attachment:
            return ""
        try:
            return self.attachment.url
        except ValueError:
            return ""


class AssignmentSubmission(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under Review"
        GRADED = "graded", "Graded"
        LATE = "late", "Late Submission"
        RESUBMIT = "resubmit", "Return for Correction"
        APPROVED = "approved", "Approved"

    student = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="assignment_submissions")
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="submissions")
    file = models.FileField(upload_to="assignments/submissions/")
    notes = models.TextField(blank=True, help_text="Student submission notes")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    grade = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, help_text="Marks obtained")
    feedback = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    graded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("student", "assignment")
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.student} - {self.assignment.title}"

    @property
    def file_url(self):
        from apps.core.protected_media import protected_url

        return protected_url(self.file)

    @property
    def score_display(self):
        if self.grade is None:
            return ""
        return f"{self.grade} / {self.assignment.max_score}"
