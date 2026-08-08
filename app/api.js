const API = (() => {
  const { hostname, port, protocol } = window.location;
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    if (port === '5173' || port === '5174') return 'http://localhost:8000/api';
    if (port === '8000' || port === '') return '/api';
  }
  return `${protocol}//${hostname}${port ? `:${port}` : ''}/api`;
})();
const token=()=>localStorage.getItem('peluq_token');
function clearSession(){localStorage.removeItem('peluq_token');localStorage.removeItem('peluq_role')}
function loginRequired(){clearSession();location.replace('login.html')}
async function api(path,options={}){const headers={'Content-Type':'application/json',...(options.headers||{})};if(token())headers.Authorization=`Bearer ${token()}`;const r=await fetch(API+path,{...options,headers});if(r.status===401){loginRequired();throw new Error('Sesión vencida. Redirigiendo al inicio de sesión.')}if(!r.ok){let e=await r.json().catch(()=>({detail:r.statusText}));throw new Error(typeof e.detail==='string'?e.detail:JSON.stringify(e.detail))}return r.status===204?null:r.json()}
function sessionRole(){
  const stored=localStorage.getItem('peluq_role');
  if(stored)return stored;
  try{
    const body=token()?.split('.')[0];
    if(!body)return null;
    return JSON.parse(atob(body.replace(/-/g,'+').replace(/_/g,'/'))).role||null;
  }catch{return null}
}
function sessionHome(){return sessionRole()==='admin'?'admin.html':sessionRole()==='especialista'?'specialist.html':'login.html'}
function logout(){clearSession();location.href='login.html'}
function requirePageRole(){
  const page=location.pathname.split('/').pop()||'login.html';
  const roles={
    'admin.html':'admin','admin-team.html':'admin','admin-history.html':'admin',
    'admin-staff.html':'admin','admin-services.html':'admin','admin-clients.html':'admin',
    'specialist.html':'especialista'
  };
  const required=roles[page];
  if(!required)return true;
  const role=sessionRole();
  if(!token()||!role){loginRequired();return false}
  if(role!==required){location.replace(sessionHome());return false}
  return true;
}
function applyRoleNavigation(){
  const nav=document.querySelector('.dashboard-nav');
  if(!nav)return;
  document.body.classList.add('top-nav-page');
  const role=sessionRole();
  const links=role==='admin'?[
    ['admin.html','◎','Asignar clientes'],
    ['admin-team.html','◷','Estado del equipo'],
    ['admin-history.html','◴','Historial'],
    ['admin-staff.html','♙','Editar especialistas'],
    ['admin-services.html','✦','Servicios y productos'],
    ['queue.html','◉','Cola pública']
  ]:role==='especialista'?[
    ['checkin.html','＋','Nuevo check-in'],
    ['specialist.html','◎','Mis clientes'],
    ['queue.html','◉','Cola pública']
  ]:[
    ['checkin.html','＋','Nuevo check-in'],
    ['queue.html','◉','Cola pública'],
    ['login.html','↗','Acceso del equipo']
  ];
  const current=location.pathname.split('/').pop()||'login.html';
  nav.innerHTML=links.map(([href,icon,label])=>`<a class="${href===current?'active':''}" href="${href}"><span>${icon}</span>${label}</a>`).join('');
}
applyRoleNavigation();
requirePageRole();
