"""Read-only, reproducible Q2 imagery from the archived T=1 temporal study.

No relaxation, time stepping, interpolated time states or physical gate changes.
Scientific source: the existing SF physical-time/admitted temporal specifications.
Apache-2.0. AI-assisted renderer; generated imagery is derived evidence.
"""
import argparse,hashlib,io,json,platform,sys,time,zipfile
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from PIL import Image,ImageChops

HERE=Path(__file__).resolve().parent
INK='#18324a';MUTED='#52677a';BLUE='#2167a3';TEAL='#008777';PURPLE='#8b4fa8'
COLORS=[BLUE,TEAL,PURPLE]
BASE_ASSESSMENT='reports/s5-b/006-focused-motion-convergence/assessments/20261108t010058z-672ebb4c'
BASE_RUN='reports/s5-b/006-focused-motion-convergence/runs/20261106t212927z-589f5f5d'
SOURCE_EVIDENCE_SHA='9c57be7d19ef234e16f05fee517a8146ae71c5de20edb53d5dcb4fdec0f861d1'

def stamp():
    now=datetime.now(timezone.utc)
    return {'utc':now.isoformat(),'melbourne':now.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        while block:=f.read(8*1024**2):h.update(block)
    return h.hexdigest()

def event(message,**kw):print(json.dumps({'recorded_at':stamp(),'message':message,**kw}),flush=True)

def read_inputs(repo,cache,profile,specs):
    sys.path.insert(0,str(repo/'src'))
    from electron_field_topology.sf_higher_q_sources import recover
    from electron_field_topology.sf_time import Grid,densities
    from electron_field_topology.sf_time_run import state_sha,canonical_sha
    evidence=repo/BASE_RUN/'evidence.zip'
    if sha(evidence)!=SOURCE_EVIDENCE_SHA:raise ValueError('Compact source evidence differs')
    z=zipfile.ZipFile(evidence)
    if z.testzip() is not None:raise ValueError('Source compact ZIP CRC failure')
    campaign_bytes=z.read('campaign.json')
    if (repo/BASE_RUN/'campaign.json').read_bytes()!=campaign_bytes:raise ValueError('Published and compact campaign records differ')
    campaign=json.loads(campaign_bytes)
    manifests={};histories={}
    for case,row in campaign['cases'].items():
        if not case.startswith('q2-'):continue
        manifests[case]=json.loads(z.read('cases/'+case+'/attempt-000/manifest.json'))
        histories[case]=json.loads(z.read('cases/'+case+'/history-combined.json'))
        if row['status']!='complete' or len(histories[case])!=21:raise ValueError('Source Q2 trajectory incomplete')
        original=row['assessment']['legacy_motion']
        if len(original['checks'])!=7 or not all(original['checks'].values()):raise ValueError('Source Q2 original gate result differs')
        m=manifests[case]
        if canonical_sha(row['physical'])!=m['physics_sha256']:raise ValueError('Source physical configuration differs')
        for name,h in m['physics_source_sha256'].items():
            if sha(repo/'src/electron_field_topology'/name)!=h:raise ValueError('Measured numerical source differs '+name)
    fine=profile['fine_case'];physical=campaign['cases'][fine]['physical']
    grid=Grid(tuple(physical['grid']),tuple(physical['lengths']),'fixed')
    axes=[-l/2+np.arange(n)*h for n,l,h in zip(grid.shape,grid.lengths,grid.spacing)]
    slices=tuple(slice(int(np.searchsorted(a,-profile['core_zoom_half_width'])),int(np.searchsorted(a,profile['core_zoom_half_width'],side='right'))) for a in axes)
    states={};receipts=[];whole={}
    for spec in specs:
        path=recover(spec,cache,repo)
        case=spec['archive_path'].split('/')[2]
        native=manifests[case]
        with np.load(path,allow_pickle=False) as f:
            n=f['field'].copy();v=f['field_rate'].copy();t=float(f['time']);step=int(f['step'])
            if n.dtype!=np.float64 or v.dtype!=np.float64 or n.shape!=grid.shape+(3,) or v.shape!=n.shape:raise ValueError('Checkpoint precision/geometry differs')
            if str(f['model_id'])!=native['model_id'] or str(f['scheme'])!=native['scheme'] or str(f['physics_sha256'])!=native['physics_sha256'] or str(f['code_sha256'])!=native['code_sha256']:raise ValueError('Checkpoint source/model/config identity differs')
            if t!=step*physical['dt'] and case==fine:raise ValueError('Fine snapshot time differs')
            if not np.isfinite(n).all() or not np.isfinite(v).all():raise ValueError('Nonfinite source')
        unit=float(np.max(abs(np.linalg.norm(n,axis=-1)-1)));tangent=float(np.max(abs(np.sum(n*v,axis=-1))))
        mask=grid.fixed_mask()
        if unit>=1e-10 or tangent>=1e-10 or np.max(abs(n[mask]-[0,0,1]))>1e-12 or np.max(abs(v[mask]))>1e-12:raise ValueError('Source constraints or fixed boundary differ')
        state_digest=state_sha(n,v)
        row=campaign['cases'][case]
        if t==0 and state_digest!=row['initial_state_sha256']:raise ValueError('Admitted full state changed')
        if t==1 and state_digest!=row['result']['state_sha256']:raise ValueError('Final full state changed')
        receipt={'key':spec['key'],'archive_path':spec['archive_path'],'sha256':sha(path),'bytes':path.stat().st_size,'case_id':case,'time':t,'step':step,'state_sha256':state_digest,'unit_error':unit,'tangency_error':tangent}
        if case==fine:
            data=densities(n,v,grid);rho=data['energy_density'];volume=np.prod(grid.spacing)
            hist=next(r for r in histories[case] if abs(r['time']-t)<1e-12)
            measurements={'energy':float(np.sum(data['hamiltonian_density'])*volume),'continuum_energy':float(np.sum(rho)*volume),'momentum':(np.sum(data['energy_flux'],axis=(0,1,2))*volume).tolist()}
            for key,value in measurements.items():np.testing.assert_allclose(value,hist[key],rtol=2e-11,atol=2e-12)
            receipt['recomputed_diagnostics']=measurements
            states[t]={'n':n[slices].copy(),'rho':rho[slices].copy(),'flux':data['energy_flux'][slices].copy(),'time':t,'step':step,'history':hist,'state_sha256':state_digest}
            del data,rho
        if t==1:whole[case]=(n,v)
        receipts.append(receipt);event('Verified retained Q2 state',key=spec['key'],time=t,bytes=path.stat().st_size)
    if sorted(states)!=profile['snapshot_times']:raise ValueError('Exactly the five declared full-field times are required')
    fine_n,fine_v=whole[fine];norm_n=max(np.linalg.norm(fine_n-[0,0,1]),1e-30);norm_v=max(np.linalg.norm(fine_v),1e-30)
    pairs=[]
    for coarse_dt,fine_dt in [('0.01','0.005'),('0.005','0.0025')]:
        a=whole['q2-z-n127-L20.16-dt'+coarse_dt];b=whole['q2-z-n127-L20.16-dt'+fine_dt]
        pairs.append({'pair':coarse_dt+' vs '+fine_dt,'field_relative_l2':float(np.linalg.norm(a[0]-b[0])/norm_n),'rate_relative_l2':float(np.linalg.norm(a[1]-b[1])/norm_v)})
    orders={key:float(np.log2(pairs[0][key]/pairs[1][key])) for key in ['field_relative_l2','rate_relative_l2']}
    del whole
    return states,[a[s] for a,s in zip(axes,slices)],histories,receipts,{'whole_lab_grid_T1':pairs,'descriptive_orders':orders,'normalization':'Common finest-state full-domain norms; field minus north, rate unshifted. No fitted registration.'}

def mesh(state,axes,level):
    from electron_field_topology.sf_renderer import triangles
    origin=[a[0] for a in axes];spacing=[a[1]-a[0] for a in axes]
    rho=state['rho']
    boundary=max(float(np.max(np.take(rho,i,axis=k))) for k in range(3) for i in [0,-1])
    if boundary>=level:raise ValueError('Core zoom cuts the requested isosurface')
    tri,values=triangles(rho,state['n'][...,0],origin,spacing,level)
    if not len(tri):raise ValueError('Empty energy isosurface')
    return tri,values

def scene(ax,tri,values,profile,azimuth=None,decimate=False,title=None):
    if decimate and len(tri)>profile['animation_max_triangles']:
        take=np.linspace(0,len(tri)-1,profile['animation_max_triangles']).astype(int);tri=tri[take];values=values[take]
    cmap=plt.get_cmap('coolwarm');norm=Normalize(-1,1)
    ax.add_collection3d(Poly3DCollection(tri,facecolors=cmap(norm(values)),edgecolors='none',alpha=1,linewidth=0,zsort='average'))
    limit=profile['core_zoom_half_width']
    ax.set(xlim=(-limit,limit),ylim=(-limit,limit),zlim=(-limit,limit),xlabel='x',ylabel='y',zlabel='z')
    ax.set_box_aspect((1,1,1));ax.set_proj_type('ortho');ax.view_init(elev=profile['camera']['elevation'],azim=profile['camera']['azimuth'] if azimuth is None else azimuth)
    for axis in [ax.xaxis,ax.yaxis,ax.zaxis]:axis.pane.fill=False
    ax.tick_params(labelsize=8,pad=0)
    if title:ax.set_title(title,fontsize=12,color=INK,pad=3)
    return ScalarMappable(norm=norm,cmap=cmap)

def base_figure(profile,title,subtitle,created,animation=False):
    width,height=profile['animation_pixels'] if animation else profile['static_pixels'];dpi=100 if animation else 200
    fig=plt.figure(figsize=(width/dpi,height/dpi),dpi=dpi,facecolor='white')
    fig.text(.035,.942,title,fontsize=18 if animation else 24,weight='bold',color=INK)
    fig.text(.035,.899,subtitle,fontsize=9 if animation else 12,color=MUTED)
    fig.text(.035,.046,'Source: Q2/z • β=0.3 • lab 127×127×135 • L=20.16 • fixed reflecting boundary',fontsize=7 if animation else 10,color=MUTED)
    fig.text(.035,.025,'Derived '+created['utc']+' UTC / '+created['melbourne']+' Melbourne',fontsize=6.3 if animation else 8.5,color=MUTED)
    return fig

def save_static(fig,out,name,metadata):
    fig.savefig(out/name,facecolor='white',metadata={'Title':name,'Description':json.dumps(metadata,sort_keys=True)})
    plt.close(fig);event('Rendered high-resolution static',file=name)

def gif(images,out,name,durations,metadata,profile):
    palette=images[0].convert('RGB').quantize(colors=profile['gif_palette_colours'],method=Image.Quantize.MEDIANCUT)
    frames=[im.convert('RGB').quantize(palette=palette,dither=Image.Dither.NONE) for im in images]
    frames[0].save(out/name,save_all=True,append_images=frames[1:],duration=durations,loop=0,optimize=True,disposal=2,comment=json.dumps(metadata).encode())
    event('Rendered browser animation',file=name,frames=len(frames),bytes=(out/name).stat().st_size)

def frame(fig):
    buf=io.BytesIO();fig.savefig(buf,format='png',dpi=100,facecolor='white');plt.close(fig);buf.seek(0)
    return Image.open(buf).convert('RGB').copy()

def diagnostics_axes(fig,histories,refinement,cursor=None,animation=False):
    cases=['q2-z-n127-L20.16-dt'+s for s in ['0.01','0.005','0.0025']]
    axes=[fig.add_axes(rect) for rect in [[.08,.54,.37,.28],[.57,.54,.37,.28],[.08,.16,.37,.25],[.57,.16,.37,.25]]]
    for color,case in zip(COLORS,cases):
        rows=histories[case];t=np.array([r['time'] for r in rows]);energy=np.array([r['energy'] for r in rows]);e0=energy[0];z=np.array([r['centroid'][2] for r in rows])
        axes[0].plot(t,z-z[0],color=color,lw=1.8,label='dt='+case.split('dt')[-1])
        axes[1].plot(t,(energy/e0-1)*1e12,color=color,lw=1.5,label='dt='+case.split('dt')[-1])
        axes[2].plot(t,[100*r['boundary_tail']['fraction'] for r in rows],color=color,lw=1.8)
    axes[0].plot(t,.3*t,'--',color='#8a9aac',lw=1.2,label='prescribed βt')
    axes[0].set(title='Centroid displacement along z',ylabel='Δz (model units)',xlabel='Model time');axes[0].legend(fontsize=7 if animation else 10,loc='upper left')
    axes[1].set(title='Discrete Hamiltonian drift',ylabel='ΔH/H₀ × 10¹²',xlabel='Model time')
    axes[2].axhline(.1,ls='--',color='#ae5746',lw=1.2,label='original 0.1% gate');axes[2].set(title='Width-2 shell-energy fraction',ylabel='Percent',xlabel='Model time',ylim=(0,.11));axes[2].legend(fontsize=7 if animation else 10)
    pairs=refinement['whole_lab_grid_T1'];x=np.arange(2);w=.34
    axes[3].bar(x-w/2,[r['field_relative_l2'] for r in pairs],width=w,color=BLUE,label='field')
    axes[3].bar(x+w/2,[r['rate_relative_l2'] for r in pairs],width=w,color=TEAL,label='field rate')
    axes[3].set_yscale('log');axes[3].set_xticks(x,['0.01 ↔ 0.005','0.005 ↔ 0.0025']);axes[3].set(title='Whole-grid temporal differences at T=1',ylabel='Relative L² difference')
    axes[3].legend(fontsize=7 if animation else 10)
    for ax in axes:
        ax.grid(alpha=.17);ax.set_axisbelow(True);ax.tick_params(labelsize=8 if animation else 11)
    if cursor is not None:
        for ax in axes[:3]:ax.axvline(cursor,color='#273e53',lw=1.1)
    return axes

def render_all(states,axes,histories,refinement,out,profile,created):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.labelcolor':INK,'axes.titlecolor':INK,'text.color':INK})
    maximum=max(float(s['rho'].max()) for s in states.values());level=maximum*profile['iso_fraction_of_all_snapshot_maximum']
    meshes={t:mesh(s,axes,level) for t,s in states.items()}
    for t,(tri,_) in meshes.items():event('Extracted native-grid display surface',time=t,triangles=len(tri),iso_level=level)
    final=states[1.];tri,values=meshes[1.]
    fig=base_figure(profile,'Q2 — structure and internal field','Finest saved trajectory at T=1 • dt=0.0025 • energy isosurface coloured by internal component n₁',created)
    ax=fig.add_axes([.025,.17,.46,.65],projection='3d');sm=scene(ax,tri,values,profile,title='Energy isosurface • core zoom')
    cb=fig.colorbar(sm,ax=ax,fraction=.025,pad=.04,shrink=.7);cb.set_label('Internal field n₁ (not velocity)',fontsize=10)
    for rect,dim,title in [([.57,.53,.34,.28],2,'Energy density: central x–y slice'),([.57,.17,.34,.28],0,'Energy density and in-plane flux: y–z slice')]:
        a=fig.add_axes(rect);mid=len(axes[dim])//2;rho=np.take(final['rho'],mid,axis=dim);remain=[i for i in range(3) if i!=dim]
        im=a.imshow(rho.T,origin='lower',extent=[axes[remain[0]][0],axes[remain[0]][-1],axes[remain[1]][0],axes[remain[1]][-1]],cmap='magma',vmin=0,vmax=maximum,aspect='equal')
        a.set(title=title,xlabel='xyz'[remain[0]]+' (model units)',ylabel='xyz'[remain[1]]+' (model units)');fig.colorbar(im,ax=a,fraction=.03,pad=.025,label='Continuum energy density')
        if dim==0:
            flux=np.take(final['flux'],mid,axis=dim);skip=4;u=flux[::skip,::skip,remain[0]];v=flux[::skip,::skip,remain[1]];mag=np.sqrt(u*u+v*v);active=mag>.03*np.max(mag)
            xx,yy=np.meshgrid(axes[remain[0]][::skip],axes[remain[1]][::skip],indexing='ij')
            a.quiver(xx[active],yy[active],u[active],v[active],color='#50d0bf',angles='xy',scale_units='xy',scale=max(np.max(mag)*4,1e-30),width=.004)
    fig.text(.035,.095,f'Isosurface: fixed 30% of the largest saved energy density. Core zoom ±{profile["core_zoom_half_width"]:g}; full diagnostic box is unchanged. Flux arrows are scaled for display.',fontsize=10,color=MUTED)
    save_static(fig,out,'q2-structure-4k.png',{'view':'static_structure','time':1,'source_state_sha256':final['state_sha256'],'created':created})
    fig=base_figure(profile,'Q2 — five recorded physical-time states','Same camera, physical scale, energy threshold and field colour scale in every panel • no temporal interpolation',created)
    for i,t in enumerate(profile['snapshot_times']):
        ax=fig.add_axes([.015+i*.198,.36,.188,.45],projection='3d');scene(ax,*meshes[t],profile,title=f't = {t:.2f}')
        fig.text(.050+i*.198,.355,'step '+str(states[t]['step']),fontsize=11,color=MUTED)
    rows=histories[profile['fine_case']];t=np.array([r['time'] for r in rows]);z=np.array([r['centroid'][2] for r in rows]);energy=np.array([r['energy'] for r in rows]);e0=energy[0]
    a=fig.add_axes([.07,.14,.39,.14]);a.plot(t,z-z[0],color=BLUE,lw=2,label='recorded centroid');a.plot(t,.3*t,'--',color='#8795a4',label='prescribed βt');a.set(xlabel='Model time',ylabel='Δz',title='Translation is small but measurable');a.grid(alpha=.2);a.legend(fontsize=9)
    b=fig.add_axes([.58,.14,.35,.14]);b.plot(t,(energy/e0-1)*1e15,color=PURPLE,lw=1.7);b.set(xlabel='Model time',ylabel='ΔH/H₀ × 10¹⁵',title='Finest-dt energy drift is near round-off');b.grid(alpha=.2)
    save_static(fig,out,'q2-recorded-motion-4k.png',{'view':'recorded_physical_samples','times':profile['snapshot_times'],'created':created})
    fig=base_figure(profile,'Q2 — motion and temporal-refinement diagnostics','Three time steps on one fixed lab grid • existing original gates retained • temporal refinement is not spatial/domain convergence',created)
    diagnostics_axes(fig,histories,refinement)
    fig.text(.08,.095,'Finest-dt fitted speed: 0.297458764 vs β=0.3 (0.8471% error). All seven original Q2 case gates pass in the recorded T=1 window.',fontsize=11,color=MUTED)
    save_static(fig,out,'q2-diagnostics-4k.png',{'view':'diagnostic_summary','source_observations_per_case':21,'created':created})
    # An internal-field core proxy is distinct from an energy-density contour.
    core_level=profile['core_field_component_3_isovalue']
    core_tri,core_values=mesh({'rho':-final['n'][...,2],'n':final['n']},axes,-core_level)
    fig=base_figure(profile,'Q2 — core geometry and energy envelope','Two different surfaces from the same saved field at T=1 • neither is a particle trajectory',created)
    a=fig.add_axes([.025,.16,.43,.66],projection='3d');scene(a,core_tri,core_values,profile,title=f'Core proxy: n₃ = {core_level:g}')
    b=fig.add_axes([.51,.16,.43,.66],projection='3d');sm=scene(b,tri,values,profile,title='Energy isosurface: 30% of saved peak')
    cb=fig.colorbar(sm,ax=b,fraction=.025,pad=.02,shrink=.7);cb.set_label('Internal field n₁',fontsize=10)
    fig.text(.035,.105,'The near-south-pole field surface reveals the ring core. Energy contours have their own geometry and do not identify core knot type.',fontsize=11,color=MUTED)
    save_static(fig,out,'q2-core-and-energy-4k.png',{'view':'core_and_energy_comparison','time':1,'core_component_3_level':core_level,'energy_level':level,'created':created})
    # Camera-only motion around a single measured state.
    images=[]
    for i,angle in enumerate(np.linspace(-53,307,profile['orbit_frames'],endpoint=False)):
        fig=base_figure(profile,'Q2 — camera orbit around one saved state','Field time fixed at T=1 • only the camera moves • this is not physical rotation',created,True)
        ax=fig.add_axes([.01,.16,.45,.66],projection='3d');scene(ax,core_tri,core_values,profile,azimuth=float(angle),decimate=True,title=f'Core proxy: n₃ = {core_level:g}')
        ax=fig.add_axes([.49,.16,.43,.66],projection='3d');sm=scene(ax,tri,values,profile,azimuth=float(angle),decimate=True,title='Energy: 30% of saved peak')
        cb=fig.colorbar(sm,ax=ax,fraction=.025,pad=.025,shrink=.65);cb.set_label('Internal field n₁',fontsize=8)
        fig.text(.035,.095,'Same measured state, two different surfaces. 48 camera views; physical time remains T=1 throughout.',fontsize=8,color=MUTED)
        images.append(frame(fig))
    gif(images,out,'q2-camera-orbit.gif',round(1000/profile['orbit_fps']),{'view':'camera_orbit_only','physical_times':[1.],'frames':profile['orbit_frames'],'source_state_sha256':final['state_sha256'],'created':created},profile)
    images=[]
    for t in profile['snapshot_times']:
        fig=base_figure(profile,'Q2 — recorded physical motion',f't = {t:.2f} model units • step {states[t]["step"]} • one of five saved full-field states',created,True)
        ax=fig.add_axes([.035,.15,.48,.67],projection='3d');scene(ax,*meshes[t],profile,decimate=True)
        a=fig.add_axes([.61,.47,.31,.33]);middle=len(axes[0])//2;rho=states[t]['rho'][middle]
        a.imshow(rho.T,origin='lower',extent=[axes[1][0],axes[1][-1],axes[2][0],axes[2][-1]],cmap='magma',vmin=0,vmax=maximum,aspect='equal');a.set(title='Central y–z energy slice',xlabel='y',ylabel='z');a.tick_params(labelsize=8)
        a=fig.add_axes([.61,.18,.31,.16]);a.plot([r['time'] for r in rows],[r['centroid'][2]-rows[0]['centroid'][2] for r in rows],color=BLUE);a.axvline(t,color=INK);a.set(xlabel='Model time',ylabel='Δz');a.tick_params(labelsize=8);a.grid(alpha=.2)
        fig.text(.035,.09,'Five actual samples at t=0, 0.25, 0.5, 0.75, 1. No invented intermediate fields. Playback loops back to t=0.',fontsize=8,color=MUTED)
        images.append(frame(fig))
    gif(images,out,'q2-recorded-motion.gif',profile['motion_frame_milliseconds'],{'view':'recorded_physical_samples','physical_times':profile['snapshot_times'],'temporal_interpolation':False,'created':created},profile)
    images=[]
    for t in [r['time'] for r in rows]:
        fig=base_figure(profile,'Q2 — diagnostic replay',f'Cursor at t = {t:.2f} model units • 21 retained observations • no intermediate full fields implied',created,True)
        diagnostics_axes(fig,histories,refinement,cursor=t,animation=True)
        images.append(frame(fig))
    gif(images,out,'q2-diagnostic-replay.gif',profile['diagnostic_frame_milliseconds'],{'view':'diagnostic_observations','model_times':[r['time'] for r in rows],'full_field_animation':False,'created':created},profile)
    return {'core_proxy_component_3_isovalue':core_level,'core_proxy_triangles':len(core_tri),'fixed_energy_isosurface':level,'maximum_saved_energy_density':maximum,'source_grid':[127,127,135],'native_core_grid':[len(a) for a in axes],'static_triangles':{str(t):len(m[0]) for t,m in meshes.items()},'animation_max_triangles':profile['animation_max_triangles']}

def validate_media(out,profile):
    result={}
    for p in sorted(out.glob('*.png')):
        with Image.open(p) as im:
            im.verify()
        with Image.open(p) as im:
            if list(im.size)!=profile['static_pixels']:raise ValueError('Wrong static resolution')
            result[p.name]={'bytes':p.stat().st_size,'sha256':sha(p),'pixels':list(im.size),'format':im.format}
    expected={'q2-camera-orbit.gif':profile['orbit_frames'],'q2-recorded-motion.gif':5,'q2-diagnostic-replay.gif':21}
    for name,count in expected.items():
        p=out/name
        with Image.open(p) as im:
            if im.n_frames!=count or list(im.size)!=profile['animation_pixels'] or im.info.get('loop')!=0:raise ValueError('GIF dimensions/frame count/loop mismatch')
            durations=[]
            for i in range(im.n_frames):im.seek(i);im.load();durations.append(im.info['duration'])
            im.seek(0);first=im.convert('RGB').copy();im.seek(count//2);middle=im.convert('RGB').copy()
            if ImageChops.difference(first,middle).getbbox() is None:raise ValueError('Animation frames are identical')
            result[name]={'bytes':p.stat().st_size,'sha256':sha(p),'pixels':list(im.size),'format':'GIF','frames':count,'durations_ms':durations,'loop':0,'decoded_all_frames':True}
        if p.stat().st_size>10*1024**2:raise ValueError('Browser GIF exceeds declared 10 MiB budget')
    if len(result)!=7:raise ValueError('Expected four high-resolution statics and three animations')
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,required=True);parser.add_argument('--cache',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();repo=a.repo.resolve();out=a.output.resolve();start=time.monotonic();created=stamp()
    if out.exists() and any(out.iterdir()):raise ValueError('Use a new empty imagery output directory; published evidence is immutable')
    out.mkdir(parents=True,exist_ok=True);profile=json.loads((HERE/'render-profile.json').read_text());specs=json.loads((HERE/'source-selection.json').read_text())
    states,axes,histories,receipts,refinement=read_inputs(repo,a.cache,profile,specs)
    render=render_all(states,axes,histories,refinement,out,profile,created);media=validate_media(out,profile)
    import scipy,PIL
    result={'recorded_at':created,'finished_at':stamp(),'status':'rendered_and_checked','source_run':profile['source_run'],'native_source_commit':profile['source_commit'],'source_release':profile['source_release'],'source_evidence_sha256':SOURCE_EVIDENCE_SHA,'script_sha256':sha(Path(__file__)),'profile_sha256':sha(HERE/'render-profile.json'),'selection_sha256':sha(HERE/'source-selection.json'),'environment':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,'matplotlib':matplotlib.__version__,'pillow':PIL.__version__},'read_only_source_checks':receipts,'whole_grid_T1_refinement':refinement,'rendering':render,'media':media,'wall_seconds':time.monotonic()-start,'scope':'Derived visualizations only; no new dynamics, relaxation or changed scientific acceptance. Five physical snapshots are distinct from 48 camera views and 21 diagnostic observations.'}
    (out/'render-verification.json').write_text(json.dumps(result,indent=2)+'\n');event('Gallery rendering complete',output=str(out),media_bytes=sum(v['bytes'] for v in media.values()),wall_seconds=result['wall_seconds'])

if __name__=='__main__':main()
