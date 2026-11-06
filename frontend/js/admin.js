"use strict";
/* Логика админ-панели: вход, загрузка файлов, загрузка по ссылке Яндекс.Диска. */
const $=id=>document.getElementById(id);
const esc=s=>String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
function toast(msg){ const t=$("toast"); t.textContent=msg; t.classList.add("show"); clearTimeout(t._h); t._h=setTimeout(()=>t.classList.remove("show"),2800); }

const TOKEN_KEY="schedule_admin_token";
let token=localStorage.getItem(TOKEN_KEY)||"";

const KIND_LABEL={teachers:"Учителя",subjects:"Предметы"};

async function api(path,{method="GET",body,form}={}){
  const opts={method,headers:{}};
  if(token) opts.headers.Authorization=`Bearer ${token}`;
  if(form){ opts.body=form; }
  else if(body!==undefined){ opts.headers["Content-Type"]="application/json"; opts.body=JSON.stringify(body); }
  const resp=await fetch(path,opts);
  if(resp.status===401){ logout(false); throw new Error("Сессия истекла — войдите заново"); }
  let data=null;
  try{ data=await resp.json(); }catch(e){}
  if(!resp.ok) throw new Error(data?.detail||`Ошибка ${resp.status}`);
  return data;
}

function showPanel(on){
  $("loginCard").classList.toggle("hidden",on);
  $("adminPanel").classList.toggle("hidden",!on);
}
function logout(callApi=true){
  token=""; localStorage.removeItem(TOKEN_KEY);
  showPanel(false);
  if(callApi===true) toast("Вы вышли из админ-панели");
}

function fmtDate(iso){
  try{ return new Date(iso).toLocaleString("ru-RU",{day:"numeric",month:"long",hour:"2-digit",minute:"2-digit"}); }
  catch(e){ return "—"; }
}

async function loadStatus(){
  try{
    const st=await api("/api/admin/status");
    const list=[];
    for(const kind of ["teachers","subjects"]){
      const f=st[kind];
      if(f){
        list.push(`<div class="frow">
          <span class="tag-ok">✔</span>
          <span class="fkind">${KIND_LABEL[kind]}</span>
          <div><div class="fname">${esc(f.filename)}</div>
          <div class="fmeta">классов: ${f.classes} · строк расписания: ${f.lesson_rows}</div></div>
          <div class="spacer"></div>
          <button class="btn danger" data-del="${kind}">Удалить</button>
        </div>`);
      }else{
        list.push(`<div class="frow"><span style="color:var(--busy)">✖</span>
          <span class="fkind" style="background:#fdeeee;color:var(--busy)">${KIND_LABEL[kind]}</span>
          <span class="fmeta">Файл не загружен</span>
        </div>`);
      }
    }
    $("filesList").innerHTML=list.join("");
    $("filesList").querySelectorAll("[data-del]").forEach(b=>b.onclick=async()=>{
      if(!confirm(`Удалить файл «${KIND_LABEL[b.dataset.del]}»?`)) return;
      try{ await api(`/api/admin/file/${b.dataset.del}`,{method:"DELETE"}); toast("Файл удалён"); }
      catch(e){ toast(`⚠️ ${e.message}`); }
      loadStatus();
    });
    $("updatedLabel").textContent=st.updated_at?`Последнее обновление: ${fmtDate(st.updated_at)}`:"";
  }catch(e){
    $("filesList").innerHTML=`<div class="alert err">${esc(e.message)}</div>`;
  }
}

function alertBox(elId,items){
  if(!items.length){ $(elId).innerHTML=""; return; }
  const ok=items.every(i=>i.ok);
  $(elId).innerHTML=`<div class="alert ${ok?"ok":"err"}">`+
    items.map(i=>i.ok
      ? `✔ <b>${esc(i.file)}</b> → файл «${KIND_LABEL[i.kind]}» (${i.classes} классов)`
      : `⚠️ <b>${esc(i.file)}</b>: ${esc(i.error)}`
    ).join("<br>")+`</div>`;
}

/* ── вход ── */
$("loginForm").onsubmit=async e=>{
  e.preventDefault();
  const btn=$("loginBtn"); btn.disabled=true;
  $("loginAlert").innerHTML="";
  try{
    const data=await api("/api/admin/login",{method:"POST",body:{password:$("password").value}});
    token=data.token; localStorage.setItem(TOKEN_KEY,token);
    $("password").value="";
    showPanel(true); loadStatus();
    toast("✔ Добро пожаловать!");
  }catch(err){
    $("loginAlert").innerHTML=`<div class="alert err">${esc(err.message)}</div>`;
  }finally{ btn.disabled=false; }
};

$("logoutBtn").onclick=()=>logout();
$("refreshBtn").onclick=()=>loadStatus();

/* ── загрузка файлов ── */
const dz=$("dropzone"), fi=$("fileInput");
dz.onclick=()=>fi.click();
fi.onchange=()=>{ uploadFiles([...fi.files]); fi.value=""; };
dz.ondragover=e=>{e.preventDefault();dz.classList.add("drag");};
dz.ondragleave=()=>dz.classList.remove("drag");
dz.ondrop=e=>{e.preventDefault();dz.classList.remove("drag");uploadFiles([...e.dataTransfer.files]);};

async function uploadFiles(list){
  if(!list.length) return;
  $("uploadResult").innerHTML=`<div class="alert" style="background:#f4f5fa">
    <span class="spinner" style="display:inline-block;width:14px;height:14px;border:2px solid var(--line);border-top-color:var(--acc);border-radius:50%;animation:spin 1s linear infinite;vertical-align:-2px"></span>
    Загружаю ${list.length} файл(ов)…</div>`;
  const form=new FormData();
  list.forEach(f=>form.append("files",f));
  try{
    const data=await api("/api/admin/upload",{method:"POST",form});
    alertBox("uploadResult",data.results||[]);
    toast("✔ Готово — расписание обновлено для всех посетителей");
  }catch(e){
    $("uploadResult").innerHTML=`<div class="alert err">${esc(e.message)}</div>`;
  }
  loadStatus();
}

/* ── загрузка по ссылке Яндекс.Диска ── */
$("yandexBtn").onclick=async()=>{
  const url=$("yandexUrl").value.trim();
  if(!url){ toast("Вставьте ссылку"); return; }
  const btn=$("yandexBtn"); btn.disabled=true;
  $("yandexResult").innerHTML=`<div class="alert" style="background:#f4f5fa">Скачиваю файл с Яндекс.Диска…</div>`;
  try{
    const data=await api("/api/admin/fetch-yandex",{method:"POST",body:{url}});
    alertBox("yandexResult",[{ok:true,file:data.file,kind:data.kind,classes:null}]);
    $("yandexUrl").value="";
    loadStatus();
  }catch(e){
    $("yandexResult").innerHTML=`<div class="alert err">${esc(e.message)}</div>`;
  }finally{ btn.disabled=false; }
};

/* ── автостарт: если токен сохранён, проверяем его ── */
(async()=>{
  if(token){
    try{ await loadStatus(); showPanel(true); }
    catch(e){ /* loadStatus сам вызовет logout при 401 */ }
  }
})();
