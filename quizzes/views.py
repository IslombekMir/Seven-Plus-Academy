import random

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.db.models import Prefetch
from django.views.decorators.http import require_http_methods

from users.models import User
from lessons.models import Group
from .models import Quiz, Question, Option, QuizAttempt, QuestionAnswer
from datetime import timedelta
from django.utils import timezone

from django.db.models import Exists, OuterRef

def can_create_quiz(user):
    return user.role == User.Role.TEACHER


def calculate_attempt_score(attempt: QuizAttempt):
    """Returns: (raw_score, max_score, percent_score)"""
    questions = attempt.quiz.questions.all().prefetch_related("options")
    max_score = sum(q.value for q in questions)

    correct_score = 0
    answers_map = {
        ans.question_id: ans.selected_option_id
        for ans in attempt.answers.select_related("selected_option")
    }

    for question in questions:
        selected_option_id = answers_map.get(question.id)
        if not selected_option_id:
            continue
        if question.options.filter(id=selected_option_id, is_correct=True).exists():
            correct_score += question.value

    percent = round((correct_score / max_score) * 100, 2) if max_score else 0.0
    return correct_score, max_score, percent


def _parse_questions_from_post(post):
    """
    Parse question/option blocks from POST data.
    Returns (questions_data, error_or_None).

    POST keys per question index i (1-based):
        question_text_i, value_i, correct_i ("1".."4"),
        option_i_1 .. option_i_4
    """
    question_count = int(post.get("question_count", 0))
    questions_data = []

    for i in range(1, question_count + 1):
        text = post.get(f"question_text_{i}", "").strip()
        if not text:
            continue  # blank blocks skipped (removed via JS)

        value = int(post.get(f"value_{i}") or 1)
        correct_idx = post.get(f"correct_{i}")  # "1".."4"

        options = []
        for j in range(1, 5):
            opt_text = post.get(f"option_{i}_{j}", "").strip()
            if opt_text:
                options.append({
                    "text": opt_text,
                    "is_correct": str(j) == correct_idx,
                    "order": j,
                })

        if len(options) < 2:
            return None, f"Question {i} needs at least 2 options."

        if sum(1 for o in options if o["is_correct"]) != 1:
            return None, f"Question {i}: select exactly one correct answer."

        questions_data.append({
            "text": text,
            "value": value,
            "order": i,
            "options": options,
        })

    if not questions_data:
        return None, "Add at least one question."

    return questions_data, None


def quiz_list(request):
    user = request.user

    completed_attempts = QuizAttempt.objects.filter(
        quiz=OuterRef("pk"),
        participant=user,
        is_submitted=True
    )

    quizzes = (
        Quiz.objects
        .select_related("created_by")
        .annotate(
            is_completed=Exists(completed_attempts)
        )
        .order_by("-created_at")
    )

    if user.role == User.Role.STUDENT:
        quizzes = quizzes.filter(is_active=True)

    q = request.GET.get("q", "").strip()
    if q:
        quizzes = quizzes.filter(title__icontains=q)

    my_quizzes = quizzes.filter(created_by=user)
    other_quizzes = quizzes.exclude(created_by=user)

    return render(request, "quizzes/list.html", {
        "my_quizzes": my_quizzes,
        "other_quizzes": other_quizzes,
        "can_create": can_create_quiz(user),
        "q": q,
    })


