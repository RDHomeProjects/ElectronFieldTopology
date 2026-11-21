#!/usr/bin/env python3
"""Local-only movie presentation revision; earlier outputs and records stay immutable."""
import argparse
import csv
import hashlib
import html
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('orbit_publication_base',HERE/'publication_base.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b);b.HERE=HERE
ORIGINAL_CHECKS=b.checks
BRANCH='visual/focused-smooth-orbits-20261121'
DEFAULT_OLD=Path.home()/'Matter-Waves-visual-output-20261121'


def load(p):return b.load(p)
def save(p,d):return b.save(p,d)
def run(cmd,cwd=None,capture=False):return b.run(cmd,cwd,capture)
def need(ok,msg):return b.need(ok,msg)
def sha(p):return b.sha(p)


def normalize_markdown(text):return text.rstrip()+'\n'


def make_plan(old_output,all_q=False):
 old_output=b.guard(old_output)
 original=load(old_output/'collection.json')
 need(original['complete_q_coverage']==list(range(1,17)) and not original['missing'],'Original collection is incomplete')
 indexed={v['source']['id']:v for v in original['visuals']}
 cases=[]
 for path in sorted(old_output.rglob('*.mp4')):
  relative=path.relative_to(old_output).as_posix()
  if path.name=='camera.mp4' and (path.parent/'visual.json').exists():
   receipt=load(path.parent/'visual.json');row=receipt['source'];level=receipt['display']['energy_isosurface'];selection='same fixed camera source'
  elif path.name=='sequence.mp4' and (path.parent/'sequence.json').exists():
   seq=load(path.parent/'sequence.json');receipt=indexed[seq['frames'][-1]];row=receipt['source'];level=seq['shared_energy_isosurface'];selection='last actually saved state of former '+seq['kind']+' sequence; now frozen'
  else:raise ValueError('Unmapped existing MP4: '+relative)
  cases.append({'id':'replace-'+path.parent.name,'source':row,'source_path':receipt['source_path'],'level':level,
                'replaces':relative,'old_movie_sha256':sha(path),'old_kind':'camera-only' if path.name=='camera.mp4' else seq['kind'],
                'selection_rule':selection,'parent_visual_sha256':sha(old_output/row['id']/'visual.json')})
 need(cases,'No original MP4s found')
 if all_q:
  chosen={c['source']['q'] for c in cases}
  preferred={1:'q1-parked-rest-parent',4:'q4-axial41-broad-225',5:'q5-trefoil32-1-1-broad-50',6:'q6-axial6-1-followup-400',7:'q7-trefoil-followup-1300',8:'q8-continuation-2',9:'q9-trefoil32-3-1-followup-100'}
  for q in range(1,17):
   if q in chosen:continue
   receipt=indexed.get(preferred.get(q,''))
   if receipt is None:
    candidates=[x for x in original['visuals'] if x['source']['q']==q and x['source']['kind']=='static' and 'axial' in x['source']['seed']]
    need(candidates,'No explicit retained static representative for Q'+str(q));receipt=candidates[0]
   row=receipt['source'];cases.append({'id':f'q{q:02d}-additional-orbit','source':row,'source_path':receipt['source_path'],'level':receipt['display']['energy_isosurface'],
    'replaces':None,'old_movie_sha256':None,'old_kind':None,'selection_rule':'additional explicitly labelled retained-state orbit','parent_visual_sha256':sha(old_output/row['id']/'visual.json')})
 need(len({x['id'] for x in cases})==len(cases),'Duplicate movie identity')
 return {'recorded_at':b.stamp(),'original_output':str(old_output),'original_collection_sha256':sha(old_output/'collection.json'),
         'original_seal_sha256':sha(old_output/'SHA256SUMS'),'all_q':all_q,'cases':cases,'replacement_count':sum(x['replaces'] is not None for x in cases)}


def install(args):
 work=b.guard(args.workspace);output=b.guard(args.output);old=b.guard(args.original)
 need(not work.exists() and not output.exists(),'Use a new checkout/output; existing work is never overwritten')
 need(not any(work==x or work.is_relative_to(x) or x.is_relative_to(work) for x in [old,output]),'Work/output must be separate from original data')
 b.verify(HERE);b.verify(old)
 old_control=old.parent/(old.name+'-control.json');prior=load(old_control)
 if prior.get('phase')!='merged':
  need(prior.get('pr'),'Original visual PR identity missing')
  observed=json.loads(run(['gh','pr','view',str(prior['pr']['number']),'--repo',b.REPO,'--json','state,mergeCommit'],capture=True))
  need(observed['state']=='MERGED','Original visual PR must be merged before this revision')
 plan=make_plan(old,args.all_q)
 output.mkdir(parents=True)
 state_path=output.parent/(output.name+'-control.json');need(not state_path.exists(),'Existing control state')
 run(['git','clone','https://github.com/'+b.REPO+'.git',work]);base=run(['git','rev-parse','HEAD'],work,True)
 run(['git','switch','-c',BRANCH],work)
 run(['git','bundle','create',output.parent/(output.name+'-baseline.bundle'),'--all'],work)
 for name,h in load(HERE/'SOURCE-CONTRACT.json')['modules'].items():
  need(sha(work/'src/electron_field_topology'/name)==h,'Source interface differs: '+name+'; preserve checkout for review')
 run(['uv','sync','--frozen','--all-groups'],work)
 for p in (HERE/'payload').rglob('*'):
  if p.is_file():
   target=work/p.relative_to(HERE/'payload');need(not target.exists(),'New tool already exists; do not overwrite');target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
 registry=load(work/'docs/project/roadmap.json');study=next(s for s in registry['studies'] if s['id']==prior['study_id'])
 need(study['slug']=='q1-q16-visual-explanations','Original visual study identity differs')
 state={'recorded_at':b.stamp(),'workspace':str(work),'output':str(output),'cache':str(output.parent/(output.name+'-cache')),
        'base':base,'branch':BRANCH,'package_sha256':sha(HERE/'SHA256SUMS'),'study_id':prior['study_id'],'study_path':prior['study_path'],
        'phase':'installed','plan':plan,'settings':load(HERE/'settings.json'),'original_release_tag':prior.get('tag'),
        'allowed_existing':['docs/visual-gallery/README.md','docs/project/roadmap.json','src/electron_field_topology/sf_focused_orbits.py','tests/test_sf_focused_orbits.py']}
 if args.solid:state['settings'].update(wedge_degrees=0.,surface_alpha=1.)
 record=b.record(work,state,'preparation','Focused movie presentation revision; source states unchanged',{'plan.json':plan,'settings.json':state['settings'],'source-contract.json':HERE/'SOURCE-CONTRACT.json','handover.py':HERE/'handover.py','publication-base.py':HERE/'publication_base.py'})
 state['generated']=list(b.module(work).documents(load(work/'docs/project/roadmap.json'),work));state['allowed_existing']+=state['generated']
 save(state_path,state);print(json.dumps({'recorded_at':b.stamp(),'movies':len(plan['cases']),'existing_mp4_replacements':plan['replacement_count'],'control':str(state_path)},indent=2))


def state(args):
 control=b.guard(args.control);s=load(control);need(sha(HERE/'SHA256SUMS')==s['package_sha256'],'Handover package differs');return control,s,b.guard(s['workspace']),b.guard(s['output'])


def inventory(s,output):
 rows=[]
 for case in s['plan']['cases']:
  p=b.guard(case['source_path']);need(p.is_file(),'Retained source unavailable: '+str(p));need(sha(p)==case['source']['sha256'],'Retained source changed: '+case['id'])
  old=Path(s['plan']['original_output'])
  if case['replaces']:need(sha(old/case['replaces'])==case['old_movie_sha256'],'Original MP4 changed')
  rows.append({'id':case['id'],'q':case['source']['q'],'source_sha256':case['source']['sha256'],'status':'verified'})
 save(output.parent/(output.name+'-inventory.json'),{'recorded_at':b.stamp(),'rows':rows});print('Verified source/movie identities:',len(rows))


def render(s,output,screen_idle):
 from electron_field_topology.sf_focused_orbits import build_movie,json_hash,VERSION
 from electron_field_topology.sf_visual_collection import resource_guard
 resource_guard(output,screen_idle);old=Path(s['plan']['original_output'])
 need(sha(old/'collection.json')==s['plan']['original_collection_sha256'] and sha(old/'SHA256SUMS')==s['plan']['original_seal_sha256'],'Original collection identity changed')
 identity={'version':VERSION,'plan_sha256':json_hash(s['plan']),'settings':s['settings'],'renderer_sha256':sha(Path(s['workspace'])/'src/electron_field_topology/sf_focused_orbits.py')}
 if (output/'identity.json').exists():need(load(output/'identity.json')==identity,'Output identity differs')
 else:save(output/'identity.json',identity)
 movies=[]
 for case in s['plan']['cases']:
  result=build_movie(case['source'],case['source_path'],case['level'],output/case['id'],Path(s['cache'])/case['id'],s['settings'],screen_idle=screen_idle)
  movies.append({'case':case,'receipt':result})
 # Small offline pages; videos remain local MP4s, captions remain adjacent.
 index=['<!doctype html><meta charset="utf-8"><title>Matter Waves focused rotations</title><style>body{background:#0e1726;color:#e4edf9;font:18px system-ui;max-width:1400px;margin:2em auto}img{max-width:100%}a{color:#8fcef8}section{padding:1em;border-bottom:1px solid #43536a}</style><h1>Matter Waves: focused smooth rotations</h1><p>Each film is a camera orbit of one fixed retained configuration. Previous physical-time and optimizer sequences remain archived; no unrecorded physical intermediate states are shown. Opacity wedges and fitted bounds are display settings. Actual model times are frozen and separate from playback seconds.</p>']
 for item in movies:
  case=item['case'];receipt=item['receipt'];folder=output/case['id'];row=case['source']
  frozen=html.escape(receipt['frozen_state_label']);caption=html.escape(row['interpretation'])
  page=f'''<!doctype html><meta charset="utf-8"><title>Focused rotation Q{row['q']}</title><style>body{{background:#0e1726;color:#e4edf9;font:17px system-ui;max-width:1600px;margin:2em auto}}video{{width:100%}}a{{color:#8fcef8}}p{{max-width:1100px}}</style><h1>Q{row['q']} · {html.escape(row['seed'])}</h1><p>{frozen}. Camera-only: no physical spinning.</p><video controls loop preload="metadata" poster="poster.png" src="rotation.mp4"></video><p>{caption}</p><p>30 fps, 20 playback seconds, 600 camera frames at default settings. The original box is unchanged. Cropped bounds and a fixed data-space opacity wedge enlarge and reveal the contour; no energy or field is removed. Colours represent internal nₓ, not electromagnetic B or material velocity. Appearance does not establish stability or an electron model.</p><p><a href="movie.json">Exact source, geometry, camera, timestamps and codec provenance</a> · <a href="poster.png">4K poster</a> · <a href="rotation.mp4">MP4</a></p>'''
  if s['settings']['wedge_degrees']==0:page=page.replace('a fixed data-space opacity wedge','an opaque surface (opacity window disabled)')
  page=page.replace('30 fps, 20 playback seconds, 600 camera frames',f"{s['settings']['fps']} fps, {s['settings']['seconds']} playback seconds, {s['settings']['fps']*s['settings']['seconds']} camera frames")
  (folder/'viewer.html').write_text(page);b.seal(folder)
  key=html.escape(case['id']);index.append(f'<section><h2>Q{row["q"]} · {html.escape(row["seed"])}</h2><a href="{key}/viewer.html"><img src="{key}/thumbnail.png" alt="Focused retained energy contour"></a><p>{frozen}</p><p><a href="{key}/viewer.html">Play smooth rotation</a> · <a href="{key}/rotation.mp4">MP4</a></p></section>')
 (output/'viewer.html').write_text('\n'.join(index))
 save(output/'collection.json',{'recorded_at':b.stamp(),'identity':identity,'movies':movies,'replaced_mp4s':s['plan']['replacement_count'],'animation_kind':'camera-only fixed states','original_collection_sha256':s['plan']['original_collection_sha256'],'physical_time_steps':0,'relaxation_steps':0})
 with (output/'replacements.csv').open('w',newline='') as stream:
  w=csv.writer(stream,lineterminator='\n');w.writerow(['old_mp4','old_sha256','new_mp4','q','fixed_state_id','source_sha256'])
  for item in movies:
   c=item['case'];w.writerow([c['replaces'] or '',c['old_movie_sha256'] or '',c['id']+'/rotation.mp4',c['source']['q'],c['source']['id'],c['source']['sha256']])
 save(output/'status.json',{'recorded_at':b.stamp(),'phase':'rendered','movies':len(movies)});b.seal(output)


def validate(s,output):
 from electron_field_topology.sf_focused_orbits import video_info
 b.verify(output);collection=load(output/'collection.json');need(len(collection['movies'])==len(s['plan']['cases']),'Missing movie')
 browser=load(output/'browser-validation.json');need(browser['status']=='passed','Offline playback not verified')
 expected={p.relative_to(output).as_posix() for p in output.rglob('*.html')};need(expected=={x['viewer'] for x in browser['results']},'Not every viewer was tested')
 old=Path(s['plan']['original_output']);b.verify(old)
 need(sha(old/'SHA256SUMS')==s['plan']['original_seal_sha256'],'Original parent seal changed')
 for item in collection['movies']:
  case=item['case'];receipt=item['receipt'];folder=output/case['id'];b.verify(folder)
  need(sha(case['source_path'])==case['source']['sha256'],'Retained source changed')
  if case['replaces']:need(sha(old/case['replaces'])==case['old_movie_sha256'],'Original MP4 changed')
  video_info(folder/'rotation.mp4',s['settings']['fps']*s['settings']['seconds'],s['settings'])
  need(.65<=max(max(x) for x in receipt['camera']['projected_fit_samples_fraction'])<=.90,'Contour fails screen-fill/safety gate')
  need(receipt['geometry']['triangle_deletion'] is False,'Triangle-drop mesh not allowed')
 return collection


def checks(repo,s):
 paths=ORIGINAL_CHECKS(repo,s)
 run([b.python(repo),'-m','unittest','discover','-s','tests','-p','test_sf_focused_orbits.py'],repo)
 return paths


def stage_gallery(repo,s,output):
 collection=validate(s,output)
 tag='focused-orbits-'+hashlib.sha256(json.dumps(collection['identity'],sort_keys=True).encode()).hexdigest()[:12]
 asset='matter-waves-focused-orbits.zip';url='https://github.com/'+b.REPO+'/releases/download/'+tag+'/'+asset
 files={'movies.json':collection,'replacements.csv':output/'replacements.csv','browser-validation.json':output/'browser-validation.json'}
 for item in collection['movies']:
  key=item['case']['id'];files['thumbnails/'+key+'.png']=output/key/'thumbnail.png';files['provenance/'+key+'.json']=output/key/'movie.json'
 folder=b.record(repo,s,'assessment','Focused smooth camera rotations supersede active MP4 presentation',files)
 gallery=repo/'docs/visual-gallery/README.md';prior=gallery.read_text()
 text='# Matter Waves visual explanation gallery\n\n'+json.dumps(b.stamp())+'\n\n## Current movie presentation\n\n[Download the focused smooth rotations]('+url+'). Extract and open viewer.html locally. Each movie is a camera orbit of a **fixed** retained state: 30 fps, 600 frames over 20 playback seconds, fitted bounds, a single 3D panel and a labelled opacity wedge. No physical evolution or physical spinning is implied.\n\n'
 for item in collection['movies']:
  case=item['case'];row=case['source'];key=case['id'];thumb=os.path.relpath(folder/'thumbnails'/(key+'.png'),gallery.parent).replace(os.sep,'/');prov=os.path.relpath(folder/'provenance'/(key+'.json'),gallery.parent).replace(os.sep,'/')
  direct='https://github.com/'+b.REPO+'/releases/download/'+tag+'/'+key+'.mp4'
  text+=f'### Q{row["q"]}: {row["seed"]}\n\n![Focused energy contour]({thumb})\n\n{item["receipt"]["frozen_state_label"]}. [Play/download MP4]({direct}) · [Exact source and camera]({prov}).\n\n'
 text+='## Preserved analysis figures and earlier movie versions\n\nOriginal images, charts, saved-time/optimizer movies and scientific records remain unchanged in the earlier collection. New rotations replace the active movie presentation only.\n\n'+prior.split('\n',1)[1]
 if s.get('settings',{}).get('wedge_degrees',50)==0:text=text.replace('a labelled opacity wedge','an opaque surface (opacity window disabled)')
 gallery.write_text(normalize_markdown(text))
 registry=load(repo/'docs/project/roadmap.json');study=next(x for x in registry['studies'] if x['id']==s['study_id'])
 study['next_action']='Human review of focused camera-only movie presentation; original numerical gates and findings remain unchanged.'
 save(repo/'docs/project/roadmap.json',registry);run([sys.executable,repo/'scripts/project_records.py','render'],repo)
 s.update(tag=tag,asset=asset,media_record=str(folder.relative_to(repo)),direct_movies=[{'source':item['case']['id']+'/rotation.mp4','asset':item['case']['id']+'.mp4','sha256':sha(output/item['case']['id']/'rotation.mp4')} for item in collection['movies']])


b.stage_gallery=stage_gallery;b.checks=checks


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['verify','install','inventory','render','status','browser-install','browser-validate','validate','publish','merge'])
 p.add_argument('--workspace',type=Path,default=Path.home()/'ElectronFieldTopology-focused-orbits-20261121')
 p.add_argument('--output',type=Path,default=Path.home()/'Matter-Waves-focused-orbits-20261121-output')
 p.add_argument('--control',type=Path,default=Path.home()/'Matter-Waves-focused-orbits-20261121-output-control.json')
 p.add_argument('--original',type=Path,default=DEFAULT_OLD);p.add_argument('--all-q',action='store_true');p.add_argument('--solid',action='store_true');p.add_argument('--screen-idle',action='store_true')
 a=p.parse_args()
 if a.command=='verify':print('Verified package payloads:',b.verify(HERE));return
 if a.command=='install':install(a);return
 control,s,repo,output=state(a)
 # Science/display dependencies are loaded only in the isolated frozen checkout environment.
 if a.command in ['render','validate','publish'] and Path(sys.prefix).resolve()!=(repo/'.venv').resolve():
  run([b.python(repo),HERE/'handover.py',*sys.argv[1:]],repo);return
 if a.command=='inventory':inventory(s,output)
 elif a.command=='render':
  sys.path.insert(0,str(repo/'src'));render(s,output,a.screen_idle)
 elif a.command=='status':print(json.dumps({'phase':s['phase'],'render':load(output/'status.json') if (output/'status.json').exists() else 'not started','movies':len(s['plan']['cases']),'paths':{'checkout':str(repo),'output':str(output),'cache':s['cache']}},indent=2))
 elif a.command=='browser-install':
  env=output.parent/(output.name+'-browser-env')
  if not env.exists():run(['uv','venv',env])
  run(['uv','pip','install','--python',env/'bin/python','playwright=='+load(HERE/'SOURCE-CONTRACT.json')['browser_test_playwright']]);run([env/'bin/python','-m','playwright','install','chromium'])
 elif a.command=='browser-validate':
  env=output.parent/(output.name+'-browser-env');run([env/'bin/python',HERE/'browser_probe.py',output]);b.seal(output)
 elif a.command=='validate':
  sys.path.insert(0,str(repo/'src'));validate(s,output);checks(repo,s)
 elif a.command=='publish':
  sys.path.insert(0,str(repo/'src'));b.publication(control,s,repo,output)
 elif a.command=='merge':b.merge(control,s,repo)


if __name__=='__main__':
 try:main()
 except (ValueError,OSError,subprocess.SubprocessError) as error:
  print('Stopped safely: '+str(error),file=sys.stderr);sys.exit(1)
