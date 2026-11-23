"""GolfCut fixed-camera trajectory adapter; actual observed points only."""
import numpy as np
import golf_detector as detector

def analyze(path, impact, tee, progress=lambda p: None):
    color, gray, fps = detector.read_video(str(path), geometry_v2=True)
    n, height, width = gray.shape
    frame = round(impact*fps)
    if not 0 <= frame < n-2:
        raise ValueError('Choose the impact before the end of the clip.')
    if tee is None or len(tee) != 2 or not all(np.isfinite(v) and 0 <= v <= 1 for v in tee):
        raise ValueError('Mark the ball at impact.')
    tx, ty = tee[0]*width, tee[1]*height
    yy, xx = np.mgrid[:height, :width]
    roi = (np.abs(xx-tx) <= .20*width) & (yy >= .10*height) & (yy <= ty+.03*height)
    lo, hi = frame, min(n, frame+25)
    progress(.2)
    _, maps, diagnostics = detector.response_maps(gray, frame, roi, range(lo,hi))
    candidates = {i: detector.candidates_for_frame(i,maps[i],diagnostics[i],roi) for i in range(lo,hi)}
    progress(.65)
    track, _ = detector.track_before_detect(candidates,frame,(tx,ty),width,height,geometry_v2=True)
    points = [] if track is None else [dict(frame=p.frame,time=p.frame/fps,x=p.x/width,y=p.y/height,
                                           confidence=float(p.score)) for p in track.points]
    progress(1)
    return dict(tracks=[points] if len(points)>=4 else [], fps=fps,
                adapter='golfcut-pseudoflow-v2', impact=impact, tee=tee,
                limitation='Visible ball flight only; no estimated landing point or distance.')