@login_required
def quiz_create(request):
    if not can_create_quiz(request.user):
        return HttpResponseForbidden("Only teachers can create quizzes.")

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        completion_time = request.POST.get("completion_time") or None
        random_order = request.POST.get("random_question_order") == "on"
        allowed_attempts = int(request.POST.get("allowed_attempts") or 1)

        error = None
        if not title:
            error = "Title is required."

        questions_data = None
        if not error:
            questions_data, error = _parse_questions_from_post(request.POST)

        if error:
            return render(request, "quizzes/create.html", {
                "error": error,
                "post": request.POST,
            })

        with transaction.atomic():
            quiz = Quiz.objects.create(
                created_by=request.user,
                title=title,
                description=description,
                type="quiz",
                completion_time=completion_time,
                random_question_order=random_order,
                allowed_attempts=allowed_attempts,
                is_active=True,
            )
            for qd in questions_data:
                q = Question.objects.create(
                    quiz=quiz,
                    question_text=qd["text"],
                    value=qd["value"],
                    order=qd["order"],
                )
                for od in qd["options"]:
                    Option.objects.create(
                        question=q,
                        option_text=od["text"],
                        is_correct=od["is_correct"],
                        order=od["order"],
                    )

        return redirect("quizzes:detail", pk=quiz.pk)

    return render(request, "quizzes/create.html", {})


@login_required
def quiz_detail(request, pk):
    quiz = get_object_or_404(
        Quiz.objects.select_related("created_by").prefetch_related(
            Prefetch(
                "questions",
                queryset=Question.objects.prefetch_related("options").order_by("order", "id"),
            )
        ),
        pk=pk,
    )

    attempts_qs = QuizAttempt.objects.filter(quiz=quiz, participant=request.user).order_by("-attempt_number")
    last_attempt = attempts_qs.first()
    attempts_used = attempts_qs.filter(is_submitted=True).count()
    attempts_exhausted = quiz.allowed_attempts != 0 and attempts_used >= quiz.allowed_attempts
    is_quiz_owner = can_create_quiz(request.user) and quiz.created_by_id == request.user.id

    return render(request, "quizzes/detail.html", {
        "quiz": quiz,
        "attempt": last_attempt,
        "attempts_used": attempts_used,
        "attempts_exhausted": attempts_exhausted,
        "is_quiz_owner": is_quiz_owner,
        "can_create": can_create_quiz(request.user),
    })


@login_required
@require_http_methods(["GET", "POST"])
def quiz_edit(request, pk):
    quiz = get_object_or_404(
        Quiz.objects.prefetch_related(
            Prefetch(
                "questions",
                queryset=Question.objects.prefetch_related("options").order_by("order", "id"),
            )
        ),
        pk=pk,
    )

    if not can_create_quiz(request.user) or quiz.created_by_id != request.user.id:
        return HttpResponseForbidden("Only the quiz owner can edit this quiz.")

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        completion_time = request.POST.get("completion_time") or None
        random_order = request.POST.get("random_question_order") == "on"
        allowed_attempts = int(request.POST.get("allowed_attempts") or 1)

        error = None
        if not title:
            error = "Title is required."

        questions_data = None
        if not error:
            questions_data, error = _parse_questions_from_post(request.POST)

        if error:
            return render(request, "quizzes/edit.html", {
                "quiz": quiz,
                "error": error,
                "post": request.POST,
            })

        with transaction.atomic():
            quiz.title = title
            quiz.description = description
            quiz.completion_time = completion_time
            quiz.random_question_order = random_order
            quiz.allowed_attempts = allowed_attempts
            quiz.save(update_fields=[
                "title", "description", "completion_time",
                "random_question_order", "allowed_attempts",
            ])

            quiz.questions.all().delete()

            for qd in questions_data:
                q = Question.objects.create(
                    quiz=quiz,
                    question_text=qd["text"],
                    value=qd["value"],
                    order=qd["order"],
                )
                for od in qd["options"]:
                    Option.objects.create(
                        question=q,
                        option_text=od["text"],
                        is_correct=od["is_correct"],
                        order=od["order"],
                    )

        return redirect("quizzes:detail", pk=quiz.pk)

    return render(request, "quizzes/edit.html", {"quiz": quiz})


def finalize_attempt(attempt):
    if attempt.is_submitted:
        return
    raw_score, max_score, percent = calculate_attempt_score(attempt)
    attempt.score = percent
    attempt.is_submitted = True
    attempt.finished_at = timezone.now()
    attempt.save(update_fields=["score", "is_submitted", "finished_at"])


