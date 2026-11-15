from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Author, Country, ContentProvider, SourceWork, ImportCandidate, SyncRun, Translation, FeaturedSchedule
from .sources import approve_candidate, sync_work

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display=['name','code']; search_fields=['name','code']
@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display=['name','country','death_year']; search_fields=['name']; list_select_related=['country']
@admin.register(ContentProvider)
class ProviderAdmin(admin.ModelAdmin):
    list_display=['name','kind','is_active','last_success_at']; readonly_fields=['last_success_at']
@admin.register(SourceWork)
class SourceAdmin(admin.ModelAdmin):
    list_display=['title','provider','language','license_code','approved_for_sync','last_checked_at']
    list_filter=['provider','language','approved_for_sync','license_code']; search_fields=['title','rights_notes']
    readonly_fields=['last_checked_at']; list_select_related=['provider','language']; actions=['check_sources']
    @admin.action(description='Check selected sources (up to 2; creates review candidates only)',permissions=['change'])
    def check_sources(self,request,queryset):
        for work in queryset.select_related('provider')[:2]:
            run=sync_work(work)
            self.message_user(request,f'{work}: {run.message}',messages.SUCCESS if run.succeeded else messages.WARNING)
@admin.register(ImportCandidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display=['work','status','revision_id','created_at','reviewed_by']; list_filter=['status','work__language']; search_fields=['work__title']
    readonly_fields=['work','text','revision_id','fingerprint','status','reviewed_by','reviewed_at','poem','created_at']
    actions=['approve','reject']; list_select_related=['work','reviewed_by']
    def has_add_permission(self,request): return False
    @admin.action(description='Approve selected candidates into unpublished drafts',permissions=['change'])
    def approve(self,request,queryset):
        for candidate in queryset:
            try:
                poem=approve_candidate(candidate,request.user)
                self.message_user(request,f'Draft created: {poem}. Assign classes/categories and confirm rights before publishing.')
            except (ValidationError,PermissionError) as exc: self.message_user(request,str(exc),messages.ERROR)
    @admin.action(description='Reject selected pending candidates',permissions=['change'])
    def reject(self,request,queryset): queryset.filter(status='pending').update(status='rejected',reviewed_by=request.user,reviewed_at=timezone.now())
@admin.register(SyncRun)
class RunAdmin(admin.ModelAdmin):
    list_display=['started_at','work','succeeded','message']; list_filter=['succeeded']; list_select_related=['work']
    readonly_fields=['started_at','work','succeeded','message']
    def has_add_permission(self,request): return False
    def has_change_permission(self,request,obj=None): return False
@admin.register(Translation)
class TranslationAdmin(admin.ModelAdmin):
    list_display=['original','translated_poem','method','verified','reviewer']; list_filter=['method','verified']; autocomplete_fields=['original','translated_poem']
@admin.register(FeaturedSchedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display=['poem','starts_at','ends_at','priority']; autocomplete_fields=['poem']
