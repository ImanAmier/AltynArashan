# Altyn Arashan vlog edit

Scripted edit (ffmpeg + Python) of the Altyn Arashan trip footage. The footage, photos and song are not stored in this repo.

- `edl.py`: the edit decision list (shot order, in-points, beat lengths, speed, titles, captions, ambient breaks)
- `build.py`: lays shots on the song's beat grid, mixes the audio (ducking under speech, ambient breaks), burns in titles and captions, and composites transitions
- `engine.py`: per-shot rendering (grade LUT, stabilization, slow motion, photo Ken Burns)
- `music.py`: extends the song by repeating its hook and first verse, joined on a matching bar
- `mklut.py`: builds the `day.cube` / `golden.cube` colour grades
- `beats.py`: beat detection for the song

Preview: `python3 build.py 1280 preview.mp4`. Final 1080p: `python3 build.py 1920 final_1080p.mp4`.
Set `FOOTAGE_DIR` and `WORK_DIR` (the work dir needs `song.mp3`, `audio/`, the LUTs and `beats.json`).
Fonts: Inter and Cormorant Garamond.
