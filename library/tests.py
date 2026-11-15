import json
import time
from unittest.mock import patch
from datetime import timedelta
from django.contrib.auth.models import User,Permission
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase,Client
from django.utils import timezone
from poems.models import Poem,Language,ClassLevel,Category
from .models import Country,Author,ContentProvider,SourceWork,ImportCandidate,SyncRun,Translation,FeaturedSchedule
from .sources import validate_source,retrieve,sync_work,approve_candidate,normalized
from .views import verify_workflow_token

class WorldLibraryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.en=Language.objects.create(name='English',native_name='English',code='en',slug='english')
        cls.country=Country.objects.create(name='United Kingdom',code='GB')
        cls.provider=ContentProvider.objects.create(name='Test Wikisource',language_code='en',kind='wikisource',terms_url='https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use',is_active=True)
        cls.work=SourceWork.objects.create(provider=cls.provider,title='The star',page_title='The star',source_url='https://en.wikisource.org/wiki/The_star',language=cls.en,country=cls.country,baseline_text='A little star.\nA sky of light.',rights_notes='Public-domain original test text.',approved_for_sync=True)
        cls.poem=Poem.objects.create(title='The star',slug='the-star',language=cls.en,source_work=cls.work,source_verified=True,content_kind='traditional',poem_text=cls.work.baseline_text,rights_statement=cls.work.rights_notes,rights_confirmed=True,status='published',published_at=timezone.now()-timedelta(hours=1))
        cls.staff=User.objects.create_user(username='editor',is_staff=True)
    def setUp(self): cache.clear()
    def payload(self,text=None): return {'parse':{'text':f'<div class="poem">{text or "A little star.<br>A sky of light."}</div><script>evil()</script>','revid':123}}
    def test_new_pages_and_daily_api_are_real(self):
        for path in ['/activities/','/grownups/','/sources/','/api/content-status/']:
            self.assertEqual(self.client.get(path).status_code,200)
        body=self.client.get('/api/daily-rhyme/').json()
        self.assertEqual(body['poem']['slug'],'the-star')
        self.assertEqual(body['date'],str(timezone.localdate()))
    def test_daily_never_selects_drafts_or_future_or_unverified(self):
        self.poem.status='draft';self.poem.save()
        self.assertIsNone(self.client.get('/api/daily-rhyme/').json()['poem'])
    def test_age_country_and_collection_filters_combine(self):
        self.poem.age_min=7;self.poem.save()
        for q,count in [('country=GB&age=7&collection=verified',1),('country=GB&age=3',0),('collection=original',0)]:
            self.assertEqual(self.client.get('/api/poems/?'+q).json()['count'],count)
        self.assertEqual(self.client.get('/api/poems/?age=100').status_code,400)
        self.assertEqual(self.client.get('/api/poems/?country=XX').status_code,400)
    def test_detail_escapes_source_text_and_exposes_reader_controls(self):
        self.poem.poem_text='<script>alert(1)</script>\nA star.';self.poem.save()
        r=self.client.get(self.poem.get_absolute_url())
        self.assertContains(r,'&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertContains(r,'data-repeat-line="1"')
        self.assertContains(r,'reader-voice')
        self.assertContains(r,self.work.source_url)
    def test_host_and_scheme_allowlist(self):
        for url in ['http://en.wikisource.org/wiki/X','https://evil.example/wiki/X','https://en.wikisource.org.evil.example/wiki/X','https://user@en.wikisource.org/wiki/X']:
            self.work.source_url=url
            with self.assertRaises(ValidationError):validate_source(self.work)
        self.work.source_url='https://en.wikisource.org/wiki/X';self.provider.language_code='en.evil';self.work.provider=self.provider
        with self.assertRaises(ValidationError):validate_source(self.work)
    @patch('library.sources.read_json')
    def test_api_response_cached_and_safe_text_only(self,read):
        read.return_value=self.payload()
        self.assertEqual(retrieve(self.work),(self.work.baseline_text,'123'))
        self.assertEqual(retrieve(self.work),(self.work.baseline_text,'123'))
        self.assertEqual(read.call_count,1)
    @patch('library.sources.read_json')
    def test_unmatched_remote_text_fails_closed(self,read):
        read.return_value=self.payload('A changed copyrighted poem')
        run=sync_work(self.work)
        self.assertFalse(run.succeeded)
        self.assertEqual(ImportCandidate.objects.count(),0)
        self.poem.refresh_from_db();self.assertEqual(self.poem.poem_text,self.work.baseline_text)
    @patch('library.sources.read_json')
    def test_sync_is_idempotent_and_never_publishes(self,read):
        read.return_value=self.payload()
        self.assertTrue(sync_work(self.work).succeeded)
        self.assertTrue(sync_work(self.work).succeeded)
        self.assertEqual(ImportCandidate.objects.count(),1)
        self.assertEqual(Poem.objects.count(),1)
        self.provider.refresh_from_db();self.assertIsNotNone(self.provider.last_success_at)
    @patch('library.sources.read_json',side_effect=TimeoutError)
    def test_failure_recorded_without_fabricated_success(self,read):
        self.assertFalse(sync_work(self.work).succeeded)
        self.provider.refresh_from_db();self.assertIsNone(self.provider.last_success_at)
    def test_candidate_approval_permissions_and_unpublished_result(self):
        c=ImportCandidate.objects.create(work=self.work,text=self.work.baseline_text,revision_id='123',fingerprint='a'*64)
        with self.assertRaises(PermissionError):approve_candidate(c,self.staff)
        self.staff.user_permissions.add(*Permission.objects.filter(codename__in=['add_poem','change_importcandidate']))
        editor=User.objects.get(pk=self.staff.pk)
        result=approve_candidate(c,editor)
        self.assertEqual(result.status,'draft');self.assertFalse(result.rights_confirmed)
        self.assertEqual(self.client.get(result.get_absolute_url()).status_code,404)
        with self.assertRaises(ValidationError):approve_candidate(c,editor)
    def test_candidate_fingerprint_unique(self):
        ImportCandidate.objects.create(work=self.work,text='x',revision_id='1',fingerprint='a'*64)
        with self.assertRaises(IntegrityError),transaction.atomic():ImportCandidate.objects.create(work=self.work,text='x',revision_id='1',fingerprint='a'*64)
    def test_classic_requires_source_and_age_validation(self):
        self.poem.content_kind='traditional';self.poem.source_verified=False
        with self.assertRaises(ValidationError):self.poem.full_clean()
        self.poem.content_kind='original';self.poem.age_min=11
        with self.assertRaises(ValidationError):self.poem.full_clean()
    def test_audio_cues_validation(self):
        for cues in [[{'start':0,'line':99}],[{'start':2,'line':0},{'start':1,'line':1}],[{'start':float('nan'),'line':0}],{'line':0}]:
            self.poem.audio_cues=cues
            with self.assertRaises(ValidationError):self.poem.clean()
        self.poem.audio_cues=[{'start':0,'line':0},{'start':2.3,'line':1}];self.poem.clean()
    def test_translation_requires_review_and_distinct_poems(self):
        t=Translation(original=self.poem,translated_poem=self.poem,method='machine',translator='Test',rights_notes='Test')
        with self.assertRaises(ValidationError):t.clean()
    def test_admin_authentication_still_required(self):
        r=self.client.get('/admin/library/importcandidate/')
        self.assertEqual(r.status_code,302)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get('/admin/library/importcandidate/').status_code,403)
    @patch('library.sources.read_json',side_effect=AssertionError('Tests must not call external key infrastructure'))
    def test_scheduled_endpoint_is_not_public(self,external):
        csrf_client=Client(enforce_csrf_checks=True)
        self.assertEqual(csrf_client.get('/api/editorial/sync/').status_code,405)
        self.assertEqual(csrf_client.post('/api/editorial/sync/').status_code,401)
        self.assertEqual(csrf_client.post('/api/editorial/sync/',HTTP_AUTHORIZATION='Bearer fake').status_code,403)
        external.assert_not_called()
    @patch('library.views.verify_workflow_token',return_value={'run_id':'123','run_attempt':'1'})
    @patch('library.sources.sync_work')
    def test_verified_job_replay_blocked_and_zero_publications(self,sync,verify):
        sync.return_value=SyncRun(work=self.work,succeeded=True,message='Checked')
        r=self.client.post('/api/editorial/sync/',HTTP_AUTHORIZATION='Bearer signed')
        self.assertEqual(r.status_code,200);self.assertEqual(r.json()['published'],0)
        self.assertEqual(self.client.post('/api/editorial/sync/',HTTP_AUTHORIZATION='Bearer signed').status_code,409)
    def test_feature_schedule_constraint(self):
        now=timezone.now()
        with self.assertRaises(IntegrityError),transaction.atomic():FeaturedSchedule.objects.create(poem=self.poem,starts_at=now,ends_at=now-timedelta(minutes=1))

