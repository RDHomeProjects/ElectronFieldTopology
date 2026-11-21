"""Smooth, tightly framed camera-only films of authenticated retained fields.

Apache-2.0. Opacity/camera/crop are display settings; no solver calls or field writes.
"""
import hashlib
import json
from pathlib import Path
import os
import subprocess
import textwrap
import numpy as np
from .sf_visual_collection import sha, need, save, stamp, derive, load_state, resource_guard, seal, verify_seal

VERSION='EFT-interior-orbit-v1'
DEFAULT={'fps':30,'seconds':20,'width':1920,'height':1080,'segment_frames':120,
         'elevation':24.,'start_azimuth':-55.,'surface_grid_cap':81,'iso_fraction_fallback':None,
         'wedge_degrees':50.,'wedge_alpha':.10,'surface_alpha':.96,'wedge_direction':0.,
         'occupancy':.78,'padding':.06,'crf':18}


def config(settings=None,fixture=False):
 c={**DEFAULT,**(settings or {})}
 need(set(c)==set(DEFAULT),'Unknown movie setting')
 for key in ['fps','seconds','width','height','segment_frames','surface_grid_cap','crf']:
  need(type(c[key]) is int and c[key]>0,'Positive integer setting required: '+key)
 need(c['width']%2==0 and c['height']%2==0,'H.264 frame dimensions must be even')
 need(c['width']*9==c['height']*16,'16:9 movie required')
 need(c['fps']>=24 and c['seconds']>=10 or fixture,'Production needs >=24 fps and >=10 seconds')
 need(.5<=c['occupancy']<=.90 and 0<c['padding']<.5,'Invalid camera fit')
 need(0<=c['wedge_degrees']<=120 and 0<=c['wedge_alpha']<=1 and 0<c['surface_alpha']<=1,'Invalid display opacity wedge')
 need(c['surface_grid_cap']>=9 and c['crf']<=30,'Invalid geometry/codec quality')
 return c


def angles(c):
 return c['start_azimuth']+np.arange(c['fps']*c['seconds'])*360/(c['fps']*c['seconds'])


def json_hash(obj):return hashlib.sha256(json.dumps(obj,sort_keys=True).encode()).hexdigest()


def contour_geometry(n,v,lengths,level,cap,c=None):
 """Native D4 density first; crop before any optional display interpolation."""
 from .sf_renderer import triangles
 from .sf_preview import resample
 need(np.isfinite(level) and level>0,'Original positive threshold required')
 e=derive(n,v,lengths,curves=False,acceleration_map=False)['energy']
 active=np.argwhere(e>=level)
 need(len(active)>0 and e.min()<level,'No contour at original threshold')
 low=np.maximum(active.min(axis=0)-2,0);high=np.minimum(active.max(axis=0)+2,np.asarray(e.shape)-1)
 need(np.all(high>low),'Degenerate contour crop')
 slices=tuple(slice(int(a),int(b)+1) for a,b in zip(low,high))
 crop_e=e[slices];crop_color=n[slices+(0,)]
 native_spacing=np.asarray(lengths)/(np.asarray(n.shape[:3])-1)
 origin=-np.asarray(lengths)/2+low*native_spacing
 crop_lengths=(high-low)*native_spacing
 display=tuple(min(cap,int(x)) for x in crop_e.shape)
 sampled_e=resample(crop_e,display,'fixed');sampled_c=resample(crop_color,display,'fixed')
 display_spacing=crop_lengths/(np.asarray(display)-1)
 verts,colors=triangles(sampled_e,sampled_c,origin,display_spacing,level)
 need(len(verts)>0 and np.isfinite(verts).all(),'Empty/invalid contour mesh')
 section_vertices,section_values=energy_sections(e,-np.asarray(lengths)/2,native_spacing,verts,level,c or config())
 # Never discard individual triangles: that creates visible holes.
 return verts,colors,{'native_grid':list(n.shape[:3]),'native_spacing':native_spacing.tolist(),
  'native_crop_index_low':low.tolist(),'native_crop_index_high_inclusive':high.tolist(),
  'native_crop_grid':list(crop_e.shape),'display_crop_grid':list(display),'display_origin':origin.tolist(),
  'display_spacing':display_spacing.tolist(),'original_box_lengths':list(lengths),'absolute_energy_level':float(level),
  'density':'D4-derived continuum T00; native derivatives before optional display interpolation',
  '_section_vertices':section_vertices,'_section_values':section_values,
  'interior_sections':{'quantity':'native-derived D4 continuum T00, trilinear display sampling', 'sampling_grid':[65,65], 'planes':'two radial vertical planes at fixed opacity wedge edges', 'mask':'all triangle vertex energies >= same absolute isovalue; low-density holes remain unpainted', 'triangles':len(section_vertices), 'color_scale':'log10(T00 / contour level)', 'max_ratio':float(section_values.max()/level) if len(section_values) else 1.},
  'triangles':len(verts),'triangle_deletion':False,'field_components':'x,y,z array axes; internal component last'}


