import {useEffect,useRef,useState} from 'react';
import {Clock3, Crosshair, MapPin, Navigation, RefreshCw, RadioTower, Save, ShieldAlert} from 'lucide-react';
import {api,post,put} from './api';
import type {Kind,Operator,Position,Role,Service,Tariff,Estimate} from './types';
const list:Record<string,string>={parcel:'Paquetería',scheduled_route:'Ruta programada',tow:'Grúa / remolque',jumpstart:'Paso de corriente',tire_change:'Cambio de goma',fuel:'Entrega de combustible',mechanical:'Auxilio mecánico'};
const fmt=(v:string|number)=>Number(v).toLocaleString('es-DO',{maximumFractionDigits:5});
const money=(v:string|number)=>`RD$ ${Number(v).toLocaleString('es-DO',{minimumFractionDigits:2,maximumFractionDigits:2})}`;
const coordsUrl=(lat:string,lng:string)=>`https://www.openstreetmap.org/?mlat=${encodeURIComponent(lat)}&mlon=${encodeURIComponent(lng)}#map=16/${encodeURIComponent(lat)}/${encodeURIComponent(lng)}`;
export function LiveDispatch({role,operators,services,revision}:{role:Role,operators:Operator[],services:Service[],revision:number}){
  const [positions,setPositions]=useState<Position[]>([]);
  const [error,setError]=useState('');
  const [sharing,setSharing]=useState(false);
  const [sent,setSent]=useState('');
  const watch=useRef<number|null>(null);
  const lastSent=useRef(0);
  const refresh=async()=>{if(role==='driver')return;try{setPositions(await api<Position[]>('/dispatch/positions'));setError('')}catch(e){setError((e as Error).message)}};
  useEffect(()=>{refresh()},[revision,role]);
  useEffect(()=>()=>{if(watch.current!=null)navigator.geolocation.clearWatch(watch.current)},[]);
  const stop=()=>{if(watch.current!=null)navigator.geolocation.clearWatch(watch.current);watch.current=null;setSharing(false)};
  const start=()=>{
    if(!('geolocation' in navigator)){setError('Tu navegador no permite obtener GPS. Abre desde localhost o mediante HTTPS.');return}
    setSharing(true);setError('');setSent('Esperando permiso y señal GPS...');
    watch.current=navigator.geolocation.watchPosition(async pos=>{
      if(Date.now()-lastSent.current<10000)return;
      lastSent.current=Date.now();
      try{await post('/dispatch/my-location',{lat:Number(pos.coords.latitude.toFixed(7)),lng:Number(pos.coords.longitude.toFixed(7)),accuracy_m:pos.coords.accuracy});setSent('Posición enviada: '+new Date().toLocaleTimeString('es-DO'))}
      catch(e){stop();setError((e as Error).message)}
    },e=>{stop();setError(`No se puede acceder al GPS (${e.message}). Se requiere permiso y conexión segura.`)},
    {enableHighAccuracy:true,maximumAge:5000,timeout:15000});
  };
  if(role==='driver')return <div className="operations"><div className="ops-head"><div><h2><Crosshair size={22}/> Mi ubicación GPS</h2><p>Compartir posición únicamente durante tu turno. Al cerrar esta pestaña deja de enviarse.</p></div></div><div className="ops-panel"><p>El sistema solo permite reportar GPS si tu cuenta está asociada a un operador activo y aprobado.</p><div className="ops-actions"><button className="primary" type="button" disabled={sharing} onClick={start}><Navigation size={16}/> Compartir mi ubicación</button><button className="outline" type="button" disabled={!sharing} onClick={stop}>Detener GPS</button></div>{sent&&<p className="ops-note">{sent}</p>}{error&&<p role="alert" className="ops-error">{error}</p>}</div></div>;
  const active=services.filter(s=>['assigned','en_route','on_site'].includes(s.status));
  return <div className="operations"><div className="ops-head"><div><h2><RadioTower size={22}/> Centro de despacho en vivo</h2><p>Ubicaciones reportadas voluntariamente por conductores · disponibilidad e incidencias.</p></div><button className="outline" onClick={refresh}><RefreshCw size={16}/> Actualizar GPS</button></div>
  <div className="ops-stats"><span><b>{positions.filter(p=>p.online).length}</b> operadores con GPS reciente</span><span><b>{positions.filter(p=>p.available).length}</b> disponibles</span><span><b>{active.length}</b> servicios activos</span></div>
  {error&&<p className="ops-error" role="alert">{error}</p>}
  <div className="ops-columns"><section className="ops-panel"><h3>Operadores y ubicaciones</h3><p className="ops-caption">GPS reciente: menos de 3 minutos. Si no hay posición, no se supone que el conductor esté disponible.</p>
   {operators.map(op=>{const x=positions.find(p=>p.operator_id===op.id);const busy=active.find(s=>s.operator_id===op.id);return <article className="ops-row" key={op.id}><div><b>{op.name}</b><small>{op.kind==='delivery'?'Delivery':'Asistencia Vial'} · #{op.id}</small>{x?<><small><MapPin size={12}/> {fmt(x.lat)}, {fmt(x.lng)} · ±{Math.round(x.accuracy_m)}m</small><small><Clock3 size={12}/> {new Date(x.recorded_at).toLocaleTimeString('es-DO')}</small><a href={coordsUrl(x.lat,x.lng)} target="_blank" rel="noopener noreferrer">Ver punto GPS en mapa ↗</a></>:<small>Sin posición GPS reportada</small>}</div><div><span className={`ops-chip ${x?.available?'available':x?.online?'busy':'offline'}`}>{busy?'En servicio':x?.available?'Disponible':x?.online?'No disponible':'Sin señal'}</span></div></article>})}
   {operators.length===0&&<p className="ops-note">Todavía no hay operadores registrados.</p>}</section>
   <section className="ops-panel"><h3>Servicios en operación</h3>{active.map(s=><article className="ops-row" key={s.id}><div><b>{s.code}</b><small>{s.kind==='delivery'?'Delivery':'Asistencia Vial'} · {s.customer_name}</small><small>{s.pickup_address}</small><small>Operador #{s.operator_id||'Sin asignar'}</small></div><span className="ops-chip busy">{({assigned:'Asignado',en_route:'En ruta',on_site:'En sitio'} as Record<string,string>)[s.status]}</span></article>)}{active.length===0&&<p className="ops-note">Sin servicios activos. Los cambios aparecerán automáticamente.</p>}</section></div>
  <div className="ops-warning"><ShieldAlert size={18}/> El GPS procede del dispositivo y no constituye prueba antifraude. La distancia vial, los tiempos de llegada y el tráfico requieren un proveedor de rutas adicional.</div></div>;
}
export function TariffsPanel({role}:{role:Role}){
 const [tariffs,setTariffs]=useState<Tariff[]>([]);const [kind,setKind]=useState<Kind>('delivery');const [type,setType]=useState('parcel');
 const [base,setBase]=useState('0');const [rate,setRate]=useState('0');const [minimum,setMinimum]=useState('0');const [fee,setFee]=useState('0');const [active,setActive]=useState(true);
 const [error,setError]=useState('');const [notice,setNotice]=useState('');const [busy,setBusy]=useState(false);
 const types=kind==='delivery'?['parcel','scheduled_route']:['tow','jumpstart','tire_change','fuel','mechanical'];
 const refresh=()=>api<Tariff[]>('/tariffs').then(setTariffs).catch(e=>setError((e as Error).message));
 useEffect(()=>{refresh()},[]);
 useEffect(()=>{const t=tariffs.find(t=>t.service_type===type);setBase(t?.base_dop||'0');setRate(t?.per_km_dop||'0');setMinimum(t?.minimum_dop||'0');setFee(t?.operator_base_dop||'0');setActive(t?.active??true)},[type,tariffs]);
 const save=async()=>{setBusy(true);setError('');try{await put(`/tariffs/${type}`,{service_type:type,base_dop:base,per_km_dop:rate,minimum_dop:minimum,operator_base_dop:fee,active});await refresh();setNotice('Tarifa de referencia guardada. No se modifica ninguna cotización anterior.')}catch(e){setError((e as Error).message)}finally{setBusy(false)}};
 return <div className="operations"><div className="ops-head"><div><h2>Tarifas de referencia</h2><p>Valores base por servicio. Las cotizaciones deben ser revisadas por despacho.</p></div></div>
 <div className="ops-columns"><section className="ops-panel"><h3>Reglas existentes</h3>{tariffs.map(t=><button key={t.id} type="button" className="tariff-row" onClick={()=>{setKind(t.kind);setType(t.service_type)}}><strong>{list[t.service_type]}</strong><small>{money(t.base_dop)} base · {money(t.per_km_dop)}/km · mínimo {money(t.minimum_dop)}</small><span className={t.active?'ops-chip available':'ops-chip offline'}>{t.active?'Activa':'Inactiva'}</span></button>)}{tariffs.length===0&&<p className="ops-note">Sin tarifas configuradas. Las cotizaciones manuales siguen disponibles.</p>}</section>
 <section className="ops-panel"><h3>Configurar tarifa</h3><div className="ops-form"><label>Modalidad<select value={kind} onChange={e=>{const k=e.target.value as Kind;setKind(k);setType(k==='delivery'?'parcel':'tow')}}><option value="delivery">Delivery</option><option value="roadside">Asistencia Vial</option></select></label><label>Tipo<select value={type} onChange={e=>setType(e.target.value)}>{types.map(t=><option key={t} value={t}>{list[t]}</option>)}</select></label><label>Base RD$<input type="number" min="0" step="0.01" value={base} onChange={e=>setBase(e.target.value)}/></label><label>Por km RD$<input type="number" min="0" step="0.01" value={rate} onChange={e=>setRate(e.target.value)}/></label><label>Mínimo RD$<input type="number" min="0" step="0.01" value={minimum} onChange={e=>setMinimum(e.target.value)}/></label><label>Pago base operador RD$<input type="number" min="0" step="0.01" value={fee} onChange={e=>setFee(e.target.value)}/></label><label className="ops-check"><input type="checkbox" checked={active} onChange={e=>setActive(e.target.checked)}/> Tarifa activa</label>{role==='admin'&&<button className="primary" disabled={busy} onClick={save}><Save size={16}/> Guardar tarifa</button>}{role!=='admin'&&<p className="ops-note">Solo un administrador puede editar tarifas.</p>}</div></section></div>
 {notice&&<p className="ops-success">{notice}</p>}{error&&<p className="ops-error">{error}</p>}<p className="ops-warning"><ShieldAlert size={18}/> No se calculan rutas reales ni se incluyen automáticamente peajes, combustible, seguros, impuestos o recargos. Esta herramienta solo ayuda a estimar un precio preliminar.</p></div>;
}
export function EstimateButton({serviceId,onApply}:{serviceId:number;onApply:()=>void}){
 const [estimate,setEstimate]=useState<Estimate|null>(null);const [error,setError]=useState('');const [busy,setBusy]=useState(false);
 const retrieve=async()=>{setError('');try{setEstimate(await api<Estimate>(`/tariffs/estimate/${serviceId}`))}catch(e){setError((e as Error).message)}};
 const apply=async()=>{if(!estimate)return;setBusy(true);setError('');try{await post(`/services/${serviceId}/quote`,{quoted_total_dop:estimate.suggested_total_dop,operator_fee_dop:estimate.suggested_operator_fee_dop});onApply()}catch(e){setError((e as Error).message)}finally{setBusy(false)}};
 return <div className="estimate"><button type="button" className="outline" onClick={retrieve}>Calcular tarifa orientativa</button>{estimate&&<div className="ops-panel"><b>Estimado: {money(estimate.suggested_total_dop)}</b><p>Pago operador: {money(estimate.suggested_operator_fee_dop)} · {estimate.distance_km?`Distancia recta aprox. ${estimate.distance_km} km`:'Tarifa base'}</p><small>{estimate.warning}</small><button disabled={busy} type="button" onClick={apply} className="primary">Confirmar como cotización</button></div>}{error&&<p className="ops-error" role="alert">{error}</p>}</div>;
}

export function DispatchCandidates({serviceId}:{serviceId:number}){
 const [items,setItems]=useState<Array<{operator_id:number;name:string;distance_straight_km:number|null;accuracy_m:number}>>([]);
 const [message,setMessage]=useState('');
 useEffect(()=>{let mounted=true;api<{candidates:Array<{operator_id:number;name:string;distance_straight_km:number|null;accuracy_m:number}>;warning:string}>(`/dispatch/candidates/${serviceId}`)
 .then(result=>{if(mounted)setItems(result.candidates)}).catch(e=>{if(mounted)setMessage((e as Error).message)});
 return()=>{mounted=false}},[serviceId]);
 return <div className="candidates"><h4>Operadores sugeridos con GPS reciente</h4><p className="ops-caption">Disponibles y compatibles con esta solicitud. Distancias aproximadas en línea recta.</p>
 {items.map(x=><div className="candidate-row" key={x.operator_id}><span>{x.name} · #{x.operator_id}</span><b>{x.distance_straight_km!=null?`${x.distance_straight_km} km rectos`:'Sin GPS de origen'}</b></div>)}
 {!items.length&&<p className="ops-note">Sin candidatos con posición reciente. Puedes asignar manualmente un operador aprobado si confirmaste su disponibilidad.</p>}{message&&<p className="ops-error">{message}</p>}</div>
}
