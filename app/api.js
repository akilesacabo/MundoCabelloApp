const API = (() => {
  const { hostname, port, protocol } = window.location;
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    if (port === '5173' || port === '5174') return 'http://localhost:8000/api';
    if (port === '8000' || port === '') return '/api';
  }
  return `${protocol}//${hostname}${port ? `:${port}` : ''}/api`;
})();
const token=()=>localStorage.getItem('peluq_token');
async function api(path,options={}){const headers={'Content-Type':'application/json',...(options.headers||{})};if(token())headers.Authorization=`Bearer ${token()}`;const r=await fetch(API+path,{...options,headers});if(!r.ok){let e=await r.json().catch(()=>({detail:r.statusText}));throw new Error(typeof e.detail==='string'?e.detail:JSON.stringify(e.detail))}return r.status===204?null:r.json()}
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
function logout(){localStorage.removeItem('peluq_token');localStorage.removeItem('peluq_role');location.href='login.html'}
