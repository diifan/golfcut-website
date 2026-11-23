"""GolfCut reviewed chain selection, extracted from tools/tracknet_batch.py."""

import numpy as np

DISP_MIN=.12
CHAIN_MIN=3
FIT_MIN=5
DT_MAX=5
RMS_MAX=.025
Y_TEE_MIN=.35
IMP_WIN=(1,2)
REVERSAL_DEG=90.0

def disp(c):
    return float(np.hypot(c[-1][1] - c[0][1], c[-1][2] - c[0][2]))

def build_chains(per_frame, step_max, hop_max=None, impact=None):
    """与 tracknet_diag.chain_ball 同构的贪心链;hop_max 限制单跳总位移。
    impact 非 None 时,跨 impact 帧的起飞跳不吃 hop_max(球起飞最快,
    20fps 实测真链有 dt=2~4、总位移 0.26~0.49 的合法大跳)。"""
    chains = []
    for i, bs in enumerate(per_frame):
        for cx, cy, a, p in bs:
            best = None
            for ch in chains:
                li, lx, ly = ch[-1]
                dt = i - li
                if dt <= 0 or dt > DT_MAX:
                    continue
                d = np.hypot(cx - lx, cy - ly)
                if d / dt >= step_max:
                    continue
                spans_impact = impact is not None and li < impact <= i
                if not spans_impact and hop_max is not None and d >= hop_max:
                    continue
                if best is None or d / dt < best[1]:
                    best = (ch, d / dt)
            (best[0].append([i, cx, cy]) if best else chains.append([[i, cx, cy]]))
    return chains

def chain_shape(chain):
    """链形状统计: 二次拟合 RMS、最大相邻方向角变化(°)、总扫描角(°)。"""
    fr = np.array([p[0] for p in chain], float)
    xs = np.array([p[1] for p in chain])
    ys = np.array([p[2] for p in chain])
    rms = None
    if len(chain) >= CHAIN_MIN:
        t = fr - fr[0]
        rx = xs - np.polyval(np.polyfit(t, xs, 2), t)
        ry = ys - np.polyval(np.polyfit(t, ys, 2), t)
        rms = float(np.sqrt((rx ** 2 + ry ** 2).mean()))
    seg = np.diff(np.stack([xs, ys], 1), axis=0)
    ang = np.unwrap(np.arctan2(seg[:, 1], seg[:, 0]))
    dang = np.abs(np.diff(ang)) if len(ang) > 1 else np.array([0.0])
    return {"rms": rms, "max_dang": float(np.degrees(dang.max())),
            "sweep": float(np.degrees(abs(ang[-1] - ang[0]))) if len(ang) > 1 else 0.0}

def identity_check(chain, impact):
    """弹道身份三道闸(便宜→贵)。返回 (ok, reason, stats)。"""
    stats = chain_shape(chain)
    stats["covers_impact"] = True
    if impact is not None:
        lo, hi = impact - IMP_WIN[0], impact + IMP_WIN[1]
        stats["covers_impact"] = any(lo <= f <= hi for f in (p[0] for p in chain))
        if not stats["covers_impact"]:
            return False, "anchor_span", stats
        j = min(range(len(chain)), key=lambda k: abs(chain[k][0] - impact))
        stats["y_at_impact"] = round(chain[j][2], 3)
        if chain[j][2] < Y_TEE_MIN:
            return False, "anchor_height", stats
    if stats["rms"] is not None and stats["rms"] > RMS_MAX:
        return False, "shape_rms", stats
    # 反转否决只作用于非弹道形状;RMS 干净的链(过顶点抛物线)豁免
    if stats["max_dang"] > REVERSAL_DEG and (stats["rms"] or 0) > RMS_MAX:
        return False, "reversal", stats
    return True, "ok", stats

