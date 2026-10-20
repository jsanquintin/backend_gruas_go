from app.models import Operator, ServiceEvent
from sqlalchemy import select

def delivery():
    return {'kind':'delivery','service_type':'parcel','customer_name':'Cliente Prueba','customer_phone':'8095551234','pickup_address':'Santo Domingo, Ensanche Naco','destination_address':'Santo Domingo, Piantini','quoted_total_dop':'300.00','operator_fee_dop':'150.00','recipient_name':'Receptor Test','recipient_phone':'8095558888','package_description':'Caja de papeles'}

def roadside():
    return {'kind':'roadside','service_type':'tow','customer_name':'Auxilio Prueba','customer_phone':'8095551266','pickup_address':'Autopista Las Americas Km 11','destination_address':'Taller Boca Chica','quoted_total_dop':'3500.00','operator_fee_dop':'2800.00','vehicle_plate':'A123456','vehicle_description':'SUV color gris'}

def req(client, token, payload=None):
    return client.post('/api/v1/services',headers=token,json=payload or delivery())

def create_operator(client,token,kind='delivery',verified=True,user_id=None):
    r=client.post('/api/v1/operators',headers=token,json={'name':'Operador A','phone':'8095551987','kind':kind,'vehicle_type':'moto' if kind=='delivery' else 'grua plataforma','verified':verified,'user_id':user_id,'license_plate':'A123456'})
    assert r.status_code==201,r.text
    op_id=r.json()['id']
    assert r.json()['verified'] is False
    if verified:
        set_docs(client,token,op_id)
        check=client.patch(f'/api/v1/operators/{op_id}/verification',headers=token,json={'status':'approved','documents_checked':True,'note':'Póliza, licencia y matrícula contrastadas contra originales'})
        assert check.status_code==200,check.text
    return op_id

def set_docs(client,token,op_id,license_exp='2030-12-31'):
    response=client.patch(f'/api/v1/operators/{op_id}/documents',headers=token,json={
       'license_number':'LC-LOCAL-001','license_expires_on':license_exp,
       'registration_reference':'MAT-LOCAL-001','insurance_policy':'POL-LOCAL-001',
       'insurance_expires_on':'2030-12-31'})
    assert response.status_code==200,response.text
    return response

def test_health_no_auth(env):
    client,tk,_=env
    assert client.get('/health').json()['product']=='DEGARITAO Express'
    assert client.get('/api/v1/services').status_code==401
    assert client.post('/api/v1/auth/login',json={'email':'admin@example.com','password':'wrong'}).status_code==401

def test_create_each_service_and_history(env):
    c,t,_=env
    for payload in (delivery(),roadside()):
        r=req(c,t['dispatcher'],payload)
        assert r.status_code==201,r.text
        data=r.json()
        assert data['kind']==payload['kind']
        assert data['code'].startswith('DEX-')
        assert data['events'][0]['event_type']=='created'
    assert c.get('/api/v1/dashboard',headers=t['admin']).json()['total']==2

def test_invalid_service_and_coordinates(env):
    c,t,_=env
    x=delivery();x['service_type']='tow'
    assert req(c,t['admin'],x).status_code==422
    x=delivery();x['lat']=18.5
    assert req(c,t['admin'],x).status_code==422
    x=roadside();x['destination_address']=None
    assert req(c,t['admin'],x).status_code==422
    x=delivery();x['operator_fee_dop']='700'
    assert req(c,t['admin'],x).status_code==422

