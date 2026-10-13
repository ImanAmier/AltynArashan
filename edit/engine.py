import subprocess, json, os, math, numpy as np, cv2, sys, hashlib
SRC = os.environ.get("FOOTAGE_DIR", "/home/user/footage/raw/altynarashan vid")
WORK = os.environ.get("WORK_DIR", "/home/user/work")
FPS_NUM, FPS_DEN = 30000, 1001
FPS = FPS_NUM/FPS_DEN

def run(cmd):
    r = subprocess.run(cmd, shell=isinstance(cmd,str), capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-3000:]); raise SystemExit(f"cmd failed: {cmd if isinstance(cmd,str) else ' '.join(cmd)}")
    return r

def nframes(dur): return max(1, int(round(dur*FPS)))

def lut_path(name): return f"{WORK}/{name}.cube"

def enc_args(W):
    return ['-c:v','libx264','-preset','veryfast' if W<1920 else 'medium','-crf','18' if W<1920 else '16','-pix_fmt','yuv420p','-r',f'{FPS_NUM}/{FPS_DEN}','-an']

def shot_key(s, W):
    return hashlib.md5((json.dumps(s, sort_keys=True)+str(W)).encode()).hexdigest()[:12]

def render_video_shot(s, out, W, H):
    src = f"{SRC}/{s['src']}.MOV"
    speed = s.get('speed',1.0); dur = s['dur']; n = nframes(dur)
    span = dur*speed
    tin = s['in']
    vf = []
    if s.get('stab'):
        trf = f"{WORK}/render/{s['src']}_{tin}_{span:.2f}.trf"
        if not os.path.exists(trf):
            run(['ffmpeg','-v','error','-y','-ss',str(tin),'-t',str(span+0.2),'-i',src,'-vf',f'vidstabdetect=shakiness=8:accuracy=12:result={trf}','-f','null','-'])
        vf.append(f"vidstabtransform=input={trf}:smoothing={s.get('smooth',20)}:optzoom=0:zoom={s.get('stabzoom',6)}:interpol=bicubic")
    if s.get('rotate'): vf.append(f"rotate={s['rotate']}*PI/180:ow=iw:oh=ih")
    z = s.get('zoom',1.0); zx=s.get('zx',0.5); zy=s.get('zy',0.5)
    if z != 1.0:
        vf.append(f"crop=iw/{z}:ih/{z}:(iw-iw/{z})*{zx}:(ih-ih/{z})*{zy}")
    if s.get('zoomto'):  # slow punch-in over the shot (smooth via scale+crop expressions)
        z1 = s['zoomto']
        vf.append(f"scale={W*2}:{H*2}")
        vf.append(f"crop=w='{W*2}/(1+({z1}-1)*t/{span})':h='{H*2}/(1+({z1}-1)*t/{span})':x='(iw-ow)*{zx}':y='(ih-oh)*{zy}'")
    vf.append(f"scale={W}:{H}:flags=bicubic")
    vf.append(f"lut3d={lut_path(s.get('lut','day'))}")
    eq = []
    if s.get('bright'): eq.append(f"brightness={s['bright']}")
    if s.get('sat'): eq.append(f"saturation={s['sat']}")
    if s.get('gamma'): eq.append(f"gamma={s['gamma']}")
    if eq: vf.append("eq="+":".join(eq))
    if speed != 1.0:
        vf.append(f"setpts=PTS/{speed}")
        if speed < 1.0:
            vf.append(f"minterpolate=fps={FPS_NUM}/{FPS_DEN}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1")
        else:
            vf.append(f"fps={FPS_NUM}/{FPS_DEN}")
    else:
        vf.append(f"fps={FPS_NUM}/{FPS_DEN}")
    if s.get('freeze_end'):
        vf.append(f"tpad=stop_mode=clone:stop_duration={s['freeze_end']}")
    vf.append("setpts=PTS-STARTPTS")
    vf.append("format=yuv420p")
    total_n = n + (nframes(s['freeze_end']) if s.get('freeze_end') else 0)
    run(['ffmpeg','-v','error','-y','-ss',str(tin),'-t',str(span+0.5),'-i',src,'-vf',",".join(vf),'-frames:v',str(total_n)]+enc_args(W)+[out])

