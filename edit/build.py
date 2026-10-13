import json, sys, os, subprocess, math, numpy as np, soundfile as sf, cv2
sys.path.insert(0, '/home/user/work')
import engine
from edl import EDL
from music import extended, ext_beats, SR

W = int(sys.argv[1]) if len(sys.argv) > 1 else 1280
H = W * 9 // 16
OUT = sys.argv[2] if len(sys.argv) > 2 else f'/home/user/work/preview_{W}.mp4'
FPS = engine.FPS
WORK = '/home/user/work'
SRC = engine.SRC

# ---------------------------------------------------------------- timeline
if os.environ.get('NO_EXTEND'):
    from music import load_song
    music = load_song(); beats = json.load(open(f'{WORK}/beats.json'))['beats']
else:
    beats = ext_beats()
    music = extended()
MUSIC_LEN = len(music) / SR
grid = [0.0] + beats[1:]          # treat t=0 as beat 0 so the teaser starts immediately

def next_beat_idx(t, tol=0.08):
    for i, b in enumerate(grid):
        if b >= t - tol: return i
    return len(grid) - 1

def clip_len(src):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f'{SRC}/{src}.MOV'], capture_output=True, text=True)
    return float(r.stdout.strip())

shots = []
t = 0.0; bi = 0
for s in EDL:
    s = dict(s)
    if s.get('b', 0) == 999:
        end = max(MUSIC_LEN - 0.4, t + 7.0)
    elif 'b' in s:
        bi2 = bi + s['b']; end = grid[min(bi2, len(grid) - 1)]
    else:
        end = t + s['d']
        if not s.get('exact'):
            end = grid[next_beat_idx(end)]
    s['t0'] = t; s['t1'] = end; s['dur'] = end - t
    bi = next_beat_idx(end, tol=0.12)
    t = end
    shots.append(s)
TOTAL = t
print(f'timeline length {TOTAL:.2f}s, music {MUSIC_LEN:.2f}s, shots {len(shots)}')

# transition handles: incoming shot starts tr/2 earlier, outgoing ends tr/2 later
for i, s in enumerate(shots):
    s['head'] = 0.0; s['tail'] = 0.0
for i, s in enumerate(shots):
    tr = s.get('tr')
    if tr and tr[0] in ('fade', 'whip') and i > 0:
        h = tr[1] / 2
        s['head'] = h; shots[i - 1]['tail'] = h
for s in shots:
    if s['type'] == 'video':
        sp = s.get('speed', 1.0)
        L = clip_len(s['src'])
        need = (s['dur'] + s['head'] + s['tail'] - (s.get('freeze_end') or 0)) * sp
        s['rin'] = s['in'] - s['head'] * sp
        if s['rin'] < 0: s['rin'] = 0.0
        if s['rin'] + need > L - 0.05:
            print(f"  ! {s['src']} in={s['in']} needs {need:.2f}s, clip {L:.2f}s -> pulling in-point back")
            s['rin'] = max(0.0, L - 0.05 - need)

# ---------------------------------------------------------------- render shots
def spec(s):
    keys = ['type', 'src', 'speed', 'stab', 'zoom', 'zx', 'zy', 'lut', 'bright', 'kb', 'ypos', 'xpos', 'sat', 'gamma', 'smooth']
    d = {k: s[k] for k in keys if k in s}
    if s['type'] == 'video':
        d['in'] = round(s['rin'], 3)
        fe = s.get('freeze_end') or 0
        d['dur'] = round(s['dur'] + s['head'] + s['tail'] - fe, 4)
        if fe: d['freeze_end'] = fe
    else:
        d['dur'] = round(s['dur'] + s['head'] + s['tail'], 4)
    return d

from concurrent.futures import ThreadPoolExecutor
def do(i):
    s = shots[i]
    f = engine.render_shot(spec(s), W, H)
    return i, f
with ThreadPoolExecutor(max_workers=3) as ex:
    for i, f in ex.map(do, range(len(shots))):
        shots[i]['file'] = f
print('shots rendered')
json.dump([s['file'] for s in shots], open(f'{WORK}/shotfiles.json','w'))
json.dump([{k: v for k, v in s.items() if k not in ('file',)} for s in shots], open(f'{WORK}/timeline.json', 'w'), indent=1, default=str)
if os.environ.get('SHOTS_ONLY'): sys.exit(0)

