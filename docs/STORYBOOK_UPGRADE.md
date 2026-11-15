# Little Rhymes storybook upgrade

## Existing service and compatibility

Live service: https://little-rhymes-1.onrender.com/
Admin: https://little-rhymes-1.onrender.com/admin/
Source: https://github.com/VV244/little-rhymes (main).
Render service: srv-dbskrsmc6qcc739f820g, Singapore, Python, free web compute.
The separate similarly named Render service is not used by this release.

Django 5.2, PostgreSQL, Redis, S3-compatible media, Django authentication, Axes,
CSRF, contact protection, permanent poem URLs, SEO and the existing admin remain.
Migrations only add tables/fields/constraints; they do not remove existing poems,
media, users, contact messages or URLs. No passwords are changed by deployment.
PostgreSQL server-side cursors are disabled for transaction-pooler compatibility, including language filters and sitemap iteration. The existing environment variables remain valid. No new paid resource is required.

## Local setup

1. Install Python 3.12+ and Git. Clone this repository.
2. Create a virtual environment: `python -m venv .venv`.
3. Activate it (`.venv\Scripts\activate` on Windows, `source .venv/bin/activate` on Linux/macOS).
4. `pip install -r requirements.txt`.
5. Copy `.env.example` to `.env`; keep `DEBUG=True` locally. Never commit `.env`.
6. `python manage.py migrate`.
7. `python manage.py seed_demo` then `python manage.py seed_world_library`.
8. `python manage.py createsuperuser` if a local administrator is needed.
9. `python manage.py runserver` and open http://127.0.0.1:8000/.
10. For frontend changes, install Node 22+, run `npm ci`, `npm run typecheck`,
    and `npm run build`. Bundles are committed, so Node is not required by the
    existing Render Python build. Remove obsolete scene chunks after rebuilding.
11. Run `python manage.py check`, `python manage.py makemigrations --check`,
    and `python manage.py test` before committing.

## Experience

- Homepage: original miniature 3D storybook island, opening book, original animal
  geometry, trees, flowers, rainbow, river/waterfall and soft light/shadows.
  Pip and the book respond to pointer selection; links offer equivalent keyboard
  navigation. Five reader themes: garden, night, jungle, ocean and rain.
- WebGL 2 is required for 3D. Unsupported browsers, reduced motion, low memory,
  Save-Data or an explicit 2D preference get an original SVG illustration instead.
  The 3D engine is not downloaded for these users. Device pixel ratio is capped
  at 1.5, frame rate at 30fps, and offscreen/hidden scenes do not render.
- Reader: matching-language installed voice selection, slow pace, volume,
  pause/stop/repeat, line replay, word-boundary highlighting where supported,
  actual recording line cues where supplied. No guessed word timing is shown.
- Five English classics include original synthetic Flite recordings, served as
  small static MP3s, with measured line cues and text checksum protection.
  This is synthetic speech, not a human performance or musical sing-along.
- Optional gentle tones are generated locally with WebAudio after a deliberate
  click. No autoplay music, videos, microphone use or recording occurs.
- Wonder Workshop: alphabet, counting, colours/shapes, animal sound words,
  nature, rhymes, memory, picture matching, listen/repeat and simple quizzes.
  English activities; counting and memory complexity vary by selected stage.
  Speech depends on an installed English voice. Animal sounds are spoken
  imitations/words, not animal recordings. Voice pronunciation is not assessed.
- Grown-up dashboard: culture/age/class/language/category filters, local reading
  lists (10 lists × 50 poems), favourites, print tools, light/dark and 2D/3D
  preferences. Parent mode shows list tools on readers; mode is not authentication.
- Browser-local data is not synced between devices. Clearing browser data removes
  lists/favourites. Use topic names, not children’s names. No child accounts or
  scores are collected.

## Real poetry and rights

`library/data/classics.json` contains 17 documented original-language selections
across 12 languages. Existing 16 generated demos remain, marked AI demonstrations.
New fields record source, origin, author, rights, theme, ages and excerpt status.
Sources are named editions of Wikisource and manual publisher references.
Underlying public-domain text is used; no modern performance/art/translation is
copied. Individual versions retain their historical wording. Tagore’s selection
is the opening of Nadi, not the different poem Amader Chhoto Nodi. Andrade’s
Los pollitos is not the separate song Los pollitos dicen.

The Wheels on the Bus is not included: a reliable license for reproducing its
protected modern lyrics/performances has not been supplied. Do not infer that
familiarity or availability on the internet grants publication rights.

The Marathi Wikisource reference has an edition-verification warning. Its
Balakavi text/author dates were separately checked; automatic updates for that
page stay disabled until an editor compares an authoritative scan.

Every poem has source/rights information. Translations are separate records,
with translator, method and reviewer. Only verified, published equivalents get
hreflang links. Machine translations must remain identified until reviewed.

## API and actual source synchronization

Read-only APIs:

- `/api/poems/` and `/api/poems/<slug>/` — published poems and provenance.
- `/api/daily-rhyme/` — date-based rotation of verified, published records.
- `/api/content-status/` — actual provider state and last successful checks.

The word “daily” describes rotation, not a promise of a newly discovered poem.
There is no fake live counter, trend ranking or visitor-based recommendation.

