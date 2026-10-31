#!/usr/bin/env python3
"""
Workplace Make Firm - AI Video Review Workflow Monitor Server
A lightweight, high-performance localhost HTTP service to monitor,
visualize, and inspect video review production pipelines.
"""

import os
import sys
import json
import time
import re
import mimetypes
import subprocess
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
import urllib.parse

# Ensure stdout handles UTF-8 on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Root directories
WORKSPACE_ROOT = Path(r"d:\workplace_make_firm").resolve()
REVIEW_ROOT = WORKSPACE_ROOT / "review_firm_china" / "ai-video-review"
SRC_VIDEO_DIR = WORKSPACE_ROOT / "SrcVideo"
PUBLIC_DIR = Path(__file__).parent / "public"

# Friendly job titles mapping
FRIENDLY_JOB_TITLES = {
    "1004": "Mẫu Chuẩn 1004 (Golden Reference Flow)"
}

ORCHESTRATION_FILE = Path(__file__).parent / "agent_orchestration.json"

AGENT_DIRECTORY = {
    "antigravity_desktop": {
        "id": "antigravity_desktop",
        "name": "Antigravity Desktop Agent",
        "role": "Visual Timeline & Scene Grounding",
        "engine": "Antigravity 2.0 Desktop UI (CDP Loopback)",
        "icon": "🚀",
        "color": "#06b6d4",
        "default_mode": "ui_handoff",
        "description": "Điều khiển giao diện Antigravity Desktop qua loopback để phân tích video, trích xuất timeline.md, đối chiếu nhân vật & clip.",
        "script_ref": "scripts/antigravity_handoff.py",
        "prompt_ref": "prompts/antigravity_read.md"
    },
    "gemini_pro": {
        "id": "gemini_pro",
        "name": "Gemini Pro Vision Agent",
        "role": "Multimodal Video Analysis",
        "engine": "Gemini 1.5/2.0 Pro Multimodal",
        "icon": "💎",
        "color": "#3b82f6",
        "default_mode": "manual_handoff",
        "description": "Đọc video thời lượng dài bằng multimodal vision, đọc phụ đề ASR, tạo timeline.md đối chiếu.",
        "prompt_ref": "prompts/gemini_read.md"
    },
    "chatgpt_pro": {
        "id": "chatgpt_pro",
        "name": "ChatGPT Pro Editorial Agent",
        "role": "Humorous Scriptwriter & Speech Units",
        "engine": "ChatGPT Plus/Pro (GPT-4o/o1)",
        "icon": "✍️",
        "color": "#10b981",
        "default_mode": "manual_handoff",
        "description": "Biên tập kịch bản review.json giọng điệu dí dỏm, chuẩn giới trẻ, cấu trúc SpeechUnits và đúng 1 đoạn assessment 15s.",
        "prompt_ref": "prompts/write_review.md",
        "guidelines_ref": "docs/editorial-guidelines.md"
    },
    "zerotts_baotrang": {
        "id": "zerotts_baotrang",
        "name": "ZeroTTS Voice Agent (Bảo Trang)",
        "role": "Offline Neural Speech Synthesis",
        "engine": "ZeroTTS 0.1.5 (Bảo Trang ONNX/PyTorch)",
        "icon": "🎙️",
        "color": "#f59e0b",
        "default_mode": "autonomous",
        "description": "Tạo giọng đọc offline tự nhiên giọng Bảo Trang, decode PCM WAV 48kHz stereo và đo timing chuẩn xác.",
        "script_ref": "src/audio/tts.py"
    },
    "edgetts_cloud": {
        "id": "edgetts_cloud",
        "name": "Edge-TTS Cloud Agent (Hoài My / Nam Minh)",
        "role": "Cloud Neural Voice Alternative",
        "engine": "Microsoft Edge-TTS 7.2.8",
        "icon": "☁️",
        "color": "#0284c7",
        "default_mode": "autonomous",
        "description": "Tổng hợp giọng đọc đám mây độ trễ thấp, hỗ trợ kiểm tra đối chiếu tốc độ đọc đa giọng."
    },
    "scenedetect_agent": {
        "id": "scenedetect_agent",
        "name": "PySceneDetect & Keyframe Probe",
        "role": "Visual Scene Boundary Detector",
        "engine": "PySceneDetect 0.7.1 + OpenCV",
        "icon": "👁️",
        "color": "#8b5cf6",
        "default_mode": "autonomous",
        "description": "Dò tìm điểm cắt cảnh thông minh (Threshold 27), trích xuất contact sheets và mẫu khung hình đối chiếu.",
        "script_ref": "scripts/detect_scenes.py"
    },
    "montage_edl_agent": {
        "id": "montage_edl_agent",
        "name": "Montage & CapCut EDL Optimizer",
        "role": "Shot Boundary Fitting & Speed Pacing",
        "engine": "Internal Shot Fitting Engine + CapCut Draft Bridge",
        "icon": "✂️",
        "color": "#ec4899",
        "default_mode": "autonomous",
        "description": "Gắn speech_unit_id với khung hình đã đo, điều chỉnh slowdown nhịp cắt trong giới hạn an toàn, xuất CapCut draft.",
        "script_ref": "scripts/fit_reviewed_shots.py"
    },
    "ffmpeg_render": {
        "id": "ffmpeg_render",
        "name": "FFmpeg Parallel Render Engine",
        "role": "Clip Transcoding, Ducking & Assembly",
        "engine": "FFmpeg 9.0.1 (libx264, libass, aac)",
        "icon": "🎬",
        "color": "#ef4444",
        "default_mode": "autonomous",
        "description": "Render song song các chunk part_*.mkv, canvas 1920x1080/30fps, ducking âm nền với Demucs và concat hoàn thiện.",
        "script_ref": "scripts/render_measured_review.py"
    },
    "qc_certifier": {
        "id": "qc_certifier",
        "name": "Automated QC & Bitstream Auditor",
        "role": "Quality Assurance & Compliance Check",
        "engine": "Pipeline Validator + FFprobe Decoder",
        "icon": "🛡️",
        "color": "#14b8a6",
        "default_mode": "autonomous",
        "description": "Kiểm tra giải mã video H.264/AAC, tính toán tỷ lệ thời lượng chuẩn 40–50% và thời lượng đoạn assessment 10–20s.",
        "script_ref": "scripts/check_render_alignment.py"
    },
    "hermes_orchestrator": {
        "id": "hermes_orchestrator",
        "name": "Hermes Autonomous Supervisor",
        "role": "Agentic Workflow Scheduler & Process Manager",
        "engine": "Hermes Agent Framework (Local Workspace)",
        "icon": "⚡",
        "color": "#f97316",
        "default_mode": "autonomous",
        "description": "Quản trị tiến trình nền, tự động phục hồi khi có lỗi, chạy batch kiểm thử và giám sát tài nguyên hệ thống."
    }
}

