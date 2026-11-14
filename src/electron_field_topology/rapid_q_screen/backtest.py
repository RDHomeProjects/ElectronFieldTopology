import zipfile,json,csv
from pathlib import Path
from .common import save,sha,stamp
from .policy import classify,trend
def backtest(evidence,out,p):
 out.mkdir(parents=True,exist_ok=True);rows=[]
 with zipfile.ZipFile(evidence) as z:
  if z.testzip() is not None:raise ValueError('Past evidence CRC failed')
  r=json.loads(z.read('campaign.json'))
  for key,c in r['rest'].items():
   history=json.loads(z.read('rest/'+key+'/history.json'));early=[v for v in history if v['iteration']<=50];initial=early[0];last=early[-1];decision=classify(last,initial,c['q'],p)
   row={'rest_id':key,'q':c['q'],'seed_id':c['seed_id'],'level':c['level'],'early_iteration':last['iteration'],'force_ratio':last['relative_force_l2']/initial['relative_force_l2'],'early_decision':decision['decision'],'later_native_status':c['status'],'later_stationary':c['status']=='stationary','early_trend':trend(early)};rows.append(row)
  motions=[{'case_id':k,'native_status':v.get('status'),'scope':'Outcome retained; static screen does not predict motion success'} for k,v in r['cases'].items()]
 retained={'priority_continue','static_survivor','boundary_followup'};success=[v for v in rows if v['later_stationary']];continued=[v for v in rows if v['early_decision'] in retained]
 result={'recorded_at':stamp(),'source_sha256':sha(evidence),'status':'retrospective_policy_replay_complete','rows':rows,'motion_outcomes':motions,'count':len(rows),'stationary_later':len(success),'stationary_retained':sum(v['early_decision'] in retained for v in success),'priority_count':len(continued),'priority_stationary_later':sum(v['later_stationary'] for v in continued),'hard_Q_rejections':0,'caveats':['All these records were previously inspected; this is policy engineering, not independent validation.','Unresolved endpoints are censored, not proven physical negatives.','Multiple grids share Q/seed ancestry; rows are not independent trials.','Early priority does not certify stationarity, boundary admission or future motion.']}
 save(out/'backtest.json',result)
 keys=[k for k in rows[0] if k!='early_trend']
 with (out/'backtest.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,keys,lineterminator='\n');w.writeheader();w.writerows({k:v[k] for k in keys} for v in rows)
 return result
