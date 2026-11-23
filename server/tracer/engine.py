"""Bounded media handling and actual measured-trace rendering on 112."""
import hashlib,json,subprocess,sys
from pathlib import Path
import cv2
cv2.setNumThreads(2)
import numpy as np

def probe(path):
    raw=subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)],timeout=30)
    data=json.loads(raw);stream=next(x for x in data['streams'] if x['codec_type']=='video')
    duration=float(data['format']['duration'])
    if not 0 < duration <= 600 or max(stream['width'],stream['height'])>4096:raise ValueError('invalid_video')
    return dict(duration=duration,width=stream['width'],height=stream['height'])

def run(folder,app,task):
    start,end=task['trim'];target=folder/'trim.mp4'
    if not 0<=start<end or end-start>30.001:raise ValueError('invalid_range')
    subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-ss',str(start),'-i',str(folder/'source'),'-t',str(end-start),
       '-vf',"scale='min(1280,iw)':'min(720,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2,fps=30",'-c:a','aac',
       '-c:v','libx264','-threads','2','-preset','fast','-crf','18',str(target)],check=True,timeout=90)
    def progress(value):
        temp=folder/'progress.tmp';temp.write_text(json.dumps({'stage':'tracking','progress':15+int(60*value)}));temp.replace(folder/'progress.json')
    if app=='acecut':
        from tennis import analyze
        result=analyze(target,progress)
    else:
        from tracknet import analyze
        result=analyze(target,task['options']['impact'],task['options']['tee'],progress)
    (folder/'observations.json').write_text(json.dumps(result))
    if not result['tracks']:
        return {'state':'no_shots'}
    cap=cv2.VideoCapture(str(target),cv2.CAP_FFMPEG,[cv2.CAP_PROP_N_THREADS,2]);fps=cap.get(cv2.CAP_PROP_FPS);w=int(cap.get(3));h=int(cap.get(4))
    output=folder/'result.mp4'
    process=subprocess.Popen(['ffmpeg','-nostdin','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s',f'{w}x{h}',
      '-r',str(fps),'-i','pipe:0','-i',str(target),'-map','0:v','-map','1:a?','-c:v','libx264','-threads','2',
      '-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart','-shortest',str(output)],stdin=subprocess.PIPE)
    colors={'firework':(55,210,255),'ice':(255,225,80),'cosmic':(220,75,240),'sunset':(80,100,255)}
    color=colors[task['effect']];i=0
    try:
        while True:
            ok,image=cap.read()
            if not ok:break
            overlay=image.copy()
            for track in result['tracks']:
                points=[p for p in track if i/fps-.30<=p['time']<=i/fps]
                if len(points)<2:continue
                coords=np.array([[round(p['x']*w),round(p['y']*h)] for p in points],np.int32)
                cv2.polylines(overlay,[coords],False,color,max(2,round(w/260)),cv2.LINE_AA)
                cv2.circle(overlay,tuple(coords[-1]),max(2,round(w/200)),(255,255,255),-1,cv2.LINE_AA)
            image=cv2.addWeighted(overlay,.9,image,.1,0)
            process.stdin.write(image.tobytes());i+=1
        process.stdin.close()
        if process.wait(timeout=60):raise ValueError('render_failed')
    finally:
        cap.release()
        if process.poll() is None:process.kill();process.wait()
    info=probe(output)
    return dict(state='ready',render=dict(sha256=hashlib.sha256(output.read_bytes()).hexdigest(),duration=info['duration'],size_bytes=output.stat().st_size))

if __name__=='__main__':
    folder=Path(sys.argv[1]);task=json.loads((folder/'task.json').read_text())
    result=run(folder,sys.argv[2],task)
    (folder/'result.json').write_text(json.dumps(result))
