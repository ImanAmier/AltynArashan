# Altyn Arashan vlog edit

Scripted edit (ffmpeg + Python) of the Altyn Arashan trip footage. The footage, photos and song are not stored in this repo.

- `edl.py`: the edit decision list (shot order, in-points, beat lengths, speed, titles, captions, ambient breaks). Current cut: video only, no lake or car footage, no location labels
- `edl_v1_with_photos.py`: the first preview cut (with photos, lake and car footage), kept for reference
- `build.py`: lays shots on the song's beat grid, mixes the audio (ducking under speech, ambient breaks), burns in titles and captions, and composites transitions
- `engine.py`: per-shot rendering (grade LUT, stabilization, slow motion, photo Ken Burns)
- `music.py`: extends the song by repeating its hook and first verse, joined on a matching bar
- `mklut.py`: builds the `day.cube` / `golden.cube` colour grades
- `beats.py`: beat detection for the song

Preview: `NO_EXTEND=1 python3 build.py 1280 preview.mp4`. Final 1080p: `NO_EXTEND=1 python3 build.py 1920 final_1080p.mp4`.
`NO_EXTEND=1` uses the song at its original length (the current cut is about 3:14); without it the hook and first verse repeat to make the song longer.
Set `FOOTAGE_DIR` and `WORK_DIR` (the work dir needs `song.mp3`, `audio/`, the LUTs and `beats.json`).
Fonts: Inter and Cormorant Garamond.
