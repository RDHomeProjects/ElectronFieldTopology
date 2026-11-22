from common import save,load,stamp,need
from integrity import reserves
CONTEXT={}
def charge(kind='production_step'):
    out=CONTEXT['out'];path=out/'motion-attempt-ledger.json';ledger=load(path) if path.exists() else []
    need(len(ledger)<300,'Conditional motion integration-call allocation exhausted')
    ledger.append({'recorded_at':stamp(),'attempt':len(ledger)+1,'charged_before_execution':True,'kind':kind});save(path,ledger)
def resources(folder,p):
    out=CONTEXT['out']
    if CONTEXT['stop']() or (out/'STOP.json').exists():raise KeyboardInterrupt('Orderly motion pause')
    reserves(out);charge()