# ---------------------------------------------------------------- compositor
class Reader:
    def __init__(self, path):
        self.p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', path, '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-'], stdout=subprocess.PIPE)
        self.last = None
    def read(self):
        b = self.p.stdout.read(W * H * 3)
        if len(b) == W * H * 3:
            self.last = np.frombuffer(b, np.uint8).reshape(H, W, 3)
        return self.last if self.last is not None else np.zeros((H, W, 3), np.uint8)
    def close(self):
        try: self.p.stdout.close(); self.p.kill()
        except Exception: pass

NF = int(round(TOTAL * FPS))
ass_path = f'{WORK}/subs.ass'
audio_path = f'{WORK}/mix.wav'
enc = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', f'{engine.FPS_NUM}/{engine.FPS_DEN}', '-i', '-',
       '-i', audio_path, '-vf', f"ass={ass_path}:fontsdir=/root/.fonts",
       '-c:v', 'libx264', '-preset', 'medium' if W < 1920 else 'slow', '-crf', '20' if W < 1920 else '16', '-pix_fmt', 'yuv420p',
       '-c:a', 'aac', '-b:a', '256k', '-movflags', '+faststart', '-shortest', OUT]

def build_audio():
    n = int(TOTAL * SR) + SR
    mus = np.zeros((n, 2), np.float32)
    m = music[:n]
    mus[:len(m)] = m
    gain = np.ones(n, np.float32)
    voice = np.zeros((n, 2), np.float32)
    amb = np.zeros((n, 2), np.float32)
    cache = {}
    def clip_audio(src):
        if src not in cache:
            p = f'{WORK}/audio48/{src}.wav'
            if not os.path.exists(p):
                os.makedirs(f'{WORK}/audio48', exist_ok=True)
                subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f'{SRC}/{src}.MOV', '-vn', '-ac', '2', '-ar', str(SR), p], check=True)
            cache[src] = sf.read(p, dtype='float32')[0]
        return cache[src]
    def hp(x, fc):
        # simple 2nd-order highpass via scipy
        from scipy.signal import butter, sosfilt
        sos = butter(2, fc, 'hp', fs=SR, output='sos'); return sosfilt(sos, x, axis=0).astype(np.float32)
    def fades(x, fi, fo):
        a = int(fi * SR); b = int(fo * SR)
        if a: x[:a] *= np.linspace(0, 1, a)[:, None]
        if b: x[-b:] *= np.linspace(1, 0, b)[:, None]
        return x
    def env_dip(t0, t1, level, att, rel):
        i0 = int((t0 - att) * SR); i1 = int(t0 * SR); i2 = int(t1 * SR); i3 = int((t1 + rel) * SR)
        i0 = max(0, i0); i3 = min(n, i3)
        e = np.ones(n, np.float32)
        if i1 > i0: e[i0:i1] = np.linspace(1, level, i1 - i0)
        e[max(i1, 0):i2] = level
        if i3 > i2: e[i2:i3] = np.linspace(level, 1, i3 - i2)
        return e
    voice_spans = []
    for s in shots:
        for (src, a, b, lines) in s.get('voice', []):
            pos = s['t0'] + s.get('vat', 0.0) + (a - s['voice'][0][1] if len(s['voice']) > 1 else 0)
            x = clip_audio(src)[int(a * SR):int(b * SR)].copy()
            x = hp(x, 90)
            rms = np.sqrt(np.mean(x ** 2)) + 1e-9
            x *= min(10 ** (-15.5 / 20) / rms, 10.0)
            x = fades(x, 0.04, 0.06)
            i = int(pos * SR); voice[i:i + len(x)] += x[:max(0, n - i)]
            voice_spans.append((pos, pos + (b - a), lines))
        if s.get('amb'):
            src, a, g, filt = s['amb']
            t0 = s['t0'] - 0.6; t1 = s['t1'] + 0.9
            L = t1 - t0
            x = clip_audio(src)[int(a * SR):int((a + L) * SR)].copy()
            if filt == 'hp': x = hp(x, 160)
            rms = np.sqrt(np.mean(x ** 2)) + 1e-9
            x *= 10 ** ((-15 + g) / 20) / rms
            x = fades(x, 0.8, 1.2)
            i = int(t0 * SR); amb[i:i + len(x)] += x[:max(0, n - i)]
            gain = np.minimum(gain, env_dip(s['t0'] + 0.2, s['t1'] - 0.5, 0.0, 1.2, 1.4))
    # merge voice spans that are close so the music doesn't pump between lines
    spans = sorted([(a, b) for a, b, _ in voice_spans])
    merged = []
    for a, b in spans:
        if merged and a - merged[-1][1] < 1.2: merged[-1][1] = max(merged[-1][1], b)
        else: merged.append([a, b])
    for a, b in merged:
        gain = np.minimum(gain, env_dip(a, b, 0.2, 0.35, 0.7))
    # smooth the gain curve (no sudden jumps)
    k = int(0.05 * SR); ker = np.ones(k, np.float32) / k
    gain = np.convolve(gain, ker, mode='same')
    # music level and final fade-out
    mus *= 0.72
    fo = int(4.0 * SR); end = int(TOTAL * SR)
    gain[end - fo:end] *= np.linspace(1, 0, fo); gain[end:] = 0
    mix = mus * gain[:, None] + voice + amb
    mix = mix[:end]
    pk = np.max(np.abs(mix)) + 1e-9
    if pk > 0.95: mix *= 0.95 / pk
    sf.write(audio_path, mix, SR)
    return voice_spans

def ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f'{h}:{m:02d}:{s:05.2f}'

def build_ass(voice_spans):
    hdr = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Inter SemiBold,54,&H00FFFFFF,&H00FFFFFF,&H64000000,&H78000000,0,0,0,0,100,100,0.5,0,1,2.2,1.5,2,200,200,72,1
Style: Main,Cormorant Garamond,140,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,100,100,3,0,1,0,3,5,80,80,0,1
Style: Sub,Inter Medium,32,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,100,100,12,0,1,0,2,5,80,80,0,1
Style: Chapter,Cormorant Garamond,96,&H00FFFFFF,&H00FFFFFF,&H00000000,&H8C000000,0,1,0,0,100,100,1.5,0,1,0,3,1,140,80,150,1
Style: ChapNum,Inter Medium,28,&H00FFFFFF,&H00FFFFFF,&H00000000,&H8C000000,0,0,0,0,100,100,10,0,1,0,2,1,146,80,262,1
Style: Loc,Inter Medium,32,&H00FFFFFF,&H00FFFFFF,&H00000000,&H8C000000,0,0,0,0,100,100,10,0,1,0,2,1,140,80,140,1
Style: Moment,Cormorant Garamond,96,&H00FFFFFF,&H00FFFFFF,&H00000000,&H8C000000,0,1,0,0,100,100,1.5,0,1,0,3,8,80,80,120,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    chap = 0
    for s in shots:
        if not s.get('title'): continue
        text, style = s['title']
        a = s['t0'] + 0.25; b = s['t1'] - 0.15
        if style == 'main':
            b = s['t1'] - 0.3
            ev.append(f"Dialogue: 2,{ts(a)},{ts(b)},Main,,0,0,0,,{{\\fad(900,700)\\move(960,560,960,520,0,1400)\\blur0.6}}{text}")
            ev.append(f"Dialogue: 2,{ts(a+0.6)},{ts(b)},Sub,,0,0,0,,{{\\fad(900,700)\\move(960,650,960,625,0,1400)}}A TRAVEL DIARY")
        elif style == 'chapter':
            chap += 1
            b = min(b, a + 3.6)
            ev.append(f"Dialogue: 2,{ts(a)},{ts(b)},ChapNum,,0,0,0,,{{\\fad(600,500)\\move(116,818,146,818,0,700)}}{chap:02d}  ———")
            ev.append(f"Dialogue: 2,{ts(a+0.15)},{ts(b)},Chapter,,0,0,0,,{{\\fad(700,500)\\move(110,930,140,930,0,800)\\blur0.4}}{text}")
        elif style == 'location':
            b = min(b, a + 3.2)
            ev.append(f"Dialogue: 2,{ts(a)},{ts(b)},Loc,,0,0,0,,{{\\fad(600,500)\\move(110,940,140,940,0,700)}}———  {text.upper()}")
        elif style == 'moment':
            ev.append(f"Dialogue: 2,{ts(a)},{ts(b)},Moment,,0,0,0,,{{\\fad(500,400)\\blur0.4}}{text}")
        elif style == 'end':
            a = s['t0'] + 1.6; b = TOTAL - 0.4
            ev.append(f"Dialogue: 2,{ts(a)},{ts(b)},Main,,0,0,0,,{{\\fad(1400,1600)\\move(960,480,960,455,0,2500)\\blur0.6}}{text}")
            ev.append(f"Dialogue: 2,{ts(a+0.8)},{ts(b)},Sub,,0,0,0,,{{\\fad(1400,1600)\\pos(960,560)}}KYRGYZSTAN")
    glow = []
    for e in ev:
        if e.startswith('Dialogue: 2,'):
            parts = e.split(',,0,0,0,,', 1)
            head = parts[0].replace('Dialogue: 2,', 'Dialogue: 1,')
            body = parts[1].replace('{', '{\\c&H000000&\\1a&H60&\\blur16\\bord0\\shad0', 1)
            glow.append(head + ',,0,0,0,,' + body)
    ev = glow + ev
    caps = []
    for (a, b, lines) in voice_spans:
        tot = sum(len(l) for l in lines)
        cur = a
        for l in lines:
            d = (b - a) * len(l) / tot
            caps.append([cur, cur + d + 0.15, l])
            cur += d
    caps.sort()
    for i, c in enumerate(caps):
        if i + 1 < len(caps): c[1] = min(c[1], caps[i + 1][0] - 0.03)
        ev.append(f"Dialogue: 1,{ts(c[0])},{ts(c[1])},Cap,,0,0,0,,{{\\fad(80,80)}}{c[2]}")
    open(ass_path, 'w').write(hdr + "\n".join(ev) + "\n")

