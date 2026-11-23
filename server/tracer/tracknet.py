"""112 inference for the original GolfCut TrackNet weights, not a generic detector."""
import os
import cv2
cv2.setNumThreads(2)
import numpy as np
import onnxruntime as ort
from golf_chains import select_device

def analyze(path,impact,tee,progress=lambda p:None):
    c=cv2.VideoCapture(str(path),cv2.CAP_FFMPEG,[cv2.CAP_PROP_N_THREADS,2]);fps=c.get(cv2.CAP_PROP_FPS);frames=[]
    while True:
        ok,f=c.read()
        if not ok:break
        if len(frames)>901:raise ValueError('clip_too_long')
        frames.append(cv2.cvtColor(cv2.resize(f,(512,288)),cv2.COLOR_BGR2RGB))
    c.release()
    if len(frames)<8:return {'tracks':[],'fps':fps,'adapter':'golfcut-tracknet-v1'}
    model=os.environ.get('GOLFCUT_TRACKNET','/var/lib/swi-codex/web-tracer/models/GolfCut-TrackNet.onnx')
    settings=ort.SessionOptions();settings.intra_op_num_threads=2;settings.log_severity_level=3
    session=ort.InferenceSession(model,settings,providers=['CPUExecutionProvider'])
    med=np.median(np.stack(frames[::max(1,len(frames)//9)]),axis=0).transpose(2,0,1)/255
    per=[[] for _ in frames];imp=round(impact*fps)
    lo=max(0,imp-8);hi=min(len(frames),imp+max(30,round(fps*1.5)))
    starts=list(range(lo,max(lo+1,hi-7),8));starts.append(max(lo,hi-8));starts=sorted(set(starts))
    for n,start in enumerate(starts):
        window=frames[start:start+8]
        if len(window)<8:continue
        data=np.concatenate([med,*[f.transpose(2,0,1)/255 for f in window]],axis=0)[None].astype(np.float32)
        heat=session.run(None,{session.get_inputs()[0].name:data})[0][0]
        for j in range(8):
            mask=(heat[j]>.5).astype(np.uint8)
            count,labels,stats,_=cv2.connectedComponentsWithStats(mask,8)
            candidates=[]
            for k in range(1,count):
                x,y,w,h,area=stats[k];candidates.append([(x+w/2)/512,(y+h/2)/288,int(area),float(heat[j][labels==k].max())])
            per[start+j]=candidates
        progress((n+1)/len(starts))
    audit,chain=select_device(per,imp,fps=fps,tee_hint=tuple(tee),time_normalization=True)
    audit['candidate_chain']=chain
    tracks=[]
    if audit['stage']=='OK' and chain:
        tracks=[[dict(frame=f,time=f/fps,x=x,y=y,confidence=.5) for f,x,y in chain if f>=imp]]
    return dict(tracks=tracks,fps=fps,adapter='golfcut-tracknet-v1',audit=audit,impact=impact,tee=tee)
