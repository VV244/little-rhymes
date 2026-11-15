"""Optional editor-only Azure Speech REST integration. No visitor data is sent."""
import json
import os
import re
from urllib.error import URLError,HTTPError
from urllib.request import Request,build_opener
from xml.sax.saxutils import escape,quoteattr
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand,CommandError
from poems.models import Poem
from poems.validators import validate_audio
from library.sources import NoRedirect

class Command(BaseCommand):
    help='Generate licensed synthetic narration with your Azure Speech subscription. Requires explicit --confirm-provider-terms; can incur provider charges.'
    def add_arguments(self,parser):
        parser.add_argument('slug');parser.add_argument('--voice',required=True)
        parser.add_argument('--confirm-provider-terms',action='store_true')
    def handle(self,*args,**options):
        if not options['confirm_provider_terms']:raise CommandError('Review Azure Speech terms and costs, then explicitly pass --confirm-provider-terms.')
        key=os.getenv('AZURE_SPEECH_KEY','');region=os.getenv('AZURE_SPEECH_REGION','')
        if not key or not re.fullmatch(r'[a-z0-9-]{3,40}',region):raise CommandError('Configure AZURE_SPEECH_KEY and AZURE_SPEECH_REGION privately.')
        try:poem=Poem.objects.select_related('language').get(slug=options['slug'])
        except Poem.DoesNotExist:raise CommandError('Poem not found.')
        if not poem.rights_confirmed:raise CommandError('Confirm narration rights on the poem first.')
        if poem.audio_file:raise CommandError('A recording already exists. Preserve it or remove it deliberately in admin before generating another.')
        voice=options['voice']
        opener=build_opener(NoRedirect)
        base=f'https://{region}.tts.speech.microsoft.com/cognitiveservices'
        headers={'Ocp-Apim-Subscription-Key':key,'User-Agent':'LittleRhymesEditorial/2.0'}
        try:
            with opener.open(Request(base+'/voices/list',headers=headers),timeout=20) as response:
                raw=response.read(2_000_001)
                if len(raw)>2_000_000:raise ValueError('Voice catalog too large.')
                voices=json.loads(raw)
            selected=next((v for v in voices if v.get('ShortName')==voice),None)
            if not selected or selected.get('Locale','').split('-')[0].lower()!=poem.language.code.split('-')[0].lower():raise ValueError('Choose an available voice matching the poem language.')
            ssml=f'<speak version="1.0" xml:lang={quoteattr(selected["Locale"])}><voice name={quoteattr(voice)}><prosody rate="-15%">{escape(poem.poem_text)}</prosody></voice></speak>'
            with opener.open(Request(base+'/v1',data=ssml.encode(),headers={**headers,'Content-Type':'application/ssml+xml','X-Microsoft-OutputFormat':'audio-24khz-48kbitrate-mono-mp3'},method='POST'),timeout=45) as response:
                audio=response.read(20*1024*1024+1)
            if not audio or len(audio)>20*1024*1024:raise ValueError('Narration exceeds the audio limit.')
            file=ContentFile(audio,name='azure-narration.mp3');validate_audio(file);file.seek(0)
            poem.audio_file.save(file.name,file,save=False)
            poem.audio_cues=[]
            poem.rights_statement=(poem.rights_statement+f' Synthetic narration: Azure Speech {voice}; generated under the operator’s Speech subscription.').strip()
            poem.full_clean();poem.save()
        except (URLError,HTTPError,ValueError,TimeoutError,json.JSONDecodeError) as exc:
            raise CommandError('Narration failed. Check provider configuration, voice, quota and service status; credentials were not logged.') from None
        self.stdout.write(self.style.SUCCESS('Synthetic narration saved in configured persistent media storage. No timing cues were invented. Review playback and credits before publication.'))
