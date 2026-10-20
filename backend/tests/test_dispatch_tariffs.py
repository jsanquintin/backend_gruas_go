from datetime import datetime, timedelta, timezone
from app.models import OperatorLocation, Operator, Service
from sqlalchemy import select
from test_api import create_operator, req, delivery, roadside

def tariff(c,t,kind='parcel',base='120',per_km='0',minimum='150',fee='100'):
    return c.put('/api/v1/tariffs/'+kind,headers=t['admin'],json={
        'service_type':kind,'base_dop':base,'per_km_dop':per_km,'minimum_dop':minimum,
        'operator_base_dop':fee,'active':True})

def test_tariff_crud_manual_quote_and_permissions(env):
    c,t,_=env
    assert c.get('/api/v1/tariffs',headers=t['merchant']).status_code==403
    assert tariff(c,t).status_code==200
    assert c.get('/api/v1/tariffs',headers=t['dispatcher']).json()[0]['base_dop']=='120.00'
    assert c.put('/api/v1/tariffs/parcel',headers=t['dispatcher'],json={'service_type':'parcel','base_dop':100,'per_km_dop':0,'minimum_dop':150,'operator_base_dop':80}).status_code==403
    service=req(c,t['admin']).json()
    estimate=c.get(f'/api/v1/tariffs/estimate/{service["id"]}',headers=t['dispatcher'])
    assert estimate.status_code==200,estimate.text
    assert estimate.json()['suggested_total_dop']=='150.00'
    assert c.get(f'/api/v1/services/{service["id"]}',headers=t['admin']).json()['quoted_total_dop']=='300.00' # no auto update
    assert c.get(f'/api/v1/tariffs/estimate/{service["id"]}',headers=t['merchant']).status_code==403
    assert c.get(f'/api/v1/tariffs/estimate/{service["id"]}',headers=t['outside']).status_code==404
    assert c.get('/api/v1/tariffs',headers=t['outside']).json()==[]

def test_distance_estimate_needs_coordinates(env):
    c,t,_=env
    assert tariff(c,t,per_km='100').status_code==200
    service=req(c,t['admin']).json()
    assert c.get(f'/api/v1/tariffs/estimate/{service["id"]}',headers=t['admin']).status_code==422
    x=delivery();x.update(lat=18.48,lng=-69.93,destination_lat=18.49,destination_lng=-69.91)
    r=req(c,t['admin'],x);assert r.status_code==201,r.text
    est=c.get(f'/api/v1/tariffs/estimate/{r.json()["id"]}',headers=t['admin'])
    assert est.status_code==200,est.text
    assert 1<float(est.json()['distance_km'])<5
    assert est.json()['mode']=='straight_line_estimate'
    x['destination_lng']=None
    assert req(c,t['admin'],x).status_code==422

def test_tariff_type_mismatch_and_negative_values(env):
    c,t,_=env
    payload={'service_type':'tow','base_dop':'200','per_km_dop':'0','minimum_dop':'0','operator_base_dop':'0'}
    assert c.put('/api/v1/tariffs/parcel',headers=t['admin'],json=payload).status_code==422
    payload['base_dop']='-3'
    assert c.put('/api/v1/tariffs/tow',headers=t['admin'],json=payload).status_code==422

def test_driver_gps_only_own_operator_and_permissions(env):
    c,t,dbmake=env
    assert c.post('/api/v1/dispatch/my-location',headers=t['admin'],json={'lat':18.49,'lng':-69.93,'accuracy_m':12}).status_code==403
    assert c.post('/api/v1/dispatch/my-location',headers=t['driver'],json={'lat':18.49,'lng':-69.93,'accuracy_m':12}).status_code==403
    assert c.get('/api/v1/dispatch/positions',headers=t['driver']).status_code==403
    with dbmake() as db:
        user=db.scalar(select(__import__('app.models',fromlist=['User']).User).where(__import__('app.models',fromlist=['User']).User.email=='driver@example.com'))
        driver_id=user.id
    op=create_operator(c,t['admin'],user_id=driver_id)
    assert c.post('/api/v1/dispatch/my-location',headers=t['driver'],json={'lat':91,'lng':-70,'accuracy_m':5}).status_code==422
    assert c.post('/api/v1/dispatch/my-location',headers=t['driver'],json={'lat':18.49,'lng':-69.93,'accuracy_m':-1}).status_code==422
    r=c.post('/api/v1/dispatch/my-location',headers=t['driver'],json={'lat':18.49,'lng':-69.93,'accuracy_m':15})
    assert r.status_code==201,r.text
    locations=c.get('/api/v1/dispatch/positions',headers=t['dispatcher'])
    assert locations.status_code==200 and len(locations.json())==1
    assert locations.json()[0]['available'] is True
    assert c.get('/api/v1/dispatch/positions',headers=t['outside']).json()==[]
    assert c.get('/api/v1/dispatch/updates',headers=t['merchant']).status_code==403

