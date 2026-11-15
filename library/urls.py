from django.urls import path
from . import views
app_name='library'
urlpatterns=[path('activities/',views.activities,name='activities'),path('grownups/',views.grownups,name='grownups'),path('sources/',views.sources,name='sources'),path('api/daily-rhyme/',views.daily_api,name='daily'),path('api/content-status/',views.sync_status,name='status'),path('api/editorial/sync/',views.scheduled_sync,name='sync')]