def select_chain(per_frame, impact, cfg):
    """单条 clip 归因。返回 (entry, champion|None)。
    identity 开启时:按优先级顺取第一条过身份闸的链,被毙的记入 entry["vetoed"]。"""
    n_blobs = sum(len(f) for f in per_frame)
    frames_hit = sum(1 for f in per_frame if f)
    entry = {"stage": None, "chain_pts": 0, "chain_disp": 0.0,
             "chain_span_frames": 0, "post_impact_pts": 0, "vetoed": []}
    if frames_hit < CHAIN_MIN or n_blobs < CHAIN_MIN:
        entry["stage"] = "NO_CANDIDATES"
        return entry, None
    linked = [c for c in build_chains(per_frame, cfg["step_max"], cfg["hop_max"],
                                      impact if cfg.get("impact_slack") else None)
              if len(c) >= 2]
    if not linked:
        entry["stage"] = "NO_CHAIN"
        return entry, None

    def key(c):
        ov = 1 if (cfg["impact_aware"] and impact is not None
                   and any(p[0] >= impact for p in c)) else 0
        return (ov, disp(c), len(c))

    champ = None
    for c in sorted(linked, key=key, reverse=True):
        if cfg.get("identity"):
            ok, why, st = identity_check(c, impact)
            if not ok:
                entry["vetoed"].append(
                    {"span": [c[0][0], c[-1][0]], "pts": len(c),
                     "disp": round(disp(c), 4), "reason": why,
                     "rms": None if st["rms"] is None else round(st["rms"], 4),
                     "max_dang": round(st["max_dang"], 1),
                     "covers": st["covers_impact"],
                     "y_at_impact": st.get("y_at_impact")})
                continue
        champ = c
        break
    entry["vetoed"] = entry["vetoed"][:5]
    if champ is None:
        entry["stage"] = "NOT_BALL"
        return entry, None
    entry.update(chain_pts=len(champ), chain_disp=round(disp(champ), 4),
                 chain_span_frames=champ[-1][0] - champ[0][0])
    if len(champ) < CHAIN_MIN or disp(champ) < DISP_MIN:
        entry["stage"] = "TOO_SHORT"
        return entry, champ
    gated = [p for p in champ if impact is None or p[0] >= impact]
    entry["post_impact_pts"] = len(gated)
    entry["stage"] = "OK" if len(gated) >= FIT_MIN else "IMPACT_GATE"
    return entry, champ

import functools
GATE_INIT=.15
GRAVITY=.004

REVERSAL_DEG = 90.0

DISP_PASS = 0.05

LOWM_DISP_MIN = 0.01

LOWM_RMS_MAX = 0.008

TELEPORT_K = 4.0

TELEPORT_ABS = 0.02

SEED_WIN_S = 0.27

ANCHOR_STEP_S = 0.5

SCAN_S = 3.0

MAX_LAUNCH_DELAY_S = 0.45

DISP_TIE = 0.005

def grow_sliding(per_frame, impact, fps, stride=1, tee_hint=None,
                 time_normalization=False):
    """规则1: 滑动播种。每个锚独立做锚定门控生长(复用 PC 的 grow_anchored),
    生长范围截到 anchor+3s。返回所有生长链(含跨锚重复,去重留给上层)。"""
    model_fps = fps / max(stride, 1)
    s = 20.0 / model_fps
    seed_hi = max(2, round(SEED_WIN_S * model_fps)) * stride
    step = max(2, round(ANCHOR_STEP_S * model_fps)) * stride
    scan = max(2, round(SCAN_S * model_fps)) * stride
    dt_max = max(2, round(DT_MAX * model_fps / 20.0)) * stride
    gate_init = GATE_INIT * s
    gravity = GRAVITY * s * s
    n = len(per_frame)
    chains = []
    a = max(0, impact)
    while a <= min(impact + scan, n - 1):
        for f0 in range(a, min(a + seed_hi, n - 1) + 1):
            for sx, sy, _, _ in per_frame[f0]:
                # TrackNetBallDetector.anchoredFlight tee seed gate.  Keep the
                # baseline raw-frame meaning unless the experiment flag is on.
                if tee_hint is not None:
                    raw_delta = max(0, f0 - impact)
                    df = (raw_delta * 20.0 / model_fps / max(stride, 1)
                          if time_normalization else raw_delta)
                    radius = 0.25 + 0.04 * df
                    if np.hypot(float(sx) - tee_hint[0],
                                float(sy) - tee_hint[1]) > radius:
                        continue
                ch = [[f0, float(sx), float(sy)]]
                i = f0 + 1
                while i < n:
                    if len(ch) >= 2:
                        dt0 = (ch[-1][0] - ch[-2][0]) / stride
                        vx = (ch[-1][1] - ch[-2][1]) / dt0
                        vy = (ch[-1][2] - ch[-2][2]) / dt0
                    else:
                        vx = vy = 0.0
                    found = None
                    for j in range(i, min(i + dt_max, n)):
                        dt = (j - ch[-1][0]) / stride
                        px = ch[-1][1] + vx * dt
                        py = ch[-1][2] + vy * dt + 0.5 * gravity * dt * dt
                        gate = gate_init if len(ch) < 2 else max(
                            0.02, np.hypot(vx, vy) * dt)
                        best = None
                        for cx, cy, _, _ in per_frame[j]:
                            d = np.hypot(cx - px, cy - py)
                            if d < gate and (best is None or d < best[0]):
                                best = (d, j, cx, cy)
                        if best is not None:
                            found = best
                            break
                    if found is None:
                        break
                    ch.append([found[1], float(found[2]), float(found[3])])
                    i = found[1] + 1
                chains.append(ch)
        a += step
    return chains

