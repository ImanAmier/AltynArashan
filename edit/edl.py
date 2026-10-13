# Edit decision list for the Altyn Arashan vlog.
# Each shot: video ('v') or photo ('p'). Length is either beats ('b': n beats on the music grid)
# or seconds ('d'), in which case the cut is pushed to the next beat unless exact=True.
# Audio is described separately per shot:
#   'voice': [(src, in, out, [caption lines...]), ...]  placed at 'at' seconds into the shot (default 0)
#   'amb':   (src, in, gain_db)   natural sound break: music fades out, clip audio plays
# 'tr': transition INTO this shot: ('fade', dur) | ('whip', dur) | ('zoom', dur) | ('flash', dur)
# 'title': (text, style) shown over the shot.

def V(src, t, b=None, d=None, **kw):
    s = dict(type='video', src=src, **{'in': t}); s.update(kw)
    if b is not None: s['b'] = b
    if d is not None: s['d'] = d
    return s

def P(src, b=None, d=None, **kw):
    s = dict(type='photo', src=src); s.update(kw)
    if b is not None: s['b'] = b
    if d is not None: s['d'] = d
    return s

EDL = [
    # ---------------- TEASER (cut to the beat) ----------------
    V('P1010143', 48.6, b=1, zoom=1.05),
    V('P1010195', 42.2, b=1),
    V('P1010226', 40.6, b=1),
    V('P1010230', 33.0, b=1, zoom=1.05, zy=0.3),
    V('P1010134', 121.5, b=1),
    V('P1010149', 6.0, b=1),
    V('P1010241', 12.4, b=1),
    V('P1010243', 44.0, b=1, lut='golden'),
    # ---------------- TITLE on the drop ----------------
    V('P1010176', 11.6, b=16, speed=0.6, stab=True, tr=('flash', 0.25),
      title=('Altyn Arashan, Kyrgyzstan', 'main')),
    # ---------------- THE TRAIL ----------------
    V('P1010127', 24.5, b=8, stab=True, tr=('fade', 0.5)),
    V('P1010127', 3.4, d=2.0, exact=True, voice=[('P1010127', 3.4, 5.9, ['Currently one kilometer down.'])]),
    V('P1010127', 7.4, d=1.9, exact=True, voice=[('P1010127', 7.9, 9.3, ['14 to go!'])], vat=0.5),
    V('P1010127', 34.0, b=4, speed=1.5),
    V('P1010127', 41.6, b=3),
    V('P1010127', 52.4, b=6, stab=True),
    V('P1010127', 66.0, b=4),
    V('P1010127', 90.9, d=1.8, zoom=1.05, voice=[('P1010127', 90.9, 92.7, ["Can't wait to see the view."])]),
    V('P1010134', 9.2, b=6),
    V('P1010134', 29.5, b=4, speed=1.5, stab=True),
    V('P1010134', 81.0, b=6, stab=True),
    # ambient break 1: the river
    V('P1010134', 116.8, b=4, stab=True),
    V('P1010134', 120.0, b=8, amb=('P1010134', 116.0, 0, None)),
    V('P1010143', 0.2, b=6, tr=('fade', 0.4)),
    V('P1010195', 40.2, b=3, freeze_end=0.6),
    V('P1010143', 19.6, b=8, voice=[('P1010143', 28.3, 30.4, ['Yeah, 12 km to go!'])], vat=1.4),
    # jeep fast cuts
    V('P1010143', 31.2, b=2, speed=1.5, tr=('whip', 0.25)),
    V('P1010143', 35.2, b=2, speed=1.5),
    V('P1010143', 46.8, b=2),
    V('P1010143', 49.0, b=2),
    V('P1010143', 51.3, b=2),
    V('P1010144', 11.8, d=2.4, voice=[('P1010144', 11.8, 14.1, ['Weather is still nice, sunny.'])]),
    V('P1010148', 25.2, b=4),
    V('P1010148', 40.0, b=3),
    # ambient break 2: river beside the trail
    V('P1010149', 0.0, b=10, amb=('P1010149', 0.0, 0, None)),
    V('P1010149', 33.4, b=6, stab=True),
    V('P1010165', 5.7, d=1.0, exact=True, voice=[('P1010165', 6.9, 9.4, ['5.1 kilometers in...'])]),
    V('P1010165', 23.0, d=1.6),
    V('P1010165', 12.9, d=2.8, voice=[('P1010165', 13.3, 16.0, ['Still sunny day, but good weather.'])]),
    V('P1010165', 45.0, b=5),
    V('P1010165', 52.5, b=4, stab=True),
    # the jeep & horse rant
    V('P1010176', 21.6, d=5.3, voice=[('P1010176', 21.6, 26.9, ['Basically, the route is for the jeep and the horse.', 'We can pay extra for it, but...'])]),
    V('P1010176', 28.6, d=1.6, exact=True, voice=[('P1010176', 28.6, 30.2, ['We built different, bro.'])]),
    V('P1010226', 35.4, d=1.5, exact=True, voice=[('P1010176', 31.0, 34.3, ["We ain't need no jeep,", "we ain't need no f***ing horse!"])]),
    V('P1010195', 42.0, d=1.8, exact=True),
    V('P1010176', 35.7, d=1.6, exact=True, voice=[('P1010176', 35.7, 37.4, ['We came for the hike!'])]),
    V('P1010144', 30.9, d=1.6, voice=[('P1010176', 39.3, 40.8, ['We got legs, innit.'])]),
    V('P1010176', 14.6, b=10, speed=0.7, stab=True),
    V('P1010177', 9.4, d=3.0, exact=True, voice=[('P1010177', 10.0, 15.3, ['An hour and 53 minutes for 6 kilometers.', "That's crazy."])], vat=0.6),
    V('P1010177', 0.9, d=3.0),
    # ambient break 3: river in the meadow
    V('P1010177', 39.0, b=10, amb=('P1010177', 36.0, 0, None)),
    V('P1010177', 46.0, b=4),
    V('P1010195', 0.0, b=6, stab=True),
    V('P1010195', 13.6, b=6, stab=True),
    V('P1010195', 36.2, b=4),
    V('P1010195', 50.6, b=4, stab=True),
    V('P1010202', 9.4, d=1.5, exact=True, voice=[('P1010202', 15.1, 18.6, ['8 kilometers in.', '6 to go.'])], vat=0.1),
    V('P1010202', 12.6, d=2.2),
    V('P1010202', 36.4, b=6, stab=True),
    V('P1010202', 42.4, b=6),
    V('P1010213', 15.6, b=6, stab=True),
    V('P1010213', 20.2, b=4, stab=True),
    V('P1010217', 2.6, d=3.8, voice=[('P1010217', 2.9, 4.7, ['10 kilometers in!']), ('P1010217', 5.4, 6.4, ["Let's go!"])]),
    V('P1010226', 0.0, b=4, stab=True),
    V('P1010226', 11.0, d=2.8, voice=[('P1010226', 10.8, 13.0, ['5 kilometers to go!'])]),
    V('P1010226', 39.7, d=1.6, voice=[('P1010226', 39.7, 41.3, ['What a nice view!'])]),
    V('P1010226', 44.3, b=12, stab=True),
    # ---------------- THE VALLEY ----------------
    V('P1010230', 18.3, b=10, stab=True, tr=('fade', 0.6)),
    V('P1010230', 7.2, b=4),
    V('P1010230', 14.9, b=4),
    V('P1010230', 50.2, b=4),
    V('P1010241', 0.0, b=3),
    V('P1010241', 6.8, b=4),
    V('P1010241', 21.2, b=3),
    V('P1010241', 10.2, b=8, voice=[('P1010241', 2.1, 4.3, ['13 kilometers!'])], vat=0.4),
    V('P1010242', 6.2, b=4, stab=True, lut='golden'),
    V('P1010243', 5.6, b=4, lut='golden'),
    V('P1010243', 23.0, b=4, lut='golden'),
    V('P1010243', 43.0, b=10, lut='golden'),
    # ---------------- ENDING ----------------
    V('P1010230', 32.6, b=6, tr=('fade', 0.5)),
    V('P1010226', 46.0, b=999, speed=0.6, stab=True, tr=('fade', 0.8), title=('Altyn Arashan', 'end')),
]