@login_required
def quiz_take(request, pk):
    quiz = get_object_or_404(
        Quiz.objects.prefetch_related(
            Prefetch(
                "questions",
                queryset=Question.objects.prefetch_related("options").order_by("order", "id"),
            )
        ),
        pk=pk,
        is_active=True,
    )

    attempts_qs = QuizAttempt.objects.filter(quiz=quiz, participant=request.user).order_by("-attempt_number")
    last_attempt = attempts_qs.first()
    attempts_used = attempts_qs.filter(is_submitted=True).count()

    if quiz.allowed_attempts != 0 and attempts_used >= quiz.allowed_attempts:
        if last_attempt and last_attempt.is_submitted:
            return redirect("quizzes:result", attempt_id=last_attempt.id)
        return HttpResponseForbidden("You have reached the attempt limit for this quiz.")

    if last_attempt and not last_attempt.is_submitted:
        attempt = last_attempt
    else:
        next_number = (last_attempt.attempt_number + 1) if last_attempt else 1
        attempt = QuizAttempt.objects.create(
            quiz=quiz,
            participant=request.user,
            attempt_number=next_number,
        )
        if quiz.completion_time:
            attempt.ends_at = timezone.now() + timedelta(minutes=quiz.completion_time)
            attempt.save()

    ordered_questions = list(quiz.questions.all())

    if request.method == "POST":
        if attempt.ends_at and timezone.now() >= attempt.ends_at:
            if not attempt.is_submitted:
                finalize_attempt(attempt)
            return redirect("quizzes:result", attempt_id=attempt.id)

        for question in ordered_questions:
            selected_option_id = request.POST.get(f"q_{question.id}")
            selected_option = None
            if selected_option_id:
                selected_option = question.options.filter(id=selected_option_id).first()

            QuestionAnswer.objects.update_or_create(
                attempt=attempt,
                question=question,
                defaults={"selected_option": selected_option},
            )

        if attempt.ends_at and timezone.now() > attempt.ends_at:
            finalize_attempt(attempt)
            return redirect("quizzes:result", attempt_id=attempt.id)

        finalize_attempt(attempt)
        return redirect("quizzes:result", attempt_id=attempt.id)

    display_questions = ordered_questions[:]
    if quiz.random_question_order:
        random.shuffle(display_questions)
    
    remaining_seconds = 0
    if attempt.ends_at:
        remaining_seconds = max(int((attempt.ends_at - timezone.now()).total_seconds()), 0)

    return render(request, "quizzes/take.html", {
        "quiz": quiz,
        "questions": display_questions,
        "attempt": attempt,
        "remaining_seconds": remaining_seconds,
    })


@login_required
def quiz_result(request, attempt_id):
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related("quiz", "participant").prefetch_related(
            Prefetch(
                "answers",
                queryset=QuestionAnswer.objects.select_related(
                    "question", "selected_option",
                ).prefetch_related(
                    "question__options"
                ).order_by("question__order", "question__id"),
            )
        ),
        id=attempt_id,
    )

    if request.user != attempt.participant and request.user.role not in [User.Role.TEACHER, User.Role.ADMIN]:
        return HttpResponseForbidden("You cannot view this result.")

    raw_score, max_score, percent = calculate_attempt_score(attempt)
    answers = list(attempt.answers.all())

    return render(request, "quizzes/result.html", {
        "attempt": attempt,
        "quiz": attempt.quiz,
        "raw_score": raw_score,
        "max_score": max_score,
        "percent": percent,
        "answers": answers,
    })


@login_required
@require_http_methods(["GET", "POST"])
def quiz_delete(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk)

    if not can_create_quiz(request.user) or quiz.created_by_id != request.user.id:
        return HttpResponseForbidden("Only the quiz owner can delete this quiz.")

    if request.method == "POST":
        quiz.delete()
        return redirect("quizzes:list")

    return render(request, "quizzes/delete_confirm.html", {"quiz": quiz})