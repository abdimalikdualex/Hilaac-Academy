"""
Seed Hilaac Academy data.

SAFE BY DEFAULT — never overwrites or resurrects courses unless you pass --demo --force.

  python manage.py seed_data              # admin/student accounts + languages only
  python manage.py seed_data --demo       # first-time demo courses (once per database)
  python manage.py seed_data --demo --force  # dev only: rebuild demo curriculum (destructive)
"""
from django.core.management.base import BaseCommand
from django.db import IntegrityError

from apps.accounts.models import User
from apps.assessments.models import AnswerOption, Question, Quiz
from apps.cms.models import FAQ, SiteStatistic, Testimonial
from apps.core.models import SiteSettings
from apps.courses.models import Language, Lesson, Level, Module
from apps.courses.preview import enforce_single_preview
from apps.library.models import LibraryResource


class Command(BaseCommand):
    help = "Seed users/languages (safe) or optional one-time demo content"

    def add_arguments(self, parser):
        parser.add_argument(
            "--demo",
            action="store_true",
            help="Include demo courses, lessons, CMS samples (runs once per database)",
        )
        parser.add_argument(
            "--if-empty",
            action="store_true",
            help="Alias for --demo (kept for deploy scripts)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="With --demo: overwrite demo prices/curriculum (development only)",
        )

    def handle(self, *args, **options):
        include_demo = options["demo"] or options["if_empty"]
        site = SiteSettings.get()

        self._seed_users()

        english, kiswahili = self._seed_languages()

        if not include_demo:
            self.stdout.write(self.style.SUCCESS("Accounts and languages ready (no demo courses touched)."))
            return

        if site.demo_content_seeded and not options["force"]:
            self.stdout.write(
                "Demo content was already seeded for this database; skipping. "
                "Your courses are never auto-restored. Use --demo --force only in development."
            )
            return

        if Level.objects.exists() and not options["force"]:
            self.stdout.write(
                "Active courses already exist; skipping demo seed to protect your data. "
                "Use --demo --force only if you intend to reset demo curriculum."
            )
            if not site.demo_content_seeded:
                site.demo_content_seeded = True
                site.save(update_fields=["demo_content_seeded"])
            return

        self.stdout.write("Seeding one-time demo content...")
        self._seed_demo_courses(english, kiswahili, force=options["force"])
        self._seed_demo_cms(english, kiswahili)

        site.demo_content_seeded = True
        site.save(update_fields=["demo_content_seeded"])
        self.stdout.write(self.style.SUCCESS("Demo seed complete. This will not run again unless --demo --force."))

    def _seed_users(self):
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                username="admin",
                email="admin@hilaacacademy.com",
                password="admin123",
                role=User.Role.SUPER_ADMIN,
                first_name="Super",
                last_name="Admin",
                is_verified=True,
            )
            self.stdout.write(self.style.SUCCESS("Created super admin (admin / admin123)"))

        if not User.objects.filter(username="student").exists():
            User.objects.create_user(
                username="student",
                email="student@example.com",
                password="student123",
                role=User.Role.STUDENT,
                first_name="Test",
                last_name="Student",
                country="Kenya",
                is_active=True,
                is_verified=True,
            )
            self.stdout.write(self.style.SUCCESS("Created test student (student / student123)"))

    def _seed_languages(self):
        english, _ = Language.objects.get_or_create(
            slug="english",
            defaults={"name": "English", "description": "Learn English from beginner to expert level."},
        )
        kiswahili, _ = Language.objects.get_or_create(
            slug="kiswahili",
            defaults={"name": "Kiswahili", "description": "Learn Kiswahili from beginner to advanced level."},
        )
        return english, kiswahili

    def _level_get_or_create(self, language, slug, defaults):
        """Never resurrect soft-deleted or duplicate slug rows."""
        tombstone = Level.all_objects.filter(language=language, slug=slug).first()
        if tombstone:
            if tombstone.is_deleted:
                self.stdout.write(f"  Skip {slug} (in recycle bin — restore manually if needed)")
            return tombstone, False
        try:
            level, created = Level.objects.get_or_create(language=language, slug=slug, defaults=defaults)
            return level, created
        except IntegrityError:
            existing = Level.all_objects.filter(language=language, slug=slug).first()
            return existing, False

    def _seed_demo_courses(self, english, kiswahili, force=False):
        english_levels = [
            ("Beginner (A1)", "a1", 0, True, 0),
            ("Elementary (A2)", "a2", 1, False, 20),
            ("Intermediate (B1)", "b1", 2, False, 28),
            ("Upper Intermediate (B2)", "b2", 3, False, 35),
            ("Advanced (C1)", "c1", 4, False, 45),
            ("Expert (C2)", "c2", 5, False, 55),
        ]
        english_keywords = {
            "a1": "english,beginner,a1,alphabet,greetings,basic",
            "a2": "english,elementary,a2,grammar,conversation",
            "b1": "english,intermediate,b1,writing,speaking,workplace",
            "b2": "english,upper-intermediate,b2,business,communication",
            "c1": "english,advanced,c1,presentation,professional",
            "c2": "english,expert,c2,fluency,academic",
        }

        for name, slug, order, is_free, price in english_levels:
            level, created = self._level_get_or_create(
                english,
                slug,
                defaults={
                    "name": name,
                    "subtitle": f"Build confidence in {name} English step by step",
                    "level_tag": {
                        "a1": "beginner", "a2": "beginner", "b1": "intermediate",
                        "b2": "intermediate", "c1": "advanced", "c2": "advanced",
                    }.get(slug, "beginner"),
                    "order": order,
                    "is_free": is_free,
                    "price": price,
                    "is_published": True,
                    "keywords": english_keywords.get(slug, "english,language"),
                    "description": f"Master {name} English with structured video lessons, quizzes, and certificates.",
                    "learning_objectives": "Speak confidently in everyday situations\nWrite clear emails and messages\nUnderstand native speakers at this level",
                    "skills": "Conversation\nGrammar\nVocabulary\nListening",
                    "target_audience": "Somali speakers learning English\nStudents preparing for work or study\nAnyone starting at this level",
                    "requirements": "Basic smartphone or computer\nInternet connection\nWillingness to practice daily",
                    "duration_weeks": 4 + order,
                },
            )
            if created:
                if slug == "a1":
                    self._sync_english_a1_curriculum(level, force=force)
                else:
                    self._create_sample_content(level, "English")
            elif force and not level.is_deleted:
                if level.price != price:
                    level.price = price
                    level.save(update_fields=["price"])
                if slug == "a1":
                    self._sync_english_a1_curriculum(level, force=force)

        kiswahili_levels = [
            ("Beginner", "beginner", 0, True, 0),
            ("Intermediate", "intermediate", 1, False, 23),
            ("Advanced", "advanced", 2, False, 39),
        ]
        kiswahili_keywords = {
            "beginner": "kiswahili,beginner,swahili,greetings",
            "intermediate": "kiswahili,intermediate,grammar",
            "advanced": "kiswahili,advanced,business,professional",
        }

        for name, slug, order, is_free, price in kiswahili_levels:
            level, created = self._level_get_or_create(
                kiswahili,
                slug,
                defaults={
                    "name": name,
                    "subtitle": f"Learn Kiswahili at {name} level with expert guidance",
                    "level_tag": slug,
                    "order": order,
                    "is_free": is_free,
                    "price": price,
                    "is_published": True,
                    "keywords": kiswahili_keywords.get(slug, "kiswahili,swahili"),
                    "description": f"Learn Kiswahili at {name} level with expert-designed lessons.",
                    "learning_objectives": "Hold basic conversations in Kiswahili\nUnderstand common phrases and grammar\nBuild vocabulary for daily life",
                    "skills": "Speaking\nListening\nVocabulary\nGrammar",
                    "target_audience": "Somali speakers in East Africa\nTravelers and professionals\nBeginners to advanced learners",
                    "requirements": "No prior Kiswahili required for Beginner\nInternet access for video lessons",
                    "duration_weeks": 4 + order * 2,
                },
            )
            if created:
                self._create_sample_content(level, "Kiswahili")
            elif force and not level.is_deleted and level.price != price:
                level.price = price
                level.save(update_fields=["price"])

        if force:
            self._ensure_preview_lessons()
            self._ensure_overview_content()

    def _seed_demo_cms(self, english, kiswahili):
        library_items = [
            ("English Grammar Basics", LibraryResource.Category.GRAMMAR, english, "Essential English grammar rules for beginners."),
            ("Kiswahili Vocabulary List", LibraryResource.Category.VOCABULARY, kiswahili, "Common Kiswahili words and phrases."),
            ("English Practice Worksheets", LibraryResource.Category.WORKSHEETS, english, "Printable worksheets for daily practice."),
            ("Kiswahili Grammar Guide", LibraryResource.Category.KISWAHILI_NOTES, kiswahili, "Complete Kiswahili grammar reference."),
            ("English Vocabulary Book", LibraryResource.Category.ENGLISH_NOTES, english, "500 essential English words with examples."),
        ]
        for title, category, lang, desc in library_items:
            LibraryResource.objects.get_or_create(
                title=title,
                defaults={"category": category, "language": lang, "description": desc, "is_published": True},
            )

        stats = [
            ("Total Students", 500, "students", 0),
            ("Total Courses", 9, "courses", 1),
            ("Graduates", 120, "graduates", 2),
            ("Certificates Issued", 150, "certificates", 3),
        ]
        for label, value, icon, order in stats:
            SiteStatistic.objects.get_or_create(label=label, defaults={"value": value, "icon": icon, "order": order})

        testimonials = [
            ("Amina Hassan", "English Beginner (A1)", "Hilaac Academy helped me learn English from scratch. Now I can communicate confidently at work!", 5),
            ("Mohamed Ali", "Kiswahili Beginner", "The Kiswahili course is excellent. Clear lessons and great support via WhatsApp.", 5),
            ("Fatima Abdi", "English Intermediate (B1)", "I passed my job interview thanks to the workplace English module. Highly recommended!", 5),
        ]
        for i, (name, course, quote, rating) in enumerate(testimonials):
            Testimonial.objects.get_or_create(
                student_name=name,
                course_name=course,
                defaults={"quote": quote, "rating": rating, "order": i, "is_featured": True},
            )

        faqs = [
            ("What languages do you offer?", "We currently offer English and Kiswahili courses for all proficiency levels."),
            ("Are there free courses?", "Yes! Both English Beginner (A1) and Kiswahili Beginner courses are completely free."),
            ("How do I get my certificate?", "Complete all lessons and pass the final assessment. Your certificate will be generated automatically."),
            ("What payment methods are accepted?", "We accept M-Pesa (Kenya) and EVC Plus (Somalia) for paid courses."),
            ("Can I learn on my phone?", "Absolutely! Hilaac Academy is mobile-first and works on all devices. You can even install it as an app."),
        ]
        for i, (question, answer) in enumerate(faqs):
            FAQ.objects.get_or_create(question=question, defaults={"answer": answer, "order": i})

    def _create_sample_content(self, level, lang_name):
        if level.is_deleted:
            return
        module, _ = Module.objects.get_or_create(
            level=level,
            order=1,
            defaults={"title": "Module 1: Getting Started", "description": f"Introduction to {level.name} {lang_name}."},
        )

        lessons = [
            ("Greetings & Introductions", "video", "Learn basic greetings and how to introduce yourself.", 15),
            ("Numbers & Counting", "video", "Master numbers from 1 to 100.", 12),
            ("Reading: Daily Conversations", "reading", "Read and understand simple daily conversation texts.", 10),
            ("Vocabulary: Common Words", "vocabulary", "Practice the 50 most common words at this level.", 8),
            ("PDF Study Notes", "pdf", "Downloadable notes for this module.", 5),
        ]

        for i, (title, ltype, content, duration) in enumerate(lessons):
            Lesson.objects.get_or_create(
                module=module,
                order=i + 1,
                defaults={
                    "title": title,
                    "lesson_type": ltype,
                    "content": content,
                    "duration_minutes": duration,
                    "video_url": "https://www.w3schools.com/html/mov_bbb.mp4" if ltype == "video" else "",
                    "is_preview": False,
                },
            )

        quiz, _ = Quiz.objects.get_or_create(
            module=module,
            defaults={"title": f"{module.title} Quiz", "pass_mark": 70, "time_limit_minutes": 15},
        )

        q1, _ = Question.objects.get_or_create(
            quiz=quiz,
            order=1,
            defaults={
                "text": f"What is the first thing you learn in {level.name}?",
                "question_type": Question.QuestionType.MULTIPLE_CHOICE,
            },
        )
        if not q1.options.exists():
            AnswerOption.objects.bulk_create([
                AnswerOption(question=q1, text="Greetings", is_correct=True),
                AnswerOption(question=q1, text="Advanced grammar", is_correct=False),
                AnswerOption(question=q1, text="Business writing", is_correct=False),
            ])

        q2, _ = Question.objects.get_or_create(
            quiz=quiz,
            order=2,
            defaults={
                "text": "Read the passage and answer: What is the main topic?",
                "question_type": Question.QuestionType.READING,
                "passage": f"This module introduces {level.name} {lang_name}. Students learn greetings, numbers, and basic conversation skills.",
            },
        )
        if not q2.options.exists():
            AnswerOption.objects.bulk_create([
                AnswerOption(question=q2, text="Basic language skills", is_correct=True),
                AnswerOption(question=q2, text="Advanced literature", is_correct=False),
            ])

        final, _ = Quiz.objects.get_or_create(
            level=level,
            is_final=True,
            defaults={"title": f"{level.name} Final Assessment", "pass_mark": 70, "time_limit_minutes": 30},
        )
        fq, _ = Question.objects.get_or_create(
            quiz=final,
            order=1,
            defaults={
                "text": f"I can confidently use {level.name} {lang_name} in daily conversation.",
                "question_type": Question.QuestionType.TRUE_FALSE,
            },
        )
        if not fq.options.exists():
            AnswerOption.objects.bulk_create([
                AnswerOption(question=fq, text="True", is_correct=True),
                AnswerOption(question=fq, text="False", is_correct=False),
            ])

        enforce_single_preview(level)

    def _sync_english_a1_curriculum(self, level, force=False):
        """Only touch English A1 when newly created or --demo --force."""
        if level.is_deleted:
            return

        video_url = "https://www.w3schools.com/html/mov_bbb.mp4"
        structure = [
            ("Introduction", "Your first steps into English.", [
                ("Welcome to English", "Meet your course and learn what to expect.", 10),
                ("Alphabet Basics", "Master the English alphabet from A to Z.", 12),
                ("Pronunciation", "Practice essential English sounds.", 15),
            ]),
            ("Vocabulary", "Build everyday vocabulary.", [
                ("Common Words", "Essential words for daily conversations.", 12),
                ("Daily Expressions", "Phrases you will hear every day.", 14),
            ]),
            ("Grammar", "Core grammar building blocks.", [
                ("Nouns", "People, places, and things.", 15),
                ("Verbs", "Actions and states of being.", 15),
            ]),
        ]

        for sec_idx, (title, desc, lessons) in enumerate(structure, 1):
            module, _ = Module.objects.update_or_create(
                level=level,
                order=sec_idx,
                defaults={"title": title, "description": desc},
            )
            for les_idx, (ltitle, lcontent, dur) in enumerate(lessons, 1):
                Lesson.objects.update_or_create(
                    module=module,
                    order=les_idx,
                    defaults={
                        "title": ltitle,
                        "lesson_type": Lesson.LessonType.VIDEO,
                        "content": lcontent,
                        "duration_minutes": dur,
                        "video_url": video_url,
                        "is_published": True,
                        "is_preview": False,
                    },
                )

        if force:
            Module.objects.filter(level=level).exclude(order__in=[1, 2, 3]).delete()

        grammar_module = Module.objects.filter(level=level, order=3).first()
        if grammar_module:
            quiz, _ = Quiz.objects.get_or_create(
                module=grammar_module,
                defaults={"title": "Grammar Quiz", "pass_mark": 70, "time_limit_minutes": 15},
            )
            q1, _ = Question.objects.get_or_create(
                quiz=quiz,
                order=1,
                defaults={
                    "text": "Which word is a noun?",
                    "question_type": Question.QuestionType.MULTIPLE_CHOICE,
                },
            )
            if not q1.options.exists():
                AnswerOption.objects.bulk_create([
                    AnswerOption(question=q1, text="Book", is_correct=True),
                    AnswerOption(question=q1, text="Run", is_correct=False),
                    AnswerOption(question=q1, text="Quickly", is_correct=False),
                ])

        final, _ = Quiz.objects.get_or_create(
            level=level,
            is_final=True,
            defaults={"title": "English Beginner (A1) Final Assessment", "pass_mark": 70, "time_limit_minutes": 30},
        )
        fq, _ = Question.objects.get_or_create(
            quiz=final,
            order=1,
            defaults={
                "text": "I can introduce myself and use basic English greetings.",
                "question_type": Question.QuestionType.TRUE_FALSE,
            },
        )
        if not fq.options.exists():
            AnswerOption.objects.bulk_create([
                AnswerOption(question=fq, text="True", is_correct=True),
                AnswerOption(question=fq, text="False", is_correct=False),
            ])

        enforce_single_preview(level)
        self.stdout.write(self.style.SUCCESS(f"  Synced English A1 curriculum ({level.name})"))

    def _ensure_preview_lessons(self):
        for level in Level.objects.filter(is_published=True):
            enforce_single_preview(level)

    def _ensure_overview_content(self):
        defaults = {
            "learning_objectives": "Speak confidently in everyday situations\nWrite clear messages\nUnderstand lessons at your level",
            "skills": "Conversation\nGrammar\nVocabulary\nListening",
            "target_audience": "Somali speakers learning online\nStudents preparing for work or study",
            "requirements": "Smartphone or computer\nInternet connection\nDaily practice time",
        }
        updated = 0
        for level in Level.objects.filter(is_published=True):
            changed = False
            for field, value in defaults.items():
                if not getattr(level, field):
                    setattr(level, field, value)
                    changed = True
            if changed:
                level.save()
                updated += 1
        if updated:
            self.stdout.write(f"  Updated overview content on {updated} courses")
