"""Only serve a bundled narration while its exact text checksum still matches."""
import hashlib
import json
from functools import lru_cache
from pathlib import Path
from django.templatetags.static import static

@lru_cache(maxsize=1)
def manifest():
    return json.loads((Path(__file__).parent/'data'/'audio_manifest.json').read_text())

def builtin_recording(poem):
    entry=manifest().get(poem.builtin_audio)
    if entry and entry['sha256']==hashlib.sha256(poem.poem_text.encode()).hexdigest():
        return {**entry,'url':static(f'audio/classics/{poem.builtin_audio}.mp3')}
    return None
