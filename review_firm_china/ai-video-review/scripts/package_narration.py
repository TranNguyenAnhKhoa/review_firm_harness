"""Package verified TTS-only results for listening; this is not a rendered video."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.measure_review import cache_signatures
from src.audio.narration_builder import concatenate_pcm
from src.pipeline.build_review import load_config
from src.pipeline.editorial import require_timing
from src.pipeline.schema import ReviewScript
from src.subtitle.generator import generate_ass
from src.utils import executable, run_command
from src.video.probe import probe_audio, probe_video


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review',required=True)
    parser.add_argument('--output-dir',required=True)
    parser.add_argument('--config',default=str(ROOT/'config/config.yaml'))
    args=parser.parse_args()
    root=Path(args.output_dir)
    review_file=Path(args.review)
    review=ReviewScript.load(review_file)
    report=json.loads((root/'review_timing.json').read_text(encoding='utf-8'))
    require_timing(report)
    if report['review_sha256']!=hashlib.sha256(review_file.read_bytes()).hexdigest():
        raise ValueError('Timing report belongs to another revision')
    config=load_config(args.config)
    code_hash=hashlib.sha256(b''.join(p.read_bytes() for p in sorted((ROOT/'src/audio').glob('*.py')))).hexdigest()
    paths, subtitles, index=[],[],[]
    cursor=0.0
    for segment in review.segments:
        wav=root/'audio'/f'segment_{segment.id:03d}.wav'
        debug=root/'debug'/f'segment_{segment.id:03d}_tts.json'
        marker=json.loads((root/'debug'/f'segment_{segment.id:03d}.cache.json').read_text(encoding='utf-8'))
        signature,_=cache_signatures(segment,config,code_hash,{})
        if (marker['signature']!=signature or marker['audio_sha256']!=hashlib.sha256(wav.read_bytes()).hexdigest()
                or marker['debug_sha256']!=hashlib.sha256(debug.read_bytes()).hexdigest()):
            raise ValueError(f'Unverified or stale speech cache for segment {segment.id}')
        data=json.loads(debug.read_text(encoding='utf-8'))
        duration=probe_audio(wav)
        if abs(duration-data['duration'])>.001:
            raise ValueError(f'Audio duration mismatch for segment {segment.id}')
        for unit in data['units']:
            subtitles.append({'narration':unit['text'],'start':cursor+unit['start'],'duration':unit['end']-unit['start']})
        index.append({'segment_id':segment.id,'audio_start':cursor,'audio_end':cursor+duration,
                      'source_start':segment.source_start,'source_end':segment.source_end})
        cursor+=duration
        paths.append(wav)
    output=root/'listening'
    output.mkdir(parents=True,exist_ok=True)
    wav=output/'moana_narration.wav'
    mp3=output/'moana_narration.mp3'
    if wav.exists() or mp3.exists():
        raise FileExistsError('Preserve existing listening package; choose another output directory or archive it explicitly')
    concatenate_pcm(paths,wav)
    if abs(probe_audio(wav)-cursor)>.001:
        raise RuntimeError('Concatenated narration duration mismatch')
    run_command([executable('ffmpeg','FFMPEG_BINARY'),'-hide_banner','-i',str(wav),
                 '-c:a','libmp3lame','-b:a','192k',str(mp3)])
    metadata=probe_video(review.source_video)
    generate_ass(subtitles,str(output/'moana_narration.ass'),
        font_size=config['subtitle']['font_size'],max_chars_per_line=config['subtitle']['max_chars_per_line'],
        width=metadata['width'],height=metadata['height'],position=config['subtitle'].get('position','bottom'))
    (output/'audio_index.json').write_text(json.dumps({'audio_duration':cursor,
        'note':'Audio-only offsets; final video offsets include per-clip frame rounding. No video rendered.',
        'segments':index},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Listening WAV:',wav,'seconds:',cursor)
    print('Listening MP3:',mp3)
    print('Subtitles follow speech-unit timing and exclude inserted pauses. These are audio-only preview offsets.')


if __name__=='__main__':main()