def energy_sections(energy,origin,spacing,vertices,level,c):
 """Two sampled radial cross-sections, never an invented solid or a filled hole."""
 from scipy.ndimage import map_coordinates
 if c['wedge_degrees']==0:return np.empty((0,3,3)),np.empty(0)
 center,_,bounds=fit_bounds(vertices,c['padding'])
 points=vertices.reshape(-1,3);radius=np.linalg.norm(points[:,:2]-center[:2],axis=1).max()
 radial=np.linspace(0,radius,65);vertical=np.linspace(points[:,2].min(),points[:,2].max(),65)
 r,z=np.meshgrid(radial,vertical,indexing='ij');all_vertices=[];all_values=[]
 for degrees in [c['wedge_direction']-c['wedge_degrees']/2,c['wedge_direction']+c['wedge_degrees']/2]:
  theta=np.radians(degrees)
  p=np.stack((center[0]+r*np.cos(theta),center[1]+r*np.sin(theta),z),axis=-1)
  coordinates=((p-np.asarray(origin))/np.asarray(spacing)).reshape(-1,3).T
  density=map_coordinates(energy,coordinates,order=1,mode='constant',cval=0,prefilter=False).reshape(r.shape)
  a=p[:-1,:-1];b=p[1:,:-1];d=p[:-1,1:];e=p[1:,1:]
  va=density[:-1,:-1];vb=density[1:,:-1];vd=density[:-1,1:];ve=density[1:,1:]
  for triangle,value in [(np.stack((a,b,e),axis=-2),np.stack((va,vb,ve),axis=-1)),(np.stack((a,e,d),axis=-2),np.stack((va,ve,vd),axis=-1))]:
   keep=np.all(value>=level,axis=-1)
   all_vertices.append(triangle[keep]);all_values.append(value[keep].mean(axis=-1))
 return np.concatenate(all_vertices),np.concatenate(all_values)


def fit_bounds(vertices,padding=.06):
 points=vertices.reshape(-1,3);low=points.min(axis=0);high=points.max(axis=0)
 center=(low+high)/2;radius=float(np.linalg.norm(points-center,axis=1).max())
 need(np.isfinite(radius) and radius>0,'Invalid contour extent')
 half=radius*(1+padding)
 return center,half,{'contour_bounds':[low.tolist(),high.tolist()],'view_bounds':np.stack((center-half,center+half)).tolist(),
                    'view_center':center.tolist(),'rotation_safe_radius':radius,'view_half_length':half,'physical_box_modified':False}


def wedge_mask(vertices,center,c):
 centroid=vertices.mean(axis=1)-center
 theta=np.degrees(np.arctan2(centroid[:,1],centroid[:,0]))
 delta=(theta-c['wedge_direction']+180)%360-180
 return abs(delta)<c['wedge_degrees']/2


def frozen_label(row):
 if row['kind']=='physical-time':
  return 'Frozen saved state: model t='+str(row['time'])+'; step '+str(row['step'])+' · camera motion only'
 return ('Fixed optimizer state: iteration '+str(row['iteration']) if row.get('iteration') is not None else 'Fixed retained optimizer state')+' · no physical elapsed time'


