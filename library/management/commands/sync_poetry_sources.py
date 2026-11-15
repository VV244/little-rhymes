from django.core.management.base import BaseCommand
from library.models import SourceWork
from library.sources import sync_work
import time

class Command(BaseCommand):
    help='Check approved Wikisource selections; queue drafts only. No automatic publication.'
    def add_arguments(self,parser):
        parser.add_argument('--limit',type=int,default=0,help='Maximum works; 0 checks the full approved catalog.')
    def handle(self,*args,**kwargs):
        works=SourceWork.objects.filter(approved_for_sync=True,provider__is_active=True).select_related('provider').order_by('last_checked_at','pk')
        if kwargs['limit']>0:works=works[:kwargs['limit']]
        for work in works:
            run=sync_work(work)
            self.stdout.write(f'{work}: {run.message}')
            time.sleep(2.1)
