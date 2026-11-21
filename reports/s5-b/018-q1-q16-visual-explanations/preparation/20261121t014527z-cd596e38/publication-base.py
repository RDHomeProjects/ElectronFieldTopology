#!/usr/bin/env python3
"""Local workstation handover. GitHub operations occur only when run on the zbook."""
import argparse
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED

HERE=Path(__file__).resolve().parent
REPO='RDHomeProjects/ElectronFieldTopology'
SLUG='q1-q16-visual-explanations'
BRANCH='visual/q1-q16-explanations-20261121'


def need(ok,message):
 if not ok:raise ValueError(message)


def stamp():
 t=datetime.now(timezone.utc)
 return {'utc':t.isoformat(),'melbourne':t.astimezone(ZoneInfo('Australia/Melbourne')).isoformat()}


def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
 return h.hexdigest()


def load(p):return json.loads(Path(p).read_text())


def save(p,d):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp')
 tmp.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n');tmp.replace(p)


def run(cmd,cwd=None,capture=False):
 env=dict(os.environ,GIT_OPTIONAL_LOCKS='0',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',MPLBACKEND='Agg',PYTHONDONTWRITEBYTECODE='1')
 r=subprocess.run([str(x) for x in cmd],cwd=cwd,env=env,check=True,text=True,stdout=subprocess.PIPE if capture else None)
 return r.stdout.strip() if capture else None


def seal(root):
 root=Path(root);(root/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.relative_to(root).as_posix()+'\n' for p in sorted(root.rglob('*')) if p.is_file() and p!=root/'SHA256SUMS'))


def verify(root):
 root=Path(root);covered=set()
 for line in (root/'SHA256SUMS').read_text().splitlines():
  h,n=line.split('  ',1);p=Path(n)
  need(not p.is_absolute() and '..' not in p.parts and '\\' not in n and n not in covered,'Bad seal path')
  need(not (root/p).is_symlink() and (root/p).resolve().is_relative_to(root.resolve()) and sha(root/p)==h,'Seal mismatch: '+n);covered.add(n)
 need(covered=={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=root/'SHA256SUMS'},'Incomplete recursive checksum coverage')
 return len(covered)


def guard(p):
 p=Path(p).expanduser().resolve()
 need(not any(x in str(p) for x in ['adaptive-q-screen','adaptive-q17-q32']),'Screen checkout/output forbidden')
 return p


def python(repo):return repo/'.venv/bin/python'