def scene(vertices,colors,row,geometry,c,width=None,height=None,sections=None):
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.colors import Normalize
 from mpl_toolkits.mplot3d.art3d import Poly3DCollection
 from mpl_toolkits.mplot3d import proj3d
 width=width or c['width'];height=height or c['height']
 fig=plt.figure(figsize=(width/120,height/120),dpi=120,facecolor='#0e1726')
 ax=fig.add_axes([.015,.125,.97,.73],projection='3d',facecolor='#0e1726')
 ax.set_proj_type('ortho')
 center,half,bounds=fit_bounds(vertices,c['padding'])
 palette=plt.colormaps['coolwarm'](Normalize(-1,1)(colors));mask=wedge_mask(vertices,center,c)
 palette[:,3]=np.where(mask,c['wedge_alpha'],c['surface_alpha'])
 render_vertices=vertices
 if sections is not None and len(sections[0]):
  section_vertices,section_values=sections
  maximum=max(1.01,geometry['interior_sections']['max_ratio'])
  logmax=float(np.log10(maximum))
  section_palette=plt.colormaps['viridis'](Normalize(0,logmax)(np.log10(section_values/geometry['absolute_energy_level'])))
  section_palette[:,3]=1.
  render_vertices=np.concatenate((vertices,section_vertices))
  palette=np.concatenate((palette,section_palette))
  energy_bar=fig.add_axes([.075,.116,.16,.012])
  energy_cb=fig.colorbar(plt.cm.ScalarMappable(norm=Normalize(0,logmax),cmap='viridis'),cax=energy_bar,orientation='horizontal',ticks=[0,logmax])
  energy_cb.ax.tick_params(colors='#c9d8ed',labelsize=7,pad=1);energy_cb.ax.set_xticklabels(['1×',f'{maximum:.2g}×'])
  fig.text(.075,.137,'Sections: energy / contour level (log)',fontsize=8,color='#c9d8ed')
 # One collection sorts shell and section facets together rather than hiding an entire section behind the shell.
 mesh=Poly3DCollection(render_vertices,facecolors=palette,edgecolors='none',zsort='average',clip_on=False)
 ax.add_collection3d(mesh)
 for i,setter in enumerate([ax.set_xlim,ax.set_ylim,ax.set_zlim]):setter(center[i]-half,center[i]+half)
 ax.set_box_aspect((1,1,1));ax.grid(False);ax.set_axis_off()
 for axis in [ax.xaxis,ax.yaxis,ax.zaxis]:
  axis.set_pane_color((0,0,0,0));axis.line.set_color('#71849b');axis.label.set_color('#b7c4d7')
 ax.tick_params(colors='#93a7c1',labelsize=7,pad=0)
 ax.set_xlabel('x',labelpad=-2);ax.set_ylabel('y',labelpad=-2);ax.set_zlabel('z',labelpad=-2)
 # Orthographic screen fit is fixed for the entire orbit, avoiding zoom breathing.
 points=vertices.reshape(-1,3)
 max_size=np.zeros(2);samples=[]
 fig.canvas.draw()
 for angle in np.arange(c['start_azimuth'],c['start_azimuth']+360,15):
  ax.view_init(c['elevation'],float(angle))
  x,y,z=proj3d.proj_transform(*points.T,ax.get_proj());pixels=ax.transData.transform(np.column_stack((x,y)))
  size=np.ptp(pixels,axis=0);max_size=np.maximum(max_size,size);samples.append(size)
 # Axes3D reserves a square box. Fit against the intended widescreen scene,
 # allowing the mesh beyond that square while remaining inside the figure.
 viewport=np.array([fig.bbox.width*.97,fig.bbox.height*.73]);zoom=float(np.min(c['occupancy']*viewport/max_size))
 ax.set_box_aspect((1,1,1),zoom=zoom);ax.view_init(c['elevation'],c['start_azimuth'])
 title='Q'+str(row['q'])+' · '+row['seed']+' · CAMERA ORBIT'
 fig.text(.045,.966,'\n'.join(textwrap.wrap(title,115)),color='white',fontsize=12,va='top')
 fig.text(.045,.875,str(row.get('stage',''))+' · '+str(row.get('outcome','')),color='#9bb0cc',fontsize=8)
 fig.text(.045,.904,frozen_label(row)+' · NOT PHYSICAL SPINNING',color='#bfd1e9',fontsize=9)
 bar=fig.add_axes([.075,.066,.16,.012])
 cb=fig.colorbar(plt.cm.ScalarMappable(norm=Normalize(-1,1),cmap='coolwarm'),cax=bar,orientation='horizontal',ticks=[-1,0,1])
 cb.ax.tick_params(colors='#c9d8ed',labelsize=7,pad=1);cb.outline.set_edgecolor('#64748b')
 fig.text(.075,.087,'Internal nₓ on energy contour',fontsize=8,color='#c9d8ed')
 fig.text(.31,.073,f"Opacity wedge {c['wedge_degrees']:g}° / α={c['wedge_alpha']:g} · sampled energy sections",fontsize=8,color='#c9d8ed')
 fig.text(.31,.048,f"Isovalue {geometry['absolute_energy_level']:.7g} · view ±{half:.4g} about {tuple(round(float(x),3) for x in center)} · model length",fontsize=7,color='#9bb0cc')
 fig.text(.045,.014,'Source '+row['sha256'][:16]+'… · original box '+str(row['lengths'])+' · native '+str(geometry['native_grid'])+' · ROI display '+str(geometry['display_crop_grid']),fontsize=7,color='#9bb0cc')
 counter=fig.text(.95,.075,'',fontsize=8,color='#c9d8ed',ha='right')
 created=stamp()
 fig.text(.045,.033,'Rendered UTC '+created['utc']+' / Australia/Melbourne '+created['melbourne'],fontsize=6,color='#8197b6')
 bounds.update(scene_created_at=created,intended_scene_fraction=[.97,.73],orthographic_zoom=zoom,fit_target_fraction=c['occupancy'],projected_fit_samples_fraction=(np.array(samples)*zoom/viewport).tolist(),
               wedge_triangles=int(mask.sum()),wedge_coordinate_frame='fixed data-space azimuth about contour center; no rotating cut or field removal')
 return fig,ax,counter,bounds