The only automated external provider is Wikisource’s MediaWiki API. The importer
uses a fixed HTTPS host allowlist, no redirects, a 12-second network timeout,
2MB response cap, six-hour caching, maxlag=5, two-second provider pacing and
exact normalized matching against an editor-selected baseline. It imports only
that reviewed selection, never arbitrary page prose, scripts, images or commentary.
Failures are recorded; published poems are never overwritten or automatically
unpublished. Change a baseline only after rechecking source text and rights.

### Editorial steps

1. Admin → World poetry & editorial desk → Authors / Countries / Content providers.
2. Add a Source work: exact Wikisource language/page, source URL, text selection,
   rights evidence and language. Enable synchronization only after review.
3. Select at most two source works → “Check selected sources”, or run
   `python manage.py sync_poetry_sources` in a trusted server shell.
4. Admin → Import candidates. Compare the text, revision and license evidence.
5. “Approve into unpublished drafts” requires editorial change permission AND
   poem-add permission. It never changes an existing published poem.
6. Open the draft; set age/class/category/theme, verify attribution and media
   rights, preview it, then explicitly confirm rights and publish.
7. Use Featured schedules for date-bounded editorial picks. Performance/logs
   remain in Render’s monitoring dashboard, not a made-up application metric.

The GitHub workflow `.github/workflows/content-sync.yml` schedules bounded checks
at 03:37 UTC (09:07 IST) each day and allows manual “Run workflow”. It checks the
two least-recently checked approved works (unchecked works first, with explicit PostgreSQL NULL ordering); the catalog rotates over subsequent
runs. GitHub may delay scheduled jobs. To check the entire catalog now, use the
management command above. Failed checks need review in Sync runs.

No long-lived sync key is used. The machine endpoint verifies GitHub’s RS256
OIDC signature, issuer, audience, expiry, repository name AND ID, main ref,
exact workflow path, and schedule/manual event. A job identity is accepted once.
A shared Redis lock prevents overlapping runs. Requests create candidates only.
Cookie-authenticated browser/admin mutations still require CSRF.

`CONTENT_SYNC_REPOSITORY` defaults to `VV244/little-rhymes`; repository ID is
pinned. A fork or transfer needs a deliberate backend/workflow allowlist update.
Gutenberg is cited manually; no main-site crawler is configured. No third-party
paid poetry API is represented as connected.

## Optional Azure neural narration

Device speech and bundled recordings work without Azure. To generate other
language recordings, an operator may configure `AZURE_SPEECH_KEY` and
`AZURE_SPEECH_REGION` privately. This requires the operator’s own Azure Speech
resource, provider terms and quota; it can incur charges. It is not enabled or
claimed to be connected in this release.

After reviewing costs, terms and voice availability:

```sh
python manage.py generate_narration poem-slug --voice hi-IN-SwaraNeural --confirm-provider-terms
```

The command verifies an available language-matching voice, safely escapes SSML,
sends the approved poem text only, saves MP3 through existing persistent media
storage, and clears alignment rather than inventing timings. It refuses to
replace an existing uploaded recording. Add measured cues separately in admin.
Reference: https://learn.microsoft.com/azure/ai-services/speech-service/rest-text-to-speech

## Deploy the existing Render service

1. Keep PostgreSQL, Redis, S3 and current secret/environment settings.
2. Review migrations and take a database backup under your existing backup policy.
3. Commit application, migrations, `static/dist`, curated JSON and audio assets.
4. Push the tested commit to `VV244/little-rhymes`, `main`.
5. The connected service auto-deploys. Its current build command invokes `build.sh`
   and then repeats idempotent migrate/seed_demo steps. `build.sh` installs pinned
   dependencies, collects/compresses static assets, checks production settings,
   applies additive migrations, seeds missing records and runs two bounded source checks. Provider failures are recorded without failing publication or inventing success. It preserves edits.
   Build-time release steps are retained for compatibility with this free web
   service; a paid service may move migrations/seeding to pre-deploy.
6. Monitor the specific commit’s deploy to `live`; verify `/health/`, homepage,
   reader/audio, games, API filters and `/admin/` login. Do not create a new service
   or change paid plans for this upgrade.
7. In GitHub Actions, manually run “Check approved poetry sources” once after the
   new version is live, or wait for its daily schedule. Provider timestamps are
   blank until a real successful check occurs on the live environment.
8. Inspect `/sources/` and admin Sync runs / Import candidates. Nothing remote
   publishes without staff approval.

Security settings remain fail-closed: production requires DEBUG=False,
PostgreSQL, shared Redis, strong SECRET_KEY, HTTPS SITE_URL, explicit hosts and
CSRF origins, USE_S3=True and exact MEDIA_ORIGINS. Keep keys out of Git and chat.
The custom domain/DNS, backup, monitoring, and admin instructions in
`docs/DEPLOYMENT.md` still apply. Never recover or reset a live password as part
of a visual update; use the existing staff account.

## Verification limits

Automated Django tests cover public/draft visibility, permissions, CSRF/contact,
combined filters, Unicode, seed preservation, source host allowlists, caching,
API failure paths, candidate idempotency/approval, scheduled identity scoping,
replay protection, database constraints and recording text alignment.
TypeScript is checked and bundles built before release. Browser QA checks the
actual reading, games, favourites/lists and graceful unsupported-device path.
The managed QA browser disables WebGL and has no installed device voices;
full GPU rendering and device-voice pronunciation require validation on a
WebGL-enabled phone/computer with the desired voices installed.