def test_assignment_checks(env):
    c,t,dbmaker=env
    service_id=req(c,t['admin']).json()['id']
    operator_id=create_operator(c,t['admin'],verified=False)
    assert c.post(f'/api/v1/services/{service_id}/assign',headers=t['dispatcher'],json={'operator_id':operator_id}).status_code==422
    set_docs(c,t['admin'],operator_id)
    assert c.patch(f'/api/v1/operators/{operator_id}/verification',headers=t['admin'],json={'status':'approved','documents_checked':True,'note':'Licencia, matrícula y seguro contrastados en originales'}).status_code==200
    incompatible=create_operator(c,t['admin'],kind='roadside')
    assert c.post(f'/api/v1/services/{service_id}/assign',headers=t['admin'],json={'operator_id':incompatible}).status_code==422
    r=c.post(f'/api/v1/services/{service_id}/assign',headers=t['admin'],json={'operator_id':operator_id})
    assert r.status_code==200,r.text
    assert r.json()['status']=='assigned'
    assert c.post(f'/api/v1/services/{service_id}/assign',headers=t['admin'],json={'operator_id':operator_id}).status_code==409
    with dbmaker() as db:
        ev=db.scalars(select(ServiceEvent)).all()
        assert len(ev)==2

def test_full_delivery_workflow_and_proof(env):
    c,t,_=env
    payload=delivery(); payload['quoted_total_dop']=None; payload['operator_fee_dop']=None
    s=req(c,t['merchant'],payload).json()
    op=create_operator(c,t['admin'])
    assigned=c.post(f'/api/v1/services/{s["id"]}/assign',json={'operator_id':op},headers=t['dispatcher'])
    assert assigned.status_code==200
    assert c.post(f'/api/v1/services/{s["id"]}/status',json={'status':'completed'},headers=t['dispatcher']).status_code==409
    assert c.post(f'/api/v1/services/{s["id"]}/status',json={'status':'en_route'},headers=t['dispatcher']).status_code==200
    assert c.post(f'/api/v1/services/{s["id"]}/status',json={'status':'completed'},headers=t['dispatcher']).status_code==422
    r=c.post(f'/api/v1/services/{s["id"]}/status',json={'status':'completed','note':'Código OTP 8842 confirmado'},headers=t['dispatcher'])
    assert r.status_code==200,r.text
    assert r.json()['proof_note']=='Código OTP 8842 confirmado'
    assert c.post(f'/api/v1/services/{s["id"]}/status',json={'status':'canceled'},headers=t['dispatcher']).status_code==409

def test_roadside_workflow(env):
    c,t,_=env
    id=req(c,t['admin'],roadside()).json()['id']
    op=create_operator(c,t['admin'],'roadside')
    assert c.post(f'/api/v1/services/{id}/assign',headers=t['admin'],json={'operator_id':op}).status_code==200
    for status in ['en_route','on_site','completed']:
        r=c.post(f'/api/v1/services/{id}/status',json={'status':status,'note':'Trabajo finalizado correctamente'},headers=t['admin'])
        assert r.status_code==200,r.text
    assert c.get('/api/v1/dashboard',headers=t['admin']).json()['completed']==1

def test_permissions_and_tenant_isolation(env):
    c,t,dbmaker=env
    id=req(c,t['admin']).json()['id']
    assert c.get(f'/api/v1/services/{id}',headers=t['merchant']).status_code==404
    assert c.get(f'/api/v1/services/{id}',headers=t['outside']).status_code==404
    assert c.get('/api/v1/services',headers=t['outside']).json()==[]
    assert c.get('/api/v1/operators',headers=t['merchant']).status_code==403
    assert req(c,t['driver']).status_code==403
    op=create_operator(c,t['admin'])
    assert c.post(f'/api/v1/services/{id}/assign',headers=t['merchant'],json={'operator_id':op}).status_code==403
    assert c.post(f'/api/v1/services/{id}/assign',headers=t['outside'],json={'operator_id':op}).status_code==404
    assert c.get('/api/v1/dashboard',headers=t['merchant']).status_code==403

