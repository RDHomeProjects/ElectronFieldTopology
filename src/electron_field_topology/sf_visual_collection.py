"""Additive retained-field visual explanations. No solver stepping or relaxation.

Apache-2.0. Derived displays never amend scientific gates or source fields.
"""
import base64
import csv
import hashlib
import html
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import textwrap
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import numpy as np

VERSION = 'EFT-visual-collection-v1'
COLOR_RANGE = (-1., 1.)
TARGET = (.000007, .000011, -1.)
EXPLAIN = '''The internal unit vector n maps each spatial point to an internal sphere; it is not electromagnetic B or material velocity. The surface is a threshold of D4-derived continuum energy density, not the original cell/Gauss density and not automatically a knot core. A selected-target preimage curve follows points with the same internal direction; failed extraction stays unresolved. Axes and boxes use dimensionless model length. Q labels a Hopf sector, not one unique shape, electric charge or quantum spin. Pixel resolution does not refine the numerical grid. A pleasing geometry, falling energy or low residual does not prove physical stability, isolated motion or an electron model.'''


def stamp():
    now = datetime.now(timezone.utc)
    return {'utc': now.isoformat(), 'melbourne': now.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}


def need(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4*1024**2), b''):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    tmp.replace(path)


def seal(root):
    root = Path(root)
    files = sorted(p for p in root.rglob('*') if p.is_file() and p != root/'SHA256SUMS')
    (root/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.relative_to(root).as_posix()+'\n' for p in files))


def verify_seal(root):
    root = Path(root)
    expected = {}
    for line in (root/'SHA256SUMS').read_text().splitlines():
        h, name = line.split('  ', 1)
        p = Path(name)
        need(not p.is_absolute() and '..' not in p.parts and '\\' not in name and name not in expected, 'Unsafe checksum entry')
        target = root/p
        need(not target.is_symlink() and target.resolve().is_relative_to(root.resolve()), 'Checksum path escape')
        need(sha(target) == h, 'Checksum differs: '+name)
        expected[name] = h
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p != root/'SHA256SUMS'}
    need(actual == set(expected), 'Recursive checksum coverage differs')
    for p in root.rglob('*.csv'):
        need(b'\r' not in p.read_bytes(), 'CSV must use LF')
    return len(expected)


def resolve(row, home, overrides=None):
    path = Path((overrides or {}).get(row['id'], Path(home)/row['home_path'])).expanduser().resolve()
    need('adaptive-q-screen' not in str(path) and 'adaptive-q17-q32' not in str(path), 'Live screen source forbidden')
    if not path.is_file():
        return None
    need(sha(path) == row['sha256'], 'Source hash mismatch for '+row['id'])
    return path


def load_state(row, path):
    need(sha(path) == row['sha256'], 'Source hash changed')
    shape = tuple(row['nodes']) if isinstance(row['nodes'], list) else (row['nodes'],)*3
    with np.load(path, allow_pickle=False) as data:
        key = 'n' if 'n' in data else 'field'
        n = data[key].copy()
        need(n.dtype == np.float64 and n.shape == shape+(3,) and np.isfinite(n).all(), 'Wrong field precision/shape/values')
        need(np.max(abs(np.linalg.norm(n, axis=-1)-1)) < 1e-8, 'Invalid unit-vector input; no repair')
        vkey = 'v' if 'v' in data else 'field_rate' if 'field_rate' in data else None
        v = data[vkey].copy() if vkey else np.zeros_like(n)
        need(v.shape == n.shape and np.isfinite(v).all(), 'Invalid rate')
        if row['kind'] == 'static':
            need(np.max(abs(v)) < 1e-12, 'Declared rest state has nonzero velocity')
        if 'expected_q' in data:
            need(int(data['expected_q']) == row['q'], 'Embedded Q mismatch')
        if 'model_id' in data:
            need(str(data['model_id']) == row['model'], 'Embedded model mismatch')
        if row['kind'] == 'physical-time':
            need('time' in data and 'step' in data, 'Physical time/step metadata missing')
            need(abs(float(data['time'])-row['time']) < 1e-12 and int(data['step']) == row['step'], 'Saved physical time/step mismatch')
        if 'iteration' in data and row.get('iteration') is not None:
            need(int(data['iteration']) == row['iteration'], 'Native optimizer iteration mismatch')
        if 'h' in data:
            spacing = np.asarray(row['lengths'])/(np.asarray(shape)-1)
            need(np.max(abs(spacing-float(data['h']))) < 1e-12, 'Embedded spacing mismatch')
    return n, v