voice_spans = build_audio()
build_ass(voice_spans)
print('audio + subs built')

# per-shot frame ranges (with handles)
for s in shots:
    s['f0'] = int(round(s['t0'] * FPS)); s['f1'] = int(round(s['t1'] * FPS))
    s['h0'] = int(round(s['head'] * FPS)); s['t1f'] = int(round(s['tail'] * FPS))

p = subprocess.Popen(enc, stdin=subprocess.PIPE)
readers = {}
white = np.full((H, W, 3), 255, np.float32)
def frame_of(i, f):
    s = shots[i]
    if i not in readers:
        readers[i] = Reader(s['file'])
        # skip to the right frame (first request is at f0 - h0)
        readers[i].pos = s['f0'] - s['h0']
    r = readers[i]
    fr = None
    while r.pos <= f:
        fr = r.read(); r.pos += 1
    return (fr if fr is not None else r.last).astype(np.float32)

si = 0
for f in range(NF):
    while si < len(shots) - 1 and f >= shots[si]['f1']:
        si += 1
        for k in [k for k in readers if k < si - 1]: readers.pop(k).close()
    s = shots[si]
    img = frame_of(si, f)
    # incoming transition into this shot (overlap with previous)
    tr = s.get('tr')
    if tr and si > 0 and tr[0] in ('fade', 'whip'):
        h = s['h0']
        if f < s['f0'] + h:
            prev = frame_of(si - 1, f)
            a = (f - (s['f0'] - h) + 0.5) / (2 * h)
            if tr[0] == 'fade':
                img = prev * (1 - a) + img * a
            else:
                e = a * a * (3 - 2 * a)
                sh = int(e * W)
                out = np.zeros_like(img)
                out[:, :W - sh] = prev[:, sh:]; out[:, W - sh:] = img[:, :sh]
                k = int(9 + 70 * math.sin(math.pi * a))
                img = cv2.blur(out, (k | 1, 1))
    # outgoing tail into next shot's fade is handled by the next shot
    if si < len(shots) - 1:
        nx = shots[si + 1]; ntr = nx.get('tr')
        if ntr and ntr[0] in ('fade', 'whip') and f >= nx['f0'] - nx['h0']:
            nxt = frame_of(si + 1, f)
            h = nx['h0']; a = (f - (nx['f0'] - h) + 0.5) / (2 * h)
            if ntr[0] == 'fade':
                img = img * (1 - a) + nxt * a
            else:
                e = a * a * (3 - 2 * a); sh = int(e * W)
                out = np.zeros_like(img)
                out[:, :W - sh] = img[:, sh:]; out[:, W - sh:] = nxt[:, :sh]
                k = int(9 + 70 * math.sin(math.pi * a))
                img = cv2.blur(out, (k | 1, 1))
    if tr and tr[0] == 'flash':
        k = f - s['f0']; L = max(1, int(tr[1] * FPS))
        if 0 <= k < L:
            a = (1 - k / L) ** 1.5 * 0.85
            img = img * (1 - a) + white * a
    # fade from black at the very start, to black at the very end
    if f < 4: img = img * (f / 4)
    end_fade = int(2.2 * FPS)
    if f > NF - end_fade: img = img * max(0.0, (NF - f) / end_fade)
    p.stdin.write(np.clip(img, 0, 255).astype(np.uint8).tobytes())
p.stdin.close(); p.wait()
for r in readers.values(): r.close()

json.dump([{k: v for k, v in s.items() if k not in ('file',)} for s in shots], open(f'{WORK}/timeline.json', 'w'), indent=1, default=str)
print('done', OUT)
