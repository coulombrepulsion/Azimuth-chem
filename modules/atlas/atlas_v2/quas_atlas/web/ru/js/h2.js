/* H2 dissociation page (Atlas v2).  All numbers come from the Python model
   quas_atlas.core.h2 through the local server: h2.scan (curves), h2.point
   (one bond length: energies, CI vector, orbitals), h2.errors (error budget).
   This script only draws. */
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const NS='http://www.w3.org/2000/svg';
function el(p,t,a){const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);p.appendChild(e);return e}
const fc=(x,d)=>x.toFixed(d).replace('.',',').replace('-','−');
/* curves on the R grid, filled from h2.scan before the first drawing */
let PTS=[],LIM=0,RE=0;
const METH=[{id:'rhf',name:'RHF',col:'--accent',dash:'none',what:'один определитель |σ<sub>g</sub>σ̄<sub>g</sub>|'},
 {id:'uhf',name:'UHF',col:'--rho-l',dash:'none',what:'орбитали α и β свои; спин не сохраняется'},
 {id:'ci',name:'КВ',col:'--ci',dash:'none',what:'c₀|σ<sub>g</sub>σ̄<sub>g</sub>| + c₁|σ<sub>u</sub>σ̄<sub>u</sub>| — точно в этом базисе'},
 {id:'mp2',name:'MP2',col:'--mp2',dash:'7 4',what:'RHF + поправка 2-го порядка теории возмущений'},
 {id:'trip',name:'Триплет ³Σ<sub>u</sub><sup>+</sup>',col:'--trip',dash:'3 3',what:'σ<sub>g</sub>¹σ<sub>u</sub>¹, спины параллельны'}];