def derive(n, v, lengths, curves=True, acceleration_map=True):
    from .sf_time import Grid, gradients, acceleration
    from .skyrme import K, NORTH
    grid = Grid(tuple(n.shape[:3]), tuple(lengths), 'fixed')
    # Same continuum T00 as sf_time.densities, without allocating unused stress arrays.
    d = gradients(n-NORTH, grid)
    e2 = np.sum(d*d, axis=(-2, -1))
    e4 = sum(np.sum(np.cross(d[...,i,:], d[...,j,:])**2, axis=-1) for i,j in ((0,1),(0,2),(1,2)))
    kinetic = np.sum(v*v, axis=-1) + sum(np.sum(np.cross(v, d[...,i,:])**2, axis=-1) for i in range(3))
    energy = K*(e2+e4+kinetic)
    del d, e2, e4, kinetic
    amap = np.linalg.norm(acceleration(n, v, grid)[1], axis=-1) if acceleration_map else np.zeros(n.shape[:3])
    result = {'energy': energy, 'acceleration': amap, 'curves': [], 'preimage_status': 'not requested', 'target': list(TARGET)}
    if curves and len(set(n.shape[:3])) == 1 and len(set(lengths)) == 1:
        from .sf_topology import preimages
        try:
            extracted = preimages(n, grid.spacing[0], TARGET)
            result.update(curves=extracted.pop('curves'), preimage_status=extracted['status'], preimage_details=extracted)
        except ValueError as exc:
            result['preimage_status'] = 'unresolved: '+str(exc)
    return result


