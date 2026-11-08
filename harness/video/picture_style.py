"""Reference picture layout: fit the source, black bars, small channel watermark."""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path
from typing import Literal
import cv2
import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator
from harness.subtitle import _ass_time, _escape_ass, choose_font


class PictureStyle(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    enabled: bool = False
    width: int = Field(default=1920, ge=64, le=7680)
    height: int = Field(default=1080, ge=64, le=4320)
    top_bar: int = Field(default=116, ge=0)
    bottom_bar: int = Field(default=116, ge=0)
    crop_source_bars: bool = True
    fit_mode: Literal['cover','contain'] = 'cover'
    watermark: str = 'Review Phim'
    font_size: int = Field(default=28, ge=8, le=200)
    margin_right: int = Field(default=90, ge=0)
    margin_bottom: int = Field(default=250, ge=0)

    @model_validator(mode='after')
    def layout(self):
        if self.width % 2 or self.height % 2 or self.top_bar % 2 or self.bottom_bar % 2:
            raise ValueError('Canvas and bars must use even pixel sizes')
        if self.top_bar + self.bottom_bar >= self.height - 32:
            raise ValueError('Bars leave no usable picture area')
        if self.margin_right >= self.width or self.margin_bottom >= self.height:
            raise ValueError('Watermark margins must lie inside the canvas')
        return self


@lru_cache(maxsize=64)
def _source_bars(path: str, size: int, modified: int) -> tuple[int, int]:
    capture = cv2.VideoCapture(path)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    count = capture.get(cv2.CAP_PROP_FRAME_COUNT)
    masks = []
    for position in np.linspace(.1, .9, 7):
        capture.set(cv2.CAP_PROP_POS_FRAMES, round(position * max(0, count - 1)))
        ok, frame = capture.read()
        if ok:
            light = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            mask = (light <= 12).mean(axis=1) > .97
            if not mask.all():
                masks.append(mask)
    capture.release()
    if not masks:
        return 0, 0
    black = np.mean(masks, axis=0) >= .85
    rows = np.flatnonzero(~black)
    if not len(rows):
        return 0, 0
    top, bottom = int(rows[0]) // 2 * 2, int(height - 1 - rows[-1]) // 2 * 2
    return (top, bottom) if top + bottom < height * .4 else (0, 0)


def picture_filters(style: PictureStyle, source: str, duration: float, directory: Path) -> tuple[list[str], Path | None]:
    if not style.enabled:
        return [], None
    filters = []
    if style.crop_source_bars:
        path = Path(source).resolve()
        stat = path.stat()
        top, bottom = _source_bars(str(path), stat.st_size, stat.st_mtime_ns)
        if top or bottom:
            filters.append(f'crop=iw:ih-{top+bottom}:0:{top}')
    active = style.height - style.top_bar - style.bottom_bar
    if style.fit_mode == 'cover':
        filters += [f'scale={style.width}:{active}:force_original_aspect_ratio=increase:force_divisible_by=2',
                    f'crop={style.width}:{active}',f'pad={style.width}:{style.height}:0:{style.top_bar}:color=black']
    else:
        filters += [f'scale={style.width}:{active}:force_original_aspect_ratio=decrease:force_divisible_by=2',
                    f'pad={style.width}:{style.height}:(ow-iw)/2:{style.top_bar}+({active}-ih)/2:color=black']
    filters.append('setsar=1')
    if not style.watermark.strip():
        return filters, None
    directory.mkdir(parents=True, exist_ok=True)
    overlay = directory / 'branding.ass'
    text = '\n'.join([
        '[Script Info]', 'ScriptType: v4.00+', f'PlayResX: {style.width}', f'PlayResY: {style.height}', '',
        '[V4+ Styles]',
        'Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding',
        f'Style: Channel,{choose_font()},{style.font_size},&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,1,0,0,0,100,100,0,0,1,1,1,3,0,{style.margin_right},{style.margin_bottom},1', '',
        '[Events]', 'Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text',
        f'Dialogue: 0,0:00:00.00,{_ass_time(duration)},Channel,,0,0,0,,{_escape_ass(style.watermark)}', ''])
    overlay.write_text(text, encoding='utf-8-sig')
    return filters, overlay