def video_info(path,expected_frames=None,c=None):
 info=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=codec_name,pix_fmt,width,height,nb_read_frames,r_frame_rate:format=duration','-of','json',str(path)]))
 stream=info['streams'][0]
 need(stream['codec_name']=='h264' and stream['pix_fmt']=='yuv420p','Wrong browser codec')
 if expected_frames is not None:need(int(stream['nb_read_frames'])==expected_frames,'Encoded frame count mismatch')
 if c:
  need((stream['width'],stream['height'])==(c['width'],c['height']),'Encoded dimensions mismatch')
  num,den=map(int,stream['r_frame_rate'].split('/'));need(abs(num/den-c['fps'])<1e-10,'Wrong frame rate')
  need(abs(float(info['format']['duration'])-int(stream['nb_read_frames'])/c['fps'])<.08,'Playback duration mismatch')
 subprocess.run(['ffmpeg','-v','error','-threads','1','-i',str(path),'-f','null','-'],check=True)
 return {'sha256':sha(path),'probe':info,'full_decode':'passed'}


def render_segment(fig,ax,counter,path,start,stop,c,status):
 angle=angles(c);temp=path.with_suffix('.partial.mp4');log=path.with_suffix('.log')
 command=['ffmpeg','-v','error','-y','-threads','1','-filter_threads','1','-f','rawvideo','-pixel_format','rgba','-video_size',f"{c['width']}x{c['height']}",'-framerate',str(c['fps']),'-i','pipe:0','-an','-c:v','libx264','-threads','1','-preset','medium','-crf',str(c['crf']),'-pix_fmt','yuv420p','-movflags','+faststart',str(temp)]
 with log.open('wb') as errors:
  proc=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=errors)
  try:
   for frame in range(start,stop):
    ax.view_init(c['elevation'],float(angle[frame]));counter.set_text(f"Camera {angle[frame]%360:05.1f}°\nPlayback {frame/c['fps']:.2f} s")
    fig.canvas.draw();proc.stdin.write(fig.canvas.buffer_rgba())
    if frame%c['fps']==0:save(status,{'recorded_at':stamp(),'phase':'rendering camera frames','frame':frame,'total_frames':len(angle),'movie':path.parent.name})
   proc.stdin.close();need(proc.wait()==0,'Encoder failed; see '+str(log))
  finally:
   if proc.poll() is None:
    proc.terminate();proc.wait()  # Only this renderer's encoder child; never the screening job.
 temp.replace(path)
 return video_info(path,stop-start,c)