def plot_state(row, n, data, path, settings, energy_level, azimuth=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize, LogNorm
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from .sf_renderer import triangles
    from .sf_preview import resample
    from PIL import Image
    shape = n.shape[:3]
    display = tuple(min(settings['display_nodes'], count) for count in shape)
    sampled = resample(n, display, 'fixed')
    e = resample(data['energy'], display, 'fixed')
    spacing = np.asarray(row['lengths'])/(np.asarray(display)-1)
    origin = -np.asarray(row['lengths'])/2
    vertices, values = triangles(e, sampled[...,0], origin, spacing, energy_level)
    total_triangles = len(vertices)
    stride = max(1, int(np.ceil(total_triangles/settings['max_triangles'])))
    vertices, values = vertices[::stride], values[::stride]
    fig = plt.figure(figsize=(16, 9), dpi=settings['width']/16, facecolor='white')
    ax = fig.add_axes([.025, .29, .36, .51], projection='3d')
    norm = Normalize(*COLOR_RANGE)
    if len(vertices):
        ax.add_collection3d(Poly3DCollection(vertices, facecolor=plt.colormaps['coolwarm'](norm(values)), edgecolor='none', alpha=.72))
    for curve in data['curves']:
        ax.plot(*curve.T, color='#222222', linewidth=1.1)
    from itertools import product, combinations
    corners = list(product(*[(-L/2, L/2) for L in row['lengths']]))
    for a,b in combinations(corners, 2):
        if sum(x != y for x,y in zip(a,b)) == 1:
            ax.plot(*np.array([a,b]).T, color='#8a8a8a', linewidth=.6)
    lim = settings['axis_half_length']
    for setter in (ax.set_xlim, ax.set_ylim, ax.set_zlim):
        setter(-lim, lim)
    ax.set_box_aspect((1,1,1))
    ax.view_init(24, settings['azimuth'] if azimuth is None else azimuth)
    ax.set(xlabel='x / model length', ylabel='y / model length', zlabel='z / model length', title='Energy contour + selected preimage')
    color_axis=fig.add_axes([.415,.40,.007,.30]);plt.colorbar(plt.cm.ScalarMappable(norm=norm,cmap='coolwarm'),cax=color_axis);color_axis.set_title('nₓ',fontsize=9);color_axis.tick_params(labelsize=8)
    # Native central-z internal-field slice, with x horizontal and y vertical.
    bx = fig.add_axes([.50, .38, .19, .35])
    k = shape[2]//2
    extent = [-row['lengths'][0]/2, row['lengths'][0]/2, -row['lengths'][1]/2, row['lengths'][1]/2]
    bx.imshow(n[:,:,k,0].T, origin='lower', extent=extent, cmap='coolwarm', vmin=-1, vmax=1, interpolation='nearest')
    step = max(1, shape[0]//14)
    xs = np.linspace(extent[0], extent[1], shape[0])[::step]
    ys = np.linspace(extent[2], extent[3], shape[1])[::step]
    bx.quiver(xs, ys, n[::step,::step,k,0].T, n[::step,::step,k,1].T, color='black', scale=20)
    bx.set(xlabel='x / model length', ylabel='y / model length', title='Internal nₓ,nᵧ arrows\n(no material velocity)')
    bx.set_xlim(-lim, lim);bx.set_ylim(-lim, lim)
    cx = fig.add_axes([.76, .38, .18, .35])
    # Maximum-over-z projection localizes a small peak hidden by an average residual.
    acceleration = data['acceleration']
    projection = acceleration.max(axis=2)
    img = cx.imshow(np.maximum(projection.T, 1e-8), origin='lower', extent=extent,
                    cmap='magma', norm=LogNorm(1e-8, 1e2), interpolation='nearest')
    peak = np.unravel_index(np.argmax(acceleration), shape)
    position = origin + np.asarray(peak)*np.asarray(row['lengths'])/(np.asarray(shape)-1)
    cx.plot(position[0], position[1], '+', color='cyan', markersize=9)
    if projection.min() < 1e-3 < projection.max():
        cx.contour(np.linspace(extent[0],extent[1],shape[0]), np.linspace(extent[2],extent[3],shape[1]), projection.T, levels=[1e-3], colors=['cyan'], linewidths=.6)
    for ax2 in (bx, cx):
        for length, vertical in [(row['lengths'][0], True),(row['lengths'][1],False)]:
            for sign in (-1,1):
                band = sorted([sign*length/2, sign*(length/2-2)])
                (ax2.axvspan if vertical else ax2.axhspan)(*band, color='gray', alpha=.14)
    cx.set(xlabel='x / model length', ylabel='y / model length', title='Max-over-z |D4 acceleration|' )
    cx.set_xlim(-lim, lim);cx.set_ylim(-lim, lim)
    accel_axis=fig.add_axes([.957,.40,.007,.30]);plt.colorbar(img,cax=accel_axis);accel_axis.set_title('|a|',fontsize=9);accel_axis.tick_params(labelsize=8)
    native = ('t='+str(row['time'])+' model time; step '+str(row['step'])) if row['kind']=='physical-time' else ('optimizer iteration '+str(row['iteration']) if row.get('iteration') is not None else 'retained optimizer state; iteration unspecified in selection')+'; no physical elapsed time'
    fig.suptitle('\n'.join(textwrap.wrap(f"Q{row['q']} · {row['seed']} · {row['stage']}",120)), fontsize=14, x=.04, ha='left', y=.975)
    fig.text(.04, .91, native+' · '+row['outcome'], fontsize=10)
    foot = [f"Source {row['sha256'][:20]}… · native {shape} · display {display} · export {settings['width']}×{settings['height']} pixels",
            f"Box {row['lengths']} · iso {energy_level:.6g} (fixed for this view; comparisons/sequences use shared levels; Q sectors can differ)",
            f"Preimage: {data['preimage_status']} · target normalized {TARGET} · peak xyz {tuple(round(float(x),4) for x in position)}",
            'Gray bands: width-2 boundary shell. Cyan: acceleration 1e-3 level/peak; diagnostic display does not change admission.',
            *textwrap.wrap(row['interpretation'], 158)[:3],
            'Derived D4 continuum display density; not original cell-functional density. Attractive geometry is not physical stability or an electron model.',
            f"Rendered UTC {settings['recorded_at']['utc']} / Australia/Melbourne {settings['recorded_at']['melbourne']}"]
    metrics=row.get('recorded_metrics',{})
    if all(k in metrics for k in ['force','acceleration','tail']):
        foot.insert(4,f"Recorded force {metrics['force']:.6g} / gate 1e-4; acceleration {metrics['acceleration']:.6g} / gate 1e-3; tail {metrics['tail']:.6g} / gate 0.00075. Other original gates still apply.")
    fig.text(.04,.025,'\n'.join(foot), fontsize=8, va='bottom')
    path = Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path, dpi=settings['width']/16)
    plt.close(fig)
    with Image.open(path) as im:
        need(im.size == (settings['width'],settings['height']), 'Wrong output pixel dimensions')
    return {'display_grid':list(display), 'data_grid':list(shape), 'energy_isosurface':energy_level,
            'preimage_status':data['preimage_status'], 'peak_display_position':position.tolist(),
            'density':'D4-derived continuum T00, native derivatives then display interpolation',
            'triangles_before_display_decimation':total_triangles, 'triangle_stride':stride,
            'field_color_range':list(COLOR_RANGE), 'acceleration_range':[1e-8,1e2], 'sha256':sha(path)}


def encode(frames, output, fps=2):
    need(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'ffmpeg and ffprobe required for qualified browser video')
    output=Path(output)
    with __import__('tempfile').TemporaryDirectory(dir=output.parent) as tmp:
        for i,p in enumerate(frames):
            shutil.copyfile(p, Path(tmp)/f'{i:05d}.png')
        subprocess.run(['ffmpeg','-v','error','-y','-threads','1','-filter_threads','1','-framerate',str(fps),'-i',str(Path(tmp)/'%05d.png'),
                        '-vf','scale=1920:-2','-c:v','libx264','-threads','1','-pix_fmt','yuv420p','-movflags','+faststart',str(output)],check=True)
    result=decode(output)
    need(int(result['streams'][0]['nb_frames'])==len(frames),'Encoded frame count differs from recorded states')
    need(abs(float(result['format']['duration'])-len(frames)/fps)<.1,'Playback duration differs from declared rate')
    result.update(encoded_frames=len(frames),playback_frames_per_second=fps)
    return result


def decode(path):
    data=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=codec_name,pix_fmt,width,height,nb_frames:format=duration','-of','json',str(path)]))
    stream=data['streams'][0]
    need(stream['codec_name']=='h264' and stream['pix_fmt']=='yuv420p', 'Browser codec qualification failed')
    subprocess.run(['ffmpeg','-v','error','-threads','1','-i',str(path),'-f','null','-'],check=True)
    return dict(data, sha256=sha(path), actual_full_decode='passed')


def offline_player(rows, output, title, kind, video=None):
    # Self-contained PNG frames; no fetch(), server, CDN or external font.
    frames=[{'label':label,'image':'data:image/png;base64,'+base64.b64encode(Path(p).read_bytes()).decode()} for label,p in rows]
    payload=json.dumps(frames).replace('<','\\u003c')
    document='''<!doctype html><meta charset="utf-8"><title>TITLE</title><style>body{font:17px system-ui;margin:2em;max-width:1600px;background:#f4f6fa;color:#172335}img,video{width:100%;height:auto}button,input{margin:.5em}p{max-width:1000px}</style><h1>TITLE</h1><p>KIND</p><p>Recorded model times or optimizer iterations are shown explicitly. Playback is 2 recorded frames per second at 1×, with holds and no state interpolation. Camera animations show a fixed state, not physical spinning.</p><button id="play">Play</button><button id="previous">Previous</button><button id="next">Next</button><input id="slider" type="range" min="0" value="0" aria-label="Frame"><select id="speed"><option>.5</option><option selected>1</option><option>2</option></select><output id="clock"></output><img id="scene" alt="Authenticated numerical spatial view"><p>EXPLAIN</p>VIDEO<script id="data" type="application/json">DATA</script><script>const f=JSON.parse(document.getElementById('data').textContent),s=document.getElementById('slider'),im=document.getElementById('scene'),c=document.getElementById('clock'),b=document.getElementById('play');let timer=null;s.max=f.length-1;function show(i){i=(Number(i)+f.length)%f.length;s.value=i;im.src=f[i].image;c.textContent=f[i].label;}function pause(){clearInterval(timer);timer=null;b.textContent='Play';}function start(){pause();b.textContent='Pause';timer=setInterval(()=>show(Number(s.value)+1),500/Number(document.getElementById('speed').value));}b.onclick=()=>timer===null?start():pause();s.oninput=()=>{pause();show(s.value)};document.getElementById('next').onclick=()=>{pause();show(Number(s.value)+1)};document.getElementById('previous').onclick=()=>{pause();show(Number(s.value)-1)};document.getElementById('speed').onchange=()=>{if(timer!==null)start()};show(0);</script>'''
    video_html='<video controls preload="metadata" src="'+html.escape(video)+'"></video>' if video else ''
    for key,value in [('TITLE',html.escape(title)),('KIND',html.escape(kind)),('EXPLAIN',html.escape(EXPLAIN)),('VIDEO',video_html),('DATA',payload)]:
        document=document.replace(key,value)
    Path(output).write_text(document)


def browser_check(viewer, report, executable=None):
    # Optional test dependency; never installed into the scientific environment automatically.
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=executable or shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome'), headless=True, args=['--no-sandbox','--allow-file-access-from-files'])
        page=browser.new_page();errors=[];requests=[]
        page.on('pageerror',lambda err:errors.append(str(err)))
        page.on('request',lambda req:requests.append(req.url))
        page.goto(Path(viewer).resolve().as_uri());page.wait_for_function("document.getElementById('scene').naturalWidth > 0")
        initial=page.locator('#clock').inner_text()
        page.locator('#next').click();after=page.locator('#clock').inner_text()
        count=page.evaluate("JSON.parse(document.getElementById('data').textContent).length")
        need(count==1 or initial!=after,'Offline frame control failed')
        page.locator('#previous').click();page.locator('#play').click();page.wait_for_timeout(650)
        need(page.locator('#play').inner_text()=='Pause','Offline play failed')
        page.locator('#play').click()
        videos=page.locator('video').count();video_result='not present'
        if videos:
            page.wait_for_function("document.querySelector('video').readyState>=2")
            page.evaluate("document.querySelector('video').play()")
            page.wait_for_function("document.querySelector('video').currentTime>0")
            video_result='file-URL playback advanced'
        need(not errors and not any(u.startswith(('http:','https:')) for u in requests),'Offline viewer requested network or raised script error')
        browser.close()
    result={'recorded_at':stamp(),'viewer':str(viewer),'viewer_sha256':sha(viewer),'frames':count,'frame_controls':'passed','video':video_result,'network_requests':0,'errors':errors}
    save(report,result);return result


def resource_guard(output, screen_idle=False):
    # Default rejects heavy work. A local explicit idle assertion is required every invocation.
    need(screen_idle, 'Heavy rendering deferred. Confirm screening has finished, then use --screen-idle; no screen process is modified.')
    mem={k:int(v.split()[0]) for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())}
    need(mem['MemAvailable']>6*1024**2,'Heavy rendering deferred: preserve at least 6 GiB available RAM')
    need(shutil.disk_usage(output).free>12*1024**3,'Heavy rendering deferred: preserve 12 GiB disk reserve')
    need(os.getloadavg()[0] <= max(1,os.cpu_count()//2), 'Heavy rendering deferred: CPU load exceeds conservative reserve')
    # Detect native screen runner modules without reading checkpoint files or printing command lines.
    for proc in Path('/proc').glob('[0-9]*/cmdline'):
        try:
            cmd=proc.read_bytes().replace(b'\0',b' ')
        except (OSError,PermissionError):
            continue
        try:
            process_cwd=str((proc.parent/'cwd').resolve())
        except OSError:
            process_cwd=''
        if b'python' in cmd and (b'adaptive_q_screen' in cmd or b'adaptive-q17-q32' in cmd or b'adaptive-q-screen-' in cmd or 'adaptive-q-screen-' in process_cwd):
            raise ValueError('Heavy rendering deferred: active screening process detected')
    return {'recorded_at':stamp(),'screen_idle_asserted':True,'available_ram_kib':mem['MemAvailable'],'load':os.getloadavg()[0],'gpu_used':False,'threads':1}


def render_collection(selection, output, home, overrides=None, screen_idle=False, settings=None):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    resource=resource_guard(output,screen_idle)
    cfg={'width':3840,'height':2160,'display_nodes':49,'max_triangles':18000,'axis_half_length':14.,'azimuth':-55.,'recorded_at':stamp(),**(settings or {})}
    need(cfg['width']>=3840 and cfg['height']==cfg['width']*9//16,'Production export must be at least 3840 and 16:9')
    settings_hash=hashlib.sha256(json.dumps({k:v for k,v in cfg.items() if k!='recorded_at'},sort_keys=True).encode()).hexdigest()
    selection_hash=hashlib.sha256(json.dumps(selection,sort_keys=True).encode()).hexdigest()
    identity={'version':VERSION,'selection_hash':selection_hash,'settings_hash':settings_hash,'renderer_sha256':sha(__file__),'operator_sha256':{name:sha(Path(__file__).with_name(name)) for name in ['sf_time.py','sf_dynamics.py','sf_renderer.py','sf_preview.py','sf_topology.py','skyrme.py']}}
    if (output/'identity.json').exists():
        need(json.loads((output/'identity.json').read_text())==identity,'Output identity differs; use a new tree')
    else:save(output/'identity.json',identity)
    receipts=[];missing=[]
    # Each state restart is authenticated; completed image/provenance pair is reused only by matching identity and hashes.
    for row in selection['records']:
        resource_guard(output,screen_idle)
        path=resolve(row,home,overrides)
        if path is None:
            missing.append(row['id']);continue
        folder=output/row['id'];folder.mkdir(exist_ok=True)
        receipt_path=folder/'visual.json'
        if receipt_path.exists():
            old=json.loads(receipt_path.read_text());need(old['source']['sha256']==row['sha256'] and old['identity']==identity,'Resume identity mismatch')
            verify_seal(folder);receipts.append(old);continue
        n,v=load_state(row,path)
        data=derive(n,v,row['lengths'],curves=row['kind']=='static')
        # Per-state fractional threshold; all videos using a comparison get a fixed shared level below.
        level=float(data['energy'].max())*.3
        need(level>0,'No nonzero spatial energy representation')
        details=plot_state(row,n,data,folder/'spatial.png',cfg,level)
        from PIL import Image
        with Image.open(folder/'spatial.png') as image:
            image.thumbnail((960,540));image.save(folder/'thumbnail.png')
        curve_files={}
        for i,curve in enumerate(data['curves']):
            p=folder/f'preimage-{i:03d}.npz';np.savez_compressed(p,curve=curve,target=np.asarray(TARGET));curve_files[p.name]=sha(p)
        if row['id']=='q2-retained-reference-broad-0':
            frame_paths=[]
            for i,angle in enumerate(np.linspace(-55,305,24,endpoint=False)):
                # Camera-only presentation: same n and derived arrays, explicit caption.
                camera_row=dict(row,stage='CAMERA ORBIT · FIXED CONFIGURATION · NO PHYSICAL SPINNING')
                p=folder/f'camera-{i:03d}.png';plot_state(camera_row,n,data,p,cfg,level,azimuth=float(angle));frame_paths.append(p)
            movie=dict(encode(frame_paths,folder/'camera.mp4',fps=2),animation_kind='camera-only',azimuth_degrees=np.linspace(-55,305,24,endpoint=False).tolist(),elevation_degrees=24.,playback_frames_per_second=2,physical_elapsed_time=None,fixed_source_sha256=row['sha256'])
            offline_player([(f'Camera azimuth {-55+i*15} degrees; fixed state; physical elapsed time not applicable',p) for i,p in enumerate(frame_paths)],folder/'camera.html','Q2 reference camera orbit','camera-only; fixed configuration','camera.mp4')
            # Embedded frame HTML retains images; no loose 4K orbit frames in archive.
            for p in frame_paths:p.unlink()
        else:movie=None
        with np.load(path,allow_pickle=False) as checkpoint:
            embedded={name:str(checkpoint[name].item()) for name in ['written_utc','written_melbourne','model_id','scheme','iteration','time','step','h','code_sha256','physics_sha256','config_sha256'] if name in checkpoint and checkpoint[name].size==1}
        caption={'source':row,'embedded_source_metadata':embedded,'array_order':'axes x,y,z; internal component last; no axis permutation','source_path':str(path),'identity':identity,'rendered_at':cfg['recorded_at'],'settings':cfg,'display':details,'curve_files':curve_files,'camera_video':movie,'physical_time_seconds_SI':None,'interpretation':EXPLAIN,'resource_qualification':resource}
        save(receipt_path,caption);seal(folder);receipts.append(caption)
        save(output/'status.json',{'recorded_at':stamp(),'phase':'rendering','completed':len(receipts),'missing':missing})
        del n,v,data
    # Sequences retain only measured states, with labels; each frame's threshold is explicitly noted.
    by_id={r['source']['id']:r for r in receipts};sequence_results=[]
    for seq in selection['sequences']:
        resource_guard(output,screen_idle)
        if not all(key in by_id for key in seq['frames']):
            missing.append('sequence:'+seq['id']);continue
        folder=output/('sequence-'+seq['id']);folder.mkdir(exist_ok=True)
        if (folder/'sequence.json').exists():
            previous=json.loads((folder/'sequence.json').read_text());need(previous['identity']==identity,'Sequence resume identity differs');verify_seal(folder);sequence_results.append(previous);continue
        frames=[]
        shared_level=max(by_id[key]['display']['energy_isosurface'] for key in seq['frames'])
        for i,key in enumerate(seq['frames']):
            row=by_id[key]['source'];source=resolve(row,home,overrides)
            n,v=load_state(row,source);data=derive(n,v,row['lengths'],curves=False)
            frame=folder/f'frame-{i:04d}.png'
            plot_state(row,n,data,frame,cfg,shared_level)
            frames.append(frame)
            del n,v,data
        labels=[('t='+str(by_id[key]['source']['time'])+' model time' if seq['kind']=='physical-time' else 'optimizer iteration '+str(by_id[key]['source']['iteration'])) for key in seq['frames']]
        movie=encode(frames,folder/'sequence.mp4',fps=2)
        offline_player(list(zip(labels,frames)),folder/'viewer.html',seq['id'],seq['label']+'; shared absolute energy contour across this sequence','sequence.mp4')
        result={'recorded_at':stamp(),'identity':identity,**seq,'frame_labels':labels,'playback_frames_per_second':2,'display_interpolation':'none; holds at saved states','shared_energy_isosurface':shared_level,'threshold_scope':'shared absolute threshold, fixed field/acceleration ranges, camera and physical axes','video':movie}
        save(folder/'sequence.json',result)
        for frame in frames:frame.unlink()
        seal(folder);sequence_results.append(result)
    comparison_results=[]
    for pair in selection.get('comparisons',[]):
        resource_guard(output,screen_idle)
        if not all(key in by_id for key in pair['frames']):
            missing.append('comparison:'+pair['id']);continue
        folder=output/('comparison-'+pair['id']);folder.mkdir(exist_ok=True)
        if (folder/'comparison.json').exists():
            previous=json.loads((folder/'comparison.json').read_text());need(previous['identity']==identity,'Comparison resume identity differs');verify_seal(folder);comparison_results.append(previous);continue
        shared_level=max(by_id[key]['display']['energy_isosurface'] for key in pair['frames'])
        images=[]
        for i,key in enumerate(pair['frames']):
            row=by_id[key]['source'];source=resolve(row,home,overrides)
            n,v=load_state(row,source);data=derive(n,v,row['lengths'],curves=True)
            frame=folder/f'arm-{i:02d}.png';plot_state(row,n,data,frame,cfg,shared_level)
            images.append(frame);del n,v,data
        from PIL import Image
        canvas=Image.new('RGB',(cfg['width']*len(images),cfg['height']),'white')
        for i,frame in enumerate(images):
            with Image.open(frame) as im:canvas.paste(im,(i*cfg['width'],0))
        canvas.save(folder/'comparison.png');canvas.thumbnail((1920,540));canvas.save(folder/'thumbnail.png')
        result={'recorded_at':stamp(),'identity':identity,**pair,'shared_energy_isosurface':shared_level,'registration':'none; common physical axes and camera; native geometry retained','interpretation':'Static comparison, not a temporal sequence'}
        save(folder/'comparison.json',result)
        for frame in images:frame.unlink()
        seal(folder);comparison_results.append(result)
    gallery=['<!doctype html><meta charset="utf-8"><title>Matter Waves Q1–Q16</title><style>body{font:18px system-ui;max-width:1500px;margin:2em auto}img{max-width:100%}section{padding:1em;border-top:1px solid #ddd}a{color:#075c94}</style><h1>Matter Waves: Q1–Q16 visual evidence</h1><p>'+html.escape(EXPLAIN)+'</p><p>Read Q2 first as the numerical reference. Q1 is parked context. Q alone does not specify a shape. Repository HTML must be downloaded and opened locally; GitHub does not execute it in its file viewer.</p>']
    for q in [2,*range(1,2),*range(3,17)]:
        gallery.append(f'<section id="q{q}"><h2>Q{q}'+(' · parked context' if q==1 else '')+'</h2>')
        for receipt in receipts:
            row=receipt['source']
            if row['q']!=q:continue
            key=html.escape(row['id']);gallery.append(f'<h3>{html.escape(row["seed"])} · {html.escape(row["stage"])}</h3><p>{html.escape(row["interpretation"])}</p><a href="{key}/spatial.png"><img src="{key}/thumbnail.png" alt="Q{q} retained numerical spatial view"></a><p><a href="{key}/visual.json">Source, thresholds and renderer provenance</a></p>')
            if receipt['camera_video']:gallery.append(f'<p><a href="{key}/camera.html">Offline camera player</a> · <a href="{key}/camera.mp4">MP4 camera orbit</a></p>')
        gallery.append('</section>')
    for seq in sequence_results:
        key=html.escape(seq['id']);gallery.append(f'<p><a href="sequence-{key}/viewer.html">{key}: offline {seq["kind"]} player</a></p>')
    for pair in comparison_results:
        key=html.escape(pair['id']);gallery.append(f'<h2>{key}: spatial comparison</h2><p>{html.escape(pair["label"])}</p><a href="comparison-{key}/comparison.png"><img src="comparison-{key}/thumbnail.png" alt="Controlled spatial comparison"></a>')
    (output/'viewer.html').write_text('\n'.join(gallery))
    result={'recorded_at':stamp(),'identity':identity,'complete_q_coverage':sorted({r['source']['q'] for r in receipts if r['source']['kind']=='static'}),'missing':missing,'visuals':receipts,'sequences':sequence_results,'comparisons':comparison_results,'status':'complete' if not missing else 'missing-inputs','source_fields_written':0,'relaxation_steps':0,'physical_time_steps':0}
    with (output/'coverage.csv').open('w',newline='') as stream:
        writer=csv.writer(stream,lineterminator='\n');writer.writerow(['q','state_id','seed','stage','source_sha256','kind','data_grid','display_grid','width','height'])
        for receipt in receipts:
            row=receipt['source'];writer.writerow([row['q'],row['id'],row['seed'],row['stage'],row['sha256'],row['kind'],json.dumps(receipt['display']['data_grid']),json.dumps(receipt['display']['display_grid']),cfg['width'],cfg['height']])
    save(output/'collection.json',result);save(output/'status.json',{'recorded_at':stamp(),'phase':result['status'],'completed':len(receipts),'missing':missing});seal(output)
    return result