def split_reversals(chain, deg=REVERSAL_DEG):
    """规则2(端侧同步 v2):先摘单点抖动(seg i 反转但 i-1 与 i+1 同向——
    转码噪声/单点误检),只有摘不掉的结构性折返(球+头噪缝合,7bdd)才在
    首个 >deg 反转段处切开,两段各自为候选(递归到无反转)。高弧过顶点是
    连续转向(340ca ~90°),摘点后不切。<3 点的链不存在段间角,原样返回。"""
    if len(chain) < 3:
        return [chain]
    pts = [list(p) for p in chain]

    def dang(a, b):
        d = abs(a - b)
        return 2 * np.pi - d if d > np.pi else d

    def ang(a, b):
        return np.arctan2(b[2] - a[2], b[1] - a[1])

    i = 2
    while len(pts) >= 3 and i < len(pts) - 1:
        a1 = ang(pts[i - 2], pts[i - 1])
        a2 = ang(pts[i - 1], pts[i])
        a3 = ang(pts[i], pts[i + 1])
        if dang(a2, a1) > np.pi / 2 and dang(a3, a2) > np.pi / 2 and dang(a3, a1) <= np.pi / 2:
            pts.pop(i)
        else:
            i += 1
    if len(pts) < 3:
        return [pts]
    arr = np.array([[p[1], p[2]] for p in pts])
    seg = np.diff(arr, axis=0)
    a = np.arctan2(seg[:, 1], seg[:, 0])
    d = np.abs(np.diff(a))
    d = np.minimum(d, 2 * np.pi - d)
    hit = np.where(d > np.radians(deg))[0]
    if len(hit) == 0:
        return [pts]
    k = int(hit[0]) + 1
    return split_reversals(pts[:k + 1], deg) + split_reversals(pts[k + 1:], deg)

def teleport_veto(chain):
    """规则3: ≥4 点,每帧折算步长 max > 3×median 且 > 0.02 → True。"""
    if len(chain) < 4:
        return False
    steps = [float(np.hypot(b[1] - a[1], b[2] - a[2]) / (b[0] - a[0]))
             for a, b in zip(chain, chain[1:])]
    # Swift 端豁免首步（起飞首跳天然可能是全链最大）。
    mx = max(steps[1:]) if len(steps) > 1 else 0.0
    med = float(np.median(steps))
    return mx > TELEPORT_K * med and mx > TELEPORT_ABS

def identity_gate(pts_count, d, rms, dy=1.0, near_tee=False):
    """规则4(端侧同步): 返回 (ok, tag)。dy=链 |Δy|——重力判据,静止物 dy≈0。"""
    if pts_count < 3:
        return False, "veto:too_short"
    if dy < 0.005:
        return False, "veto:flat"
    disp_floor = LOWM_DISP_MIN if near_tee else DISP_PASS
    if d >= disp_floor:
        return True, "ok"
    if pts_count >= 5 and d >= disp_floor and rms is not None \
            and rms <= LOWM_RMS_MAX and dy >= 0.01:
        return True, "low_motion"
    return False, "veto:identity"

def champ_cmp(a, b):
    """规则5: 链长降 → 位移降(差>0.005 才分胜负) → rms 升。"""
    if a["pts"] != b["pts"]:
        return -1 if a["pts"] > b["pts"] else 1
    if abs(a["disp"] - b["disp"]) > DISP_TIE:
        return -1 if a["disp"] > b["disp"] else 1
    ra = a["rms"] if a["rms"] is not None else 9.9
    rb = b["rms"] if b["rms"] is not None else 9.9
    return (ra > rb) - (ra < rb)