def module(repo):
 spec=importlib.util.spec_from_file_location('visual_project_records',repo/'scripts/project_records.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def record(repo,state,role,title,files):
 rid=datetime.now(timezone.utc).strftime('%Y%m%dt%H%M%Sz-')+os.urandom(4).hex()
 folder=repo/state['study_path']/({'preparation':'preparation','assessment':'assessments'}[role])/rid
 folder.mkdir(parents=True)
 for name,value in files.items():
  p=folder/name;p.parent.mkdir(parents=True,exist_ok=True)
  if isinstance(value,Path):shutil.copyfile(value,p)
  elif isinstance(value,str):p.write_text(value)
  else:save(p,value)
 save(folder/'record.json',{'study_id':state['study_id'],'record_id':rid,'role':role,'recorded_at':stamp(),'source_commit':state['base'],
                          'outcome':title,'model_and_units':'Neutral SF model units; visualization only; original scientific gates unchanged',
                          'field_retention':'Original retained sources read-only; no full fields enter Git',
                          'source_selection_sha256':sha(HERE/'selection.json'),'limitations':['No new relaxation or evolution; no physical stability/electron claim.']})
 if not (folder/'README.md').exists():(folder/'README.md').write_text('# '+title+'\n\n'+json.dumps(stamp())+'\n\nSee the [central visual gallery](../../../../../docs/visual-gallery/README.md). Existing scientific findings and gates are preserved.\n')
 seal(folder)
 registry=load(repo/'docs/project/roadmap.json')
 study=next(s for s in registry['studies'] if s['id']==state['study_id'])
 entry={'role':role,'path':(folder.relative_to(repo)/'README.md').as_posix(),'label':title}
 study['records'].append(entry)
 # Companion links appear in the authoritative catalogs for the existing low-Q/closure studies.
 if role=='assessment':
  for s in registry['studies']:
   if s['id'] in {'s5-b-006','s5-b-009','s5-b-010','s5-b-012','s5-b-013','s5-b-014','s5-b-015'}:
    s['records'].append(dict(entry))
 registry['updated_at']=stamp();save(repo/'docs/project/roadmap.json',registry)
 run([sys.executable,repo/'scripts/project_records.py','render'],repo)
 return folder


def install(work,output):
 work=guard(work);output=guard(output)
 need(work!=output and not output.is_relative_to(work) and not work.is_relative_to(output),'Checkout and output must be separate')
 need(not work.exists(),'Choose a new empty checkout; existing work is never overwritten')
 output.mkdir(parents=True,exist_ok=True)
 state_path=output.parent/(output.name+'-control.json');need(not state_path.exists(),'Existing control state; use status/resume')
 verify(HERE)
 run(['git','clone','https://github.com/'+REPO+'.git',work])
 base=run(['git','rev-parse','HEAD'],work,True)
 run(['git','switch','-c',BRANCH],work)
 run(['git','bundle','create',output.parent/(output.name+'-baseline.bundle'),'--all'],work)
 for name,h in load(HERE/'SOURCE-CONTRACT.json')['modules'].items():
  need(sha(work/'src/electron_field_topology'/name)==h,'Source contract changed for '+name+'; preserve checkout and review current source before rendering')
 run(['uv','sync','--frozen','--all-groups'],work)
 for p in (HERE/'payload').rglob('*'):
  if p.is_file():
   dst=work/p.relative_to(HERE/'payload');need(not dst.exists(),'Additive tool path already exists: '+str(dst));dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
 registry=load(work/'docs/project/roadmap.json')
 need(not any(s['slug']==SLUG for s in registry['studies']),'Visual study already registered; use original control state')
 number=max(s['number'] for s in registry['studies'] if s['stage']=='s5-b')+1
 sid=f's5-b-{number:03d}';study_path=f'reports/s5-b/{number:03d}-{SLUG}'
 registry['studies'].append({'id':sid,'stage':'s5-b','number':number,'slug':SLUG,'title':'Q1 to Q16 retained-field visual explanations','state':'prepared','gate':'not-applicable',
 'question':'How do authenticated retained spatial fields explain existing Q1 to Q16 outcomes?',
 'finding':'Additive renderer prepared. Q1 remains parked; numerical gates and outcomes are unchanged.',
 'next_action':'Render authenticated retained fields when resources permit, validate decoding/offline playback, then publish companion records.',
 'exit_evidence':'Q1 to Q16 spatial coverage, explicit failures and gaps, source hashes, high-resolution PNGs, offline viewers and verified Release media.',
 'depends_on':[s['id'] for s in registry['studies'] if s['id']=='s5-b-010'],'requirements':['VIS-001','VIS-002','VIS-003','VIS-004','REP-001','REP-002'],'specifications':['docs/visual-gallery/README.md'],'records':[]})
 save(work/'docs/project/roadmap.json',registry)
 gallery=work/'docs/visual-gallery/README.md';gallery.parent.mkdir(parents=True)
 gallery.write_text('# Matter Waves visual explanation gallery\n\n'+json.dumps(stamp())+'\n\nRead Q2 first as the numerical reference. Q1 is parked context; Q3 has mixed motion outcomes, and Q4–Q16 retain all failed, unresolved and deferred findings.\n\n'+(HERE/'INTRODUCTION.md').read_text()+'\n\nThe preparation record is listed in the [S5-B catalog](../../reports/s5-b/INDEX.md). Production links will be added only after media generation and verification.\n')
 for name in ['docs/offline-renderer.md','docs/models/SF-candidate-survey.md','docs/models/SF-physical-time.md','docs/models/SF-J2015-static.md']:
  p=work/name
  if p.exists():
   rel=os.path.relpath(gallery,p.parent).replace(os.sep,'/')
   p.write_text(p.read_text()+'\n## Companion visual explanations\n\nSee the [Q1–Q16 visual explanation gallery]('+rel+'). Numerical records and scientific outcomes remain unchanged.\n')
 readme=work/'README.md';text=readme.read_text();text=text.replace('## Start here\n','## Start here\n\n[Q1–Q16 visual explanation gallery](docs/visual-gallery/README.md).\n',1);readme.write_text(text)
 state={'recorded_at':stamp(),'workspace':str(work),'output':str(output),'base':base,'package_sha256':sha(HERE/'SHA256SUMS'),'study_id':sid,'study_path':study_path,'branch':BRANCH,'overrides':{},'phase':'installed'}
 record(work,state,'preparation','Visual tooling preparation; no production media',{'selection.json':HERE/'selection.json','source-contract.json':HERE/'SOURCE-CONTRACT.json','evidence-review.md':HERE/'EVIDENCE-REVIEW.md'})
 state['generated']=list(module(work).documents(load(work/'docs/project/roadmap.json'),work))
 state['allowed_existing']=['README.md','docs/project/roadmap.json','docs/offline-renderer.md','docs/models/SF-candidate-survey.md','docs/models/SF-physical-time.md','docs/models/SF-J2015-static.md',*state['generated']]
 save(state_path,state);print('Installed. Control state:',state_path)


def get_state(args):
 p=guard(args.control);s=load(p);need(sha(HERE/'SHA256SUMS')==s['package_sha256'],'Handover package changed');return p,s,guard(s['workspace']),guard(s['output'])


def inventory(state,repo,output,hash_fields=False):
 rows=[]
 selection=load(HERE/'selection.json')
 for row in selection['records']:
  p=Path(state['overrides'].get(row['id'],Path.home()/row['home_path']))
  guard(p)
  status='missing'
  if p.is_file():
   status='present; SHA pending'
   if hash_fields:need(sha(p)==row['sha256'],'Source differs: '+row['id']);status='hash verified'
  rows.append({'id':row['id'],'q':row['q'],'path':str(p),'sha256_expected':row['sha256'],'status':status})
 save(output.parent/(output.name+'-inventory.json'),{'recorded_at':stamp(),'rows':rows,'hashes_replayed':hash_fields})
 print(json.dumps({'recorded_at':stamp(),'states':len(rows),'present':sum(r['status']!='missing' for r in rows),'missing':[r['id'] for r in rows if r['status']=='missing']},indent=2))


def recover(state,repo,output):
 sys.path.insert(0,str(repo/'src'))
 from electron_field_topology.sf_higher_q_sources import recover as restore
 for row in load(HERE/'selection.json')['records']:
  p=Path(state['overrides'].get(row['id'],Path.home()/row['home_path']))
  if p.is_file():continue
  if 'recovery' in row:
   p=restore(row['recovery'],output.parent/(output.name+'-recovered'),repo)
   need(sha(p)==row['sha256'],'Recovered field differs');state['overrides'][row['id']]=str(p)
 # No solver fallback for other missing fields. Selective verified restores may be mapped explicitly.


def checks(repo,state):
 run([python(repo),'-m','unittest','discover','-s','tests','-p','test_sf_visual_collection.py'],repo)
 run([sys.executable,'scripts/project_records.py','check','--compare-ref',state['base']],repo)
 run([sys.executable,'scripts/check_docs.py'],repo)
 for script in ['scripts/test_project_records.py','scripts/test_workstation_archive.py']:
  run([sys.executable,script],repo)
 # Stage only additive visual work and authoritative generated navigation.
 changed=run(['git','diff','--name-only',state['base']],repo,True).splitlines()
 untracked=run(['git','ls-files','--others','--exclude-standard'],repo,True).splitlines()
 allowed_prefixes=[state['study_path']+'/', 'docs/visual-gallery/']
 allowed_files={'src/electron_field_topology/sf_visual_collection.py','tests/test_sf_visual_collection.py',*state['allowed_existing']}
 paths=sorted(set(changed+untracked))
 for p in paths:
  need(p in allowed_files or any(p.startswith(x) for x in allowed_prefixes),'Unexpected checkout change; not staged: '+p)
 if paths:run(['git','add','--',*paths],repo)
 run(['git','diff','--cached','--check'],repo)
 return paths


def validate_media(repo,output):
 sys.path.insert(0,str(repo/'src'))
 from electron_field_topology.sf_visual_collection import verify_seal,decode
 verify_seal(output)
 d=load(output/'collection.json')
 need(d['complete_q_coverage']==list(range(1,17)) and not d['missing'],'Coverage/missing-input gate blocks publication')
 need((output/'browser-validation.json').exists(),'Run browser validation before publication')
 br=load(output/'browser-validation.json');need(br['status']=='passed' and br['results'],'No successful browser receipt')
 from PIL import Image
 for row in d['visuals']:
  folder=output/row['source']['id'];verify_seal(folder)
  with Image.open(folder/'spatial.png') as im:need(im.width>=3840 and im.height==im.width*9//16,'Invalid production image size')
  # Re-authenticate retained input before publishing a claim about its identity.
  need(sha(row['source_path'])==row['source']['sha256'],'Source changed since rendering')
 for p in output.rglob('*.mp4'):decode(p)
 viewers={p.relative_to(output).as_posix() for p in output.rglob('*.html')}
 need(viewers=={r['viewer'] for r in br['results']},'Not every offline viewer was browser-tested')
 return d


def stage_gallery(repo,state,output):
 d=validate_media(repo,output)
 tag='visual-q1-q16-'+hashlib.sha256(json.dumps(d['identity'],sort_keys=True).encode()).hexdigest()[:12]
 asset='matter-waves-q1-q16-offline.zip'
 url='https://github.com/'+REPO+'/releases/download/'+tag+'/'+asset
 files={'collection-summary.json':{'recorded_at':stamp(),'identity':d['identity'],'coverage':d['complete_q_coverage'],'missing':d['missing'],'media_url':url},'browser-validation.json':output/'browser-validation.json'}
 for v in d['visuals']:
  key=v['source']['id'];files['provenance/'+key+'.json']=output/key/'visual.json';files['thumbnails/'+key+'.png']=output/key/'thumbnail.png'
 folder=record(repo,state,'assessment','Additive visual explanations; original numerical findings unchanged',files)
 text='# Q1–Q16 visual explanation gallery\n\n'+json.dumps(stamp())+'\n\n[Download the complete offline collection]('+url+'). Extract it and open viewer.html locally. GitHub does not execute repository HTML. [Release assets](https://github.com/'+REPO+'/releases/tag/'+tag+') include the checksum.\n\n'+(HERE/'INTRODUCTION.md').read_text()+'\n\n'
 for q in [2,1,*range(3,17)]:
  text+=f'## Q{q}'+(' — parked context' if q==1 else '')+'\n\n'
  for v in d['visuals']:
   row=v['source']
   if row['q']!=q or row['kind']!='static':continue
   rel=os.path.relpath(folder/'thumbnails'/ (row['id']+'.png'),repo/'docs/visual-gallery').replace(os.sep,'/')
   prov=os.path.relpath(folder/'provenance'/(row['id']+'.json'),repo/'docs/visual-gallery').replace(os.sep,'/')
   text+=f'### {row["seed"]} — {row["stage"]}\n\n![Retained numerical spatial view]({rel})\n\n{row["interpretation"]}\n\n[Source, metrics and render settings]({prov}). Full PNG and any video are in the offline download.\n\n'
 (repo/'docs/visual-gallery/README.md').write_text(text)
 registry=load(repo/'docs/project/roadmap.json');study=next(s for s in registry['studies'] if s['id']==state['study_id']);study['state']='assessed';study['finding']='Authenticated spatial coverage Q1–Q16 and bounded saved-state/camera/optimizer visualizations; no scientific gate changes.';study['next_action']='Human review of the additive collection; retain all original numerical limits.';save(repo/'docs/project/roadmap.json',registry)
 run([sys.executable,repo/'scripts/project_records.py','render'],repo)
 state.update(tag=tag,asset=asset,media_record=str(folder.relative_to(repo)))


def transfer_release_assets(tag, assets, release_dir, upload=True):
 # No --clobber: identical bytes can resume; a different same-name asset stops.
 for asset in assets:
  if upload:
   with tempfile.TemporaryDirectory(dir=release_dir) as tmp:
    found=subprocess.run(['gh','release','download',tag,'--repo',REPO,'--pattern',asset.name,'--dir',tmp],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
    if found:need(sha(Path(tmp)/asset.name)==sha(asset),'Different same-name Release asset; never clobbered')
    else:run(['gh','release','upload',tag,asset,'--repo',REPO])
  with tempfile.TemporaryDirectory(dir=release_dir) as tmp:
   run(['gh','release','download',tag,'--repo',REPO,'--pattern',asset.name,'--dir',tmp])
   need(sha(Path(tmp)/asset.name)==sha(asset),'Downloaded Release asset differs: '+asset.name)


def publication(control,state,repo,output):
 release_dir=output.parent/(output.name+'-release');release_dir.mkdir(exist_ok=True)
 if not state.get('tag'):
  stage_gallery(repo,state,output);save(control,state)
 paths=checks(repo,state)
 if run(['git','diff','--cached','--name-only'],repo,True):run(['git','commit','-m','Add focused smooth camera rotation videos'],repo)
 archive=release_dir/state['asset']
 if archive.exists():
  need((release_dir/'archive-source.json').exists() and load(release_dir/'archive-source.json')['output_seal_sha256']==sha(output/'SHA256SUMS'),'Offline archive was built from a different output seal; preserve it and use a new publication tree')
 if not archive.exists():
  with ZipFile(archive,'x',compression=ZIP_DEFLATED,compresslevel=1) as z:
   for p in sorted(output.rglob('*')):
    if p.is_file():z.write(p,p.relative_to(output).as_posix())
  with ZipFile(archive) as z:need(z.testzip() is None,'Offline ZIP CRC failed')
  save(release_dir/'archive-source.json',{'recorded_at':stamp(),'output_seal_sha256':sha(output/'SHA256SUMS'),'archive_sha256':sha(archive)})
 need(archive.stat().st_size<1024**3,'Media exceeds 1 GiB asset budget; preserve outputs and split by collection before publishing')
 digest=sha(archive);payloads=[archive]
 for movie in state.get('direct_movies',[]):
  source=output/movie['source'];need(sha(source)==movie['sha256'],'Direct movie source changed')
  target=release_dir/movie['asset']
  if target.exists():need(sha(target)==movie['sha256'],'Staged direct movie differs')
  else:shutil.copyfile(source,target)
  need(target.stat().st_size<1024**3,'Individual movie exceeds asset budget');payloads.append(target)
 (release_dir/'SHA256SUMS').write_text(''.join(sha(asset)+'  '+asset.name+'\n' for asset in payloads))
 assets=payloads+[release_dir/'SHA256SUMS']
 run(['git','push','-u','origin',state['branch']],repo)
 # A draft stays unpublished until uploaded bytes have been downloaded and verified.
 exists=subprocess.run(['gh','release','view',state['tag'],'--repo',REPO],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
 if not exists:
  run(['gh','release','create',state['tag'],'--repo',REPO,'--draft','--target',run(['git','rev-parse','HEAD'],repo,True),'--title','Matter Waves focused smooth rotations','--notes','Smooth, contour-focused camera orbits of frozen retained states. Earlier media remain archived; these rotations are not physical evolution. Download the ZIP, verify SHA256SUMS and open viewer.html.'])
 transfer_release_assets(state['tag'],assets,release_dir,upload=True)
 run(['gh','release','edit',state['tag'],'--repo',REPO,'--draft=false'])
 # Verify every movie, ZIP and checksum again after public publication.
 transfer_release_assets(state['tag'],assets,release_dir,upload=False)
 if not state.get('release_verified_record'):
  folder=record(repo,state,'assessment','Release media download and checksum verification',{'release-verification.json':{'recorded_at':stamp(),'tag':state['tag'],'asset':archive.name,'bytes':archive.stat().st_size,'sha256':digest,'direct_movies':state.get('direct_movies',[]),'draft_and_public_downloads_verified':True,'offline_browser_tested':True,'github_html_execution_tested':False}})
  state['release_verified_record']=str(folder.relative_to(repo));save(control,state)
 checks(repo,state)
 if run(['git','diff','--cached','--name-only'],repo,True):run(['git','commit','-m','Record verified visual Release downloads'],repo)
 run(['git','push'],repo)
 body=release_dir/'PR-BODY.md';body.write_text('## Result\n\nReplace active movie presentation with contour-focused, single-panel camera orbits: 30 fps, 600 frames over 20 seconds, fixed fitted crop, native-ROI geometry and a labelled opacity wedge. Camera-only rotations freeze exact retained states; original physical-time/optimizer movies and all prior records remain archived. No solver or scientific gate changes.\n\n## Validation\n\nSource/parent hashes, crop/coordinate and opacity controls, smooth periodic angles, real H.264/yuv420p frame-count/rate/full decoding, offline file-URL playback, recursive checksums, repository validators and staged Git whitespace checks. Verified Release downloads; hosted checks must pass before squash merge.\n')
 prs=json.loads(run(['gh','pr','list','--repo',REPO,'--head',state['branch'],'--state','open','--json','number,url'],repo,True))
 if not prs:run(['gh','pr','create','--repo',REPO,'--head',state['branch'],'--base','main','--title','Improve focused rotation video presentation','--body-file',body],repo)
 pr=json.loads(run(['gh','pr','view',state['branch'],'--repo',REPO,'--json','number,url'],repo,True));state.update(pr=pr,phase='published',published_paths=checks(repo,state));save(control,state)
 print('PR ready for hosted checks:',pr['url'])


def merge(control,state,repo):
 need(state.get('pr') and state.get('release_verified_record'),'Verified publication required')
 number=str(state['pr']['number'])
 run(['gh','pr','checks',number,'--repo',REPO,'--watch'],repo)
 info=json.loads(run(['gh','pr','view',number,'--repo',REPO,'--json','headRefOid,statusCheckRollup'],repo,True))
 need(info['headRefOid']==run(['git','rev-parse','HEAD'],repo,True),'PR head differs from validated checkout')
 need(info['statusCheckRollup'],'No hosted checks observed; merge blocked')
 for check in info['statusCheckRollup']:
  need(check.get('conclusion') in {'SUCCESS','NEUTRAL','SKIPPED'} or check.get('state')=='SUCCESS','Hosted check not successful')
 expected={p:run(['git','rev-parse','HEAD:'+p],repo,True) for p in state['published_paths'] if (repo/p).is_file()}
 run(['gh','pr','merge',number,'--repo',REPO,'--squash','--delete-branch'],repo)
 info=json.loads(run(['gh','pr','view',number,'--repo',REPO,'--json','state,mergeCommit,url'],repo,True));need(info['state']=='MERGED','Merge unconfirmed')
 run(['git','fetch','origin','main'],repo)
 merged=info['mergeCommit']['oid']
 for p,oid in expected.items():need(run(['git','rev-parse',merged+':'+p],repo,True)==oid,'Squash-published content differs: '+p)
 state.update(phase='merged',merge=info,merged_at=stamp());save(control,state);print(info['url'])


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['verify','install','inventory','recover','render','status','browser-install','browser-validate','validate','publish','merge'])
 p.add_argument('--workspace',type=Path,default=Path.home()/'ElectronFieldTopology-visual-q1-q16-20261121');p.add_argument('--output',type=Path,default=Path.home()/'Matter-Waves-visual-output-20261121')
 p.add_argument('--control',type=Path,default=Path.home()/'Matter-Waves-visual-output-20261121-control.json');p.add_argument('--hash-fields',action='store_true');p.add_argument('--screen-idle',action='store_true');p.add_argument('--source-map',type=Path)
 a=p.parse_args()
 if a.command=='verify':print('Verified',verify(HERE),'package payloads');return
 if a.command=='install':install(a.workspace,a.output);return
 control,state,repo,output=get_state(a)
 if a.source_map:
  mapping=load(a.source_map);ids={r['id'] for r in load(HERE/'selection.json')['records']};need(set(mapping)<=ids,'Unknown source-map ID');state['overrides'].update({k:str(guard(v)) for k,v in mapping.items()});save(control,state)
 if a.command=='inventory':inventory(state,repo,output,a.hash_fields)
 elif a.command=='recover':
  script='import importlib.util; from pathlib import Path; spec=importlib.util.spec_from_file_location("visual_handover",'+repr(str(HERE/'handover.py'))+'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); state=m.load('+repr(str(control))+'); m.recover(state,Path(state["workspace"]),Path(state["output"])); m.save('+repr(str(control))+',state)'
  run([python(repo),'-c',script],repo);state=load(control);inventory(state,repo,output)
 elif a.command=='render':
  script='from electron_field_topology.sf_visual_collection import render_collection; import json; from pathlib import Path; s=json.loads(Path('+repr(str(control))+').read_text()); render_collection(json.loads(Path('+repr(str(HERE/'selection.json'))+').read_text()),s["output"],Path.home(),s["overrides"],screen_idle='+repr(a.screen_idle)+')'
  run([python(repo),'-c',script],repo)
 elif a.command=='status':
  print(json.dumps({'control':state,'render':load(output/'status.json') if (output/'status.json').exists() else 'not rendered'},indent=2))
 elif a.command=='browser-install':
  browser=output.parent/(output.name+'-browser-env')
  if not browser.exists():run(['uv','venv',browser])
  run(['uv','pip','install','--python',browser/'bin/python','playwright=='+load(HERE/'SOURCE-CONTRACT.json')['browser_test_playwright']]);run([browser/'bin/python','-m','playwright','install','chromium'])
 elif a.command=='browser-validate':
  browser=output.parent/(output.name+'-browser-env');run([browser/'bin/python',HERE/'browser_probe.py',output]);seal(output)
 elif a.command=='validate':
  script='import importlib.util; from pathlib import Path; spec=importlib.util.spec_from_file_location("visual_handover",'+repr(str(HERE/'handover.py'))+'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); m.validate_media(Path('+repr(str(repo))+'),Path('+repr(str(output))+'))'
  run([python(repo),'-c',script],repo);paths=checks(repo,state);save(output.parent/(output.name+'-validation.json'),{'recorded_at':stamp(),'status':'passed','paths':paths,'hosted_checks':'pending local publication'})
 elif a.command=='publish':
  if Path(sys.prefix).resolve()!=(repo/'.venv').resolve():
   run([python(repo),HERE/'handover.py',*sys.argv[1:]],repo)
  else:publication(control,state,repo,output)
 elif a.command=='merge':merge(control,state,repo)


if __name__=='__main__':
 try:main()
 except (ValueError,OSError,subprocess.SubprocessError) as exc:
  print('Stopped safely: '+str(exc),file=sys.stderr);sys.exit(1)