def test_driver_only_own_assignments(env):
    c,t,dbmaker=env
    with dbmaker() as db:
        from app.models import User
        driver=db.scalar(select(User).where(User.email=='driver@example.com'))
        driver_id=driver.id
    service_id=req(c,t['admin']).json()['id']
    op=create_operator(c,t['admin'],user_id=driver_id)
    assert c.get('/api/v1/services',headers=t['driver']).json()==[]
    c.post(f'/api/v1/services/{service_id}/assign',headers=t['admin'],json={'operator_id':op})
    assert len(c.get('/api/v1/services',headers=t['driver']).json())==1
    assert c.post(f'/api/v1/services/{service_id}/status',headers=t['driver'],json={'status':'canceled'}).status_code==403
    assert c.post(f'/api/v1/services/{service_id}/status',headers=t['driver'],json={'status':'en_route'}).status_code==200
    assert c.get('/api/v1/services',headers=t['outside']).json()==[]

def test_create_staff_restrict_duplicates(env):
    c,t,_=env
    user={'name':'Nuevo Chofer','email':'Nuevo@Example.com','password':'Password-Seguro-123','role':'driver'}
    assert c.post('/api/v1/users',headers=t['merchant'],json=user).status_code==403
    r=c.post('/api/v1/users',headers=t['admin'],json=user)
    assert r.status_code==201,r.text
    assert r.json()['email']=='nuevo@example.com'
    assert c.post('/api/v1/users',headers=t['admin'],json=user).status_code==409

def test_quote_and_merchant_restrictions(env):
    c,t,_=env
    raw=delivery(); raw['quoted_total_dop']='300'
    assert req(c,t['merchant'],raw).status_code==403
    raw['quoted_total_dop']=None;raw['operator_fee_dop']=None
    s=req(c,t['merchant'],raw).json()
    assert s['quoted_total_dop'] is None
    assert c.post(f'/api/v1/services/{s["id"]}/quote',headers=t['merchant'],json={'quoted_total_dop':'300','operator_fee_dop':'150'}).status_code==403
    assert c.post(f'/api/v1/services/{s["id"]}/quote',headers=t['dispatcher'],json={'quoted_total_dop':'100','operator_fee_dop':'200'}).status_code==422
    r=c.post(f'/api/v1/services/{s["id"]}/quote',headers=t['dispatcher'],json={'quoted_total_dop':'300','operator_fee_dop':'150'})
    assert r.status_code==200,r.text
    assert float(r.json()['quoted_total_dop'])==300.0
    assert r.json()['events'][-1]['event_type']=='quote_set'

def test_cancel_and_dashboard(env):
    c,t,_=env
    a=req(c,t['dispatcher']).json()['id']
    assert c.post(f'/api/v1/services/{a}/status',headers=t['dispatcher'],json={'status':'canceled','note':'Cliente canceló'}).status_code==200
    r=c.get('/api/v1/dashboard',headers=t['dispatcher']).json()
    assert r['canceled']==1
    assert r['total']==1


def test_approval_requires_real_fields_and_audit(env):
    c,t,_=env
    operator_id=create_operator(c,t['admin'],verified=False)
    path=f'/api/v1/operators/{operator_id}'
    assert c.patch(path+'/verification',headers=t['admin'],json={'status':'approved','documents_checked':True,'note':'Revisado y aprobado por auditor'}).status_code==422
    assert c.patch(path+'/documents',headers=t['dispatcher'],json={}).status_code==403
    set_docs(c,t['admin'],operator_id,license_exp='2020-01-01')
    assert c.patch(path+'/verification',headers=t['admin'],json={'status':'approved','documents_checked':True,'note':'Licencia vencida rechazada por la revisión'}).status_code==422
    set_docs(c,t['admin'],operator_id)
    assert c.patch(path+'/verification',headers=t['dispatcher'],json={'status':'approved','documents_checked':True,'note':'Revisión aprobada administrativamente'}).status_code==403
    assert c.patch(path+'/verification',headers=t['admin'],json={'status':'approved','documents_checked':True,'note':'Comparé con los originales: licencia y póliza'}).status_code==200
    events=c.get(path+'/reviews',headers=t['admin'])
    assert events.status_code==200
    assert [r['action'] for r in events.json()][:2]==['approved','documents_updated']
    assert c.get(path+'/reviews',headers=t['merchant']).status_code==403
    # Si el administrador actualiza documentos, debe perder aprobación.
    assert set_docs(c,t['admin'],operator_id).json()['verified'] is False
    assert c.get('/api/v1/operators',headers=t['admin']).json()[0]['verification_status']=='pending'


