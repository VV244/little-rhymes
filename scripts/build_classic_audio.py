"""Offline audio asset build. Requires FFmpeg built with libflite (CMU SLT voice).
No runtime synthesis service, tracking or network is involved.
"""
import hashlib,json,subprocess,tempfile,wave
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
rows=json.loads((ROOT/'library/data/classics.json').read_text())
manifest={}
with tempfile.TemporaryDirectory() as temp:
    tmp=Path(temp)
    for row in rows:
        if row['language']!='en':continue
        frames=[];cues=[];seconds=0
        lines=[line for line in row['text'].splitlines() if line.strip()]
        for index,line in enumerate(lines):
            textfile=tmp/'line.txt';textfile.write_text(line)
            wavfile=tmp/'line.wav'
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi','-i',f'flite=textfile={textfile}:voice=slt','-af','atempo=0.88','-ar','22050','-ac','1',str(wavfile)],check=True)
            with wave.open(str(wavfile),'rb') as wav:
                data=wav.readframes(wav.getnframes());rate=wav.getframerate()
            cues.append({'start':round(seconds,3),'line':index})
            silence=b'\0\0'*int(rate*.3)
            frames.extend([data,silence]);seconds+=(len(data)+len(silence))/(rate*2)
        combined=tmp/'combined.wav'
        with wave.open(str(combined),'wb') as out:
            out.setnchannels(1);out.setsampwidth(2);out.setframerate(rate);out.writeframes(b''.join(frames))
        target=ROOT/'static/audio/classics'/f"{row['slug']}.mp3"
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(combined),'-c:a','libmp3lame','-b:a','56k',str(target)],check=True)
        manifest[row['slug']]={'sha256':hashlib.sha256(row['text'].encode()).hexdigest(),'cues':cues,'seconds':round(seconds,3),'voice':'Flite CMU US SLT (synthetic)','rights':'Original synthesized narration generated for Little Rhymes; Flite and voice license notices in THIRD_PARTY_NOTICES.md. Public-domain text; no third-party performance copied.'}
        print(target.name,round(seconds,2),'seconds',target.stat().st_size,'bytes')
(ROOT/'library/data/audio_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
