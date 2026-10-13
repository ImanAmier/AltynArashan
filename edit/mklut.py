# Build .cube LUTs: "day" (rich greens, deep blue sky, crisp whites, gentle warmth) and "golden" (warmer evening)
import numpy as np, colorsys, sys
def grade(rgb, warm=0.0, golden=False):
    r,g,b = rgb[...,0],rgb[...,1],rgb[...,2]
    # mild exposure/contrast S-curve on luma
    def scurve(x, k=0.18):
        return x + k*x*(1-x)*(x-0.5)*2.2
    rgb = np.clip(rgb,0,1)
    # convert to HSV vectorized
    mx = rgb.max(-1); mn = rgb.min(-1); d = mx-mn
    h = np.zeros_like(mx)
    m = d>1e-6
    rr,gg,bb = rgb[...,0],rgb[...,1],rgb[...,2]
    idx = m & (mx==rr); h[idx] = ((gg-bb)[idx]/d[idx]) % 6
    idx = m & (mx==gg); h[idx] = ((bb-rr)[idx]/d[idx]) + 2
    idx = m & (mx==bb); h[idx] = ((rr-gg)[idx]/d[idx]) + 4
    h = h*60.0
    s = np.where(mx>1e-6, d/np.maximum(mx,1e-6), 0); v = mx.copy()
    def band(h, c, w):  # smooth hue weight
        dd = np.abs(((h-c+180)%360)-180); return np.clip(1-dd/w,0,1)
    green = band(h, 100, 55)      # foliage/grass (yellow-green to green)
    blue  = band(h, 210, 35)      # sky
    orange= band(h, 30, 25)       # skin / warm
    # saturation shaping
    violet = band(h, 245, 20)
    s = s*(1 + 0.48*green + 0.42*blue + 0.06*orange)*(1-0.6*violet)
    s = s + 0.10*s*(1-s)          # vibrance-ish
    # deepen sky: lower value of saturated blues
    v = v*(1 - 0.13*blue*np.clip(s*1.5,0,1))
    # greens slightly richer/darker for depth
    v = v*(1 - 0.04*green*np.clip(s*1.5,0,1))
    # hue nudge: yellow-greens toward green, cyan-blue toward blue
    h = h + 6*band(h,75,30) - 4*band(h,185,20)
    # crisp whites: desaturate near-white highlights
    s = s*(1 - 0.6*np.clip((v-0.88)/0.12,0,1)*(s<0.25))
    s = np.clip(s,0,1); v=np.clip(v,0,1); h=h%360
    # back to RGB
    c = v*s; x = c*(1-np.abs((h/60)%2-1)); m0 = v-c
    hp = (h//60).astype(int)%6
    z=np.zeros_like(c)
    R=np.choose(hp,[c,x,z,z,x,c]); G=np.choose(hp,[x,c,c,x,z,z]); B=np.choose(hp,[z,z,x,c,c,x])
    out = np.stack([R+m0,G+m0,B+m0],-1)
    # luma contrast
    L = 0.2126*out[...,0]+0.7152*out[...,1]+0.0722*out[...,2]
    L2 = scurve(L, 0.30 if not golden else 0.24)
    out = out + (L2-L)[...,None]
    # lift shadows slightly, keep blacks rich
    out = out*0.985 + 0.012
    # warmth: highlights/mids warm, shadows neutral-cool
    hl = np.clip((L-0.35)/0.6,0,1)[...,None]
    wv = np.array([1.0+warm, 1.0+warm*0.35, 1.0-warm*0.9])
    out = out*(1-hl) + out*wv*hl
    if golden:
        # golden glow in mids/highlights, slightly teal shadows
        sh = np.clip((0.4-L)/0.4,0,1)[...,None]
        out = out*(1-sh*0.5) + out*np.array([0.97,1.0,1.03])*sh*0.5
    return np.clip(out,0,1)
def write(name, warm, golden=False, N=33):
    g = np.linspace(0,1,N)
    B,G,R = np.meshgrid(g,g,g, indexing='ij')
    rgb = np.stack([R,G,B],-1).reshape(-1,3)
    out = grade(rgb, warm, golden)
    with open(name,'w') as f:
        f.write(f'LUT_3D_SIZE {N}\n')
        for o in out: f.write(f'{o[0]:.6f} {o[1]:.6f} {o[2]:.6f}\n')
write('day.cube', 0.035)
write('golden.cube', 0.12, golden=True)
print('ok')
