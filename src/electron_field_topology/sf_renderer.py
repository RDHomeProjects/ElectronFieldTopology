"""Standalone offline renderer for EFT-preview-v1. Never imports the time solver."""
import argparse
import base64
import html
import io
import json
from pathlib import Path
import time
import numpy as np
from .sf_checkpoints import atomic_json,timestamp
from .sf_dynamics_admission import sha
from .sf_preview import resample


def presentation_settings(profile):
    cfg={'frame_stride':1,'max_frames':40,'grid':None,'colors':16,'colormap':'viridis',
         'color_field':'field','component':0,'iso_fraction':.3,'fps':10,
         'elevation':24.,'azimuth':-55.,'width':1100,'height':650,'max_triangles':12000,
         **profile.get('presentation',{})}
    allowed={'frame_stride','max_frames','grid','colors','colormap','color_field','component','iso_fraction',
             'fps','elevation','azimuth','width','height','max_triangles'}
    if set(cfg)-allowed:raise ValueError('Unknown renderer presentation setting')
    for key in ('frame_stride','max_frames','fps','width','height','max_triangles'):
        if type(cfg[key]) is not int or cfg[key]<1:raise ValueError('Positive integer '+key+' required')
    if type(cfg['colors']) is not int or cfg['colors'] not in (0,*range(2,257)):
        raise ValueError('Color count is 0 (continuous), or 2..256 field palette levels')
    if type(cfg['component']) is not int or cfg['component'] not in (0,1,2):raise ValueError('Component 0..2 required')
    if not np.isfinite(cfg['iso_fraction']) or not 0<cfg['iso_fraction']<1:raise ValueError('Isosurface fraction must be between 0 and 1')
    if cfg['grid'] is not None and (len(cfg['grid'])!=3 or any(type(n) is not int or n<1 for n in cfg['grid'])):
        raise ValueError('Three positive display dimensions required')
    return cfg


def triangles(values, colors, origin, spacing, level):
    """Display-only marching tetrahedra; linear vertex/color interpolation."""
    if min(values.shape)<2:return np.empty((0,3,3)),np.empty(0)
    corners=np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]])
    tets=((0,1,2,6),(0,2,3,6),(0,3,7,6),(0,7,4,6),(0,4,5,6),(0,5,1,6))
    base=np.indices(tuple(n-1 for n in values.shape)).reshape(3,-1).T
    indices=base[:,None,:]+corners[None,:,:]
    val=values[indices[...,0],indices[...,1],indices[...,2]]
    col=colors[indices[...,0],indices[...,1],indices[...,2]]
    coordinates=np.asarray(origin)+indices*np.asarray(spacing)
    output=[];palette=[]
    for tet in tets:
        v=val[:,tet];c=col[:,tet];xyz=coordinates[:,tet]
        active=np.flatnonzero((v.min(axis=1)<level)&(v.max(axis=1)>=level))
        for index in active:
            points=[];scalars=[]
            for i,j in ((0,1),(0,2),(0,3),(1,2),(1,3),(2,3)):
                if (v[index,i]<level)!=(v[index,j]<level):
                    fraction=(level-v[index,i])/(v[index,j]-v[index,i])
                    points.append(xyz[index,i]+fraction*(xyz[index,j]-xyz[index,i]))
                    scalars.append(c[index,i]+fraction*(c[index,j]-c[index,i]))
            if len(points) not in (3,4):continue
            pts=np.array(points);cs=np.array(scalars)
            if len(points)==4:
                centre=pts.mean(axis=0);e1=pts[0]-centre
                normal=np.cross(pts[1]-pts[0],pts[2]-pts[0]);size=np.linalg.norm(normal)
                if size<1e-14:continue
                e1/=np.linalg.norm(e1);e2=np.cross(normal/size,e1)
                order=np.argsort(np.arctan2((pts-centre)@e2,(pts-centre)@e1));pts=pts[order];cs=cs[order]
            for i in range(1,len(pts)-1):
                output.append(pts[[0,i,i+1]]);palette.append(float(cs[[0,i,i+1]].mean()))
    return np.asarray(output).reshape(-1,3,3),np.asarray(palette)