def build_movie(row,source_path,level,output,cache,settings=None,screen_idle=False,fixture=False):
 import matplotlib.pyplot as plt
 c=config(settings,fixture);output=Path(output);cache=Path(cache);output.mkdir(parents=True,exist_ok=True);cache.mkdir(parents=True,exist_ok=True)
 if not fixture:resource_guard(output,screen_idle)
 identity={'version':VERSION,'source_sha256':row['sha256'],'source_state':row,'settings':c,'absolute_energy_level':level,
           'renderer_sha256':sha(__file__),'fixture':fixture}
 identity_hash=json_hash(identity)
 if (output/'movie.json').exists():
  old=json.loads((output/'movie.json').read_text());need(old['identity_hash']==identity_hash,'Finished movie identity differs');verify_seal(output);return old
 if (cache/'identity.json').exists():need(json.loads((cache/'identity.json').read_text())==identity,'Cache identity differs')
 else:save(cache/'identity.json',identity)
 if (cache/'geometry.json').exists():
  geometry=json.loads((cache/'geometry.json').read_text());need(sha(cache/'geometry.npz')==geometry['cache_sha256'],'Cached contour differs')
  with np.load(cache/'geometry.npz',allow_pickle=False) as d:
   vertices=d['vertices'].copy();colors=d['colors'].copy();sections=(d['section_vertices'].copy(),d['section_values'].copy())
 else:
  n,v=load_state(row,source_path)
  vertices,colors,geometry=contour_geometry(n,v,row['lengths'],level,c['surface_grid_cap'],c);del n,v
  sections=(geometry.pop('_section_vertices'),geometry.pop('_section_values'))
  np.savez_compressed(cache/'geometry.npz',vertices=vertices,colors=colors,section_vertices=sections[0],section_values=sections[1]);geometry['cache_sha256']=sha(cache/'geometry.npz');save(cache/'geometry.json',geometry)
 fig,ax,counter,bounds=scene(vertices,colors,row,geometry,c,sections=sections)
 # A 4K poster uses the same camera, fit policy and mesh; videos remain 1920x1080 by default.
 poster,_,_,_=scene(vertices,colors,row,geometry,c,width=3840,height=2160,sections=sections)
 poster.savefig(output/'poster.png',dpi=120,facecolor=poster.get_facecolor());plt.close(poster)
 from PIL import Image
 with Image.open(output/'poster.png') as image:image.thumbnail((960,540));image.save(output/'thumbnail.png')
 total=c['fps']*c['seconds'];segments=[]
 old_segments=json.loads((cache/'segments.json').read_text()) if (cache/'segments.json').exists() else {}
 try:
  for start in range(0,total,c['segment_frames']):
   if not fixture:resource_guard(output,screen_idle)
   stop=min(total,start+c['segment_frames']);p=cache/f'segment-{start:06d}.mp4';key=p.name
   if key in old_segments:need(p.exists() and sha(p)==old_segments[key]['sha256'],'Previously completed segment changed')
   else:
    old_segments[key]=render_segment(fig,ax,counter,p,start,stop,c,output.parent/'status.json');save(cache/'segments.json',old_segments)
   segments.append(p)
 finally:plt.close(fig)
 # ffmpeg concat file paths are generated relative safe names, not interpolated user paths.
 listing=cache/'concat.txt';listing.write_text(''.join("file '"+p.name+"'\n" for p in segments))
 movie=output/'rotation.mp4';temp=output/'rotation.partial.mp4'
 subprocess.run(['ffmpeg','-v','error','-y','-threads','1','-f','concat','-safe','1','-i',str(listing),'-c','copy','-movflags','+faststart',str(temp)],check=True)
 temp.replace(movie);info=video_info(movie,total,c)
 need(sha(source_path)==row['sha256'],'Source changed while making movie')
 receipt={'recorded_at':stamp(),'identity_hash':identity_hash,'identity':identity,'source_path':str(Path(source_path).resolve()),
          'source':row,'geometry':geometry,'camera':bounds,'video':info,'poster_sha256':sha(output/'poster.png'),
          'animation_kind':'camera-only; one fixed retained state','frozen_state_label':frozen_label(row),
          'playback_seconds':c['seconds'],'frames':total,'camera_step_degrees':360/total,
          'seam_step_degrees':360/total,'physical_intermediate_states_generated':0,'scientific_fields_written':0,
          'opacity_scope':'Fixed angular surface transparency plus sampled interior energy cross-sections. Low-density holes are not filled. No energy or field is removed.',
          'interpretation':row['interpretation'],'limits':'Appearance and opacity do not change numerical outcomes or establish stability/electron properties.'}
 save(output/'movie.json',receipt);seal(output);return receipt
