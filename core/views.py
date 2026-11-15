from django.conf import settings
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_safe
from poems.models import Poem
from .models import ContentPage, FAQ

@require_safe
def home(request):
    from library.views import daily_poem
    from library.models import FeaturedSchedule
    from django.utils import timezone
    published = Poem.objects.published().with_relations()
    scheduled = list(FeaturedSchedule.objects.filter(starts_at__lte=timezone.now(), ends_at__gt=timezone.now()).values_list('poem_id',flat=True))
    from django.db.models import Case, When, IntegerField
    featured = published.filter(pk__in=scheduled).order_by(Case(*[When(pk=pk,then=index) for index,pk in enumerate(scheduled)],default=999,output_field=IntegerField()),'pk')
    if not featured.exists(): featured=published.filter(is_featured=True)
    return render(request, 'home.html', {
        'popular_poems': published.order_by('-home_priority', '-published_at', '-id')[:3],
        'featured_poems': featured[:3],
        'classic_poems': published.filter(source_verified=True).order_by('-home_priority','id')[:3],
        'daily_poem': daily_poem(), 'today': timezone.localdate(),
        'new_poems': published[:3],
        'faqs': FAQ.objects.filter(is_active=True)[:4],
        'title': 'Little Rhymes – Learn, Sing & Grow',
        'description': 'Discover joyful children’s poems in English, Hindi, Marathi and regional Indian languages. Read, listen and learn from Junior KG to Class 4.',
    })

@require_safe
def page(request, slug):
    page = get_object_or_404(ContentPage, slug=slug)
    return render(request, 'core/page.html', {'page': page, 'title': page.title, 'description': page.introduction})

@require_safe
def faq(request):
    return render(request, 'core/faq.html', {'faqs': FAQ.objects.filter(is_active=True), 'title': 'Little questions, helpful answers'})

@require_safe
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except Exception:
        return JsonResponse({'status': 'unavailable'}, status=503)
    return JsonResponse({'status': 'ok'})

@require_safe
def robots(request):
    return HttpResponse(f'User-agent: *\nDisallow: /admin/\nDisallow: /staff/\nDisallow: /api/\nDisallow: /favorites/\nDisallow: /contact/\nSitemap: {settings.SITE_URL}/sitemap.xml\n', content_type='text/plain')

def csrf_failure(request, reason=''):
    return render(request, 'core/error.html', {'title': 'Let’s try that again', 'description': 'For your security, this form could not be accepted. Refresh the page before sending it again.'}, status=403)

def not_found(request, exception):
    return render(request, '404.html', status=404)

def server_error(request):
    # Avoid database-driven context processors on the error path.
    from django.template.loader import render_to_string
    return HttpResponse(render_to_string('500.html'), status=500)
