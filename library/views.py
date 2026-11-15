from datetime import date
from django.conf import settings
from django.core.cache import cache
from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_safe
from poems.models import Poem
from .models import ContentProvider, SourceWork, SyncRun, FeaturedSchedule


def daily_poem():
    ids=list(Poem.objects.published().filter(source_verified=True).order_by('pk').values_list('pk',flat=True))
    if not ids: return None
    index=timezone.localdate().toordinal()%len(ids)
    return Poem.objects.with_relations().get(pk=ids[index])

@require_safe
def activities(request): return render(request,'library/activities.html',{'title':'The Wonder Workshop · Little Rhymes'})

@require_safe
def grownups(request):
    return render(request,'library/grownups.html',{'title':'For parents & teachers · Little Rhymes','daily_poem':daily_poem()})

@require_safe
def sources(request):
    return render(request,'library/sources.html',{'title':'Our sources & editorial promise','providers':ContentProvider.objects.all(),'works':SourceWork.objects.select_related('author','language','country','provider').all(),'last_run':SyncRun.objects.first()})

@require_safe
def daily_api(request):
    from poems.api import PoemSerializer
    poem=daily_poem()
    return JsonResponse({'date':str(timezone.localdate()),'selection':'Daily rotation of published, source-verified poems; not based on tracking.', 'poem':PoemSerializer(poem,context={'request':request}).data if poem else None})

@require_safe
def sync_status(request):
    return JsonResponse({'providers':list(ContentProvider.objects.values('name','kind','is_active','last_success_at')), 'publication':'Every imported candidate requires staff review; synchronization never publishes content.'})

# This machine-only endpoint uses a verified, short-lived GitHub OIDC identity,
# not cookie authentication. Browser/admin mutations retain Django CSRF protection.
@csrf_exempt
@require_POST
def scheduled_sync(request):
    from .sources import sync_work
    if len(request.body)>1000: return JsonResponse({'error':'Request too large'},status=413)
    authorization=request.headers.get('Authorization','')
    if not authorization.startswith('Bearer ') or len(authorization)>12000: return JsonResponse({'error':'Workflow authentication required'},status=401)
    try:
        claims=verify_workflow_token(authorization[7:])
    except Exception:
        return JsonResponse({'error':'Invalid workflow identity'},status=403)
    # Each GitHub job is accepted once. Retries require a newly minted job identity.
    identity=f"sync-run:{claims['run_id']}:{claims['run_attempt']}"
    if not cache.add(identity,True,24*3600): return JsonResponse({'error':'Workflow already processed'},status=409)
    if not cache.add('editorial-sync-lock',True,90):
        cache.delete(identity)
        return JsonResponse({'error':'A synchronization is already running'},status=429)
    try:
        works=SourceWork.objects.filter(approved_for_sync=True,provider__is_active=True).select_related('provider').order_by(F('last_checked_at').asc(nulls_first=True),'pk')[:2]
        import time
        results=[]
        for index,work in enumerate(works):
            if index: time.sleep(2.1)
            run=sync_work(work)
            results.append({'work':work.title,'ok':run.succeeded,'message':run.message})
    finally: cache.delete('editorial-sync-lock')
    return JsonResponse({'results':results,'published':0})

def verify_workflow_token(token):
    import jwt
    from .sources import read_json
    header=jwt.get_unverified_header(token)
    if header.get('alg')!='RS256' or not isinstance(header.get('kid'),str) or not header['kid'] or len(header['kid'])>200:
        raise ValueError('Invalid signing header.')
    keys=cache.get('github-oidc-keys')
    if keys is None:
        keys=read_json('https://token.actions.githubusercontent.com/.well-known/jwks',200000)
        cache.set('github-oidc-keys',keys,3600)
    key=next((k for k in keys['keys'] if k.get('kid')==header.get('kid')),None)
    if key is None:
        if cache.add('github-oidc-key-refresh-cooldown',True,60):cache.delete('github-oidc-keys')
        raise ValueError('Unknown key; retry after key refresh.')
    claims=jwt.decode(token,jwt.PyJWK(key).key,algorithms=['RS256'],audience='little-rhymes-content-sync',issuer='https://token.actions.githubusercontent.com',options={'require':['exp','iat','nbf','repository','repository_id','ref','workflow_ref','event_name','run_id','run_attempt']},leeway=10)
    repo=settings.CONTENT_SYNC_REPOSITORY
    if claims['repository']!=repo or str(claims['repository_id'])!=settings.CONTENT_SYNC_REPOSITORY_ID or claims['ref']!='refs/heads/main' or claims['workflow_ref']!=f'{repo}/.github/workflows/content-sync.yml@refs/heads/main' or claims['event_name'] not in ('schedule','workflow_dispatch'):
        raise ValueError('Workflow identity is outside the allowlist.')
    return claims