def select_device(per_frame, impact, fps=20.0, stride=1, tee_hint=None,
                  time_normalization=False):
    """端侧新逻辑全链路。返回 (entry, champion|None),entry 结构与 PC 对齐。"""
    entry = {"stage": None, "chain_pts": 0, "chain_disp": 0.0,
             "chain_span_frames": 0, "post_impact_pts": 0, "fps": fps,
             "grown": 0, "segments": 0, "vetoed": []}
    model_fps = fps / max(stride, 1)
    fit_min = max(3, round(FIT_MIN * model_fps / 20.0))
    max_launch_delay = max(3, round(MAX_LAUNCH_DELAY_S * model_fps)) * stride
    grown = [c for c in grow_sliding(per_frame, impact, fps, stride,
                                     tee_hint=tee_hint,
                                     time_normalization=time_normalization)
             if len(c) >= 2]
    entry["grown"] = len(grown)
    if not grown:
        entry["stage"] = "NO_CHAIN"
        return entry, None
    elig, seen, fallback = [], set(), None

    def tee_gate(chain):
        if tee_hint is None:
            return True
        raw_delta = max(0, chain[0][0] - impact)
        df = (raw_delta * 20.0 / model_fps / max(stride, 1)
              if time_normalization else raw_delta)
        radius = 0.25 + 0.04 * df
        return np.hypot(chain[0][1] - tee_hint[0],
                        chain[0][2] - tee_hint[1]) <= radius

    def launch_consistent(chain):
        if tee_hint is None or len(chain) < 3:
            return True
        dt = (chain[-1][0] - chain[0][0]) / max(fps, 1e-6)
        if dt <= 0.05:
            return True
        vx = (chain[-1][1] - chain[0][1]) / dt
        vy = (chain[-1][2] - chain[0][2]) / dt
        if vy >= -0.01:
            return True
        launch_x = chain[0][1] + vx * ((tee_hint[1] - chain[0][2]) / vy)
        return abs(launch_x - tee_hint[0]) <= 0.15

    for c in grown:
        for seg in split_reversals(c):
            key = (seg[0][0], seg[-1][0], len(seg))
            if key in seen:
                continue
            seen.add(key)
            entry["segments"] += 1
            d = disp(seg)
            st = chain_shape(seg)
            rec = {"span": [seg[0][0], seg[-1][0]], "pts": len(seg),
                   "disp": round(d, 4),
                   "rms": None if st["rms"] is None else round(st["rms"], 4)}
            if not tee_gate(seg):
                entry["vetoed"].append({**rec, "reason": "far_from_tee"})
                continue
            if teleport_veto(seg):
                entry["vetoed"].append({**rec, "reason": "teleport"})
                continue
            if seg[0][0] - impact > max_launch_delay:
                entry["vetoed"].append({**rec, "reason": "late_launch"})
                continue
            if not launch_consistent(seg):
                entry["vetoed"].append({**rec, "reason": "launch_point"})
                continue
            if st["rms"] is not None and (fallback is None
                    or len(seg) > len(fallback["chain"])
                    or (len(seg) == len(fallback["chain"])
                        and st["rms"] < fallback["rms"])):
                fallback = {"chain": seg, "rms": st["rms"]}
            ok, tag = identity_gate(len(seg), d, st["rms"],
                                    abs(seg[-1][2] - seg[0][2]),
                                    near_tee=tee_hint is not None)
            if not ok:
                entry["vetoed"].append({**rec, "reason": tag})
                continue
            rec["tag"] = tag
            rec["chain"] = seg
            elig.append(rec)
    entry["vetoed"] = entry["vetoed"][:8]
    if not elig:
        fb = fallback
        if fb is None or not tee_gate(fb["chain"]) \
                or disp(fb["chain"]) < 0.01 or fb["rms"] > 0.008 \
                or abs(fb["chain"][-1][2] - fb["chain"][0][2]) < 0.01:
            entry["stage"] = "NOT_BALL"
            return entry, None
        champ = fb["chain"]
        entry["champ_tag"] = "fallback"
    else:
        elig.sort(key=functools.cmp_to_key(champ_cmp))
        champ = elig[0]["chain"]
        entry["champ_tag"] = elig[0]["tag"]
    entry.update(chain_pts=len(champ), chain_disp=round(disp(champ), 4),
                 chain_span_frames=champ[-1][0] - champ[0][0])
    gated = [p for p in champ if p[0] >= impact]
    entry["post_impact_pts"] = len(gated)
    entry["stage"] = "OK" if len(gated) >= fit_min else "IMPACT_GATE"
    return entry, champ
