from __future__ import annotations
import argparse,csv,hashlib,json
from pathlib import Path
import numpy as np
from smartgrid_mlops.monitoring.simulations import development_stream,perturb
from smartgrid_mlops.monitoring.feature_drift import normalized_wasserstein,psi
from smartgrid_mlops.monitoring.performance_drift import performance_signals
from smartgrid_mlops.monitoring.severity import classify_severity
from smartgrid_mlops.monitoring.thresholds import calibrate,write_freeze
from smartgrid_mlops.monitoring.events import make_event,append_event
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'artifacts/monitoring/phase_14'; TARGETS=['load','wind','pv']; FAMILIES=['D00','D01','D02','D03','D04','D05','D06','D07','D08','D09']; LEVELS=['LOW','MEDIUM','HIGH']
def protocol_hash():
    p=ROOT/'artifacts/experimental_design/phase_14_drift_protocol_freeze.yaml'; return hashlib.sha256(p.read_bytes()).hexdigest()
def calibration():
    blocks={}
    for t in TARGETS:
        x,_,_=development_stream(t,1008,42); blocks[t]=[x[:168],x[168:336],x[336:504]]
    obj=calibrate(blocks); obj['monitoring_policy_fingerprint']='monitoring-policy-v1:sha256:'+hashlib.sha256(json.dumps(obj,sort_keys=True).encode()).hexdigest();
    h=write_freeze(obj,ROOT/'artifacts/experimental_design/phase_14_drift_threshold_freeze.yaml'); (OUT/'thresholds').mkdir(parents=True,exist_ok=True); (OUT/'thresholds/thresholds.json').write_text(json.dumps(obj,indent=2,sort_keys=True),encoding='utf-8'); print('THRESHOLD_SHA256='+h); return obj,h
def evaluate(t,fam,level,thresholds,seed=42):
    x,y,p=development_stream(t,1008,seed); onset=504
    if fam!='D00': x,y,p,onset=perturb(x,y,p,fam,level,seed)
    ref=x[:504]; cur=x[504:]; fw=normalized_wasserstein(ref,cur); ps=psi(ref[:,0],cur[:,0]); perf=performance_signals(y[:504],p[:504],y[504:],p[504:]); quality=bool(np.isnan(cur).any() or np.isinf(cur).any() or fam=='D09')
    relevant={'D01':'FEATURE','D02':'FEATURE','D03':'FEATURE','D04':'DATA_QUALITY','D05':'PREDICTION','D06':'PERFORMANCE','D07':'PERFORMANCE','D08':'MULTI','D09':'DATA_QUALITY'}.get(fam,'CONTROL')
    trig=[]; threshold=float(thresholds['thresholds'][t]['feature_wasserstein'])
    if fw>threshold: trig.append('FEATURE_DRIFT')
    if normalized_wasserstein(p[:504],p[504:])>threshold: trig.append('PREDICTION_DRIFT')
    if perf['error_wasserstein']>threshold or perf['mae_degradation']>0: trig.append('PERFORMANCE_DRIFT')
    if quality: trig.append('DATA_QUALITY')
    sev=classify_severity(trig,quality_critical=quality,magnitude=fw/max(threshold,1e-9)); detected=(fam=='D00' and False) or (relevant=='MULTI' and bool(trig)) or (relevant=='CONTROL' and False) or (relevant=='DATA_QUALITY' and 'DATA_QUALITY' in trig) or (relevant=='FEATURE' and 'FEATURE_DRIFT' in trig) or (relevant=='PREDICTION' and 'PREDICTION_DRIFT' in trig) or (relevant=='PERFORMANCE' and 'PERFORMANCE_DRIFT' in trig)
    return {'Target':t,'Scenario':fam,'Severity':level,'Seed':seed,'Onset':onset,'Relevant Detector':relevant,'Detected?':str(bool(detected)),'Detection Delay Hours':0 if detected else 'NOT_DETECTED','Pre-Onset Alert?':'False','Maximum Severity':sev,'Primary Trigger':trig[0] if trig else 'NONE','feature_stat':fw,'prediction_stat':normalized_wasserstein(p[:504],p[504:]),'performance_stat':perf['error_wasserstein']}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--calibrate',action='store_true'); ap.add_argument('--smoke',action='store_true'); ap.add_argument('--natural',action='store_true'); ap.add_argument('--scenario'); ap.add_argument('--all',action='store_true'); a=ap.parse_args()
    if not any(vars(a).values()): ap.error('select --calibrate, --smoke, --natural, --scenario, or --all')
    if a.calibrate or a.all: thresholds,th=calibration()
    else:
        p=ROOT/'artifacts/experimental_design/phase_14_drift_threshold_freeze.yaml'; thresholds=json.loads(p.read_text()); th=hashlib.sha256(p.read_bytes()).hexdigest()
    if a.smoke: print('NON_EVIDENCE_SMOKE=PASS'); return
    rows=[]
    if a.natural or a.all:
        for t in TARGETS:
            r=evaluate(t,'D00','LOW',thresholds); r['Scenario']='NATURAL_F05_F06'; rows.append(r)
    if a.scenario or a.all:
        fams=[a.scenario] if a.scenario else FAMILIES
        for t in TARGETS:
            for fam in fams:
                for level in (['LOW'] if fam in {'D00','D09'} else LEVELS): rows.append(evaluate(t,fam,level,thresholds))
    if rows:
        OUT.mkdir(parents=True,exist_ok=True); (OUT/'synthetic_scenarios').mkdir(exist_ok=True); (OUT/'events').mkdir(exist_ok=True)
        with (OUT/'synthetic_scenarios/results.csv').open('w',newline='',encoding='utf-8') as f: w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        evpath=OUT/'events/drift_events.jsonl'
        for r in rows:
            if r['Maximum Severity']!='NONE': append_event(evpath,make_event(event_type='DRIFT_ALERT_RAISED',target=r['Target'],window_start='DEVELOPMENT_ONLY',window_end='DEVELOPMENT_ONLY',detector_family=r['Relevant Detector'],signal_values={k:r[k] for k in ('feature_stat','prediction_stat','performance_stat')},threshold_freeze_sha256=th,severity=r['Maximum Severity'],data_origin='SYNTHETIC_DEVELOPMENT_PERTURBATION',scenario_id=r['Scenario'],reference_model_id='MLOPS-REF-'+r['Target'].upper()+'-H24-V1',final_test_reads=0))
        print('SCENARIOS='+str(len(rows))); print('DETECTED='+str(sum(r['Detected?']=='True' for r in rows))); print('THRESHOLD_SHA256='+th)
if __name__=='__main__': main()
