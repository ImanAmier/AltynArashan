import librosa, numpy as np, json
y, sr = librosa.load('song.mp3', sr=22050, mono=True)
tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units='time')
onset_env = librosa.onset.onset_strength(y=y, sr=sr)
rms = librosa.feature.rms(y=y)[0]
t = librosa.times_like(rms, sr=sr)
# per-2s energy
print("tempo", tempo)
print("nbeats", len(beats), "first", beats[:12])
seg = []
for s in range(0, int(t[-1]), 2):
    m = (t>=s)&(t<s+2)
    seg.append(round(float(rms[m].mean()),3))
print("rms per 2s:", seg)
# vocal-ish: harmonic/percussive split spectral flatness? simple: low-band vs total
S = np.abs(librosa.stft(y))
freqs = librosa.fft_frequencies(sr=sr)
low = S[freqs<150].sum(0); mid = S[(freqs>300)&(freqs<3000)].sum(0)
tt = librosa.times_like(low, sr=sr)
out=[]
for s in range(0,int(tt[-1]),2):
    m=(tt>=s)&(tt<s+2); out.append(round(float(low[m].mean()/ (mid[m].mean()+1e-9)),2))
print("low/mid per 2s:", out)
json.dump({"tempo":float(np.atleast_1d(tempo)[0]),"beats":[float(b) for b in beats]}, open('beats.json','w'))
