#!/usr/bin/env python3
"""Fixed-camera tiny-ball prototype: temporal background + track-before-detect.

This is deliberately a PC-only shadow evaluator.  It does not share state with
the shipping detector and does not change app behaviour.

Usage:
  python3 tools/pseudo_flow_ball.py VIDEO IMPACT_FRAME OUT.mp4 [TEE_X TEE_Y]

TEE_X/TEE_Y are normalized display coordinates.  When omitted, the search is
the middle 42% of the image and the tee is only used as a loose prior.
"""

from __future__ import annotations

import json
import math
import os
import sys
from dataclasses import dataclass

import cv2
cv2.setNumThreads(2)
import numpy as np


@dataclass
class Candidate:
    frame: int
    x: float
    y: float
    score: float
    bg: float
    temporal: float
    contrast: float
    area: int


@dataclass
class State:
    points: list[Candidate]
    value: float
    vx: float
    vy: float


def read_video(path: str, geometry_v2: bool = True):
    cap = cv2.VideoCapture(path,cv2.CAP_FFMPEG,[cv2.CAP_PROP_N_THREADS,2])
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    color = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        # Device parity: all spatial filters and TBD gates are calibrated at
        # this working raster. V2 preserves aspect ratio; set
        # PSEUDOFLOW_GEOMETRY_V2=0 for exact legacy PC/device geometry.
        if geometry_v2:
            scale = min(1.0, 480.0 / max(frame.shape[:2]))
            if scale < 1.0:
                frame = cv2.resize(frame, (round(frame.shape[1] * scale),
                                           round(frame.shape[0] * scale)),
                                   interpolation=cv2.INTER_LINEAR)
        elif frame.shape[1] > 480 or frame.shape[0] > 272:
            frame = cv2.resize(frame, (480, 272), interpolation=cv2.INTER_LINEAR)
        color.append(frame)
    cap.release()
    if not color:
        raise RuntimeError(f"cannot decode {path}")
    gray = np.stack([cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in color])
    return color, gray, fps


def robust_normalize(a: np.ndarray, roi: np.ndarray) -> np.ndarray:
    sampled = a[::4, ::4]
    v = sampled[roi[::4, ::4]]
    med = float(np.median(v))
    mad = float(np.median(np.abs(v - med))) + 0.35
    return np.maximum(0.0, (a - med) / (1.4826 * mad))


def response_maps(gray: np.ndarray, impact: int, roi: np.ndarray, frame_indices=None):
    # Use the whole short clip: a fast ball occupies each pixel for too few
    # frames to enter the median.  This also avoids an adaptive model warm-up.
    sample_ids = np.linspace(0, len(gray) - 1, 9).astype(int)
    background = np.median(gray[sample_ids].astype(np.float32), axis=0)
    maps = [None] * len(gray)
    diagnostics = [None] * len(gray)
    n = len(gray)
    work = range(n) if frame_indices is None else frame_indices
    for i in work:
        cur = gray[i].astype(np.float32)
        bg = cv2.blur(np.abs(cur - background), (3, 3), borderType=cv2.BORDER_REPLICATE)
        p = np.abs(cur - gray[max(0, i - 1)].astype(np.float32))
        q = np.abs(cur - gray[min(n - 1, i + 1)].astype(np.float32))
        # max(), rather than min(), preserves the ball across duplicate frames.
        # Requiring background residual prevents a one-sided codec flicker from
        # receiving a high score by itself.
        temporal = cv2.blur(np.maximum(p, q), (3, 3), borderType=cv2.BORDER_REPLICATE)
        surround = cv2.blur(cur, (9, 9), borderType=cv2.BORDER_REPLICATE)
        contrast = cv2.blur(np.abs(cur - surround), (3, 3), borderType=cv2.BORDER_REPLICATE)

        zbg = robust_normalize(bg, roi)
        ztm = robust_normalize(temporal, roi)
        zct = robust_normalize(contrast, roi)
        score = 0.46 * zbg + 0.34 * ztm + 0.20 * zct
        score[~roi] = 0
        maps[i] = score.astype(np.float32)
        diagnostics[i] = (bg, temporal, contrast)
    return background, maps, diagnostics


