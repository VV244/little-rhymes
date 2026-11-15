"""Bounded, cached MediaWiki API reads. Never auto-publish remote content."""
import hashlib
import json
import re
import unicodedata
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

from bs4 import BeautifulSoup
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from .models import ContentProvider, ImportCandidate, SyncRun

APPROVED_LANGUAGES = {'en','hi','mr','sa','ta','te','bn','gu','fr','es','de','ja','kn','ml','pa','or','as','ur'}

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Unexpected API redirect; an editor must review it.')

def validate_source(work):
    code = work.provider.language_code
    parts = urlsplit(work.source_url)
    if work.provider.kind != 'wikisource' or code not in APPROVED_LANGUAGES:
        raise ValidationError('Only approved Wikisource API languages can synchronize.')
    if parts.scheme != 'https' or parts.netloc != f'{code}.wikisource.org' or not parts.path.startswith('/wiki/') or parts.username:
        raise ValidationError('The reference must be an HTTPS page on the selected Wikisource.')
    if not work.page_title or len(work.page_title) > 300 or work.page_title.lower().startswith(('special:', 'user:', 'file:', 'mediawiki:')):
        raise ValidationError('Use an approved literary page title.')

def read_json(url, max_bytes=2_000_000):
    request = Request(url, headers={'User-Agent':'LittleRhymes/2.0 (+https://little-rhymes-1.onrender.com/contact/; reviewed educational texts)', 'Accept':'application/json'})
    with build_opener(NoRedirect).open(request, timeout=12) as response:
        if response.headers.get_content_type() != 'application/json': raise ValueError('API did not return JSON.')
        raw = response.read(max_bytes+1)
        if len(raw)>max_bytes: raise ValueError('API response exceeds the size limit.')
    return json.loads(raw)

def normalized(text):
    return re.sub(r'\s+', '', unicodedata.normalize('NFC',text).replace('\u200b','').replace('\u2060','').replace('\ufeff','')).casefold()

def retrieve(work):
    validate_source(work)
    key = f'source-api:{work.pk}'
    payload = cache.get(key)
    if payload is None:
        # At most one request per provider every two seconds across all workers.
        if not cache.add(f'provider-pace:{work.provider_id}', True, 2):
            raise ValueError('Provider is cooling down. Try again shortly.')
        url = f'https://{work.provider.language_code}.wikisource.org/w/api.php?' + urlencode({'action':'parse','page':work.page_title,'prop':'text|revid','format':'json','formatversion':2,'maxlag':5})
        payload = read_json(url)
        cache.set(key,payload,6*3600)
    parsed = payload.get('parse',{})
    html, revision = parsed.get('text',''), parsed.get('revid')
    if not html or not isinstance(revision,int): raise ValueError('Source is unavailable, lagged or missing a revision.')
    soup=BeautifulSoup(html,'html.parser')
    for unwanted in soup.select('script,style,nav,.mw-editsection,.ws-noexport,table,.licenseContainer,.licensetpl'):
        unwanted.decompose()
    # Match the reviewed selection only. Changes never replace a published poem.
    text = work.baseline_text.strip()
    if not text or normalized(text) not in normalized(soup.get_text(' ',strip=True)):
        raise ValueError('Reviewed text no longer matches the source; manual review is required.')
    return text, str(revision)

def sync_work(work):
    run=SyncRun.objects.create(work=work,message='Started')
    try:
        if not work.approved_for_sync or not work.provider.is_active: raise ValueError('Source is not enabled for synchronization.')
        text, revision=retrieve(work)
        digest=hashlib.sha256(f'{text}\n{revision}'.encode()).hexdigest()
        candidate, created=ImportCandidate.objects.get_or_create(work=work,fingerprint=digest,defaults={'text':text,'revision_id':revision})
        now=timezone.now()
        type(work).objects.filter(pk=work.pk).update(last_checked_at=now)
        ContentProvider.objects.filter(pk=work.provider_id).update(last_success_at=now)
        run.succeeded=True
        run.message='New candidate awaiting editorial approval.' if created else 'Source checked; candidate already exists.'
    except (ValueError, ValidationError, URLError, HTTPError, TimeoutError, json.JSONDecodeError, KeyError) as exc:
        # Do not store remote payloads, URLs with credentials or stack traces.
        run.message = 'Source unavailable; retry later.' if isinstance(exc,(URLError,TimeoutError)) else str(exc)[:300]
    run.save(update_fields=['succeeded','message'])
    return run

@transaction.atomic
def approve_candidate(candidate, reviewer):
    from poems.models import Poem
    if not reviewer.is_staff or not reviewer.has_perm('library.change_importcandidate') or not reviewer.has_perm('poems.add_poem'):
        raise PermissionError('Editorial and poem permissions are required.')
    candidate=ImportCandidate.objects.select_for_update().select_related('work__author','work__language').get(pk=candidate.pk)
    if candidate.status != 'pending': raise ValidationError('This candidate has already been reviewed.')
    work=candidate.work
    validate_source(work)
    if not work.rights_notes.strip() or candidate.text.strip()!=work.baseline_text.strip(): raise ValidationError('Review the rights and exact selection first.')
    poem=Poem.objects.create(title=work.title,language=work.language,source_work=work,author=work.author.name if work.author else 'Traditional; author unknown',poem_text=candidate.text,
        rights_statement=f'{work.license_code}. {work.rights_notes} Source: {work.source_url} (revision {candidate.revision_id}).',rights_confirmed=False,
        source_verified=True,is_excerpt=True,content_kind='authored' if work.author else 'traditional',status='draft',short_description='An imported source selection, awaiting publication review.')
    candidate.poem=poem; candidate.status='approved'; candidate.reviewed_by=reviewer; candidate.reviewed_at=timezone.now(); candidate.save()
    return poem
