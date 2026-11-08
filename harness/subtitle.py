from __future__ import annotations

import textwrap
import os
from pathlib import Path
from typing import Iterable


def _ass_time(seconds: float) -> str:
    centiseconds = round(max(seconds, 0) * 100)
    hours, remainder = divmod(centiseconds, 360000)
    minutes, remainder = divmod(remainder, 6000)
    sec, cs = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{sec:02d}.{cs:02d}"


def _escape_ass(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}").replace("\n", r"\N")


def choose_font() -> str:
    """Choose an installed common Unicode font; libass handles glyph fallback."""
    if os.name == "nt":
        fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        for filename, family in (("arial.ttf", "Arial"), ("segoeui.ttf", "Segoe UI"), ("tahoma.ttf", "Tahoma")):
            if (fonts / filename).exists():
                return family
    return "DejaVu Sans"


def generate_ass(segments: Iterable[dict], output_path: str, *, font_size: int = 48, max_chars_per_line: int = 35, width: int = 1920, height: int = 1080, position: str = "bottom", margin_vertical: int = 40) -> Path:
    """Build Vietnamese-safe ASS subtitles from narration and measured durations."""
    output = Path(output_path)
    if not 0 <= margin_vertical < height:
        raise ValueError("Subtitle margin_vertical must be within the picture height")
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {width}", f"PlayResY: {height}", "WrapStyle: 2", "",
        "[V4+ Styles]", "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
        f"Style: Default,{choose_font()},{font_size},&H00FFFFFF,&H000000FF,&H00101010,&H80000000,1,0,0,0,100,100,0,0,1,2,1,{2 if position == 'bottom' else 8},30,30,{margin_vertical},1", "",
        "[Events]", "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
    ]
    cursor = 0.0
    for item in segments:
        duration = float(item["duration"])
        # Split long narration into two-line events, proportionally timed (not word alignment).
        wrapped = textwrap.wrap(item["narration"], width=max_chars_per_line, break_long_words=True)
        chunks = ["\n".join(wrapped[i:i + 2]) for i in range(0, len(wrapped), 2)]
        cursor = float(item.get("start", cursor))
        end = cursor + duration
        weight = sum(len(chunk) for chunk in chunks)
        for index, chunk in enumerate(chunks):
            chunk_end = end if index == len(chunks) - 1 else cursor + duration * len(chunk) / weight
            lines.append(f"Dialogue: 0,{_ass_time(cursor)},{_ass_time(chunk_end)},Default,,0,0,0,,{_escape_ass(chunk)}")
            cursor = chunk_end
    output.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    return output