class CuratedSeedTests(TestCase):
    def test_seed_preserves_editor_changes_and_unicode(self):
        call_command('seed_demo',verbosity=0)
        call_command('seed_world_library',verbosity=0)
        self.assertEqual(Poem.objects.filter(source_verified=True).count(),17)
        self.assertEqual(Poem.objects.filter(content_kind='ai_demo').count(),16)
        p=Poem.objects.get(slug='twinkle-twinkle-little-star');p.title='Our edited display title';p.save()
        call_command('seed_world_library',verbosity=0)
        p.refresh_from_db();self.assertEqual(p.title,'Our edited display title')
        self.assertEqual(Poem.objects.filter(source_verified=True).count(),17)
        self.assertTrue(Poem.objects.filter(poem_text__contains='அகர').exists())
        self.assertTrue(Poem.objects.filter(poem_text__contains='さくら').exists())
        for record in [*Author.objects.all(),*ContentProvider.objects.all(),*SourceWork.objects.all()]:
            record.full_clean()
        self.assertTrue(any(len(a.reference_url)>200 for a in Author.objects.all()))
        for poem in Poem.objects.filter(source_verified=True):
            poem.full_clean()
        from library.audio import builtin_recording
        self.assertIsNotNone(builtin_recording(p))
        p.poem_text+='\nEditor changed the words.';p.save()
        self.assertIsNone(builtin_recording(p))

class WorkflowIdentityTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from cryptography.hazmat.primitives.asymmetric import rsa
        import jwt
        cls.private=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        cls.jwk=json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(cls.private.public_key()));cls.jwk['kid']='test-key'
    def setUp(self):cache.clear()
    def token(self,**overrides):
        import jwt
        now=int(time.time());claims={'iss':'https://token.actions.githubusercontent.com','aud':'little-rhymes-content-sync','iat':now,'nbf':now-1,'exp':now+120,'repository':'VV244/little-rhymes','repository_id':'1458484371','ref':'refs/heads/main','workflow_ref':'VV244/little-rhymes/.github/workflows/content-sync.yml@refs/heads/main','event_name':'schedule','run_id':'123','run_attempt':'1'};claims.update(overrides)
        return jwt.encode(claims,self.private,algorithm='RS256',headers={'kid':'test-key'})
    def test_signed_identity_and_all_scoping_claims(self):
        with patch('library.sources.read_json',return_value={'keys':[self.jwk]}):
            self.assertEqual(verify_workflow_token(self.token())['repository'],'VV244/little-rhymes')
            for overrides in [{'repository':'attacker/repo'},{'repository_id':'999'},{'ref':'refs/heads/evil'},{'event_name':'pull_request'},{'workflow_ref':'VV244/little-rhymes/.github/workflows/evil.yml@refs/heads/main'},{'aud':'wrong'},{'exp':1}]:
                with self.subTest(overrides=overrides),self.assertRaises(Exception):verify_workflow_token(self.token(**overrides))
