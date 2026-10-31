"""Score stored, issued predictions without recomputing their original outputs."""
import json
from datetime import datetime,timezone,timedelta,date
from validation import metrics

def record_and_score(db,uid,result,readings):
    issued=datetime.now(timezone(timedelta(hours=3,minutes=30)))
    rows=result['forecast']['days']
    with db:
        db.execute('INSERT INTO forecast_runs(user_id,issued_at,days) VALUES (?,?,?)',(uid,issued.isoformat(),json.dumps({'days':rows,'scenario':result.get('calibration',{}).get('scenario_changed',False)})))
    observed={r['date']:float(r['kwh']) for r in readings if r.get('complete',True) and r['date']<issued.date().isoformat()}
    scored=[]
    for run in db.execute('SELECT id,issued_at,days FROM forecast_runs WHERE user_id=? ORDER BY id DESC LIMIT 20',(uid,)):
        payload=json.loads(run['days']);scenario=payload.get('scenario',False) if isinstance(payload,dict) else False
        predicted={r['gregorian_date']:r['production_kwh'] for r in (payload['days'] if isinstance(payload,dict) else payload)}
        covered=[d for d in predicted if d in observed]
        row=dict(id=run['id'],issued_at=run['issued_at'],start=min(predicted),end=max(predicted),covered_days=len(covered),expected_days=len(predicted),status='pending',score=None)
        if scenario:row['status']='scenario'
        elif len(covered)==len(predicted):
            row.update(status='complete',score=metrics({date.fromisoformat(d):observed[d] for d in predicted},{date.fromisoformat(d):v for d,v in predicted.items()}))
        scored.append(row)
    return scored