def test_stale_gps_busy_operator_and_dispatch_events(env):
    c,t,dbmake=env
    with dbmake() as db:
        from app.models import User
        driver_id=db.scalar(select(User).where(User.email=='driver@example.com')).id
    op_id=create_operator(c,t['admin'],user_id=driver_id)
    c.post('/api/v1/dispatch/my-location',headers=t['driver'],json={'lat':18.49,'lng':-69.93,'accuracy_m':8})
    s=req(c,t['admin']).json()
    assert c.post(f'/api/v1/services/{s["id"]}/assign',headers=t['admin'],json={'operator_id':op_id}).status_code==200
    gps=c.get('/api/v1/dispatch/positions',headers=t['admin']).json()[0]
    assert gps['available'] is False
    other=req(c,t['admin']).json()
    assert c.post(f'/api/v1/services/{other["id"]}/assign',headers=t['admin'],json={'operator_id':op_id}).status_code==409
    with dbmake() as db:
        pos=db.scalar(select(OperatorLocation).where(OperatorLocation.operator_id==op_id))
        pos.recorded_at=datetime.now(timezone.utc)-timedelta(minutes=4)
        db.commit()
    gps=c.get('/api/v1/dispatch/positions',headers=t['admin']).json()[0]
    assert gps['online'] is False
    feed=c.get('/api/v1/dispatch/updates',headers=t['admin']).json()
    assert feed['cursor']>0
    assert any(x['kind']=='service_assigned' for x in feed['events'])
    assert c.get('/api/v1/dispatch/updates',headers=t['outside']).json()['events']==[]

def test_gps_requires_approved_operator(env):
    c,t,dbmake=env
    from app.models import User
    with dbmake() as db:
        driver_id=db.scalar(select(User).where(User.email=='driver@example.com')).id
    op=create_operator(c,t['admin'],verified=False,user_id=driver_id)
    assert c.post('/api/v1/dispatch/my-location',headers=t['driver'],json={'lat':18.49,'lng':-69.93,'accuracy_m':8}).status_code==403


def test_candidates_proximity_and_cross_company(env):
    c,t,dbmake=env
    from app.models import User
    with dbmake() as db:
        driver_id=db.scalar(select(User).where(User.email=='driver@example.com')).id
    op=create_operator(c,t['admin'],user_id=driver_id)
    sdata=delivery();sdata.update(lat='18.4800000',lng='-69.9300000')
    service=req(c,t['admin'],sdata).json()
    assert c.get(f'/api/v1/dispatch/candidates/{service["id"]}',headers=t['outside']).status_code==404
    assert c.get(f'/api/v1/dispatch/candidates/{service["id"]}',headers=t['merchant']).status_code==403
    empty=c.get(f'/api/v1/dispatch/candidates/{service["id"]}',headers=t['admin']).json()
    assert empty['candidates']==[]
    c.post('/api/v1/dispatch/my-location',headers=t['driver'],json={'lat':18.484,'lng':-69.931,'accuracy_m':12})
    candidates=c.get(f'/api/v1/dispatch/candidates/{service["id"]}',headers=t['admin'])
    assert candidates.status_code==200
    assert candidates.json()['candidates'][0]['operator_id']==op
    assert 0<candidates.json()['candidates'][0]['distance_straight_km']<1