def candidates_for_frame(frame: int, score: np.ndarray, diag, roi: np.ndarray,
                         max_count: int = 120, return_audit: bool = False):
    # 5x5 local maxima are candidate locations, but the threshold is purposely
    # low.  The trajectory, not a single frame, makes the final decision.
    maxima = score >= cv2.dilate(score, np.ones((5, 5), np.uint8)) - 1e-6
    ys, xs = np.where(maxima & roi & (score >= 0.72))
    max_score = float(np.max(score[roi])) if np.any(roi) else 0.0
    if len(xs) == 0:
        audit = {"maxScore": max_score, "scorePeaks": 0, "bgRejected": 0,
                 "areaRejected": 0, "kept": 0, "maxArea": 0}
        return ([], audit) if return_audit else []
    score_peaks = len(xs)
    order = np.argsort(score[ys, xs])[::-1][:max_count]
    bg, temporal, contrast = diag
    # A golf ball is a tiny residual component.  This rejects the golfer,
    # club and horizon *before* temporal association, even when an edge pixel
    # on those objects is a very strong local maximum.
    _, labels, stats, _ = cv2.connectedComponentsWithStats((bg > 2.0).astype(np.uint8), 8)
    h, w = score.shape
    max_area = max(80, round(80 * (w * h) / (480 * 272)))
    out = []
    bg_rejected = area_rejected = largest_area = 0
    for k in order:
        # A one-sided temporal spike without persistence against the robust
        # background is codec/edge flicker, not a moving ball.
        if bg[ys[k], xs[k]] < 2.0:
            bg_rejected += 1
            continue
        label = labels[ys[k], xs[k]]
        area = int(stats[label, cv2.CC_STAT_AREA]) if label else 0
        largest_area = max(largest_area, area)
        if area > max_area:
            area_rejected += 1
            continue
        out.append(Candidate(frame, float(xs[k]), float(ys[k]), float(score[ys[k], xs[k]]),
                             float(bg[ys[k], xs[k]]), float(temporal[ys[k], xs[k]]),
                             float(contrast[ys[k], xs[k]]), area))
    out = out[:max_count]
    audit = {"maxScore": max_score, "scorePeaks": score_peaks,
             "bgRejected": bg_rejected, "areaRejected": area_rejected,
             "kept": len(out), "maxArea": largest_area}
    return (out, audit) if return_audit else out


