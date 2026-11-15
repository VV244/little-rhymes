from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

class Country(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=2, unique=True)
    class Meta:
        ordering = ['name']
        verbose_name_plural = 'countries & cultures'
    def __str__(self): return self.name

class Author(models.Model):
    name = models.CharField(max_length=160, unique=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True)
    biography = models.TextField(blank=True, help_text='Verified facts only. Include a reference URL.')
    reference_url = models.URLField(blank=True)
    death_year = models.PositiveSmallIntegerField(null=True, blank=True)
    class Meta: ordering = ['name']
    def __str__(self): return self.name

class ContentProvider(models.Model):
    name = models.CharField(max_length=120, unique=True)
    kind = models.CharField(max_length=20, choices=[('wikisource', 'Wikisource API'), ('reference', 'Manual reference only')], default='wikisource')
    language_code = models.CharField(max_length=8, blank=True, help_text='Allowlisted Wikisource subdomain, e.g. en.')
    terms_url = models.URLField()
    is_active = models.BooleanField(default=False, help_text='Enable only after reviewing terms and selected works.')
    last_success_at = models.DateTimeField(null=True, blank=True, editable=False)
    def __str__(self): return self.name

class SourceWork(models.Model):
    provider = models.ForeignKey(ContentProvider, on_delete=models.PROTECT, related_name='works')
    title = models.CharField(max_length=250)
    page_title = models.CharField(max_length=300, blank=True, help_text='Exact API page title. No arbitrary URLs.')
    source_url = models.URLField(max_length=700)
    author = models.ForeignKey(Author, on_delete=models.SET_NULL, null=True, blank=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True)
    language = models.ForeignKey('poems.Language', on_delete=models.PROTECT)
    license_code = models.CharField(max_length=40, default='PD', choices=[('PD','Public domain text'),('CC0','CC0'),('CC-BY-4.0','CC BY 4.0'),('CC-BY-SA-4.0','CC BY-SA 4.0'),('permission','Written permission')])
    license_url = models.URLField(blank=True)
    rights_notes = models.TextField(help_text='Underlying text and edition rights, territory, author dates and evidence. Media needs separate clearance.')
    approved_for_sync = models.BooleanField(default=False)
    baseline_text = models.TextField(max_length=20000, blank=True, help_text='Reviewed excerpt or full text. API candidates require this exact text to be found in the source.')
    revision_id = models.CharField(max_length=40, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True, editable=False)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['provider','page_title'], name='unique_provider_work')]
    def __str__(self): return self.title
    def clean(self):
        from .sources import validate_source
        if self.approved_for_sync:
            validate_source(self)
            if not self.baseline_text.strip(): raise ValidationError({'baseline_text':'A reviewed text selection is required before synchronization.'})

class ImportCandidate(models.Model):
    work = models.ForeignKey(SourceWork, on_delete=models.PROTECT, related_name='candidates')
    text = models.TextField(max_length=20000)
    revision_id = models.CharField(max_length=40)
    fingerprint = models.CharField(max_length=64)
    status = models.CharField(max_length=10, choices=[('pending','Pending review'),('approved','Approved to draft'),('rejected','Rejected')], default='pending', db_index=True)
    review_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, editable=False)
    reviewed_at = models.DateTimeField(null=True, blank=True, editable=False)
    poem = models.ForeignKey('poems.Poem', on_delete=models.SET_NULL, null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
        constraints = [models.UniqueConstraint(fields=['work','fingerprint'],name='unique_source_candidate')]
    def __str__(self): return f'{self.work} · {self.get_status_display()}'

class SyncRun(models.Model):
    work = models.ForeignKey(SourceWork, on_delete=models.SET_NULL, null=True)
    started_at = models.DateTimeField(auto_now_add=True)
    succeeded = models.BooleanField(default=False)
    message = models.CharField(max_length=300)
    class Meta: ordering = ['-started_at']
    def __str__(self): return f'{self.started_at:%Y-%m-%d %H:%M} · {self.message}'

class Translation(models.Model):
    original = models.ForeignKey('poems.Poem', on_delete=models.CASCADE, related_name='translations')
    translated_poem = models.OneToOneField('poems.Poem', on_delete=models.CASCADE, related_name='translation_record')
    method = models.CharField(max_length=12, choices=[('human','Human translation'),('machine','Machine translation')])
    verified = models.BooleanField(default=False)
    translator = models.CharField(max_length=160)
    rights_notes = models.TextField()
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True)
    def clean(self):
        if self.original_id == self.translated_poem_id: raise ValidationError('A translation must be a different poem.')
        if self.verified and not self.reviewer_id: raise ValidationError('Verified translations require a reviewer.')
    def __str__(self): return f'{self.original} → {self.translated_poem}'

class FeaturedSchedule(models.Model):
    poem = models.ForeignKey('poems.Poem', on_delete=models.CASCADE)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    priority = models.PositiveSmallIntegerField(default=0)
    class Meta:
        ordering=['-priority','starts_at']
        constraints=[models.CheckConstraint(condition=Q(ends_at__gt=models.F('starts_at')),name='feature_positive_duration')]
    def clean(self):
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at: raise ValidationError('End must follow start.')
    def __str__(self): return str(self.poem)
