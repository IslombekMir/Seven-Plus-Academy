from django.db import models
from users.models import User

class Quiz(models.Model):
    TYPE_CHOICES = [
        ('quiz', 'Quiz'),
        ('poll', 'Poll'),
    ]

    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='quiz')
    completion_time = models.IntegerField(null=True, blank=True)

    random_question_order = models.BooleanField(default=False)
    allowed_attempts = models.PositiveIntegerField(default=1, help_text="0 = unlimited attempts")

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')

    question_text = models.TextField()
    image = models.ImageField(upload_to='quiz_questions/', null=True, blank=True)

    order = models.PositiveIntegerField(default=0)
    value = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.question_text[:50]}..."


class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')

    option_text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    order = models.PositiveIntegerField(default=0)


class QuizAttempt(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    participant = models.ForeignKey(User, on_delete=models.CASCADE)

    started_at = models.DateTimeField(auto_now_add=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    attempt_number = models.PositiveIntegerField()

    score = models.FloatField(null=True, blank=True)
    is_submitted = models.BooleanField(default=False)

    class Meta:
        unique_together = ('quiz', 'participant', 'attempt_number')


class QuestionAnswer(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(Option, on_delete=models.SET_NULL, null=True, blank=True)