def test_service_specific_validation(env):
    c,t,_=env
    a=delivery();a.pop('recipient_name')
    assert req(c,t['dispatcher'],a).status_code==422
    a=roadside();a.pop('vehicle_plate')
    assert req(c,t['dispatcher'],a).status_code==422
    assert req(c,t['dispatcher'],delivery()).status_code==201


def test_approval_requires_explicit_manual_attestation(env):
    client, tokens, _ = env
    op_id = create_operator(client, tokens['admin'], verified=False)
    set_docs(client, tokens['admin'], op_id)
    url = f'/api/v1/operators/{op_id}/verification'
    no_attestation = client.patch(url, headers=tokens['admin'], json={
        'status': 'approved', 'note': 'Documentos revisados presencialmente'
    })
    assert no_attestation.status_code == 422
    explicit_false = client.patch(url, headers=tokens['admin'], json={
        'status': 'approved', 'documents_checked': False,
        'note': 'Documentos revisados presencialmente'
    })
    assert explicit_false.status_code == 422
    assert client.get('/api/v1/operators', headers=tokens['admin']).json()[0]['verified'] is False
    accepted = client.patch(url, headers=tokens['admin'], json={
        'status': 'approved', 'documents_checked': True,
        'note': 'Documentos revisados presencialmente'
    })
    assert accepted.status_code == 200
    reviews = client.get(f'/api/v1/operators/{op_id}/reviews', headers=tokens['admin']).json()
    assert reviews[0]['action'] == 'approved'
    assert 'Revisión manual confirmada' in reviews[0]['note']


def test_invalid_document_references_and_approval_guards(env):
    client, tokens, _ = env
    op_id = create_operator(client, tokens['admin'], verified=False)
    url = f'/api/v1/operators/{op_id}'
    bad_docs = client.patch(url+'/documents', headers=tokens['admin'], json={
        'license_number': '   ', 'license_expires_on': '2030-12-31',
        'registration_reference': 'MAT-001', 'insurance_policy': 'POL-001',
        'insurance_expires_on': '2030-12-31'
    })
    assert bad_docs.status_code == 422
    good = set_docs(client, tokens['admin'], op_id)
    assert good.status_code == 200
    assert client.patch(url+'/verification', headers=tokens['admin'], json={
        'status': 'approved', 'documents_checked': True, 'note': '      '
    }).status_code == 422
    assert client.patch(url+'/verification', headers=tokens['dispatcher'], json={
        'status': 'approved', 'documents_checked': True,
        'note': 'Intento sin permisos de homologación'
    }).status_code == 403
    # Rejected operator can be marked with a documented reason, without attestation.
    rejected = client.patch(url+'/verification', headers=tokens['admin'], json={
        'status': 'rejected', 'note': 'Documentación inconsistente en revisión'
    })
    assert rejected.status_code == 200
    assert rejected.json()['verification_status'] == 'rejected'
    assert rejected.json()['verified'] is False


def test_approved_operator_document_updates_revoke_approval(env):
    client, tokens, _ = env
    op_id = create_operator(client, tokens['admin'])
    url = f'/api/v1/operators/{op_id}'
    assert client.get('/api/v1/operators', headers=tokens['admin']).json()[0]['verified']
    updated = set_docs(client, tokens['admin'], op_id)
    assert updated.json()['verification_status'] == 'pending'
    assert updated.json()['verified'] is False
    assert updated.json()['verified_by'] is None
    assert updated.json()['verified_at'] is None
    events = client.get(url+'/reviews', headers=tokens['admin']).json()
    assert events[0]['action'] == 'documents_updated'
