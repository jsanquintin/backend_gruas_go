import { useEffect, useRef, useState, type FormEvent } from 'react';
import { AlertCircle, ArrowRight, BarChart3, Check, ChevronDown, Clock3, LayoutDashboard, LogOut, MapPin, Package, Plus, RefreshCw, ShieldCheck, Truck, UserRound, Users, X } from 'lucide-react';
import { api, auth, patch, post, watchDispatch } from './api';
import { LiveDispatch, TariffsPanel, EstimateButton, DispatchCandidates } from './Operations';
import type { Dashboard, Kind, Operator, OperatorReview, Role, Service, Status, User } from './types';

type View='dashboard'|'services'|'operators'|'users'|'dispatch'|'tariffs';
const statusNames:Record<Status,string>={pending:'Pendiente',assigned:'Asignado',en_route:'En ruta',on_site:'En sitio',completed:'Completado',canceled:'Cancelado'};
const kindNames:Record<Kind,string>={delivery:'Delivery',roadside:'Asistencia vial'};
const types:Record<Kind,Array<[string,string]>>={delivery:[['parcel','Paquetería'],['scheduled_route','Ruta programada']],roadside:[['tow','Grúa / Remolque'],['jumpstart','Paso de corriente'],['tire_change','Cambio de neumático'],['fuel','Combustible'],['mechanical','Auxilio mecánico']]};
const transitions:Record<Status,Status[]>={pending:[],assigned:['en_route'],en_route:['on_site','completed'],on_site:['completed'],completed:[],canceled:[]};
const money=(v:string|null)=>v==null?'Sin cotizar':`RD$ ${Number(v).toLocaleString('es-DO',{minimumFractionDigits:2})}`;
const stamp=(d:string)=>new Date(d).toLocaleString('es-DO',{dateStyle:'short',timeStyle:'short'});
function Brand({compact=false}:{compact?:boolean}){return <div className={'brand '+(compact?'compact':'')}><img src="/degaritao-express.svg" alt="DEGARITAO Express"/><span>Centro de operaciones</span></div>}
function Pill({status}:{status:Status}){return <span className={`pill ${status}`}>{statusNames[status]}</span>}
function Modal({title,onClose,children}:{title:string;onClose:()=>void;children:React.ReactNode}){return <div className="overlay" role="presentation" onMouseDown={e=>{if(e.target===e.currentTarget)onClose()}}><section className="modal" role="dialog" aria-modal="true"><header><h2>{title}</h2><button className="iconbutton" onClick={onClose} aria-label="Cerrar"><X size={20}/></button></header>{children}</section></div>}
export default function App(){
  const [session,setSession]=useState<{name:string;role:Role}|null>(null);
  const [view,setView]=useState<View>('dashboard');
  const [services,setServices]=useState<Service[]>([]);
  const [operators,setOperators]=useState<Operator[]>([]);
  const [users,setUsers]=useState<User[]>([]);
  const [metrics,setMetrics]=useState<Dashboard|null>(null);
  const [kindFilter,setKindFilter]=useState<'all'|Kind>('all');
  const [selected,setSelected]=useState<Service|null>(null);
  const [reviewing,setReviewing]=useState<Operator|null>(null);
  const [reviewReload,setReviewReload]=useState(0);
  const [closing,setClosing]=useState<{service:Service;status:'completed'|'canceled'}|null>(null);
  const [modal,setModal]=useState<'new-service'|'new-operator'|'new-user'|null>(null);
  const [loading,setLoading]=useState(false);
  const [message,setMessage]=useState('');
  const [error,setError]=useState('');
  const [loginEmail,setLoginEmail]=useState('');
  const [loginPassword,setLoginPassword]=useState('');
  const [liveRevision,setLiveRevision]=useState(0);
  const [liveConnected,setLiveConnected]=useState(false);
  const load=async(role=session?.role)=>{
    if(!auth.get())return;
    try{
      const [s,o,m,u]=await Promise.all([
        api<Service[]>('/services'),
        role==='admin'||role==='dispatcher'?api<Operator[]>('/operators'):Promise.resolve([]),
        role==='admin'||role==='dispatcher'?api<Dashboard>('/dashboard'):Promise.resolve(null),
        role==='admin'?api<User[]>('/users'):Promise.resolve([])
      ]);
      setServices(s);setOperators(o);setMetrics(m);setUsers(u);setError('');
      if(selected)setSelected(s.find(x=>x.id===selected.id)??null);
    }catch(e){if(String(e).includes('401'))logout();else setError((e as Error).message)}
  };
  useEffect(()=>{if(auth.get()){api<User>('/auth/me').then(user=>setSession({name:user.name,role:user.role})).catch(()=>auth.clear())}},[]);
  const loadRef=useRef(load);loadRef.current=load;
  useEffect(()=>{if(session){load(session.role);const handle=setInterval(()=>loadRef.current(session.role),30000);return()=>clearInterval(handle)}},[session?.role]);
  useEffect(()=>{
    if(!session || !['admin','dispatcher'].includes(session.role))return;
    const controller=new AbortController();
    async function connect(){
      while(!controller.signal.aborted){
        try{
          await watchDispatch(()=>{setLiveRevision(v=>v+1);void loadRef.current()},controller.signal,()=>setLiveConnected(true));
        }catch{setLiveConnected(false)}
        if(!controller.signal.aborted)await new Promise(resolve=>setTimeout(resolve,2000));
      }
    }
    void connect();return()=>{controller.abort();setLiveConnected(false)};
  },[session?.role]);
  const logout=()=>{auth.clear();setSession(null);setServices([]);setSelected(null);setView('dashboard')};
  const submitLogin=async(e:FormEvent)=>{e.preventDefault();setLoading(true);setError('');try{const r=await post<{access_token:string;name:string;role:Role}>('/auth/login',{email:loginEmail,password:loginPassword});auth.set(r.access_token);setSession({name:r.name,role:r.role});setLoginPassword('')}catch(e){setError((e as Error).message)}finally{setLoading(false)}};
  const mutation=async(fn:()=>Promise<unknown>)=>{setLoading(true);setError('');try{await fn();setMessage('Operación realizada correctamente');await load();setModal(null)}catch(e){setError((e as Error).message)}finally{setLoading(false)}};
  if(!session)return <main className="loginpage"><div className="login-art"><div className="login-art-overlay"><div className="hero-line"/><h2>Movemos soluciones.<br/><em>Resolvemos caminos.</em></h2><p>Delivery y asistencia vial en una sola operación.</p></div></div><section className="login-box"><Brand/><p className="eyebrow">ACCESO SEGURO</p><h1>Bienvenido a bordo.</h1><p>Ingresa al centro de operaciones de DEGARITAO Express.</p><form onSubmit={submitLogin}><label>Correo electrónico<input type="email" required value={loginEmail} onChange={e=>setLoginEmail(e.target.value)} placeholder="correo@empresa.com"/></label><label>Contraseña<input required type="password" value={loginPassword} onChange={e=>setLoginPassword(e.target.value)} placeholder="••••••••••••"/></label>{error&&<p className="error"><AlertCircle size={16}/>{error}</p>}<button className="primary" disabled={loading}>{loading?'Ingresando...':'Entrar al panel'}<ArrowRight size={17}/></button></form><small>Acceso para personal y operadores autorizados.</small></section></main>;
  const canManage=session.role==='admin'||session.role==='dispatcher';
  const shown=services.filter(s=>kindFilter==='all'||s.kind===kindFilter);
  const change=async(s:Service,next:Status)=>{
    if(next==='completed'||next==='canceled'){setClosing({service:s,status:next});return}
    await mutation(()=>post(`/services/${s.id}/status`,{status:next,note:null}));setSelected(null)
  };
  const saveReviewDocs=async(data:unknown)=>{
    if(!reviewing)return;
    setLoading(true);setError('');
    try{const op=await patch<Operator>(`/operators/${reviewing.id}/documents`,data);setReviewing(op);setReviewReload(n=>n+1);setMessage('Datos documentales guardados. Aún no hay aprobación.');await load()}
    catch(e){setError((e as Error).message)}finally{setLoading(false)}
  };
  const saveReviewDecision=async(data:unknown)=>{
    if(!reviewing)return;
    setLoading(true);setError('');
    try{await patch(`/operators/${reviewing.id}/verification`,data);setReviewing(null);setMessage('Revisión documental registrada');await load()}
    catch(e){setError((e as Error).message)}finally{setLoading(false)}
  };
  return <div className="shell"><aside className="sidebar"><Brand/><nav><button className={view==='dashboard'?'selected':''} onClick={()=>setView('dashboard')}><LayoutDashboard size={18}/> Resumen</button><button className={view==='services'?'selected':''} onClick={()=>setView('services')}><Package size={18}/> Solicitudes <span>{services.length}</span></button>{(canManage||session.role==='driver')&&<button className={view==='dispatch'?'selected':''} onClick={()=>setView('dispatch')}><MapPin size={18}/> GPS y despacho</button>}{canManage&&<button className={view==='tariffs'?'selected':''} onClick={()=>setView('tariffs')}><BarChart3 size={18}/> Tarifas</button>}{canManage&&<button className={view==='operators'?'selected':''} onClick={()=>setView('operators')}><Truck size={18}/> Operadores</button>}{session.role==='admin'&&<button className={view==='users'?'selected':''} onClick={()=>setView('users')}><Users size={18}/> Usuarios</button>}</nav><div className="sidebar-bottom"><div className="online"><span/> Sistema MVP local</div><button onClick={logout}><LogOut size={18}/> Salir</button></div></aside><main className="content"><header className="topbar"><div><span className="eyebrow">DEGARITAO EXPRESS · CENTRO DE DESPACHO</span><h1>{view==='dashboard'?'Panel de operaciones':view==='services'?'Solicitudes':view==='operators'?'Red de operadores':view==='dispatch'?'GPS y despacho':view==='tariffs'?'Tarifas':'Usuarios y accesos'}</h1></div><div className="top-actions"><button className="outline" onClick={()=>load()}><RefreshCw size={16}/> Actualizar</button>{canManage&&<span className={'ops-live-indicator '+(liveConnected?'connected':'')}>{liveConnected?'Actualización en vivo':'Conexión en espera'}</span>}<div className="account"><UserRound size={17}/><span>{session.name}<small>{session.role}</small></span></div></div></header>{error&&<div className="toast error"><AlertCircle size={17}/>{error}<button onClick={()=>setError('')}>×</button></div>}{message&&<div className="toast success"><Check size={17}/>{message}<button onClick={()=>setMessage('')}>×</button></div>}
  {view==='dashboard'&&<><section className="welcome"><div><p className="eyebrow">OPERACIÓN UNIFICADA</p><h2>Dos servicios.<br/>Una sola plataforma.</h2><p>Controla entregas, remolques y asistencia desde un mismo lugar.</p><button className="light" onClick={()=>setModal('new-service')} disabled={session.role==='driver'}><Plus size={17}/> Nueva solicitud</button></div><div className="welcome-icons"><span><Package size={34}/>DELIVERY</span><span><Truck size={38}/>ASISTENCIA VIAL</span></div></section>{metrics&&<section className="metrics">{[{icon:BarChart3,label:'Solicitudes totales',num:metrics.total},{icon:Clock3,label:'Pendientes',num:metrics.pending},{icon:Truck,label:'En operación',num:metrics.active},{icon:ShieldCheck,label:'Finalizadas',num:metrics.completed}].map(x=><article key={x.label}><div className="metric-icon"><x.icon size={20}/></div><p>{x.label}</p><strong>{x.num}</strong></article>)}</section>}<div className="section-title"><h2>Operaciones recientes</h2><button className="text-link" onClick={()=>setView('services')}>Ver todas <ArrowRight size={16}/></button></div><ServiceTable data={services.slice(0,8)} onSelect={setSelected}/></>}
  {view==='services'&&<><div className="section-controls"><div className="tabs">{([['all','Todas'],['delivery','Delivery'],['roadside','Asistencia vial']] as const).map(([v,label])=><button className={kindFilter===v?'active':''} key={v} onClick={()=>setKindFilter(v)}>{label}</button>)}</div>{session.role!=='driver'&&<button className="primary small" onClick={()=>setModal('new-service')}><Plus size={16}/> Nueva solicitud</button>}</div><ServiceTable data={shown} onSelect={setSelected}/></>}
  {view==='operators'&&<><div className="section-controls"><p className="muted">Solo se pueden asignar operadores activos y verificados.</p>{session.role==='admin'&&<button className="primary small" onClick={()=>setModal('new-operator')}><Plus size={16}/> Nuevo operador</button>}</div><div className="operator-grid">{operators.map(o=><article key={o.id} className="operator-card"><div className="operator-badge">{o.kind==='delivery'?<Package/>:<Truck/>}</div><div className="operator-head"><h3>{o.name}</h3><span className={o.verified?'verify ok':'verify'}>{({pending:'Pendiente',approved:'Aprobado',rejected:'Rechazado',suspended:'Suspendido'} as const)[o.verification_status]}</span></div><p>{kindNames[o.kind]} · {o.vehicle_type}{o.license_plate?` · ${o.license_plate}`:''}</p><small>{o.phone} {o.user_id?'· Usuario vinculado':''}</small>{o.verification_note&&<p className="operator-note">{o.verification_note}</p>}{o.insurance_expires_on&&<small>Seguro hasta: {o.insurance_expires_on}</small>}{session.role==='admin'&&<button className="outline" disabled={loading} onClick={()=>setReviewing(o)}>Revisar documentos</button>}</article>)}</div>{operators.length===0&&<Empty/>}</>}
  {view==='dispatch'&&<LiveDispatch role={session.role} operators={operators} services={services} revision={liveRevision}/>}
  {view==='tariffs'&&canManage&&<TariffsPanel role={session.role}/>}
  {view==='users'&&<><div className="section-controls"><p className="muted">Usuarios de esta empresa y sus funciones.</p><button className="primary small" onClick={()=>setModal('new-user')}><Plus size={16}/> Nuevo usuario</button></div><div className="table-wrap"><table><thead><tr><th>Nombre</th><th>Correo</th><th>Rol</th></tr></thead><tbody>{users.map(u=><tr key={u.id}><td>{u.name}</td><td>{u.email}</td><td><span className="role">{u.role}</span></td></tr>)}</tbody></table></div></>}
  </main>
  {selected&&<Modal title={`${selected.code} · ${kindNames[selected.kind]}`} onClose={()=>setSelected(null)}><div className="details"><div className="detail-head"><Pill status={selected.status}/><span>{stamp(selected.created_at)}</span></div><h3>{selected.customer_name}</h3><p>{selected.customer_phone}</p><p><MapPin size={16}/>{selected.pickup_address}</p>{selected.destination_address&&<p><ArrowRight size={16}/>{selected.destination_address}</p>}{selected.package_description&&<p><Package size={16}/> Paquete: {selected.package_description}</p>}{selected.recipient_name&&<p><UserRound size={16}/> Destinatario: {selected.recipient_name} · {selected.recipient_phone}</p>}{selected.vehicle_plate&&<p><Truck size={16}/> Vehículo: {selected.vehicle_plate} · {selected.vehicle_description||'Sin descripción'}</p>}{canManage&&selected.status==='pending'&&<DispatchCandidates serviceId={selected.id}/>}<div className="detail-price"><span>Precio cotizado: <b>{money(selected.quoted_total_dop)}</b></span><span>Operador: <b>{selected.operator_id?operators.find(o=>o.id===selected.operator_id)?.name||`#${selected.operator_id}`:'Sin asignar'}</b></span></div>{canManage&&selected.status==='pending'&&<EstimateButton serviceId={selected.id} onApply={async()=>{await load();setSelected(null)}}/>}{canManage&&selected.status==='pending'&&<button className="outline" onClick={async()=>{const price=window.prompt('Total cotizado RD$',selected.quoted_total_dop||'');if(price===null||!price.trim())return;const fee=window.prompt('Pago al operador RD$',selected.operator_fee_dop||'0');if(fee===null||!fee.trim())return;await mutation(()=>post(`/services/${selected.id}/quote`,{quoted_total_dop:price,operator_fee_dop:fee}));setSelected(null)}}>Establecer cotización</button>}{selected.proof_note&&<p><Check size={16}/> Constancia: {selected.proof_note}</p>}{canManage&&selected.status==='pending'&&<form className="inline-form" onSubmit={async e=>{e.preventDefault();const f=new FormData(e.currentTarget);await mutation(()=>post(`/services/${selected.id}/assign`,{operator_id:Number(f.get('operator_id'))}));setSelected(null)}}><label>Asignar operador<select name="operator_id" required defaultValue=""><option value="" disabled>Seleccionar operador verificado</option>{operators.filter(o=>o.kind===selected.kind&&o.verified&&o.active&&!services.some(s=>s.operator_id===o.id&&['assigned','en_route','on_site'].includes(s.status))).map(o=><option key={o.id} value={o.id}>{o.name} · {o.vehicle_type}</option>)}</select></label><button className="primary small" disabled={loading}>Asignar</button></form>}{transitions[selected.status].length>0&&<div className="status-actions">{transitions[selected.status].filter(()=>!(!canManage&&session.role!=='driver')).map(t=><button key={t} className="outline" onClick={()=>change(selected,t)} disabled={loading}>{statusNames[t]}</button>)}{canManage&&['assigned','en_route','on_site'].includes(selected.status)&&<button className="danger" onClick={()=>change(selected,'canceled')}>Cancelar</button>}</div>}<h4>Historial de eventos</h4><div className="timeline">{selected.events.map(event=><div key={event.id}><b>{event.event_type==='created'?'Solicitud creada':event.event_type==='assigned'?'Operador asignado':event.event_type==='quote_set'?'Cotización registrada':'Estado actualizado'}</b><small>{stamp(event.created_at)}</small><p>{event.detail}</p></div>)}</div></div></Modal>}
  {modal==='new-service'&&<NewService onClose={()=>setModal(null)} save={d=>mutation(()=>post('/services',d))} loading={loading}/>}
  {modal==='new-operator'&&<NewOperator onClose={()=>setModal(null)} save={d=>mutation(()=>post('/operators',d))} loading={loading} users={users.filter(u=>u.role==='driver')}/>}
  {reviewing&&<OperatorReviewModal key={`${reviewing.id}-${reviewReload}`} operator={reviewing} onClose={()=>setReviewing(null)} onDocuments={saveReviewDocs} onDecision={saveReviewDecision} loading={loading} error={error}/>}
   {closing&&<ClosingModal item={closing} loading={loading} error={error} onClose={()=>setClosing(null)} onConfirm={async(note)=>{setLoading(true);setError('');try{await post(`/services/${closing.service.id}/status`,{status:closing.status,note});await load();setMessage('Estado actualizado con constancia');setClosing(null);setSelected(null)}catch(e){setError((e as Error).message)}finally{setLoading(false)}}}/> }
   {modal==='new-user'&&<NewUser onClose={()=>setModal(null)} save={d=>mutation(()=>post('/users',d))} loading={loading}/>}
  </div>;
}
function ServiceTable({data,onSelect}:{data:Service[];onSelect:(s:Service)=>void}){if(data.length===0)return <Empty/>;return <div className="table-wrap"><table><thead><tr><th>Solicitud</th><th>Servicio</th><th>Cliente</th><th>Origen</th><th>Estado</th><th>Fecha</th><th></th></tr></thead><tbody>{data.map(s=><tr key={s.id} onClick={()=>onSelect(s)}><td><strong>{s.code}</strong></td><td><span className={'kind-icon '+s.kind}>{s.kind==='delivery'?<Package size={18}/>:<Truck size={18}/>}</span>{kindNames[s.kind]}<small>{types[s.kind].find(([t])=>t===s.service_type)?.[1]||s.service_type}</small></td><td>{s.customer_name}<small>{s.customer_phone}</small></td><td className="address">{s.pickup_address}</td><td><Pill status={s.status}/></td><td>{stamp(s.created_at)}</td><td><ChevronDown size={17}/></td></tr>)}</tbody></table></div>}
function Empty(){return <div className="empty"><Package size={34}/><h3>Aún no hay registros</h3><p>Las operaciones aparecerán aquí cuando se creen.</p></div>}
function value(f:FormData,n:string){return String(f.get(n)||'').trim()}
function NewService({onClose,save,loading}:{onClose:()=>void;save:(d:unknown)=>void;loading:boolean}){
  const [kind,setKind]=useState<Kind>('delivery');
  const [serviceType,setServiceType]=useState('parcel');
  const [location,setLocation]=useState<{lat:string;lng:string}|null>(null);
  const [geoError,setGeoError]=useState('');
  const requiresDestination=['parcel','scheduled_route','tow'].includes(serviceType);
  const parcel=kind==='delivery'&&serviceType==='parcel';
  const roadside=kind==='roadside';
  const onKind=(next:Kind)=>{setKind(next);setServiceType(next==='delivery'?'parcel':'tow')};
  return <Modal title="Nueva solicitud" onClose={onClose}>
    <form className="form-grid" onSubmit={e=>{e.preventDefault();const f=new FormData(e.currentTarget);save({
       kind,service_type:serviceType,customer_name:value(f,'name'),customer_phone:value(f,'phone'),
       lat:value(f,'lat')||null,lng:value(f,'lng')||null,
       destination_lat:value(f,'destLat')||null,destination_lng:value(f,'destLng')||null,
       pickup_address:value(f,'pickup'),destination_address:requiresDestination?value(f,'destination'):null,
       recipient_name:parcel?value(f,'recipient'):null,recipient_phone:parcel?value(f,'recipientPhone'):null,
       package_description:parcel?value(f,'package'):null,vehicle_plate:roadside?value(f,'vehiclePlate'):null,
       vehicle_description:roadside?value(f,'vehicleDescription'):null,
       notes:value(f,'notes')||null,quoted_total_dop:value(f,'price')||null,operator_fee_dop:value(f,'fee')||null
    })}}>
      <div className={'service-explainer full '+kind}><strong>{roadside?'Asistencia vial':'Delivery y mensajería'}</strong><span>{roadside?'Grúas, auxilio y atención al conductor':'Paquetes, rutas y entregas para comercios'}</span></div>
      <label>Modalidad<select value={kind} onChange={e=>onKind(e.target.value as Kind)}><option value="delivery">Delivery / Mensajería</option><option value="roadside">Grúas y asistencia vial</option></select></label>
      <label>Tipo de servicio<select value={serviceType} onChange={e=>setServiceType(e.target.value)}>{types[kind].map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label>
      <p className="form-section full">Cliente y ubicación</p>
      <label>Cliente / comercio<input name="name" required minLength={2} maxLength={120}/></label><label>Teléfono<input name="phone" required minLength={7} maxLength={40}/></label>
      <label className="full">Origen / lugar de atención<input name="pickup" required minLength={5} placeholder={roadside?'Calle, punto de referencia, sector':'Dirección de recogida y referencia'}/></label>
      <div className="full ops-geofields"><p className="ops-caption">GPS opcional: utilízalo para calcular distancias orientativas. La dirección escrita no se convierte automáticamente en coordenadas.</p>
      <button type="button" className="outline" onClick={()=>{
        if(!navigator.geolocation){setGeoError('Este navegador no permite GPS');return}
        navigator.geolocation.getCurrentPosition(pos=>{setLocation({lat:String(pos.coords.latitude),lng:String(pos.coords.longitude)});setGeoError('')},
        e=>setGeoError(e.message),{enableHighAccuracy:true,timeout:15000});
      }}><MapPin size={16}/> Usar mi ubicación como origen</button>
      {geoError&&<p className="ops-error">{geoError}</p>}
      <div className="ops-coordinates"><label>Latitud origen<input name="lat" type="number" step="any" min="-90" max="90" value={location?.lat||''} onChange={e=>setLocation({lat:e.target.value,lng:location?.lng||''})}/></label><label>Longitud origen<input name="lng" type="number" step="any" min="-180" max="180" value={location?.lng||''} onChange={e=>setLocation({lat:location?.lat||'',lng:e.target.value})}/></label></div></div>
      {requiresDestination&&<div className="full ops-coordinates"><label>Latitud destino (opcional)<input name="destLat" type="number" step="any" min="-90" max="90" placeholder="18.47"/></label><label>Longitud destino (opcional)<input name="destLng" type="number" step="any" min="-180" max="180" placeholder="-69.90"/></label></div>}
      {requiresDestination&&<label className="full">Destino <span className="muted">(obligatorio)</span><input name="destination" required minLength={5} placeholder={roadside?'Dirección del taller o destino de remolque':'Dirección completa de entrega'}/></label>}
      {parcel&&<><p className="form-section full">Datos de la entrega</p><label>Destinatario<input name="recipient" required minLength={2}/></label><label>Teléfono del destinatario<input name="recipientPhone" required minLength={7}/></label><label className="full">Descripción del paquete<input name="package" required minLength={3} placeholder="Ej.: documentos, caja sellada"/></label></>}
      {roadside&&<><p className="form-section full">Vehículo que requiere asistencia</p><label>Placa del vehículo<input name="vehiclePlate" required minLength={3}/></label><label>Marca / modelo / descripción<input name="vehicleDescription" placeholder="Ej.: SUV Ford Explorer gris"/></label></>}
      <p className="form-section full">Valores operativos (opcional)</p><label>Cotización (RD$)<input name="price" type="number" min="0" step="0.01"/></label><label>Pago operador (RD$)<input name="fee" type="number" min="0" step="0.01"/></label>
      <label className="full">Observaciones<textarea name="notes" rows={3} placeholder="Instrucciones de acceso, fragilidad, condiciones, contacto alterno..."/></label>
      <footer><button type="button" className="outline" onClick={onClose}>Cancelar</button><button className="primary" disabled={loading}>Guardar solicitud</button></footer>
    </form>
  </Modal>
}

const verificationNames:Record<Operator['verification_status'],string> = {
  pending:'Pendiente de verificación', approved:'Aprobado', rejected:'Rechazado', suspended:'Suspendido'
};
const reviewActionNames:Record<string,string>={
  created:'Registro del operador', documents_updated:'Documentación actualizada',
  approved:'Aprobación', rejected:'Rechazo', suspended:'Suspensión', pending:'Devuelto a pendiente'
};
function OperatorReviewModal({operator,onClose,onDocuments,onDecision,loading,error}:{operator:Operator;onClose:()=>void;onDocuments:(d:unknown)=>void;onDecision:(d:unknown)=>void;loading:boolean;error:string}){
  const [status,setStatus]=useState<'approved'|'rejected'|'suspended'|'pending'>('approved');
  const [reason,setReason]=useState('');
  const [confirmed,setConfirmed]=useState(false);
  const [history,setHistory]=useState<OperatorReview[]>([]);
  const [historyError,setHistoryError]=useState('');
  const [historyLoading,setHistoryLoading]=useState(false);
  const historyRefreshKey=[operator.id,operator.verification_status,operator.verified_at,operator.license_number,
    operator.license_expires_on,operator.insurance_policy,operator.insurance_expires_on].join('|');
  useEffect(()=>{
    let open=true;
    setHistoryLoading(true);setHistoryError('');
    api<OperatorReview[]>(`/operators/${operator.id}/reviews`).then(items=>{if(open)setHistory(items)}).catch(e=>{if(open)setHistoryError((e as Error).message)}).finally(()=>{if(open)setHistoryLoading(false)});
    return()=>{open=false};
  },[historyRefreshKey]);
  const today=new Date().toISOString().slice(0,10); // misma referencia UTC que utiliza la API
  const hasText=(v:string|null,min=3)=>Boolean(v&&v.trim().length>=min);
  const checks=[
    {name:'Placa del vehículo',ok:hasText(operator.license_plate)},
    {name:'Número de licencia',ok:hasText(operator.license_number)},
    {name:'Licencia vigente',ok:Boolean(operator.license_expires_on&&operator.license_expires_on>=today)},
    {name:'Referencia de matrícula',ok:hasText(operator.registration_reference)},
    {name:'Número de póliza',ok:hasText(operator.insurance_policy)},
    {name:'Póliza vigente',ok:Boolean(operator.insurance_expires_on&&operator.insurance_expires_on>=today)}
  ];
  const canApprove=checks.every(c=>c.ok);
  const reasonOk=reason.trim().length>=12;
  const approved=status==='approved';
  return <Modal title={`Homologación · ${operator.name}`} onClose={onClose}>
    <div className="review-modal-content">
      {error&&<div className="review-error" role="alert"><AlertCircle size={18}/>{error}</div>}
      <div className="review-summary" aria-label="Estado de homologación">
        <div><span className="review-kicker">Situación documental</span><strong>{verificationNames[operator.verification_status]}</strong><small>{kindNames[operator.kind]} · {operator.vehicle_type}</small></div>
        <span className={'review-status-tag '+operator.verification_status}>{verificationNames[operator.verification_status]}</span>
      </div>
      <p className="review-disclaimer"><ShieldCheck size={18}/> La aprobación es manual. Registrar referencias no comprueba por sí solo la autenticidad de los documentos. Utiliza documentación real antes de autorizar servicios pagados.</p>
      <form className="review-form" key={operator.id+'-'+operator.verified_at+'-'+(operator.license_number||'')} onSubmit={e=>{e.preventDefault();const f=new FormData(e.currentTarget);onDocuments({
        license_number:value(f,'license'),license_expires_on:value(f,'licenseExp'),
        registration_reference:value(f,'registration'),insurance_policy:value(f,'insurance'),insurance_expires_on:value(f,'insuranceExp')
      })}}>
        <div className="review-step"><span>01</span><div><h3>Documentación del operador</h3><p>Registra los números y las fechas indicadas en los documentos originales.</p></div></div>
        <div className="review-fields">
          <label>Número de licencia <input name="license" required minLength={3} maxLength={80} defaultValue={operator.license_number||''} placeholder="Número como figura en licencia" autoComplete="off"/></label>
          <label>Vencimiento de licencia <input name="licenseExp" type="date" required defaultValue={operator.license_expires_on||''}/></label>
          <label className="review-span">Referencia de matrícula <input name="registration" required minLength={3} maxLength={120} defaultValue={operator.registration_reference||''} placeholder="Matrícula o referencia de registro" autoComplete="off"/></label>
          <label>Número de póliza <input name="insurance" required minLength={3} maxLength={120} defaultValue={operator.insurance_policy||''} placeholder="Número de seguro" autoComplete="off"/></label>
          <label>Vencimiento de póliza <input name="insuranceExp" type="date" required defaultValue={operator.insurance_expires_on||''}/></label>
        </div>
        <div className="review-save"><p>Guardar cambios anulará cualquier aprobación anterior y dejará al operador pendiente de revisión.</p><button type="submit" className="outline" disabled={loading}><ShieldCheck size={16}/> Guardar documentos</button></div>
      </form>
      <section className="review-section">
        <div className="review-step"><span>02</span><div><h3>Validación y decisión</h3><p>Comprueba todos los requisitos antes de permitir la asignación de servicios.</p></div></div>
        <div className="review-checks" aria-label="Lista de requisitos documentales">
          {checks.map(c=><span key={c.name} className={c.ok?'review-check ready':'review-check missing'}>{c.ok?<Check size={14}/>:<AlertCircle size={14}/>} {c.name}</span>)}
        </div>
        {!canApprove&&<p className="review-warning" role="status"><AlertCircle size={17}/> Faltan datos o hay documentos vencidos. Puedes rechazar, suspender o devolver a pendiente, pero no aprobar hasta corregir los requisitos.</p>}
        <div className="review-fields review-decision-fields">
          <label className="review-span">Resultado de la revisión
            <select value={status} onChange={e=>{setStatus(e.target.value as typeof status);setConfirmed(false)}}>
              <option value="approved">Aprobar operador</option>
              <option value="rejected">Rechazar operador</option>
              <option value="suspended">Suspender operador</option>
              <option value="pending">Devolver a pendiente</option>
            </select>
          </label>
          <label className="review-span">Motivo y evidencia revisada
            <textarea rows={3} minLength={12} maxLength={1000} required value={reason} onChange={e=>setReason(e.target.value)} placeholder="Describe qué documentos revisaste, cómo los contrastaste y por qué tomaste esta decisión."/>
            <small className="review-character-count">{reason.trim().length} / mínimo 12 caracteres</small>
          </label>
        </div>
        {approved&&<label className="review-attestation"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/><span>Confirmo que contrasté los documentos con sus originales o evidencias verificables y que cumplen los requisitos aplicables. Esta declaración quedará registrada con mi usuario.</span></label>}
        <div className="review-submit"><button type="button" className="outline" onClick={onClose}>Cerrar</button><button type="button" className="primary" disabled={loading||!reasonOk||(approved&&(!confirmed||!canApprove))} onClick={()=>onDecision({status,note:reason.trim(),documents_checked:approved&&confirmed})}>{loading?'Procesando…':'Registrar decisión'}</button></div>
      </section>
      <section className="review-section review-history">
        <div className="review-step"><span>03</span><div><h3>Historial de homologación</h3><p>Acciones registradas con fecha y usuario responsable (ID).</p></div></div>
        {historyLoading&&<p className="review-history-state">Cargando historial…</p>}
        {historyError&&<p className="review-warning">No se pudo consultar el historial: {historyError}</p>}
        {!historyLoading&&!historyError&&history.length===0&&<p className="review-history-state">Todavía no hay revisiones registradas.</p>}
        {!historyLoading&&!historyError&&<ul className="review-timeline">{history.map(item=><li key={item.id}><span className="review-history-dot"/><div><strong>{reviewActionNames[item.action]||item.action}</strong><small>{stamp(item.created_at)} · Usuario #{item.actor_id}</small><p>{item.note}</p></div></li>)}</ul>}
      </section>
    </div>
  </Modal>
}
function ClosingModal({item,onClose,onConfirm,loading,error}:{item:{service:Service;status:'completed'|'canceled'};onClose:()=>void;onConfirm:(note:string)=>void;loading:boolean;error:string}){
  const [note,setNote]=useState('');
  const completing=item.status==='completed';
  return <Modal title={`${completing?'Finalizar':'Cancelar'} · ${item.service.code}`} onClose={onClose}>
    <div className="review-decision">
      {error&&<div className="review-error"><AlertCircle size={16}/>{error}</div>}
      <p>{completing?'Registra una constancia comprobable del servicio: quién recibió el paquete o vehículo, código de referencia y resultado.':'Indica el motivo de cancelación para el historial de auditoría.'}</p>
      <label>{completing?'Constancia de entrega / asistencia':'Motivo de cancelación'}<textarea rows={4} value={note} onChange={e=>setNote(e.target.value)} minLength={4} placeholder={completing?'Ej.: entregado a Ana, recibo #1234, sin daños aparentes':'Ej.: cliente solicitó cancelación'}/></label>
      <p className="muted">La constancia es un registro escrito; no equivale a validar digitalmente firma, foto u OTP.</p>
      <div className="dialog-actions"><button className="outline" onClick={onClose}>Volver</button><button className={completing?'primary':'danger'} disabled={loading||note.trim().length<4} onClick={()=>onConfirm(note.trim())}>{completing?'Confirmar finalización':'Confirmar cancelación'}</button></div>
    </div>
  </Modal>
}

function NewOperator({onClose,save,loading,users}:{onClose:()=>void;save:(d:unknown)=>void;loading:boolean;users:User[]}){const [kind,setKind]=useState<Kind>('delivery');return <Modal title="Registrar operador" onClose={onClose}><form className="form-grid" onSubmit={e=>{e.preventDefault();const f=new FormData(e.currentTarget);save({name:value(f,'name'),phone:value(f,'phone'),kind,vehicle_type:value(f,'vehicle'),license_plate:value(f,'plate')||null,user_id:value(f,'user')?Number(value(f,'user')):null,verified:false})}}><label>Nombre<input name="name" required/></label><label>Teléfono<input name="phone" required/></label><label>Modalidad<select value={kind} onChange={e=>setKind(e.target.value as Kind)}><option value="delivery">Delivery</option><option value="roadside">Asistencia Vial</option></select></label><label>Vehículo<select name="vehicle" key={kind}>{(kind==='delivery'?['motocicleta','furgoneta','automóvil']:['grúa plataforma','grúa arrastre','vehículo asistencia']).map(v=><option key={v} value={v}>{v}</option>)}</select></label><label>Placa<input name="plate"/></label><label>Usuario conductor (opcional)<select name="user"><option value="">Sin cuenta asignada</option>{users.map(u=><option key={u.id} value={u.id}>{u.name}</option>)}</select></label><p className="muted full">Por seguridad, el operador se crea sin verificar. Un administrador debe validar documentos y seguros antes de asignarle servicios.</p><footer><button type="button" className="outline" onClick={onClose}>Cancelar</button><button className="primary" disabled={loading}>Crear operador</button></footer></form></Modal>}
function NewUser({onClose,save,loading}:{onClose:()=>void;save:(d:unknown)=>void;loading:boolean}){return <Modal title="Nuevo usuario" onClose={onClose}><form className="form-grid" onSubmit={e=>{e.preventDefault();const f=new FormData(e.currentTarget);save({name:value(f,'name'),email:value(f,'email'),password:value(f,'password'),role:value(f,'role')})}}><label>Nombre<input name="name" required/></label><label>Correo<input type="email" name="email" required/></label><label>Contraseña (mín. 12)<input type="password" name="password" required minLength={12}/></label><label>Rol<select name="role"><option value="dispatcher">Despacho</option><option value="merchant">Comercio</option><option value="driver">Conductor</option><option value="admin">Administrador</option></select></label><footer><button type="button" className="outline" onClick={onClose}>Cancelar</button><button className="primary" disabled={loading}>Crear usuario</button></footer></form></Modal>}