def ease(t, kind='inout'):
    if kind=='linear': return t
    return t*t*(3-2*t)

def render_photo_shot(s, out, W, H):
    img_path = f"{SRC}/{s['src']}.JPG"
    graded = f"{WORK}/render/photo_{s['src']}_{s.get('lut','day')}.png"
    if not os.path.exists(graded):
        run(['ffmpeg','-v','error','-y','-i',img_path,'-vf',f"lut3d={lut_path(s.get('lut','day'))}"+(f",eq=brightness={s['bright']}" if s.get('bright') else "")+(f",eq=gamma={s['gamma']}" if s.get('gamma') else ""),graded])
    im = cv2.imread(graded)
    ih, iw = im.shape[:2]
    # base 16:9 crop rect of full width
    bw = iw; bh = iw*H/W
    if bh > ih: bh = ih; bw = ih*W/H
    yc = s.get('ypos',0.5); xc = s.get('xpos',0.5)
    def rect(zoom, dx=0.0, dy=0.0):
        w = bw/zoom; h = bh/zoom
        cx = (iw - w)*xc + w/2 + dx*iw; cy = (ih - h)*yc + h/2 + dy*ih
        cx = min(max(cx, w/2), iw-w/2); cy = min(max(cy, h/2), ih-h/2)
        return cx, cy, w, h
    kb = s.get('kb','in')
    presets = {
        'in':   ((1.00,0,0),(1.12,0,0)),
        'out':  ((1.14,0,0),(1.00,0,0)),
        'left': ((1.10,0.035,0),(1.10,-0.035,0)),
        'right':((1.10,-0.035,0),(1.10,0.035,0)),
        'up':   ((1.10,0,0.03),(1.10,0,-0.03)),
        'down': ((1.10,0,-0.03),(1.10,0,0.03)),
        'punch':((1.04,0,0),(1.18,0,0)),
    }
    a, b = presets[kb] if isinstance(kb,str) else kb
    n = nframes(s['dur'])
    # pre-downscale for speed while keeping >=2x output resolution
    scale = min(1.0, (W*2.2)/bw)
    if scale < 1.0:
        im = cv2.resize(im, (int(iw*scale), int(ih*scale)), interpolation=cv2.INTER_AREA)
    sc = im.shape[1]/iw
    p = subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s',f'{W}x{H}','-r',f'{FPS_NUM}/{FPS_DEN}','-i','-']+enc_args(W)+[out], stdin=subprocess.PIPE)
    ra = rect(*a); rb = rect(*b)
    for i in range(n):
        t = ease(i/max(1,n-1), s.get('ease','linear' if s['dur']<2.5 else 'inout'))
        cx,cy,w,h = [ra[k]+(rb[k]-ra[k])*t for k in range(4)]
        cx*=sc; cy*=sc; w*=sc; h*=sc
        sx = W/w; sy = H/h
        M = np.array([[sx,0,-(cx-w/2)*sx],[0,sy,-(cy-h/2)*sy]],dtype=np.float64)
        fr = cv2.warpAffine(im, M, (W,H), flags=cv2.INTER_LINEAR if sx>=1 else cv2.INTER_AREA, borderMode=cv2.BORDER_REFLECT)
        p.stdin.write(fr.tobytes())
    p.stdin.close(); p.wait()

def render_shot(s, W, H):
    key = shot_key({k:v for k,v in s.items() if k not in ('tr','audio','sfx','vol','label','afade','aspeech')}, W)
    out = f"{WORK}/render/shot_{key}_{W}.mp4"
    if not os.path.exists(out):
        if s['type']=='video': render_video_shot(s, out, W, H)
        else: render_photo_shot(s, out, W, H)
    return out

def shot_len(s):
    return s['dur'] + (s.get('freeze_end') or 0)
