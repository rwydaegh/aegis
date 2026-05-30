# Enabling 6G Technologies - webinar bundle

Transcript and reconstructed slide deck for the Ansys webinar **"Enabling 6G
Technologies: Physics to drive the AI revolution in 6G radio and antennas"**,
presented by Shawn Carpenter (Program Director, Ansys), 26 June 2024.

Derived from `../Enabling 6G Technologies.mp4` (01:00:06, 640x360).

## Contents

| File | What it is |
| --- | --- |
| `transcript.md` | Full speech transcript with `[HH:MM:SS]` timestamps and each slide image woven in where it appears. |
| `slides.pdf` | The 53 reconstructed slides, one per page. |
| `slides/` | The 53 slide PNGs (`slide_NN_HH-MM-SS.png`; the timestamp is when the slide was fully shown). |
| `slides.json` | Manifest: per-slide on-screen start time and settled-frame time. |
| `scripts/` | The pipeline that produced everything (see below). |

## How it was made

1. **`scripts/transcribe_audio.py`** - extracts 16 kHz mono audio with ffmpeg and
   transcribes it with faster-whisper `large-v3` (float16, GPU). A 6G/EM-simulation
   prompt biases the decoder toward the talk's jargon (HFSS, MIMO, ray tracing,
   terahertz). Runs ~15x realtime on an RTX 4090.
2. **`scripts/extract_slides.py`** - the video is a full-frame slide capture, so
   slides are recovered from per-second frame differences. PowerPoint build-up
   steps and live-demo runs are collapsed by comparing the title band at the top of
   the frame (same title => same slide, keep the most complete frame); near-black
   fade frames are dropped. 77 raw change points -> 53 distinct slides.
3. **`scripts/annotate_transcript.py`** - weaves each slide image into the
   transcript at the second the slide first appears on screen.

Re-run: `transcribe_audio.py` then `extract_slides.py` then `annotate_transcript.py`.
Needs ffmpeg, an NVIDIA GPU, and `pip install faster-whisper pillow numpy img2pdf`.

## Notes

- Speech is accurate; the deck is low resolution (640x360, the recording's native
  size) and a few live-demo stretches are represented by a handful of frames rather
  than true slides.
