#!/usr/bin/env python3
"""Transcribe the webinar audio to a timestamped markdown transcript.

Extracts 16 kHz mono audio with ffmpeg, then runs faster-whisper large-v3 on the
GPU. Writes plain segment lines (``**[HH:MM:SS]** text``) to transcript.md; run
annotate_transcript.py afterwards to weave in the slide images.

Deps: ffmpeg on PATH, faster-whisper (CTranslate2 CUDA build), an NVIDIA GPU.
"""
import subprocess
import tempfile

from faster_whisper import WhisperModel

VIDEO = "/home/user/aegis/spinoff/Enabling 6G Technologies.mp4"
OUT_MD = "/home/user/aegis/spinoff/6g_webinar/transcript.md"

# domain prompt to bias the decoder toward this Ansys 6G webinar's vocabulary
PROMPT = (
    "This is a technical Ansys webinar on enabling 6G technologies and the physics "
    "driving AI into 6G radio and antenna systems. Topics include electromagnetic "
    "simulation, Ansys HFSS, finite element method, FDTD, antenna arrays, phased "
    "arrays, beamforming, massive MIMO, millimeter wave, sub-terahertz and terahertz "
    "bands, reconfigurable intelligent surfaces (RIS), channel modeling, ray tracing, "
    "EIRP, OTA testing, and the wireless link budget for 6G networks."
)


def hms(t):
    t = int(round(t))
    return f"{t//3600:02d}:{(t%3600)//60:02d}:{t%60:02d}"


def main():
    with tempfile.NamedTemporaryFile(suffix=".wav") as wav:
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", VIDEO,
             "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", wav.name, "-y"],
            check=True)
        model = WhisperModel("large-v3", device="cuda", compute_type="float16")
        segments, _ = model.transcribe(
            wav.name, language="en", beam_size=5, vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            initial_prompt=PROMPT, condition_on_previous_text=True)

        with open(OUT_MD, "w", encoding="utf-8") as f:
            f.write("# Enabling 6G Technologies - transcript\n\n")
            for seg in segments:
                f.write(f"**[{hms(seg.start)}]** {seg.text.strip()}\n\n")
    print(f"wrote {OUT_MD}")


if __name__ == "__main__":
    main()
