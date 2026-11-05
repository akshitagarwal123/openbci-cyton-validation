# Cyton + Daisy, from battery to brain waves (course video)

A 28.6-minute narrated course for beginners, in 10 chapters, filmed on the Cyton + Daisy 3D explorer
(`../cyton_3d/`) with close-ups of the OpenBCI schematics. Narration: ElevenLabs "Sarah".

- `Cyton_Daisy_course_full.mp4` (local only: 163 MB, over GitHub's 100 MB file limit, so it is git-ignored) + `Cyton_Daisy_course_full.srt`
- `chapters/`: the 10 chapters as separate MP4s, each with its own `.srt` subtitles

| # | Chapter |
|---|---|
| 1 | What the Cyton + Daisy does |
| 2 | A tour of the board (incl. reading a schematic, copper layers) |
| 3 | Power: from battery to ±2.5 V |
| 4 | The brain signal (protection, PGA, ADC, reference, input mux, lead-off, decoupling) |
| 5 | The bias loop |
| 6 | The microcontroller (crystal, SPI, DRDY, buttons, bootloader) |
| 7 | Radio and packets |
| 8 | Extras: motion and SD card |
| 9 | The Daisy: 8 more channels (bus, power sockets, sync) |
| 10 | Putting it together (and what changes for BrainTech-8) |

`src/`: script and shot list (`course_spec.py`), renderer (`course.js`, `render_course.py`), compositor (`compose_course.py`), narration (`gen_audio.py`, needs an ElevenLabs key in `~/.config/elevenlabs/key`).
