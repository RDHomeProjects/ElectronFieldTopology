"""Authenticated read-only endpoint triage; unknown native metadata is deferred."""
import gc,re,time,zipfile,json,csv,io
from pathlib import Path
import numpy as np
from common import ROOT,load,save,sha,need,stamp,canonical
from integrity import checked_evidence,reserves
from evaluations import metrics,gate_result,array_sha
from measurements import localized
from resources import geometry_budget
CACHE={}

def walk(v):
    if isinstance(v,dict):
        yield v
        for x in v.values():yield from walk(x)
    elif isinstance(v,list):
        for x in v:yield from walk(x)

def archive_for(path):
    for folder in path.parents:
        if (folder/'evidence.zip').is_file():return folder
        if folder.name=='artifacts':break
    raise RuntimeError('No retained compact source archive identifies this field')

def metadata(run,expected=None):
    key=str(run)
    if key not in CACHE:
        digest=sha(run/'evidence.zip');docs={}
        if expected:need(digest==expected,'Source archive changed since the supplied storage audit')
        with zipfile.ZipFile(run/'evidence.zip') as z:
            from pathlib import PurePosixPath
            names=z.namelist();need(len(names)==len(set(names)) and z.testzip() is None,'Source archive CRC/duplicate failure')
            need(all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts for n in names),'Unsafe source archive member')
            if 'SHA256SUMS' in names:hashes=checked_evidence(run/'evidence.zip')
            elif 'evidence-hashes.json' in names:
                hashes=json.loads(z.read('evidence-hashes.json'))['sha256']
                need(set(hashes)|{'evidence-hashes.json'}==set(names),'Legacy source coverage differs')
                import hashlib
                for n,h in hashes.items():need(hashlib.sha256(z.read(n)).hexdigest()==h,'Legacy source payload differs: '+n)
            else:
                need(expected is not None,'Legacy archive has neither a known compact manifest nor a pinned audit hash');hashes={n:None for n in names}
            for n in hashes:
                if n.endswith('.json') and not n.startswith(('handover/','review/')) and z.getinfo(n).file_size<=8*1024**2:
                    try:docs[n]=json.loads(z.read(n))
                    except (ValueError,UnicodeDecodeError):continue
        CACHE[key]=(digest,docs)
    if expected:need(CACHE[key][0]==expected,'Conflicting source archive pin')
    return CACHE[key]

def declared_hash(docs,digest,relative):
    evidence=[]
    for name,doc in docs.items():
        for d in walk(doc):
            for k,v in d.items():
                if isinstance(v,str) and v==digest and (k in {'sha256','field_sha256','checkpoint_sha256','endpoint_sha256','latest_sha256'} or str(k).endswith('.npz')):evidence.append(name)
    need(evidence,'Field SHA256 is not declared by the verified source compact records');return sorted(set(evidence))

def geometry_from(z,docs,relative,shape):
    nodes=shape[0];need(shape==(nodes,nodes,nodes,3),'Noncubic or non-vector field requires separate registration')
    if 'h' in z:
        h=float(z['h']);need(np.isfinite(h) and h>0,'Invalid stored spacing');return (h*(nodes-1),)*3,'native NPZ h'
    folder=str(Path(relative).parent);ordered=sorted(docs.items(),key=lambda x:(not x[0].startswith(folder+'/'),not x[0].startswith('handover/SOURCE'),len(x[0])))
    for name,doc in ordered:
        if not name.startswith(folder+'/'):continue
        for d in walk(doc):
            if d.get('shape')==list(shape[:3]) and isinstance(d.get('lengths'),list) and len(d['lengths'])==3:return tuple(map(float,d['lengths'])),name
            if d.get('nodes')==nodes and isinstance(d.get('length'),(int,float)):return (float(d['length']),)*3,name
    raise RuntimeError('Native box/spacing is not authenticated for this checkpoint schema')

