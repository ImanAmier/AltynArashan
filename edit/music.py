import numpy as np, soundfile as sf, subprocess, json
SR=48000
def load_song():
    subprocess.run(['ffmpeg','-v','error','-y','-i','song.mp3','-ar',str(SR),'-ac','2','song48.wav'],check=True)
    a,_=sf.read('song48.wav',dtype='float32'); return a
SPLICE_AT=65.41; JUMP_TO=3.97   # bar 34 == bar 2 (identical hook) -> repeat hook+verse1 once
def extended():
    a=load_song()
    i=int(SPLICE_AT*SR); j=int(JUMP_TO*SR); xf=int(0.03*SR)
    head=a[:i+xf].copy(); tail=a[j:].copy()
    r=np.linspace(0,1,xf)[:,None]
    head[-xf:]=head[-xf:]*(1-r)+tail[:xf]*r
    out=np.concatenate([head,tail[xf:]])
    return out
def ext_beats():
    b=json.load(open('beats.json'))['beats']
    off=SPLICE_AT-JUMP_TO
    eb=[x for x in b if x<SPLICE_AT]+[x+off for x in b if x>=JUMP_TO]
    return sorted(eb)
if __name__=='__main__':
    m=extended(); sf.write('music_ext.wav',m,SR); print(len(m)/SR)
    eb=ext_beats(); json.dump(eb,open('ext_beats.json','w')); print(len(eb), eb[:5], eb[-3:])