def track_before_detect(per_frame: dict[int, list[Candidate]], impact: int,
                        tee: tuple[float, float] | None, w: int, h: int,
                        geometry_v2: bool = True):
    frames = sorted(per_frame)
    if len(frames) < 3:
        return None, []

    # Pair-state beam search preserves velocity, allowing an acceleration
    # penalty without a cubic dynamic-programming table.  A new hypothesis may
    # start at every post-impact frame: at 30 fps the ball can be invisible for
    # several frames before it separates from the club/ground enough to see.
    beam: list[State] = []
    completed: list[State] = []
    sx = 480.0 / w if geometry_v2 else 1.0
    sy = 272.0 / h if geometry_v2 else 1.0
    for frame_index in range(1, len(frames)):
        prev_f, fi = frames[frame_index - 1], frames[frame_index]
        nxt: list[State] = []
        cands = per_frame[fi]
        for state in beam:
            last = state.points[-1]
            for q in cands:
                vx, vy = (q.x - last.x) * sx, (q.y - last.y) * sy
                speed = math.hypot(vx, vy)
                if speed > 29 or vy > 4:
                    continue
                ax, ay = vx - state.vx, vy - state.vy
                accel = math.hypot(ax, ay)
                # Perspective and duplicate frames make the apparent vertical
                # speed non-ballistic; use a robust, deliberately soft prior.
                penalty = 0.055 * accel + 0.022 * abs(vx) + 0.012 * max(0.0, vy)
                nxt.append(State(state.points + [q], state.value + math.log1p(q.score) - penalty, vx, vy))
        # Seed fresh tracks as well as extending the active beam.
        for p in per_frame[prev_f]:
            if tee is not None and abs(p.x - tee[0]) > 0.07 * w:
                continue
            for q in cands:
                vx, vy = (q.x - p.x) * sx, (q.y - p.y) * sy
                if math.hypot(vx, vy) <= 29 and vy <= 4:
                    evidence = math.log1p(p.score) + math.log1p(q.score)
                    nxt.append(State([p, q], evidence - 0.018 * abs(vx), vx, vy))
        if not nxt:
            beam = []
            continue
        # Keep geometrically distinct hypotheses, not thousands of variants
        # ending on the same bright piece of club or foliage.
        nxt.sort(key=lambda s: s.value, reverse=True)
        kept = []
        cells = set()
        for s in nxt:
            p = s.points[-1]
            key = (int(p.x // 3), int(p.y // 3), int(round(s.vx / 3)), int(round(s.vy / 3)))
            if key in cells:
                continue
            cells.add(key)
            kept.append(s)
            if len(kept) >= 3500:
                break
        beam = kept
        completed.extend(beam)

    ranked = []
    for s in completed:
        if len(s.points) < 7:
            continue
        p0, p1 = s.points[0], s.points[-1]
        rise = (p0.y - p1.y) * sy
        dx = abs(p1.x - p0.x) * sx
        if rise < 24 or dx > max(50, rise * 0.75):
            continue
        # A static high-contrast feature can collect score for many frames and
        # then jump at the two ends of the window.  A real flying ball may be
        # duplicated for one encoded frame, but cannot remain at one pixel for
        # most of the chain.  Keep this as a chain-level identity gate so weak
        # real-ball frames are still available to TBD.
        steps = [math.hypot((s.points[k].x - s.points[k - 1].x) * sx,
                            (s.points[k].y - s.points[k - 1].y) * sy)
                 for k in range(1, len(s.points))]
        static_px = .75 if geometry_v2 else max(.75, min(w, h) * .0008)
        # Device parity: reject a track that sits on one background residual
        # and then consumes the generous TBD radius to jump onto another one.
        # The daylight false positive had a ~3 px median moving step and a
        # 21 px terminal jump; the real ball chain is continuous (about
        # 5 px median / 14 px max). Duplicate frames remain explicitly valid.
        moving_steps = sorted(d for d in steps if d >= static_px)
        if not moving_steps:
            continue
        median_moving_step = moving_steps[len(moving_steps) // 2]
        step_spike_limit = max(10.0, 3.5 * median_moving_step)
        if max(moving_steps) > step_spike_limit:
            continue
        terminal_step_limit = max(6.0, 2.5 * median_moving_step)
        if steps[-1] > terminal_step_limit:
            continue
        moving_fraction = sum(d >= static_px for d in steps) / len(steps)
        longest_static = current_static = 0
        for d in steps:
            current_static = current_static + 1 if d < static_px else 0
            longest_static = max(longest_static, current_static)
        if moving_fraction < .40 or longest_static > max(2, math.floor(.30 * len(steps))):
            continue
        temporal_active = sum(p.temporal >= 2.0 for p in s.points) / len(s.points)
        if temporal_active < .70:
            continue
        if p1.temporal < 2.0:
            continue
        moving_segments = [
            ((s.points[k].x - s.points[k - 1].x) * sx,
             (s.points[k].y - s.points[k - 1].y) * sy)
            for k in range(1, len(s.points)) if steps[k - 1] >= static_px
        ]
        path_length = sum(math.hypot(dx0, dy0) for dx0, dy0 in moving_segments)
        net_length = math.hypot((p1.x - p0.x) * sx, (p1.y - p0.y) * sy)
        straightness = net_length / path_length if path_length > 0 else 0
        angles = [math.atan2(dy0, dx0) for dx0, dy0 in moving_segments]
        turns = [abs(math.degrees(math.atan2(math.sin(b - a), math.cos(b - a))))
                 for a, b in zip(angles, angles[1:])]
        if straightness < .65 or (turns and max(turns) > 75):
            continue
        if tee is not None:
            # A clubhead can sweep smoothly away from tee in screen x while
            # remaining in the ground band.  A usable DTL ball chain must have
            # visibly left that band by its tail.
            if tee[1] - p1.y < .06 * h:
                continue
            # Flight identity: extrapolating the observed x(y) line back to
            # tee height must land near the independently selected tee.  This
            # rejects smooth hops between unrelated static sky features.
            ys = np.asarray([p.y for p in s.points], dtype=np.float64)
            xs = np.asarray([p.x for p in s.points], dtype=np.float64)
            vy_var = float(np.sum((ys - ys.mean()) ** 2))
            if vy_var <= 1e-6:
                continue
            slope = float(np.sum((ys - ys.mean()) * (xs - xs.mean())) / vy_var)
            tee_x_projected = float(xs.mean() + slope * (tee[1] - ys.mean()))
            if abs(tee_x_projected - tee[0]) > .10 * w:
                continue
        # Reward accumulated evidence and vertical displacement.  When an
        # independently selected tee is available, launch escape must also be
        # a first-class identity cue: tiny high-contrast residuals otherwise
        # beat the dim, fast ball simply because their response is stronger.
        value = s.value + 0.055 * rise - 0.018 * dx
        tee_escape = 0.0
        if tee is not None:
            tx, ty = tee
            tee_escape = max(0.0, ty - p1.y)
            value += 0.18 * tee_escape
            # Back-project the first observed velocity towards impact/tee.
            dt = max(1, p0.frame - impact)
            bx = p0.x - s.points[1].x + p0.x
            by = p0.y - s.points[1].y + p0.y
            dtee = math.hypot((bx - tx) / w, (by - ty) / h)
            value -= 2.0 * min(dtee, 0.5)
        ranked.append((value, s))
    ranked.sort(key=lambda x: x[0], reverse=True)
    return (ranked[0][1] if ranked else None), ranked[:10]


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    path = sys.argv[1]
    impact = int(sys.argv[2])
    out = sys.argv[3] if len(sys.argv) > 3 else "/tmp/pseudo_flow_ball.mp4"
    geometry_v2 = os.environ.get("PSEUDOFLOW_GEOMETRY_V2", "1") != "0"
    color, gray, fps = read_video(path, geometry_v2=geometry_v2)
    n, h, w = gray.shape
    tee = None
    if len(sys.argv) >= 6:
        tee = (float(sys.argv[4]) * w, float(sys.argv[5]) * h)

    yy, xx = np.mgrid[:h, :w]
    if tee is None:
        if geometry_v2:
            roi = (xx >= 0.04 * w) & (xx <= 0.96 * w) & (yy >= 0.06 * h) & (yy <= 0.90 * h)
        else:
            roi = (xx >= 0.38 * w) & (xx <= 0.72 * w) & (yy >= 0.12 * h) & (yy <= 0.78 * h)
    else:
        tx, ty = tee
        roi = (np.abs(xx - tx) <= 0.20 * w) & (yy >= 0.10 * h) & (yy <= ty + 0.03 * h)

    # Device parity: include the event frame so a one-frame-late impact event
    # does not discard the strongest launch observation.
    lo, hi = max(0, impact), min(n, impact + 25)
    background, maps, diagnostics = response_maps(gray, impact, roi, range(lo, hi))
    extracted = {i: candidates_for_frame(i, maps[i], diagnostics[i], roi, return_audit=True)
                 for i in range(lo, hi)}
    per_frame = {i: extracted[i][0] for i in range(lo, hi)}
    audits = {i: extracted[i][1] for i in range(lo, hi)}
    track, ranked = track_before_detect(per_frame, impact, tee, w, h,
                                        geometry_v2=geometry_v2)

    print(f"[PseudoFlow] video={os.path.basename(path)} shape={w}x{h} fps={fps:.3f} frames={n} impact={impact}")
    print(f"[PseudoFlow] geometry={'v2_aspect' if geometry_v2 else 'v1_stretched'} "
          f"roi={'wide[.04,.96]x[.06,.90]' if tee is None and geometry_v2 else ('center[.38,.72]x[.12,.78]' if tee is None else 'tee_strip')} "
          f"teeHint={'nil' if tee is None else 'set'}")
    for i in range(lo, hi):
        a = audits[i]
        print(f"[PseudoFlowAudit] f{i} max={a['maxScore']:.2f} peaks={a['scorePeaks']} "
              f"bgReject={a['bgRejected']} areaReject={a['areaRejected']} "
              f"kept={a['kept']} maxArea={a['maxArea']}")
    print("[PseudoFlow] candidates=" + ",".join(f"f{i}:{len(per_frame[i])}" for i in per_frame))
    for rank, (value, state) in enumerate(ranked[:5], 1):
        p0, p1 = state.points[0], state.points[-1]
        escape = max(0.0, tee[1] - p1.y) if tee is not None else 0.0
        print(f"[PseudoFlow] hypothesis#{rank} score={value:.2f} rise={p0.y-p1.y:.1f}px "
              f"teeEscape={escape:.1f}px dx={p1.x-p0.x:.1f}px frames={p0.frame}-{p1.frame}")
    if track is None:
        print("[PseudoFlow] result=none")
        result = []
    else:
        result = [{"frame": p.frame, "x": p.x / w, "y": p.y / h, "score": p.score,
                   "bg": p.bg, "temporal": p.temporal, "contrast": p.contrast,
                   "area": p.area} for p in track.points]
        print("[PseudoFlow] champion " + " ".join(f"f{p.frame}({p.x:.1f},{p.y:.1f})" for p in track.points))
        print("[PseudoFlowJSON] " + json.dumps(result, separators=(",", ":")))

    writer = cv2.VideoWriter(out, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    root, ext = os.path.splitext(out)
    clean_out = root + "_overlay" + (ext or ".mp4")
    clean_writer = cv2.VideoWriter(clean_out, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    history = []
    selected = {p.frame: p for p in track.points} if track is not None else {}
    for i, frame in enumerate(color):
        vis = frame.copy()
        clean = frame.copy()
        if i in per_frame:
            for p in per_frame[i][:40]:
                cv2.circle(vis, (round(p.x), round(p.y)), 2, (0, 220, 255), 1)
        if tee is not None:
            tee_px = (round(tee[0]), round(tee[1]))
            cv2.circle(vis, tee_px, 7, (255, 255, 0), 2)
            cv2.circle(clean, tee_px, 7, (255, 255, 0), 2)
        if i in selected:
            p = selected[i]
            history.append((round(p.x), round(p.y)))
            cv2.circle(vis, history[-1], 7, (0, 255, 0), 2)
            cv2.circle(clean, history[-1], 7, (0, 255, 0), 2)
        for j in range(1, len(history)):
            cv2.line(vis, history[j - 1], history[j], (0, 0, 255), 2)
            cv2.line(clean, history[j - 1], history[j], (0, 0, 255), 2)
        cv2.putText(vis, f"pseudo-flow f{i}", (10, 24), cv2.FONT_HERSHEY_SIMPLEX, .55, (255, 255, 255), 2)
        writer.write(vis)
        clean_writer.write(clean)
    writer.release()
    clean_writer.release()
    print(f"[PseudoFlow] debug={out}")
    print(f"[PseudoFlow] overlay={clean_out}")
    return 0 if track is not None else 2


if __name__ == "__main__":
    raise SystemExit(main())