def triage(home,item,out,source):
    result={'recorded_at':stamp(),**item,'status':'deferred','physical_Q_rejected':False,'optimizer_attempts':0,'physical_time_steps':0};path=home/item['relative_home_path'];clock=time.perf_counter()
    try:
        need(path.is_file() and not path.is_symlink(),'Retained endpoint missing or linked')
        run=archive_for(path);evidence_sha,docs=metadata(run,item.get('audit_source_evidence_sha256'));timer=time.perf_counter();digest=sha(path);hash_seconds=time.perf_counter()-timer;relative=path.relative_to(run).as_posix();declared=declared_hash(docs,digest,relative)
        with zipfile.ZipFile(path) as z:need(z.testzip() is None,'NPZ CRC failure')
        timer=time.perf_counter()
        with np.load(path,allow_pickle=False) as z:
            key='field' if 'field' in z else 'n' if 'n' in z else None;need(key is not None,'Unrecognized full-field key');n=z[key].copy();need(n.dtype==np.float64 and np.isfinite(n).all(),'Native float64 field is required; no normalization or promotion is performed')
            if 'expected_q' in z:need(int(z['expected_q'])==item['q_label'],'Stored charge label differs from catalogue')
            if str(path)==source['endpoint'] or str(path)==source['contrast']:lengths=(30.72,)*3;geometry_origin='Pinned completed conditioning SOURCE.json'
            else:lengths,geometry_origin=geometry_from(z,docs,relative,n.shape)
            iteration=int(z['iteration']) if 'iteration' in z else None;alpha=float(z['alpha']) if 'alpha' in z else None;memory={k:bool(k in z and z[k].size) for k in ['old_g','old_z','direction']}
            if 'model_id' in z:need(str(z['model_id'])=='SF-relativistic-neutral-v1','Different physical model')
            if 'scheme' in z:need(str(z['scheme'])=='D4-action-projected-RK4-v1','Different native scheme/operator')
        # Only known native D4 campaign roots enter the registry. Cell historical
        # fields are represented by separate, explicitly deferred ledger rows.
        need(any(s in str(run) for s in ['intermediate-q-survey','rapid-q-screen/','rapid-q-followup/','targeted-q-diagnostic/','targeted-q-campaign2/','adaptive-q17-q32-screen/','q17-q32-policy-v2/','q21-q22-controlled-evaluation/','q21-final-tranche-q22-recovery/','q21-conditioning-calibration/']),'Native operator registry does not qualify this run')
        load_seconds=time.perf_counter()-timer;admission=geometry_budget(n.shape[0],'cpu');need(admission['passed'],'Read-only geometry exceeds current host memory reserve')
        from electron_field_topology.sf_time import Grid
        g=Grid(tuple(n.shape[:3]),lengths,'fixed');before=array_sha(n);p=load(ROOT/'PLAN.json')['registered_gates'];timer=time.perf_counter();m=metrics(n,g,p);metrics_seconds=time.perf_counter()-timer;gates=gate_result(m,item['q_label'],p);classes=[]
        if not gates['representation']:classes.append('representation_unresolved')
        if not gates['boundary_admitted']:classes.append('boundary_limited')
        if m['max_neighbour_angle']>np.pi/6:classes.append('resolution_warning_angle_above_30_degrees_not_a_gate')
        if not gates['strict_stationary']:classes.append('core_or_optimizer_unresolved')
        if gates['all_readiness_gates']:classes.append('already_admitted_reference_preserved')
        # Detailed spatial/spectral summaries are reserved for the stratified pilot,
        # avoiding repeating heavy diagnostics on every old stage/shift copy.
        detail=localized(n,g,spectral=item.get('pilot_diagnostic',False)) if gates['representation'] else None
        need(array_sha(n)==before and sha(path)==digest,'Read-only replay changed or raced the source')
        result.update(status='native_D4_replayed',source_sha256=digest,source_evidence_sha256=evidence_sha,authenticated_declarations=declared,native_operator='D4-action-projected-RK4-v1',native_iteration=iteration,alpha=alpha,memory_present=memory,shape=list(g.shape),lengths=list(g.lengths),spacing=list(g.spacing),geometry_origin=geometry_origin,array_sha256=before,metrics=m,gates=gates,classes=classes,localized=detail,source_modified=False,timing={'source_field_hash_seconds':hash_seconds,'field_load_seconds':load_seconds,'metrics_seconds':metrics_seconds,'localization_seconds':detail['wall_seconds'] if detail else 0.})
        del n;gc.collect()
    except (RuntimeError,ValueError,KeyError,OSError,zipfile.BadZipFile) as error:result['reason']=str(error)
    result['wall_seconds']=time.perf_counter()-clock;save(out/'bulk'/(item['id']+'.json'),result);return result

def run(home,out,source,stop,phase,progress=None):
    rows=[]
    for i,item in enumerate(load(ROOT/'CATALOGUE.json')['candidates']):
        if stop() or (out/'STOP.json').exists():raise KeyboardInterrupt('Orderly retained-field audit pause')
        phase.clear();phase.update(name='bulk-native-replay',candidate=item['id'],q=item['q_label'],index=i+1,total=len(load(ROOT/'CATALOGUE.json')['candidates']))
        path=out/'bulk'/(item['id']+'.json')
        if path.exists():
            row=load(path)
            if row.get('source_sha256'):need(sha(home/item['relative_home_path'])==row['source_sha256'],'Retained source changed after bulk replay')
        else:reserves(out);row=triage(home,item,out,source)
        rows.append(row)
        if progress is not None:progress()
    summary=[]
    for q in range(2,33):
        group=[r for r in rows if r['q_label']==q];summary.append({'q':q,'catalogued':len(group),'replayed':sum(r['status']=='native_D4_replayed' for r in group),'deferred':sum(r['status']=='deferred' for r in group),'all_readiness_passes':sum(r.get('gates',{}).get('all_readiness_gates',False) for r in group),'scope':'Catalogue coverage only; untested seed families and historical cell-native fields remain distinct'})
    result={'recorded_at':stamp(),'rows':rows,'q_summary':summary,'deferred':['Historical cell-native Q22 success is retained as historical evidence; missing exact native geometry/operator qualification is not replaced with D4 admission.','Time-evolution frames, unretained pre-loss states and variants outside the finite endpoint catalogue are not manufactured.'],'optimizer_attempts':0,'physical_time_steps':0};save(out/'BULK-LEDGER.json',result)
    flat=[{'utc':r['recorded_at']['utc'],'melbourne':r['recorded_at']['melbourne'],'q':r['q_label'],'candidate':r['id'],'source':r['relative_home_path'],'status':r['status'],'reason':r.get('reason',''),'classes':'; '.join(r.get('classes',[])),**{k:r.get('metrics',{}).get(k) for k in ['energy','relative_force_l2','acceleration_max','tail_fraction','guard_fraction','max_neighbour_angle']}} for r in rows]
    buf=io.StringIO(newline='');writer=csv.DictWriter(buf,fieldnames=list(flat[0]) if flat else ['q'],lineterminator='\n');writer.writeheader();writer.writerows(flat);(out/'BULK-LEDGER.csv').write_text(buf.getvalue());return result