def render(input_path, output, profile=None, colors=None):
    """Read completed preview records; emit a GIF and a representative PNG."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.animation import PillowWriter
    from matplotlib.colors import Normalize
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    started=timestamp();clock=time.monotonic();source=Path(input_path).resolve()
    if source.is_file():source=source.parent
    manifest=json.loads((source/'manifest.json').read_text()) if (source/'manifest.json').is_file() else {}
    if manifest.get('format')!='EFT-preview-v1' and (source/'preview/manifest.json').is_file():
        source=source/'preview';manifest=json.loads((source/'manifest.json').read_text())
    if manifest.get('format')!='EFT-preview-v1' or not manifest.get('frames'):
        raise ValueError('A nonempty EFT-preview-v1 dataset is required')
    cfg=presentation_settings(profile if profile is not None else {'presentation':manifest.get('presentation',{})})
    if colors is not None:cfg['colors']=colors;cfg=presentation_settings({'presentation':cfg})
    selected=manifest['frames'][::cfg['frame_stride']]
    if len(selected)>cfg['max_frames']:
        selected=[selected[i] for i in np.unique(np.linspace(0,len(selected)-1,cfg['max_frames']).round().astype(int))]
    shape=tuple(cfg['grid'] or manifest['display_grid'])
    if any(m>n for m,n in zip(shape,manifest['display_grid'])):
        raise ValueError('Display sampling cannot exceed the saved preview resolution')
    lengths=[h*(n if manifest['boundary']=='periodic' or n==1 else n-1)
             for h,n in zip(manifest['spacing'],manifest['display_grid'])]
    spacing=[l/(m if manifest['boundary']=='periodic' or m==1 else max(1,m-1)) for l,m in zip(lengths,shape)]
    def load(row):
        filename=Path(row['npz'])
        if filename.is_absolute() or len(filename.parts)!=1:raise ValueError('Unexpected frame path')
        path=source/filename
        if sha(path)!=row['npz_sha256']:raise ValueError('Preview frame SHA-256 mismatch')
        with np.load(path,allow_pickle=False) as data:
            if 'energy_density' not in data or cfg['color_field'] not in data:raise ValueError('Requested fields were not exported')
            energy=resample(data['energy_density'],shape,manifest['boundary'])
            values=resample(data[cfg['color_field']],shape,manifest['boundary'])
            if values.ndim==4:values=values[...,cfg['component']]
            if not np.isfinite(energy).all() or not np.isfinite(values).all():raise ValueError('Nonfinite preview values')
            return energy,values
    lower=np.inf;upper=-np.inf;max_energy=0.
    for row in selected:
        energy,values=load(row);lower=min(lower,float(values.min()));upper=max(upper,float(values.max()));max_energy=max(max_energy,float(energy.max()))
    if lower==upper:lower-=.5;upper+=.5
    level=cfg['iso_fraction']*max_energy;normalization=Normalize(lower,upper)
    cmap=plt.get_cmap(cfg['colormap'],cfg['colors'] or None)
    out=Path(output)
    if out.exists() and any(out.iterdir()):raise ValueError('Use a new or empty renderer output directory')
    out.mkdir(parents=True,exist_ok=True)
    fig=plt.figure(figsize=(cfg['width']/100,cfg['height']/100),dpi=100,facecolor='#f7f9fc')
    ax3=fig.add_axes([.025,.19,.46,.65],projection='3d')
    ax2=fig.add_axes([.58,.46,.32,.34]);axm=fig.add_axes([.58,.18,.32,.16])
    header=fig.text(.035,.94,'Neutral SF physical-time solver: recorded numerical evolution',fontsize=14,weight='bold')
    label=fig.text(.035,.885,'',fontsize=10)
    origin=manifest['origin'];xlast=[o+(n-1)*h for o,n,h in zip(origin,shape,spacing)]
    times=np.array([f['time'] for f in manifest['frames']]);measure=[f['diagnostics'] for f in manifest['frames']]
    e0=measure[0]['energy'];e=np.array([f['energy'] for f in measure]);p=np.array([f['momentum'] for f in measure])
    scale=max(abs(e0),1e-30);axm.plot(times,(e-e0)/scale,label='discrete energy change / E0',color='#1d4ed8')
    axm.plot(times,np.linalg.norm(p-p[0],axis=1)/scale,label='momentum change / E0',color='#b45309')
    cursor=axm.axvline(times[0],color='#334155',lw=1)
    axm.set_xlabel('Simulation time (model units)',fontsize=8);axm.tick_params(labelsize=7);axm.grid(alpha=.2)
    axm.legend(fontsize=7,loc='upper left');axm.ticklabel_format(axis='y',style='sci',scilimits=(-2,2))
    image=ax2.imshow(np.zeros(shape[:2]).T,origin='lower',extent=[origin[0],xlast[0] or 1,origin[1],xlast[1] or 1],
                     cmap=cmap,norm=normalization,aspect='auto',interpolation='nearest')
    fig.colorbar(image,ax=ax2,fraction=.05,pad=.03).set_label(cfg['color_field']+'['+str(cfg['component'])+']',fontsize=8)
    ax2.set(title='Central z slice',xlabel='x (model units)',ylabel='y (model units)');ax2.tick_params(labelsize=8)
    source_start=manifest['provenance']['started_at']
    fig.text(.035,.085,'Source run: '+source_start['utc']+' UTC  |  '+source_start['melbourne']+' Melbourne',fontsize=7,color='#475569')
    fig.text(.035,.05,'Rendered: '+started['utc']+' UTC  |  '+started['melbourne']+' Melbourne',fontsize=7,color='#475569')
    fig.text(.035,.02,'Preview only. Fixed colour scale and energy contour. No electron or knot-stability claim.',fontsize=8,color='#475569')
    movie=out/'wave.gif';writer=PillowWriter(fps=cfg['fps']);frame_metadata=[];browser_frames=[]
    with writer.saving(fig,str(movie),dpi=100):
        for number,row in enumerate(selected):
            energy,values=load(row);tri,face=triangles(energy,values,origin,spacing,level)
            if len(tri)>cfg['max_triangles']:
                choose=np.linspace(0,len(tri)-1,cfg['max_triangles']).astype(int);tri=tri[choose];face=face[choose]
            ax3.clear()
            if len(tri):
                collection=Poly3DCollection(tri,facecolors=cmap(normalization(face)),edgecolors='none',alpha=.88)
                ax3.add_collection3d(collection)
            else:ax3.text2D(.2,.5,'No energy isosurface at this threshold',transform=ax3.transAxes,fontsize=9)
            for setter,a,b in [(ax3.set_xlim,origin[0],xlast[0]),(ax3.set_ylim,origin[1],xlast[1]),(ax3.set_zlim,origin[2],xlast[2])]:
                setter(a,b if b>a else a+1)
            ax3.view_init(elev=cfg['elevation'],azim=cfg['azimuth']);ax3.set_box_aspect([max(1e-3,b-a) for a,b in zip(origin,xlast)])
            ax3.set(xlabel='x',ylabel='y',zlabel='z',title='Energy isosurface coloured by internal field')
            ax3.tick_params(labelsize=7)
            image.set_data(values[:,:,shape[2]//2].T);cursor.set_xdata([row['time'],row['time']])
            label.set_text(f"{manifest['case_id']}  |  t={row['time']:.5f} model units  |  step {row['step']}  |  "
                           f"solver {manifest['source_grid']} → preview {list(shape)}  |  {cfg['colors'] or 'continuous'} colours")
            writer.grab_frame()
            buffer=io.BytesIO();fig.savefig(buffer,format='png',dpi=100,facecolor=fig.get_facecolor())
            browser_frames.append({'step':row['step'],'time':row['time'],
                'image':'data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode('ascii')})
            if number==len(selected)//2:fig.savefig(out/'preview.png',dpi=100,facecolor=fig.get_facecolor())
            frame_metadata.append({'step':row['step'],'time':row['time'],'source_frame_sha256':row['npz_sha256'],'triangles':len(tri)})
    plt.close(fig)
    payload=json.dumps(browser_frames,separators=(',',':')).replace('<','\\u003c')
    viewer='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Neutral SF solver replay</title><style>
body{margin:0;background:#e8edf4;color:#15243b;font:16px system-ui,sans-serif}main{max-width:1160px;margin:24px auto;padding:20px;background:white;border-radius:12px;box-shadow:0 8px 32px #172f5018}
h1{font-size:22px;margin:0 0 6px}p{color:#52637a;line-height:1.45}.controls{display:flex;gap:14px;align-items:center;flex-wrap:wrap;padding:12px 0}button,select{font:inherit;padding:7px 14px;border:1px solid #becbdc;border-radius:6px;background:#f3f6fb;color:#15243b}input{flex:1;min-width:160px}img{display:block;width:100%;height:auto;border:1px solid #dae2ed;border-radius:6px}.small{font-size:13px}output{font-variant-numeric:tabular-nums}
</style><main><h1>Neutral SF physical-time solver: offline replay</h1><p>CASE_NAME · Solver-generated data. Display samples are separate from scientific checkpoints.</p>
<div class="controls"><button id="play">Play</button><button id="previous" aria-label="Previous frame">Previous</button><button id="next">Next</button><input id="frame" aria-label="Simulation frame" type="range" min="0" value="0"><select id="speed" aria-label="Playback speed"><option value="0.5">0.5×</option><option value="1" selected>1×</option><option value="2">2×</option></select><output id="clock"></output></div>
<img id="scene" alt="Energy isosurface, internal-field slice and conservation diagnostics"><p class="small">Playback speed is a viewing setting. Simulation time is in model units, not measured electron seconds. Camera, palette and sampling can be changed by rerendering the same data. Open series.pvd in ParaView for interactive 3D exploration.</p>
<p class="small">UTC_STAMP UTC / MELBOURNE_STAMP Australia/Melbourne</p></main><script id="frames" type="application/json">FRAME_DATA</script><script>
const frames=JSON.parse(document.getElementById('frames').textContent),slider=document.getElementById('frame'),scene=document.getElementById('scene'),clock=document.getElementById('clock'),play=document.getElementById('play');
slider.max=frames.length-1;let timer=null;function show(i){i=(Number(i)+frames.length)%frames.length;slider.value=i;scene.src=frames[i].image;clock.textContent='Frame '+(i+1)+'/'+frames.length+' · t='+frames[i].time.toFixed(5)+' · step '+frames[i].step;}
function pause(){if(timer!==null)clearInterval(timer);timer=null;play.textContent='Play';}function start(){pause();play.textContent='Pause';timer=setInterval(()=>show(Number(slider.value)+1),1000/(FPS*Number(document.getElementById('speed').value)));}
play.onclick=()=>timer===null?start():pause();slider.oninput=()=>{pause();show(slider.value);};document.getElementById('next').onclick=()=>{pause();show(Number(slider.value)+1);};document.getElementById('previous').onclick=()=>{pause();show(Number(slider.value)-1);};document.getElementById('speed').onchange=()=>{if(timer!==null)start();};document.addEventListener('visibilitychange',()=>{if(document.hidden)pause();});show(0);
</script></html>'''
    viewer=viewer.replace('FPS',str(cfg['fps'])).replace('CASE_NAME',html.escape(manifest['case_id'])).replace('UTC_STAMP',html.escape(started['utc'])).replace('MELBOURNE_STAMP',html.escape(started['melbourne'])).replace('FRAME_DATA',payload)
    (out/'viewer.html').write_text(viewer)
    result={'started_at':started,'finished_at':timestamp(),'source_manifest_sha256':sha(source/'manifest.json'),
            'presentation':cfg,'frames':frame_metadata,'fixed_color_range':[lower,upper],'fixed_energy_isosurface':level,
            'wall_seconds':time.monotonic()-clock,'outputs':{'wave.gif':sha(movie),'preview.png':sha(out/'preview.png'),'viewer.html':sha(out/'viewer.html')},
            'scope':'Basic offline visualization of display samples. Internal field direction is not particle velocity.'}
    atomic_json(out/'render.json',result);print(json.dumps({k:result[k] for k in ('finished_at','wall_seconds','scope')},indent=2))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--profile',type=Path);p.add_argument('--colors',type=int)
    a=p.parse_args();render(a.input,a.output,json.loads(a.profile.read_text()) if a.profile else None,a.colors)


if __name__=='__main__':main()
