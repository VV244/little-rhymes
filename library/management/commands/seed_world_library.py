"""Add reviewed classics without replacing any existing poem or editorial change."""
import json
from pathlib import Path
from urllib.parse import quote
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from library.models import Author, Country, ContentProvider, SourceWork
from poems.models import Poem, Language, ClassLevel, Category

LANGUAGES={'en':('English','English','english'),'hi':('Hindi','हिन्दी','hindi'),'mr':('Marathi','मराठी','marathi'),'sa':('Sanskrit','संस्कृतम्','sanskrit'),'ta':('Tamil','தமிழ்','tamil'),'te':('Telugu','తెలుగు','telugu'),'bn':('Bengali','বাংলা','bengali'),'gu':('Gujarati','ગુજરાતી','gujarati'),'fr':('French','Français','french'),'es':('Spanish','Español','spanish'),'de':('German','Deutsch','german'),'ja':('Japanese','日本語','japanese')}
COUNTRIES={'GB':'United Kingdom','US':'United States','IN':'India','FR':'France','AR':'Argentina','DE':'Germany','JP':'Japan'}

class Command(BaseCommand):
    help='Add 17 documented public-domain text selections; preserve existing content and URLs.'
    @transaction.atomic
    def handle(self,*args,**options):
        rows=json.loads((Path(__file__).resolve().parents[2]/'data'/'classics.json').read_text())
        countries={code:Country.objects.get_or_create(code=code,defaults={'name':name})[0] for code,name in COUNTRIES.items()}
        langs={code:Language.objects.get_or_create(code=code,defaults={'name':values[0],'native_name':values[1],'slug':values[2]})[0] for code,values in LANGUAGES.items()}
        created=0
        for order,row in enumerate(rows):
            lang=langs[row['language']]; country=countries[row['country']]
            author=None
            if row['author']:
                author,_=Author.objects.get_or_create(name=row['author'],defaults={'country':country,'death_year':row['death_year']})
            manual=row['source'].startswith('https:') or not row['sync']
            provider,_=ContentProvider.objects.get_or_create(name=f'Wikisource · {lang.name}' if not row['source'].startswith('https:') else ('Carus / SWR Liederprojekt' if row['language']=='de' else 'Ekatra Foundation'),defaults={'kind':'reference' if manual else 'wikisource','language_code':lang.code,'terms_url':'https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use' if not row['source'].startswith('https:') else row['source'],'is_active':not manual})
            source_url=row['source'] if row['source'].startswith('https:') else f'https://{lang.code}.wikisource.org/wiki/'+quote(row['source'],safe='/')
            work,_=SourceWork.objects.get_or_create(provider=provider,page_title=row['source'],defaults={'title':row['title'],'source_url':source_url,'author':author,'country':country,'language':lang,'license_code':'PD','license_url':'https://creativecommons.org/publicdomain/mark/1.0/','rights_notes':row['rights_notes'],'baseline_text':row['text'],'revision_id':row['revision'],'approved_for_sync':not manual})
            if author and not author.reference_url: author.reference_url=source_url;author.save(update_fields=['reference_url'])
            older=lang.code in ('hi','mr','sa','ta','te','bn','gu')
            poem,new=Poem.objects.get_or_create(slug=row['slug'],defaults={'title':row['title'],'language':lang,'source_work':work,'author':row['author'] or 'Traditional; author unknown','content_kind':'authored' if author else 'traditional','source_verified':True,'poem_text':row['text'],'short_description':row['description'],'theme':row['theme'],'illustration':{'night':'night','jungle':'bird','ocean':'rain'}.get(row['theme'],'garden'),'builtin_audio':row['slug'] if lang.code=='en' else '', 'is_excerpt':row['is_excerpt'],'age_min':7 if older else 3,'age_max':10,'keywords':f"{country.name} {lang.name} traditional classic public domain {row['theme']}",'rights_statement':f"Public-domain underlying text. {row['rights_notes']} Source: {source_url}. All 3D geometry and fallback illustrations are original Little Rhymes assets. English bundled recordings are original synthetic narration using Flite CMU US SLT; voice/engine notices are in THIRD_PARTY_NOTICES.md.",'rights_confirmed':True,'status':'published','published_at':timezone.now(),'home_priority':200-order,'is_featured':order in (0,7,13)})
            if new:
                created+=1
                levels=ClassLevel.objects.filter(is_active=True)
                if older: levels=levels.filter(slug__in=['class-2','class-3','class-4'])
                poem.classes.set(levels)
                tags=['nursery-rhymes'] if not older else ['educational-poems']
                tags+=['animal-poems'] if row['theme']=='jungle' else ['bedtime-poems','nature-poems'] if row['theme']=='night' else ['nature-poems']
                poem.categories.set(Category.objects.filter(slug__in=tags,is_active=True))
        # Only known generated demo records are relabelled. Text, media and URLs stay intact.
        Poem.objects.filter(author='Little Rhymes · original demonstration',source_work__isnull=True).update(content_kind='ai_demo')
        cache.delete('navigation')
        self.stdout.write(self.style.SUCCESS(f'Added {created} sourced classics; existing poems and editor changes preserved.'))