let S={R:1.4,show:{rhf:true,uhf:true,ci:true,mp2:false,trip:false}};
try{const s=JSON.parse(localStorage.getItem('h2d-state')||'null');if(s){if(s.R)S.R=s.R;if(s.show)S.show=s.show}}catch(e){}
const getPoint=QC.live('h2.point');
/* ===== график энергии ===== */
function drawE(p){const sv=document.getElementById('ech');sv.innerHTML='';const mut=tok('--muted'),ink=tok('--ink');
  const L=62,T=12,W=480,H=320,lo=-1.2,hi=-0.5;const sx=R=>L+(R-0.5)/7.5*W,sy=e=>T+H-(e-lo)/(hi-lo)*H;
  const cp=el(sv,'clipPath',{id:'cE'});el(cp,'rect',{x:L,y:T,width:W,height:H});
  for(let e=-1.2;e<=-0.49;e+=0.1){el(sv,'line',{x1:L,x2:L+W,y1:sy(e),y2:sy(e),stroke:tok('--line'),'stroke-width':.7});el(sv,'text',{x:L-6,y:sy(e)+4,'text-anchor':'end','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=fc(e,1)}
  [1,2,3,4,5,6,7,8].forEach(R=>el(sv,'text',{x:sx(R),y:T+H+16,'text-anchor':'middle','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=R);
  el(sv,'text',{x:L+W,y:T+H+34,'text-anchor':'end','font-size':13,'font-style':'italic','font-family':'PT Serif, serif',fill:mut}).textContent='R, бор';
  const g=el(sv,'g',{'clip-path':'url(#cE)'});
  el(g,'line',{x1:L,x2:L+W,y1:sy(LIM),y2:sy(LIM),stroke:mut,'stroke-width':1.2,'stroke-dasharray':'6 4'});
  el(sv,'text',{x:L+6,y:sy(LIM)+16,'text-anchor':'start','font-size':12,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent='2E(H) — два атома';
  METH.slice().reverse().forEach(m=>{if(!S.show[m.id])return;el(g,'polyline',{points:PTS.map(q=>sx(q.R).toFixed(1)+','+sy(q[m.id]).toFixed(1)).join(' '),fill:'none',stroke:tok(m.col),'stroke-width':m.id==='trip'?1.8:2.5,'stroke-dasharray':m.dash})});
  el(sv,'line',{x1:sx(S.R),x2:sx(S.R),y1:T,y2:T+H,stroke:ink,'stroke-width':1,'stroke-dasharray':'2 3',opacity:.7});
  METH.forEach(m=>{if(!S.show[m.id])return;const e=p[m.id];if(e<lo||e>hi)return;el(sv,'circle',{cx:sx(S.R),cy:sy(e),r:4.5,fill:tok(m.col),stroke:tok('--panel'),'stroke-width':1.5})});
  document.getElementById('eleg').innerHTML=METH.filter(m=>S.show[m.id]).map(m=>'<span><i class="sw" style="border-color:var('+m.col+');border-top-style:'+(m.dash==='none'?'solid':m.id==='trip'?'dotted':'dashed')+'"></i>'+m.name+'</span>').join('')+'<span><i class="sw" style="border-color:var(--muted);border-top-style:dashed"></i>предел: два атома H</span>'}
/* ===== числа в точке ===== */
function drawPanel(p){document.getElementById('atR').innerHTML='При R = '+fc(S.R,2)+' бор ('+fc(S.R*0.529177,3)+' Å), ат. ед.';
  document.getElementById('etab').innerHTML=METH.map(m=>'<tr><td><i class="sw" style="border-color:var('+m.col+');border-top-style:'+(m.dash==='none'?'solid':m.id==='trip'?'dotted':'dashed')+'"></i>'+m.name+'</td><td>'+fc(p[m.id],4)+'</td><td>'+(m.id==='trip'?'—':(p[m.id]-p.ci>=0?'+':'−')+fc(Math.abs(p[m.id]-p.ci),4))+'</td><td style="font-family:var(--f-body);font-size:12.5px;text-align:left;white-space:normal;color:var(--muted)">'+m.what+'</td></tr>').join('');
  const ecorr=p.ci-p.rhf;
  document.getElementById('ci').innerHTML='<div>Ψ = <b>'+fc(p.c0,3)+'</b>·|σ<sub>g</sub>σ̄<sub>g</sub>| '+(p.c1<0?'−':'+')+' <b>'+fc(Math.abs(p.c1),3)+'</b>·|σ<sub>u</sub>σ̄<sub>u</sub>| &nbsp; <span class="hint">(вес второй конфигурации '+fc(100*p.c1*p.c1,1)+' %)</span></div>'+
   '<div>Связь конфигураций K = (σ<sub>g</sub>σ<sub>u</sub>|σ<sub>g</sub>σ<sub>u</sub>) = '+fc(p.K,4)+'; щель ε<sub>u</sub> − ε<sub>g</sub> = '+fc(p.eu-p.eg,3)+'</div>'+
   '<div>Энергия корреляции E<sub>КВ</sub> − E<sub>RHF</sub> = <b>'+fc(ecorr,4)+'</b> ат. ед. = '+fc(ecorr*27.2114,2)+' эВ'+(S.show.mp2?'; MP2 даёт '+fc(p.mp2-p.rhf,4)+' ('+Math.round(100*(p.mp2-p.rhf)/ecorr)+' %)':'')+'</div>';
  const nu=2*p.c1*p.c1,ng=2*p.c0*p.c0;
  const row=(n,v,th,bad)=>'<tr><td>'+n+'</td><td class="'+(bad?'bad':'okc')+'">'+v+'</td><td>'+th+'</td></tr>';
  document.getElementById('diag').innerHTML=row('коэффициент главной конфигурации c₀',fc(p.c0,3),'&lt; 0,9',p.c0<0.9)+row('заселённости натуральных орбиталей n(σ<sub>g</sub>) / n(σ<sub>u</sub>)',fc(ng,3)+' / '+fc(nu,3),'&lt; 1,9 / &gt; 0,1',ng<1.9)+
    row('различие RHF и UHF, ⟨S²⟩ UHF',(p.rhf-p.uhf>1e-5?'есть, ':'нет, ')+fc(p.s2,2),'≠ 0 у синглета',p.s2>0.01)+row('щель ε<sub>u</sub> − ε<sub>g</sub>',fc(p.eu-p.eg,3),'мала',p.eu-p.eg<0.5)}
function drawExplain(p){let t;const cf=PTS.find(q=>q.s2>1e-3).R;
  if(S.R<1.8)t='<b>Около равновесия (R<sub>e</sub> ≈ '+fc(RE,2)+' бор в этом базисе): один определитель качественно верен.</b> c₀ = '+fc(p.c0,3)+', вторая конфигурация весит меньше '+Math.ceil(100*p.c1*p.c1)+' %. Поправка КВ к RHF небольшая — это <b>динамическая корреляция</b>: электроны чуть «уклоняются» друг от друга. Её хорошо берёт и MP2 (включите на графике). RHF и UHF здесь совпадают.';
  else if(S.R<3.6)t='<b>Связь растянута.</b> Щель между σ<sub>g</sub> и σ<sub>u</sub> сокращается, и вес конфигурации σ<sub>u</sub>² быстро растёт: c₀ = '+fc(p.c0,3)+'. '+(S.R>=cf?'После R ≈ '+fc(cf,2)+' бор UHF уходит ниже RHF — решение нарушает симметрию, разнося электроны α и β к разным атомам, но ⟨S²⟩ = '+fc(p.s2,2)+' вместо 0: это уже не чистый синглет.':'Пока R < '+fc(cf,2)+' бор, UHF совпадает с RHF.')+' Корреляция становится <b>статической</b>: ошибка RHF уже '+fc(p.rhf-p.ci,3)+' ат. ед. = '+fc((p.rhf-p.ci)*27.2114,1)+' эВ.';
  else t='<b>Диссоциация: σ<sub>g</sub>² и σ<sub>u</sub>² почти равноправны</b> (c₀ ≈ '+fc(p.c0,2)+', c₁ ≈ '+fc(p.c1,2)+'), один определитель качественно неверен — это <b>статическая корреляция</b>. В функции RHF ионная структура H⁺H⁻ входит с тем же коэффициентом, что и ковалентная (при R → ∞, где перекрывание исчезает, это половина H⁺ + H⁻), и RHF уходит на '+fc((p.rhf-LIM)*27.2114,1)+' эВ выше двух атомов. UHF правильно идёт к пределу диссоциации, но при конечном R ещё отличается от точного решения в этом базисе (КВ): здесь на '+fc((p.uhf-p.ci)*2625.5,1)+' кДж/моль. Функция UHF — смесь синглета и триплета (⟨S²⟩ ≈ '+fc(p.s2,2)+'), и с ростом R её энергия становится близкой к энергии триплета. <b>MP2 разваливается:</b> знаменатель ε<sub>g</sub> − ε<sub>u</sub> стремится к нулю, поправка неограниченно растёт и при больших R уводит энергию даже ниже точной — MP2 не вариационный. Только КВ (здесь оно совпадает с МКССП(2,2)) правильно описывает и энергию, и спин.';
  document.getElementById('explain').innerHTML=t}
/* ===== диагностика вдоль R ===== */
function drawDiag(){const sv=document.getElementById('dch');sv.innerHTML='';const mut=tok('--muted'),ink=tok('--ink');const L=44,T=10,W=480,H=196;const sx=R=>L+(R-0.5)/7.5*W,sy=v=>T+H-v/1.05*H;
  [0,0.5,1].forEach(v=>{el(sv,'line',{x1:L,x2:L+W,y1:sy(v),y2:sy(v),stroke:tok('--line'),'stroke-width':.7});el(sv,'text',{x:L-6,y:sy(v)+4,'text-anchor':'end','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=fc(v,1)});
  [0.9,0.1].forEach(v=>el(sv,'line',{x1:L,x2:L+W,y1:sy(v),y2:sy(v),stroke:mut,'stroke-width':1,'stroke-dasharray':'6 4'}));
  [1,2,3,4,5,6,7,8].forEach(R=>el(sv,'text',{x:sx(R),y:T+H+16,'text-anchor':'middle','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=R);
  el(sv,'text',{x:L+W,y:T+H+34,'text-anchor':'end','font-size':13,'font-style':'italic','font-family':'PT Serif, serif',fill:mut}).textContent='R, бор';
  const line=(f,c,d)=>el(sv,'polyline',{points:PTS.map(q=>sx(q.R).toFixed(1)+','+sy(f(q)).toFixed(1)).join(' '),fill:'none',stroke:tok(c),'stroke-width':2.3,'stroke-dasharray':d||'none'});
  line(q=>q.c0,'--ci');line(q=>2*q.c1*q.c1,'--mp2');line(q=>Math.max(0,q.s2),'--rho-l');
  el(sv,'line',{x1:sx(S.R),x2:sx(S.R),y1:T,y2:T+H,stroke:ink,'stroke-width':1,'stroke-dasharray':'2 3',opacity:.7})}
/* ===== орбитали ===== */
function drawOrb(p){const sv=document.getElementById('och');sv.innerHTML='';const mut=tok('--muted'),ink=tok('--ink');
  const L=30,T=10,W=500,H=196;const z0=-2,z1=S.R+2;const O=p.orb,zs=O.z;
  const cur={g:O.g,u:O.u,a:O.a,b:O.b};const all=Object.values(cur).flat();const lo=Math.min(...all)*1.1,hi=Math.max(...all)*1.1;
  const sx=z=>L+(z-z0)/(z1-z0)*W,sy=v=>T+H-(v-lo)/(hi-lo)*H;const pts=a=>a.map((v,i)=>sx(zs[i]).toFixed(1)+','+sy(v).toFixed(1)).join(' ');
  el(sv,'line',{x1:L,x2:L+W,y1:sy(0),y2:sy(0),stroke:tok('--line'),'stroke-width':1.2});
  el(sv,'polyline',{points:pts(cur.u),fill:'none',stroke:tok('--virt'),'stroke-width':1.8,'stroke-dasharray':'6 4'});
  el(sv,'polyline',{points:pts(cur.g),fill:'none',stroke:tok('--accent'),'stroke-width':2.6});
  const same=p.s2<1e-3;el(sv,'polyline',{points:pts(cur.a),fill:'none',stroke:tok('--rho-l'),'stroke-width':same?1.2:2.4,opacity:same?.8:1});
  el(sv,'polyline',{points:pts(cur.b),fill:'none',stroke:tok('--rho-l'),'stroke-width':2.4,'stroke-dasharray':'2 3'});
  [[0,'H'],[S.R,'H']].forEach(([z,n])=>{el(sv,'circle',{cx:sx(z),cy:sy(0),r:5,fill:ink});el(sv,'text',{x:sx(z),y:T+H+18,'text-anchor':'middle','font-size':13,fill:ink,'font-weight':600,'font-family':'Golos Text, sans-serif'}).textContent=n});
  if(same)el(sv,'text',{x:L+6,y:T+14,'font-size':12.5,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent='UHF = RHF: орбитали α и β совпадают с σg';
  else el(sv,'text',{x:L+6,y:T+14,'font-size':12.5,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent='UHF: α тяготеет к одному атому, β — к другому'}
/* ===== ковалентная и ионная структуры ===== */
function drawVB(p){const lam=p.lam;
  const bar=(name,l)=>'<div class="vb"><b>'+name+'</b><span class="t"><i style="width:'+(100*Math.min(1,l))+'%;background:var(--rho-l)"></i></span><span class="val">λ = '+fc(l,2)+'</span></div>';
  document.getElementById('vb').innerHTML=bar('RHF',1)+bar('КВ',lam)+'<div class="legend"><span>Ψ ∝ [A(1)B(2) + B(1)A(2)] + λ·[A(1)A(2) + B(1)B(2)]: длина полосы — отношение коэффициентов ионной и ковалентной структур λ (от 0 до 1). Это не вероятности: при конечном R структуры не ортогональны, и квадраты коэффициентов не дают долей.</span></div>'+
   '<p style="font-size:14.5px">У RHF λ = 1 <b>при любом R</b>: σ<sub>g</sub>² ∝ (A + B)(A + B) содержит ионные и ковалентные члены с равными коэффициентами — отсюда неправильная диссоциация: при R → ∞ функция наполовину описывает H⁺ + H⁻. КВ подбирает λ сама: при R = '+fc(S.R,2)+' бор λ = '+fc(lam,2)+(S.R<1.8?' (около равновесия ≈ 0,25–0,3: связь в основном ковалентная, но с заметной ионной примесью)':S.R>5?' — практически чистая ковалентная функция Гайтлера–Лондона, H• + H•.':'.')+'</p>'}
/* ===== управление ===== */
async function render(){document.getElementById('Rv').textContent=fc(S.R,2)+' бор = '+fc(S.R*0.529177,3)+' Å';
  const box=document.getElementById('show');box.innerHTML='';METH.forEach(m=>{const b=document.createElement('button');b.type='button';b.className='chip';b.innerHTML=m.name;b.setAttribute('aria-pressed',!!S.show[m.id]);b.onclick=()=>{S.show[m.id]=!S.show[m.id];save();render()};box.appendChild(b)})
  if(!PTS.length)return;let r;try{r=await getPoint({R:S.R})}catch(e){return}
  const p=Object.assign({},r.p,{orb:r.orb});drawE(p);drawPanel(p);drawExplain(p);drawDiag();drawOrb(p);drawVB(p);}
function save(){try{localStorage.setItem('h2d-state',JSON.stringify(S))}catch(e){}}
const Rin=document.getElementById('R');Rin.value=S.R;Rin.oninput=e=>{S.R=+e.target.value;save();render()};
document.getElementById('ech').addEventListener('click',e=>{const r=e.currentTarget.getBoundingClientRect();const R=0.5+((e.clientX-r.left)/r.width*560-62)/480*7.5;if(R<0.5||R>8)return;S.R=Math.round(R*20)/20;Rin.value=S.R;save();render()});
render();
QC.api('h2.scan',{}).then(d=>{PTS=d.R.map((R,i)=>({R,rhf:d.rhf[i],uhf:d.uhf[i],ci:d.ci[i],mp2:d.mp2[i],trip:d.trip[i],s2:d.s2[i],c0:d.c0[i],c1:d.c1[i]}));LIM=d.lim;RE=d.re;render()}).catch(()=>{});
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',render);
new MutationObserver(render).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});

/* ===== три вида ошибок ===== */
const getErr=QC.live('h2.errors');const ES={R:1.4,b:'6-31G**',m:'rhf',it:0};
function chipsE(id,items,cur,set){const g=document.getElementById(id);g.innerHTML='';items.forEach(([v,l,dis])=>{const b=document.createElement('button');b.type='button';b.className='chip';b.innerHTML=l;b.setAttribute('aria-pressed',v===cur);if(dis)b.disabled=true;b.onclick=()=>{set(v);drawErr()};g.appendChild(b)})}
async function drawErr(){const rhfOnly=ES.m==='rhf';
  chipsE('eR',[[1.4,'1,4 бор (равновесие)'],[10,'10 бор (два атома)']],ES.R,v=>ES.R=v);
  chipsE('eB',[['STO-3G','STO-3G'],['6-31G','6-31G'],['6-31G**','6-31G**']],ES.b,v=>ES.b=v);
  chipsE('eM',[['rhf','RHF'],['mp2','MP2'],['fci','полное КВ']],ES.m,v=>ES.m=v);
  chipsE('eI',[[1,'1',!rhfOnly],[2,'2',!rhfOnly],[3,'3',!rhfOnly],[0,'до сходимости',!rhfOnly]],rhfOnly?ES.it:0,v=>ES.it=v);
  let d;try{d=await getErr({R:ES.R,basis:ES.b,method:ES.m,iters:rhfOnly?ES.it:0})}catch(e){return}
  const E=d.E,eS=d.scf,eM=d.method,eB=d.basis,tot=d.total;
  const f=x=>fc(x*1000,1),k=x=>fc(x*2625.5,1);
  const row=(n,x,how,b)=>'<tr'+(b?' style="font-weight:600"':'')+'><td class="l">'+n+'</td><td>'+f(x)+'</td><td>'+k(x)+'</td><td class="l">'+how+'</td></tr>';
  document.getElementById('eTab').innerHTML='<tr><td class="l">E выбранного расчёта</td><td colspan="2">'+fc(E,6)+' E<sub>h</sub></td><td class="l">'+d.nbf+' базисных функций</td></tr>'+
    row('Ошибка E − E<sub>точн</sub>, всего',tot,'',true)+row('несошедшийся SCF: E(k итераций) − E(RHF)',eS,'сходимость SCF: итерации, DIIS, демпфирование, начальное приближение')+
    row('метод: E(метод) − E(полное КВ) в этом базисе',eM,'метод, лучше учитывающий корреляцию')+row('базис: E(полное КВ) − E<sub>точн</sub>',eB,'расширение базиса');
  let t='';
  if(eS>1e-4)t+='Расчёт не сошёлся: '+f(eS)+' мE<sub>h</sub> ошибки устраняет доведение SCF до сходимости: здесь хватает ещё нескольких итераций, а в трудных случаях нужны DIIS, демпфирование или другое начальное приближение. Метод и базис к этой части ошибки отношения не имеют. ';
  else if(rhfOnly&&ES.it>0)t+=(ES.b==='STO-3G'?'В минимальном базисе орбиталь H₂ задана симметрией, и RHF сходится за одну итерацию. ':'Итерации уже сошлись: дальнейшие не изменят энергию. ');
  if(ES.m==='fci')t+='Полное КВ — точное решение уравнения Шрёдингера в данном базисе, поэтому ошибки метода нет. Остаётся только ошибка базиса'+(ES.R===10?': при R = 10 бор это удвоенная ошибка атома H в этом базисе.':'.');
  else if(ES.m==='mp2'&&eM<0)t+='MP2 опустился ниже полного КВ на '+f(-eM)+' мE<sub>h</sub>: при растянутой связи теория возмущений расходится, а ниже точного решения в базисе вариационный метод опуститься не может — MP2 не вариационный.';
  else if(ES.R===10&&ES.m==='rhf')t+='Ошибка метода огромна ('+k(eM)+' кДж/моль), и расширение базиса её не устраняет: от STO-3G к 6-31G** она меняется с 337 до 248 мE<sub>h</sub>, но остаётся огромной. Один определитель RHF не описывает два отдельных атома — это статическая корреляция; нужен многоконфигурационный метод, здесь полное КВ.';
  else t+='Ошибка метода — недостающая энергия корреляции в этом базисе; она сама зависит от базиса (для RHF при 1,4 бор: 20,6 мE<sub>h</sub> в STO-3G и 33,9 мE<sub>h</sub> в 6-31G**). Ошибка базиса уменьшается при переходе STO-3G → 6-31G → 6-31G**.';
  document.getElementById('eSt').innerHTML=t}
drawErr();