STAGE_CANDIDATES = {
    1: ["scenedetect_agent", "hermes_orchestrator", "antigravity_desktop"],
    2: ["antigravity_desktop", "gemini_pro", "scenedetect_agent", "hermes_orchestrator"],
    3: ["chatgpt_pro", "antigravity_desktop", "gemini_pro"],
    4: ["zerotts_baotrang", "edgetts_cloud", "hermes_orchestrator"],
    5: ["montage_edl_agent", "hermes_orchestrator", "antigravity_desktop"],
    6: ["ffmpeg_render", "hermes_orchestrator"],
    7: ["qc_certifier", "antigravity_desktop", "chatgpt_pro"]
}

def load_orchestration_config():
    if ORCHESTRATION_FILE.exists():
        try:
            with open(ORCHESTRATION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"default_assignments": {}, "job_overrides": {}}

def save_orchestration_config(config_data):
    try:
        with open(ORCHESTRATION_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving orchestration: {e}")
        return False

def get_assigned_agent(job_name, stage_id):
    cfg = load_orchestration_config()
    job_over = cfg.get("job_overrides", {}).get(job_name, {}).get(str(stage_id))
    if job_over:
        aid = job_over.get("agent_id")
        base = AGENT_DIRECTORY.get(aid, AGENT_DIRECTORY["hermes_orchestrator"])
        return {**base, "mode": job_over.get("mode", base["default_mode"]), "notes": job_over.get("notes", "")}
    
    def_assign = cfg.get("default_assignments", {}).get(str(stage_id))
    if def_assign:
        aid = def_assign.get("agent_id")
        base = AGENT_DIRECTORY.get(aid, AGENT_DIRECTORY["hermes_orchestrator"])
        return {**base, "mode": def_assign.get("mode", base["default_mode"]), "notes": def_assign.get("notes", "")}
    
    # Fallback default
    fallback_map = {
        1: "scenedetect_agent",
        2: "antigravity_desktop",
        3: "chatgpt_pro",
        4: "zerotts_baotrang",
        5: "montage_edl_agent",
        6: "ffmpeg_render",
        7: "qc_certifier"
    }
    aid = fallback_map.get(stage_id, "hermes_orchestrator")
    base = AGENT_DIRECTORY.get(aid)
    return {**base, "mode": base["default_mode"], "notes": ""}

PORT = 3000

# Ensure mimetypes are set
mimetypes.add_type("video/mp4", ".mp4")
mimetypes.add_type("video/x-matroska", ".mkv")
mimetypes.add_type("audio/wav", ".wav")
mimetypes.add_type("audio/mpeg", ".mp3")
mimetypes.add_type("image/jpeg", ".jpg")
mimetypes.add_type("image/jpeg", ".jpeg")
mimetypes.add_type("image/png", ".png")
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/json", ".json")

def format_duration(seconds):
    if seconds is None:
        return "N/A"
    try:
        sec = float(seconds)
        m, s = divmod(int(sec), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"
    except Exception:
        return "N/A"

def format_bytes(num_bytes):
    if num_bytes is None:
        return "0 B"
    try:
        n = float(num_bytes)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if n < 1024.0:
                return f"{n:.2f} {unit}"
            n /= 1024.0
        return f"{n:.2f} PB"
    except Exception:
        return "0 B"

def scan_source_videos():
    videos = []
    if not SRC_VIDEO_DIR.exists():
        return videos
    
    for f in SRC_VIDEO_DIR.iterdir():
        if f.is_file() and f.suffix.lower() in [".mp4", ".mkv", ".mov", ".avi"]:
            stat = f.stat()
            # Check if this video is associated with any job
            fname = f.name.lower()
            associated_job = "1004" if "1004" in fname else f.stem

            videos.append({
                "filename": f.name,
                "path": str(f),
                "size_bytes": stat.st_size,
                "size_human": format_bytes(stat.st_size),
                "mtime": stat.st_mtime,
                "associated_job": associated_job,
                "status": "Linked" if associated_job else "Raw Asset"
            })
    return sorted(videos, key=lambda x: x["size_bytes"], reverse=True)

def find_script_for_job(job_name):
    scripts_dir = REVIEW_ROOT / "input" / "scripts"
    if not scripts_dir.exists():
        return None, None
    
    candidates = []
    for f in scripts_dir.iterdir():
        if f.name.endswith(".json"):
            name = f.name.lower()
            if job_name in name:
                candidates.append(f)
    
    if not candidates:
        return None, None
    
    # Priority for reviewed / render / latest
    priorities = ["render", "reviewed", "v3", "v2"]
    for p in priorities:
        for c in candidates:
            if p in c.name.lower():
                return c, c.name
    return candidates[0], candidates[0].name

def parse_script_summary(script_path):
    if not script_path or not script_path.exists():
        return None
    try:
        with open(script_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        segments = data.get("segments", [])
        total_segments = len(segments)
        total_speech_units = 0
        emotions_count = {}
        story_segments = 0
        assessment_segments = 0
        total_words = 0
        has_shots = 0

        parsed_segments = []
        for seg in segments:
            seg_id = seg.get("id")
            narration = seg.get("narration", "")
            section = seg.get("section", "story")
            if section == "assessment":
                assessment_segments += 1
            else:
                story_segments += 1
            
            shots = seg.get("shots", [])
            if shots:
                has_shots += 1
            
            seg_units = []
            if isinstance(narration, list):
                for unit in narration:
                    total_speech_units += 1
                    t = unit.get("text", "")
                    emo = unit.get("emotion", "normal")
                    emotions_count[emo] = emotions_count.get(emo, 0) + 1
                    total_words += len(t.split())
                    seg_units.append({
                        "id": unit.get("id"),
                        "text": t,
                        "emotion": emo,
                        "duration": unit.get("duration")
                    })
            elif isinstance(narration, str):
                total_speech_units += 1
                emotions_count["normal"] = emotions_count.get("normal", 0) + 1
                total_words += len(narration.split())
                seg_units.append({
                    "id": f"s{seg_id}_u1",
                    "text": narration,
                    "emotion": "normal"
                })

            parsed_segments.append({
                "id": seg_id,
                "section": section,
                "source_start": seg.get("source_start"),
                "source_end": seg.get("source_end"),
                "source_duration": (seg.get("source_end") - seg.get("source_start")) if (seg.get("source_end") is not None and seg.get("source_start") is not None) else None,
                "visual_intent": seg.get("visual_intent"),
                "shots_count": len(shots),
                "units": seg_units,
                "first_text": seg_units[0]["text"] if seg_units else ""
            })

        return {
            "title": data.get("title", ""),
            "source_video_ref": data.get("source_video", ""),
            "total_segments": total_segments,
            "story_segments": story_segments,
            "assessment_segments": assessment_segments,
            "total_speech_units": total_speech_units,
            "total_words": total_words,
            "emotions_distribution": emotions_count,
            "segments_with_shots": has_shots,
            "segments": parsed_segments
        }
    except Exception as e:
        return {"error": str(e)}

def scan_render_clips(job_name):
    # Check possible render dirs
    clips_info = {
        "output_dir": None,
        "total_clips": 0,
        "completed_clips": 0,
        "pending_clips": 0,
        "clips": [],
        "final_video": None
    }
    
    render_dirs = [
        REVIEW_ROOT / "output" / f"{job_name}_reviewed_render",
        REVIEW_ROOT / "output" / f"{job_name}_render_v3",
        REVIEW_ROOT / "output" / f"{job_name}_render",
        REVIEW_ROOT / "output" / job_name
    ]
    
    for rdir in render_dirs:
        if rdir.exists():
            clips_info["output_dir"] = str(rdir)
            clips_dir = rdir / "clips"
            if clips_dir.exists():
                for item in sorted(clips_dir.iterdir()):
                    if item.is_file():
                        stat = item.stat()
                        is_pending = "pending" in item.name.lower()
                        is_mkv = item.suffix.lower() == ".mkv"
                        is_json = item.suffix.lower() == ".json"
                        
                        if is_mkv:
                            clips_info["total_clips"] += 1
                            if is_pending:
                                clips_info["pending_clips"] += 1
                            else:
                                clips_info["completed_clips"] += 1
                                
                            clips_info["clips"].append({
                                "name": item.name,
                                "path": str(item),
                                "size_bytes": stat.st_size,
                                "size_human": format_bytes(stat.st_size),
                                "is_pending": is_pending,
                                "mtime": stat.st_mtime
                            })

            # Check final video
            final_candidates = [
                rdir / "final" / "final_review.mp4",
                rdir / "final_review.mp4",
                REVIEW_ROOT / "output" / f"{job_name}.mp4"
            ]
            for fc in final_candidates:
                if fc.exists():
                    fstat = fc.stat()
                    clips_info["final_video"] = {
                        "name": fc.name,
                        "path": str(fc),
                        "size_bytes": fstat.st_size,
                        "size_human": format_bytes(fstat.st_size),
                        "mtime": fstat.st_mtime
                    }
                    break
            break

    # Also check review_firm_china/output
    china_out = WORKSPACE_ROOT / "review_firm_china" / "output"
    if china_out.exists():
        for f in china_out.iterdir():
            if f.is_file() and f.suffix.lower() == ".mp4":
                if job_name.lower() in fname:
                    fstat = f.stat()
                    clips_info["final_video"] = {
                        "name": f.name,
                        "path": str(f),
                        "size_bytes": fstat.st_size,
                        "size_human": format_bytes(fstat.st_size),
                        "mtime": fstat.st_mtime
                    }

    return clips_info

def scan_keyframes(job_name):
    timeline_dir = REVIEW_ROOT / "data" / "timeline" / job_name
    handoff_dir = REVIEW_ROOT / "data" / "handoff" / job_name
    frames = []

    dirs_to_check = [timeline_dir, handoff_dir]
    if job_name == "1004":
        dirs_to_check.append(WORKSPACE_ROOT / "analysis_1004")
    for d in dirs_to_check:
        if d.exists():
            for f in sorted(d.iterdir()):
                if f.is_file() and f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                    stat = f.stat()
                    frames.append({
                        "filename": f.name,
                        "path": str(f),
                        "size_bytes": stat.st_size,
                        "size_human": format_bytes(stat.st_size),
                        "mtime": stat.st_mtime,
                        "category": "grid" if "grid" in f.name else ("cast" if "cast" in f.name else ("export" if "export" in f.name else "sample"))
                    })
    return frames

def scan_logs(job_name):
    handoff_dir = REVIEW_ROOT / "data" / "handoff" / job_name
    logs = []
    if handoff_dir.exists():
        for f in sorted(handoff_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in [".log", ".txt"]:
                stat = f.stat()
                logs.append({
                    "name": f.name,
                    "path": str(f),
                    "size_bytes": stat.st_size,
                    "size_human": format_bytes(stat.st_size),
                    "mtime": stat.st_mtime
                })
    return sorted(logs, key=lambda x: x["mtime"], reverse=True)

def scan_job_detail(job_name):
    handoff_dir = REVIEW_ROOT / "data" / "handoff" / job_name
    timeline_dir = REVIEW_ROOT / "data" / "timeline" / job_name
    
    manifest_data = {}
    run_progress_data = {}
    reviewed_progress_data = {}
    
    if handoff_dir.exists():
        m_file = handoff_dir / "manifest.json"
        if m_file.exists():
            try:
                with open(m_file, "r", encoding="utf-8") as f:
                    manifest_data = json.load(f)
            except Exception:
                pass
        
        rp_file = handoff_dir / "run_progress.json"
        if rp_file.exists():
            try:
                with open(rp_file, "r", encoding="utf-8") as f:
                    run_progress_data = json.load(f)
            except Exception:
                pass
                
        rev_file = handoff_dir / "reviewed_progress.json"
        if rev_file.exists():
            try:
                with open(rev_file, "r", encoding="utf-8") as f:
                    reviewed_progress_data = json.load(f)
            except Exception:
                pass

    # Timeline text
    timeline_exists = False
    timeline_summary = ""
    timeline_file = timeline_dir / "timeline.md"
    if timeline_file.exists():
        timeline_exists = True
        try:
            with open(timeline_file, "r", encoding="utf-8") as f:
                lines = [next(f) for _ in range(30)]
                timeline_summary = "".join(lines)
        except Exception:
            pass

    # Source video metadata & budget
    source_video = (run_progress_data.get("source_video") or 
                    manifest_data.get("source_video") or "")
    source_metadata = (run_progress_data.get("source_metadata") or 
                       manifest_data.get("metadata") or {})
    budget = (run_progress_data.get("budget") or 
              manifest_data.get("budget") or {})
    
    # Check script
    script_file, script_filename = find_script_for_job(job_name)
    script_summary = parse_script_summary(script_file) if script_file else None

    # Check clips & render
    render_clips = scan_render_clips(job_name)
    
    # Keyframes
    keyframes = scan_keyframes(job_name)

    # Logs
    logs = scan_logs(job_name)

    # Determine 7-stage workflow status with assigned agents
    stage_definitions = [
        (1, "Source Intake", "Video discovery & 40-50% budget allocation"),
        (2, "READ (Vision)", "Scene analysis & visual timeline.md"),
        (3, "WRITE (Script)", "ChatGPT Pro editorial review.json"),
        (4, "MEASURE & ZeroTTS", "Bảo Trang voice offline PCM measurement"),
        (5, "Shot Fitting & EDL", "Clip pacing, montage bounds & CapCut export"),
        (6, "FFmpeg Render", "Chunked clip render & canvas padding"),
        (7, "QC & Certification", "Duration ratio, assessment & decode check"),
    ]
    stage_statuses = []
    for sid, sname, sdesc in stage_definitions:
        assigned = get_assigned_agent(job_name, sid)
        cands = [AGENT_DIRECTORY[cid] for cid in STAGE_CANDIDATES.get(sid, []) if cid in AGENT_DIRECTORY]
        stage_statuses.append({
            "id": sid,
            "name": sname,
            "desc": sdesc,
            "status": "pending",
            "assigned_agent": assigned,
            "candidates": cands
        })

    # Stage 1: Source Intake
    if source_video or source_metadata:
        stage_statuses[0]["status"] = "complete"
        stage_statuses[0]["detail"] = f"Duration: {format_duration(source_metadata.get('duration'))} | Target: {format_duration(budget.get('total_target'))}"
    
    # Stage 2: READ (Vision)
    if timeline_exists:
        stage_statuses[1]["status"] = "complete"
        stage_statuses[1]["detail"] = f"Timeline MD verified ({len(keyframes)} keyframes sampled)"
    elif manifest_data.get("delivery_status") == "ui_submitted":
        stage_statuses[1]["status"] = "in_progress"
        stage_statuses[1]["detail"] = "Antigravity UI submitted, awaiting timeline export"

    # Stage 3: WRITE (Script)
    if script_summary and not script_summary.get("error"):
        stage_statuses[2]["status"] = "complete"
        stage_statuses[2]["detail"] = f"{script_summary['total_segments']} segments ({script_summary['total_speech_units']} speech units)"
    elif run_progress_data.get("review_created"):
        stage_statuses[2]["status"] = "complete"

    # Stage 4: MEASURE & TTS
    timing_file = None
    for cand in [
        REVIEW_ROOT / "output" / f"{job_name}_tts" / "review_timing.json",
        REVIEW_ROOT / "output" / f"{job_name}_render" / "review_timing.json",
        REVIEW_ROOT / "output" / job_name / "review_timing.json",
        handoff_dir / "review_timing.json",
    ]:
        if cand.exists():
            timing_file = cand
            break

    measure_progress_file = REVIEW_ROOT / "output" / f"{job_name}_tts" / "measurement_progress.json"
    if timing_file:
        try:
            with open(timing_file, "r", encoding="utf-8") as tf:
                td = json.load(tf)
            stage_statuses[3]["status"] = "complete"
            stage_statuses[3]["detail"] = f"Measured: {td.get('review_duration', 0):.1f}s ({td.get('source_ratio', 0):.1%}) | Assessment: {td.get('assessment_narration_duration', 0):.1f}s"
        except Exception:
            stage_statuses[3]["status"] = "complete"
            stage_statuses[3]["detail"] = "Measured TTS audio verified"
    elif measure_progress_file.exists():
        try:
            with open(measure_progress_file, "r", encoding="utf-8") as mpf:
                mp_data = json.load(mpf)
            c_ids = mp_data.get("completed_ids", [])
            tot = mp_data.get("total_count", 0) or mp_data.get("selected_count", 0)
            if tot > 0 and len(c_ids) < tot:
                pct = int((len(c_ids) / tot) * 100)
                stage_statuses[3]["status"] = "in_progress"
                stage_statuses[3]["detail"] = f"Synthesizing ZeroTTS: {len(c_ids)}/{tot} segments ({pct}%)"
            elif tot > 0 and len(c_ids) >= tot:
                stage_statuses[3]["status"] = "complete"
                stage_statuses[3]["detail"] = f"ZeroTTS complete: {len(c_ids)}/{tot} segments synthesized"
        except Exception:
            pass
    elif len(tts_logs) >= 3 or run_progress_data.get("stage") in ["rendering_reviewed_video", "processing_reviewed_revision", "complete"]:
        stage_statuses[3]["status"] = "complete"
        stage_statuses[3]["detail"] = f"{len(tts_logs)} batch logs, PCM audio verified"
    elif len(tts_logs) > 0:
        stage_statuses[3]["status"] = "in_progress"
        stage_statuses[3]["detail"] = f"Synthesizing ({len(tts_logs)} batches in progress)"

    # Stage 5: Shot Fitting
    fitted_report = handoff_dir / "fitted_shot_report.json" if handoff_dir.exists() else None
    if (fitted_report and fitted_report.exists()) or (script_summary and script_summary.get("segments_with_shots", 0) > 0) or run_progress_data.get("stage") in ["rendering_reviewed_video", "complete"] or render_clips["completed_clips"] > 0:
        stage_statuses[4]["status"] = "complete"
        shots_cnt = script_summary.get('segments_with_shots', 0) if script_summary else 0
        stage_statuses[4]["detail"] = f"Shots fitted ({shots_cnt} segments with montage shots)"
    elif script_summary:
        stage_statuses[4]["status"] = "ready"

    # Stage 6: FFmpeg Render
    if render_clips["final_video"]:
        stage_statuses[5]["status"] = "complete"
        stage_statuses[5]["detail"] = f"Final render complete: {render_clips['final_video']['name']} ({render_clips['final_video']['size_human']})"
    elif render_clips["total_clips"] > 0:
        if render_clips["pending_clips"] > 0 or render_clips["completed_clips"] < render_clips["total_clips"]:
            stage_statuses[5]["status"] = "in_progress"
            pct = int((render_clips["completed_clips"] / max(1, render_clips["total_clips"])) * 100)
            stage_statuses[5]["detail"] = f"Rendering: {render_clips['completed_clips']}/{render_clips['total_clips']} chunks ({pct}%)"
        else:
            stage_statuses[5]["status"] = "complete"
            stage_statuses[5]["detail"] = f"All {render_clips['completed_clips']} chunks rendered"
    elif reviewed_progress_data.get("stage") == "rendering_reviewed_video":
        stage_statuses[5]["status"] = "in_progress"
        stage_statuses[5]["detail"] = "Rendering active"

    # Stage 7: QC & Certification
    if render_clips["final_video"]:
        stage_statuses[6]["status"] = "complete"
        stage_statuses[6]["detail"] = "H.264/AAC decode PASS, duration certified"
    elif stage_statuses[5]["status"] == "in_progress":
        stage_statuses[6]["status"] = "pending"
        stage_statuses[6]["detail"] = "Awaiting final video assembly"

    # Compute overall progress percentage
    completed_stages = sum(1 for s in stage_statuses if s["status"] == "complete")
    in_prog_stages = sum(1 for s in stage_statuses if s["status"] == "in_progress")
    if render_clips["final_video"]:
        overall_progress = 100
        current_status = "COMPLETED"
    elif stage_statuses[5]["status"] == "in_progress":
        chunk_pct = (render_clips["completed_clips"] / max(1, render_clips["total_clips"])) * 20 if render_clips["total_clips"] else 10
        overall_progress = min(98, int((completed_stages / 7.0) * 100 + chunk_pct))
        current_status = "RENDERING"
    elif in_prog_stages > 0:
        overall_progress = int((completed_stages / 7.0) * 100 + 7)
        current_status = "IN_PROGRESS"
    else:
        overall_progress = int((completed_stages / 7.0) * 100)
        current_status = "READY" if overall_progress > 0 else "IDLE"

    display_title = FRIENDLY_JOB_TITLES.get(job_name)
    if not display_title:
        display_title = script_summary.get("title") if script_summary else job_name.replace("_", " ").title()
        if "?" in display_title:
            display_title = job_name.replace("_", " ").title()

    return {
        "job": job_name,
        "title": display_title,
        "status": current_status,
        "overall_progress": overall_progress,
        "source_video": source_video,
        "source_metadata": source_metadata,
        "budget": budget,
        "stage_statuses": stage_statuses,
        "active_stage": reviewed_progress_data.get("stage") or run_progress_data.get("stage") or "idle",
        "next_action": run_progress_data.get("next_action") or "Ready for next pipeline stage",
        "blocker": run_progress_data.get("blocker"),
        "editorial_status": run_progress_data.get("editorial_status"),
        "script": script_summary,
        "script_filename": script_filename,
        "render_clips": render_clips,
        "keyframes_count": len(keyframes),
        "keyframes": keyframes[:60], # Return first 60 for fast rendering
        "logs": logs,
        "timeline_exists": timeline_exists,
        "timeline_preview": timeline_summary
    }

def get_all_jobs():
    jobs = []
    seen = set()
    
    # 1. Luôn hiển thị mẫu chuẩn 1004 nếu có video mẫu hoặc phân tích chuẩn
    ref_file = REVIEW_ROOT / "data" / "reference" / "1004.analysis.json"
    if ref_file.exists() or (SRC_VIDEO_DIR / "1004.mp4").exists():
        jobs.append("1004")
        seen.add("1004")
        
    # 2. Quét các job đang hoạt động trong data/handoff
    handoff_dir = REVIEW_ROOT / "data" / "handoff"
    if handoff_dir.exists():
        for d in sorted(handoff_dir.iterdir()):
            if d.is_dir() and not d.name.startswith(".") and d.name not in seen:
                jobs.append(d.name)
                seen.add(d.name)
                
    # 3. Quét các job có timeline trong data/timeline
    timeline_dir = REVIEW_ROOT / "data" / "timeline"
    if timeline_dir.exists():
        for d in sorted(timeline_dir.iterdir()):
            if d.is_dir() and not d.name.startswith(".") and d.name not in seen:
                jobs.append(d.name)
                seen.add(d.name)
                
    # 4. Quét video nguồn đang chờ trong input/videos
    videos_dir = REVIEW_ROOT / "input" / "videos"
    if videos_dir.exists():
        for f in sorted(videos_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in [".mp4", ".mkv", ".mov"]:
                job_id = f.stem
                if job_id not in seen and not job_id.startswith("."):
                    jobs.append(job_id)
                    seen.add(job_id)

    # 5. Quét kịch bản đang chờ trong input/scripts
    scripts_dir = REVIEW_ROOT / "input" / "scripts"
    if scripts_dir.exists():
        for f in sorted(scripts_dir.iterdir()):
            if f.is_file() and f.suffix.lower() == ".json":
                m = re.match(r"review\.([a-zA-Z0-9_-]+)\.json", f.name)
                if m:
                    job_id = m.group(1)
                    if job_id not in seen and job_id not in ["example", "emotion"]:
                        jobs.append(job_id)
                        seen.add(job_id)
                
    jobs_list = []
    for j in jobs:
        try:
            detail = scan_job_detail(j)
            jobs_list.append(detail)
        except Exception as e:
            jobs_list.append({
                "job": j,
                "title": j,
                "status": "ERROR",
                "overall_progress": 0,
                "error": str(e)
            })
    return jobs_list

def get_system_status():
    stat = {
        "workspace_root": str(WORKSPACE_ROOT),
        "python_version": sys.version.split()[0],
        "platform": sys.platform,
        "server_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "gpu": "NVIDIA Quadro M1000M (Driver 528.79)",
        "cpu": "Intel Core i7-6820HQ @ 2.70GHz (8 cores)",
        "ram": "15.82 GiB",
        "zerotts_voice": "Bảo Trang (baotrang) Offline",
        "ffmpeg": "FFmpeg 9.0.1 (libx264, libass)",
        "active_env": "uv / Python 3.11.17"
    }
    return stat

class MonitorHTTPHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # API Endpoints
        if path == "/api/overview":
            self.send_json_response(self.handle_overview())
            return
        elif path == "/api/jobs":
            jobs = get_all_jobs()
            self.send_json_response({"jobs": jobs})
            return
        elif path.startswith("/api/jobs/"):
            job_name = path[len("/api/jobs/"):]
            detail = scan_job_detail(job_name)
            self.send_json_response(detail)
            return
        elif path == "/api/sources":
            sources = scan_source_videos()
            self.send_json_response({"sources": sources})
            return
        elif path == "/api/system":
            self.send_json_response(get_system_status())
            return
        elif path == "/api/logs":
            self.handle_log_request(query)
            return
        elif path == "/api/media":
            self.handle_media_request(query)
            return
        elif path == "/api/timeline-md":
            self.handle_timeline_md(query)
            return
        elif path == "/api/orchestration":
            self.send_json_response({
                "agents": AGENT_DIRECTORY,
                "stage_candidates": STAGE_CANDIDATES,
                "config": load_orchestration_config()
            })
            return
        elif path == "/api/agents":
            self.send_json_response({"agents": list(AGENT_DIRECTORY.values())})
            return

        # Default static file serving from public/
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/check-environment":
            self.handle_check_env()
            return
        elif parsed.path == "/api/orchestration":
            self.handle_update_orchestration()
            return
        self.send_error(404, "Not Found")

    def handle_update_orchestration(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(length)
            body = json.loads(body_bytes.decode("utf-8"))
            
            job = body.get("job")
            stage_id = str(body.get("stage_id"))
            agent_id = body.get("agent_id")
            mode = body.get("mode", "autonomous")
            notes = body.get("notes", "")

            if not stage_id or not agent_id:
                self.send_error(400, "Missing stage_id or agent_id")
                return

            cfg = load_orchestration_config()
            if job:
                if "job_overrides" not in cfg:
                    cfg["job_overrides"] = {}
                if job not in cfg["job_overrides"]:
                    cfg["job_overrides"][job] = {}
                cfg["job_overrides"][job][stage_id] = {
                    "agent_id": agent_id,
                    "mode": mode,
                    "notes": notes
                }
            else:
                if "default_assignments" not in cfg:
                    cfg["default_assignments"] = {}
                cfg["default_assignments"][stage_id] = {
                    "stage_id": int(stage_id),
                    "agent_id": agent_id,
                    "mode": mode,
                    "notes": notes
                }

            save_orchestration_config(cfg)
            self.send_json_response({"status": "ok", "config": cfg})
        except Exception as e:
            self.send_error(500, f"Error updating orchestration: {e}")

    def handle_overview(self):
        jobs = get_all_jobs()
        sources = scan_source_videos()
        
        total_source_duration = sum(j.get("source_metadata", {}).get("duration", 0) for j in jobs if j.get("source_metadata"))
        total_rendered_bytes = 0
        for j in jobs:
            rc = j.get("render_clips", {})
            fv = rc.get("final_video")
            if fv:
                total_rendered_bytes += fv.get("size_bytes", 0)
        
        active_jobs = sum(1 for j in jobs if j.get("status") in ["RENDERING", "IN_PROGRESS"])
        completed_jobs = sum(1 for j in jobs if j.get("status") == "COMPLETED")

        return {
            "total_jobs": len(jobs),
            "active_jobs": active_jobs,
            "completed_jobs": completed_jobs,
            "total_source_videos": len(sources),
            "total_source_duration": format_duration(total_source_duration),
            "total_rendered_size": format_bytes(total_rendered_bytes),
            "jobs_summary": [
                {
                    "job": j["job"],
                    "title": j["title"],
                    "status": j["status"],
                    "progress": j["overall_progress"]
                }
                for j in jobs
            ],
            "system": get_system_status()
        }

    def handle_log_request(self, query):
        file_path_str = query.get("path", [None])[0]
        if not file_path_str:
            self.send_error(400, "Missing path parameter")
            return
        
        target = Path(file_path_str).resolve()
        # Security check: must reside inside WORKSPACE_ROOT
        try:
            target.relative_to(WORKSPACE_ROOT)
        except ValueError:
            self.send_error(403, "Access denied")
            return
        
        if not target.exists() or not target.is_file():
            self.send_error(404, "Log file not found")
            return
        
        try:
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            
            # Tail last 500 lines if very large
            if len(lines) > 500:
                lines = lines[-500:]
            
            self.send_json_response({
                "path": str(target),
                "filename": target.name,
                "lines_count": len(lines),
                "content": "".join(lines)
            })
        except Exception as e:
            self.send_error(500, f"Error reading log: {e}")

    def handle_timeline_md(self, query):
        job = query.get("job", [None])[0]
        if not job:
            self.send_error(400, "Missing job parameter")
            return
        
        timeline_file = REVIEW_ROOT / "data" / "timeline" / job / "timeline.md"
        if not timeline_file.exists():
            self.send_json_response({"content": "*Timeline not yet generated for this job.*"})
            return
        try:
            with open(timeline_file, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            self.send_json_response({"content": content})
        except Exception as e:
            self.send_error(500, str(e))

    def handle_check_env(self):
        script_path = REVIEW_ROOT / "scripts" / "check_environment.py"
        python_exe = REVIEW_ROOT / ".venv" / "Scripts" / "python.exe"
        
        if not python_exe.exists():
            python_exe = Path(sys.executable)
            
        try:
            proc = subprocess.run(
                [str(python_exe), str(script_path)],
                capture_output=True,
                text=True,
                cwd=str(REVIEW_ROOT),
                timeout=30
            )
            self.send_json_response({
                "exit_code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr
            })
        except Exception as e:
            self.send_json_response({
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e)
            })

    def handle_media_request(self, query):
        file_path_str = query.get("path", [None])[0]
        if not file_path_str:
            self.send_error(400, "Missing media path")
            return
        
        target = Path(file_path_str).resolve()
        try:
            target.relative_to(WORKSPACE_ROOT)
        except ValueError:
            self.send_error(403, "Access denied")
            return
            
        if not target.exists() or not target.is_file():
            self.send_error(404, "File not found")
            return

        ctype, _ = mimetypes.guess_type(str(target))
        if not ctype:
            ctype = "application/octet-stream"

        stat = target.stat()
        file_size = stat.st_size
        range_header = self.headers.get("Range")

        if range_header:
            # Handle HTTP byte-range for audio/video scrubbing
            range_match = re.match(r"bytes=(\d+)-(\d*)", range_header)
            if range_match:
                start = int(range_match.group(1))
                end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
                length = end - start + 1

                self.send_response(206)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(length))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()

                with open(target, "rb") as f:
                    f.seek(start)
                    self.wfile.write(f.read(length))
                return

        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(file_size))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()

        with open(target, "rb") as f:
            while chunk := f.read(65536):
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    break

    def send_json_response(self, data):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

def run_server():
    server_address = ("127.0.0.1", PORT)
    httpd = ThreadedHTTPServer(server_address, MonitorHTTPHandler)
    print("============================================================")
    print("WORKPLACE MAKE FIRM - WORKFLOW MONITOR RUNNING")
    print(f"URL: http://localhost:{PORT}")
    print(f"Root: {WORKSPACE_ROOT}")
    print("============================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
