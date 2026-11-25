/* H2 dissociation page (Atlas v2).  All numbers come from the Python model
   quas_atlas.core.h2 through the local server: h2.scan (curves), h2.point
   (one bond length: energies, CI vector, orbitals), h2.errors (error budget).
   This script only draws. */
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const NS='http://www.w3.org/2000/svg';
function el(p,t,a){const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);p.appendChild(e);return e}
const fc=(x,d)=>x.toFixed(d).replace('-','−');
/* curves on the R grid, filled from h2.scan before the first drawing */
let PTS=[],LIM=0,RE=0;
const METH=[{id:'rhf',name:'RHF',col:'--accent',dash:'none',what:'单个行列式 |σ<sub>g</sub>σ̄<sub>g</sub>|'},
 {id:'uhf',name:'UHF',col:'--rho-l',dash:'none',what:'α 和 β 各有自己的轨道；自旋不守恒'},
 {id:'ci',name:'CI',col:'--ci',dash:'none',what:'c₀|σ<sub>g</sub>σ̄<sub>g</sub>| + c₁|σ<sub>u</sub>σ̄<sub>u</sub>|——在此基组中是精确的'},
 {id:'mp2',name:'MP2',col:'--mp2',dash:'7 4',what:'RHF + 二阶微扰校正'},
 {id:'trip',name:'三重态 ³Σ<sub>u</sub><sup>+</sup>',col:'--trip',dash:'3 3',what:'σ<sub>g</sub>¹σ<sub>u</sub>¹，自旋平行'}];
let S={R:1.4,show:{rhf:true,uhf:true,ci:true,mp2:false,trip:false}};
try{const s=JSON.parse(localStorage.getItem('h2d-state')||'null');if(s){if(s.R)S.R=s.R;if(s.show)S.show=s.show}}catch(e){}
const getPoint=QC.live('h2.point');
/* ===== график энергии ===== */
function drawE(p){const sv=document.getElementById('ech');sv.innerHTML='';const mut=tok('--muted'),ink=tok('--ink');
  const L=62,T=12,W=480,H=320,lo=-1.2,hi=-0.5;const sx=R=>L+(R-0.5)/7.5*W,sy=e=>T+H-(e-lo)/(hi-lo)*H;
  const cp=el(sv,'clipPath',{id:'cE'});el(cp,'rect',{x:L,y:T,width:W,height:H});
  for(let e=-1.2;e<=-0.49;e+=0.1){el(sv,'line',{x1:L,x2:L+W,y1:sy(e),y2:sy(e),stroke:tok('--line'),'stroke-width':.7});el(sv,'text',{x:L-6,y:sy(e)+4,'text-anchor':'end','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=fc(e,1)}
  [1,2,3,4,5,6,7,8].forEach(R=>el(sv,'text',{x:sx(R),y:T+H+16,'text-anchor':'middle','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=R);
  el(sv,'text',{x:L+W,y:T+H+34,'text-anchor':'end','font-size':13,'font-style':'italic','font-family':'PT Serif, serif',fill:mut}).textContent='R，玻尔';
  const g=el(sv,'g',{'clip-path':'url(#cE)'});
  el(g,'line',{x1:L,x2:L+W,y1:sy(LIM),y2:sy(LIM),stroke:mut,'stroke-width':1.2,'stroke-dasharray':'6 4'});
  el(sv,'text',{x:L+6,y:sy(LIM)+16,'text-anchor':'start','font-size':12,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent='2E(H)——两个原子';
  METH.slice().reverse().forEach(m=>{if(!S.show[m.id])return;el(g,'polyline',{points:PTS.map(q=>sx(q.R).toFixed(1)+','+sy(q[m.id]).toFixed(1)).join(' '),fill:'none',stroke:tok(m.col),'stroke-width':m.id==='trip'?1.8:2.5,'stroke-dasharray':m.dash})});
  el(sv,'line',{x1:sx(S.R),x2:sx(S.R),y1:T,y2:T+H,stroke:ink,'stroke-width':1,'stroke-dasharray':'2 3',opacity:.7});
  METH.forEach(m=>{if(!S.show[m.id])return;const e=p[m.id];if(e<lo||e>hi)return;el(sv,'circle',{cx:sx(S.R),cy:sy(e),r:4.5,fill:tok(m.col),stroke:tok('--panel'),'stroke-width':1.5})});
  document.getElementById('eleg').innerHTML=METH.filter(m=>S.show[m.id]).map(m=>'<span><i class="sw" style="border-color:var('+m.col+');border-top-style:'+(m.dash==='none'?'solid':m.id==='trip'?'dotted':'dashed')+'"></i>'+m.name+'</span>').join('')+'<span><i class="sw" style="border-color:var(--muted);border-top-style:dashed"></i>极限：两个 H 原子</span>'}
/* ===== числа в точке ===== */
function drawPanel(p){document.getElementById('atR').innerHTML='R = '+fc(S.R,2)+' bohr（'+fc(S.R*0.529177,3)+' Å）时，原子单位';
  document.getElementById('etab').innerHTML=METH.map(m=>'<tr><td><i class="sw" style="border-color:var('+m.col+');border-top-style:'+(m.dash==='none'?'solid':m.id==='trip'?'dotted':'dashed')+'"></i>'+m.name+'</td><td>'+fc(p[m.id],4)+'</td><td>'+(m.id==='trip'?'—':(p[m.id]-p.ci>=0?'+':'−')+fc(Math.abs(p[m.id]-p.ci),4))+'</td><td style="font-family:var(--f-body);font-size:12.5px;text-align:left;white-space:normal;color:var(--muted)">'+m.what+'</td></tr>').join('');
  const ecorr=p.ci-p.rhf;
  document.getElementById('ci').innerHTML='<div>Ψ = <b>'+fc(p.c0,3)+'</b>·|σ<sub>g</sub>σ̄<sub>g</sub>| '+(p.c1<0?'−':'+')+' <b>'+fc(Math.abs(p.c1),3)+'</b>·|σ<sub>u</sub>σ̄<sub>u</sub>| &nbsp; <span class="hint">（第二个组态的权重 '+fc(100*p.c1*p.c1,1)+' %)</span></div>'+
   '<div>组态耦合 K = (σ<sub>g</sub>σ<sub>u</sub>|σ<sub>g</sub>σ<sub>u</sub>) = '+fc(p.K,4)+'；能隙 ε<sub>u</sub> − ε<sub>g</sub> = '+fc(p.eu-p.eg,3)+'</div>'+
   '<div>相关能 E<sub>CI</sub> − E<sub>RHF</sub> = <b>'+fc(ecorr,4)+'</b> a.u. = '+fc(ecorr*27.2114,2)+' eV'+(S.show.mp2?'；MP2 给出 '+fc(p.mp2-p.rhf,4)+' ('+Math.round(100*(p.mp2-p.rhf)/ecorr)+' %)':'')+'</div>';
  const nu=2*p.c1*p.c1,ng=2*p.c0*p.c0;
  const row=(n,v,th,bad)=>'<tr><td>'+n+'</td><td class="'+(bad?'bad':'okc')+'">'+v+'</td><td>'+th+'</td></tr>';
  document.getElementById('diag').innerHTML=row('主组态系数 c₀',fc(p.c0,3),'&lt; 0.9',p.c0<0.9)+row('自然轨道布居 n(σ<sub>g</sub>) / n(σ<sub>u</sub>)',fc(ng,3)+' / '+fc(nu,3),'&lt; 1.9 / &gt; 0.1',ng<1.9)+
    row('RHF 与 UHF 的差异，UHF 的 ⟨S²⟩',(p.rhf-p.uhf>1e-5?'有，':'无，')+fc(p.s2,2),'单重态应为 ≠ 0',p.s2>0.01)+row('能隙 ε<sub>u</sub> − ε<sub>g</sub>',fc(p.eu-p.eg,3),'小',p.eu-p.eg<0.5)}
function drawExplain(p){let t;const cf=PTS.find(q=>q.s2>1e-3).R;
  if(S.R<1.8)t='<b>平衡附近（R<sub>e</sub> ≈ '+fc(RE,2)+' bohr，在此基组中）：单个行列式定性正确。</b> c₀ = '+fc(p.c0,3)+'，第二个组态的权重小于 '+Math.ceil(100*p.c1*p.c1)+' %。CI 对 RHF 的校正很小——这是<b>动态相关</b>：电子彼此稍稍“回避”。MP2 也能很好地描述它（可在图上打开）。这里 RHF 与 UHF 相同。';
  else if(S.R<3.6)t='<b>键被拉伸。</b>σ<sub>g</sub> 与 σ<sub>u</sub> 之间的能隙减小，组态 σ<sub>u</sub>² 的权重迅速增大：c₀ = '+fc(p.c0,3)+'. '+(S.R>=cf?'R ≈ '+fc(cf,2)+' bohr 之后，UHF 降到 RHF 以下——该解破缺对称性，把 α 和 β 电子分到不同原子上，但 ⟨S²⟩ = '+fc(p.s2,2)+'，而不是 0：这已不是纯单重态。':'R < '+fc(cf,2)+' bohr 时，UHF 与 RHF 相同。')+'相关变为<b>静态相关</b>：RHF 的误差已达 '+fc(p.rhf-p.ci,3)+' a.u. = '+fc((p.rhf-p.ci)*27.2114,1)+' eV。';
  else t='<b>解离：σ<sub>g</sub>² 与 σ<sub>u</sub>² 几乎同等重要</b>（c₀ ≈ '+fc(p.c0,2)+', c₁ ≈ '+fc(p.c1,2)+'），单个行列式在定性上就是错误的——这是<b>静态相关</b>。在 RHF 函数中，离子结构 H⁺H⁻ 以与共价结构相同的系数出现（在 R → ∞、重叠消失时，这意味着一半是 H⁺ + H⁻），RHF 比两个原子高出 '+fc((p.rhf-LIM)*27.2114,1)+' eV。UHF 正确地趋向解离极限，但在有限 R 下仍与该基组中的精确解（CI）不同：这里相差 '+fc((p.uhf-p.ci)*2625.5,1)+' kJ/mol。UHF 函数是单重态和三重态的混合（⟨S²⟩ ≈ '+fc(p.s2,2)+'），随着 R 增大，其能量接近三重态的能量。<b>MP2 失效：</b>分母 ε<sub>g</sub> − ε<sub>u</sub> 趋于零，校正无限增大，在大 R 下甚至使能量低于精确值——MP2 不是变分方法。只有 CI（这里与 MCSCF(2,2) 相同）能同时正确描述能量和自旋。';
  document.getElementById('explain').innerHTML=t}
/* ===== диагностика вдоль R ===== */
function drawDiag(){const sv=document.getElementById('dch');sv.innerHTML='';const mut=tok('--muted'),ink=tok('--ink');const L=44,T=10,W=480,H=196;const sx=R=>L+(R-0.5)/7.5*W,sy=v=>T+H-v/1.05*H;
  [0,0.5,1].forEach(v=>{el(sv,'line',{x1:L,x2:L+W,y1:sy(v),y2:sy(v),stroke:tok('--line'),'stroke-width':.7});el(sv,'text',{x:L-6,y:sy(v)+4,'text-anchor':'end','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=fc(v,1)});
  [0.9,0.1].forEach(v=>el(sv,'line',{x1:L,x2:L+W,y1:sy(v),y2:sy(v),stroke:mut,'stroke-width':1,'stroke-dasharray':'6 4'}));
  [1,2,3,4,5,6,7,8].forEach(R=>el(sv,'text',{x:sx(R),y:T+H+16,'text-anchor':'middle','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=R);
  el(sv,'text',{x:L+W,y:T+H+34,'text-anchor':'end','font-size':13,'font-style':'italic','font-family':'PT Serif, serif',fill:mut}).textContent='R，玻尔';
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
  if(same)el(sv,'text',{x:L+6,y:T+14,'font-size':12.5,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent='UHF = RHF：α 和 β 轨道均与 σg 相同';
  else el(sv,'text',{x:L+6,y:T+14,'font-size':12.5,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent='UHF：α 偏向一个原子，β 偏向另一个'}
/* ===== ковалентная и ионная структуры ===== */
function drawVB(p){const lam=p.lam;
  const bar=(name,l)=>'<div class="vb"><b>'+name+'</b><span class="t"><i style="width:'+(100*Math.min(1,l))+'%;background:var(--rho-l)"></i></span><span class="val">λ = '+fc(l,2)+'</span></div>';
  document.getElementById('vb').innerHTML=bar('RHF',1)+bar('CI',lam)+'<div class="legend"><span>Ψ ∝ [A(1)B(2) + B(1)A(2)] + λ·[A(1)A(2) + B(1)B(2)]：条的长度是离子结构与共价结构系数之比 λ（0 到 1）。这不是概率：在有限 R 下这些结构不正交，系数的平方不能给出份额。</span></div>'+
   '<p style="font-size:14.5px">RHF 在<b>任何 R 下</b> λ = 1：σ<sub>g</sub>² ∝ (A + B)(A + B) 中离子项和共价项的系数相等——由此导致错误的解离：R → ∞ 时函数有一半描述 H⁺ + H⁻。CI 自行选择 λ：在 R = '+fc(S.R,2)+' bohr 时 λ = '+fc(lam,2)+(S.R<1.8?'（平衡附近 ≈ 0.25–0.3：键以共价为主，但有明显的离子成分）':S.R>5?'——几乎是纯共价的海特勒–伦敦函数，H• + H•。':'.')+'</p>'}
/* ===== управление ===== */
async function render(){document.getElementById('Rv').textContent=fc(S.R,2)+' 玻尔 = '+fc(S.R*0.529177,3)+' Å';
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
  chipsE('eR',[[1.4,'1.4 bohr（平衡）'],[10,'10 bohr（两个原子）']],ES.R,v=>ES.R=v);
  chipsE('eB',[['STO-3G','STO-3G'],['6-31G','6-31G'],['6-31G**','6-31G**']],ES.b,v=>ES.b=v);
  chipsE('eM',[['rhf','RHF'],['mp2','MP2'],['fci','完全 CI']],ES.m,v=>ES.m=v);
  chipsE('eI',[[1,'1',!rhfOnly],[2,'2',!rhfOnly],[3,'3',!rhfOnly],[0,'直到收敛',!rhfOnly]],rhfOnly?ES.it:0,v=>ES.it=v);
  let d;try{d=await getErr({R:ES.R,basis:ES.b,method:ES.m,iters:rhfOnly?ES.it:0})}catch(e){return}
  const E=d.E,eS=d.scf,eM=d.method,eB=d.basis,tot=d.total;
  const f=x=>fc(x*1000,1),k=x=>fc(x*2625.5,1);
  const row=(n,x,how,b)=>'<tr'+(b?' style="font-weight:600"':'')+'><td class="l">'+n+'</td><td>'+f(x)+'</td><td>'+k(x)+'</td><td class="l">'+how+'</td></tr>';
  document.getElementById('eTab').innerHTML='<tr><td class="l">所选计算的 E</td><td colspan="2">'+fc(E,6)+' E<sub>h</sub></td><td class="l">'+d.nbf+' 个基函数</td></tr>'+
    row('误差 E − E<sub>精确</sub>，总计',tot,'',true)+row('未收敛的 SCF：E（k 次迭代）− E(RHF)',eS,'SCF 收敛：迭代、DIIS、阻尼、初始猜测')+
    row('方法：E（方法）− E（完全 CI），同一基组',eM,'能更好地描述相关的方法')+row('基组：E（完全 CI）− E<sub>精确</sub>',eB,'扩大基组');
  let t='';
  if(eS>1e-4)t+='计算未收敛：'+f(eS)+' mE<sub>h</sub> 的误差靠使 SCF 收敛来消除：这里再迭代几次就够了，困难情况下需要 DIIS、阻尼或另一个初始猜测。方法和基组与这部分误差无关。';
  else if(rhfOnly&&ES.it>0)t+=(ES.b==='STO-3G'?'在最小基组中 H₂ 的轨道由对称性决定，RHF 一次迭代即收敛。':'迭代已经收敛：继续迭代不会改变能量。');
  if(ES.m==='fci')t+='完全 CI 是给定基组中薛定谔方程的精确解，因此没有方法误差。只剩下基组误差'+(ES.R===10?'：在 R = 10 bohr 时，这是该基组中 H 原子误差的两倍。':'.');
  else if(ES.m==='mp2'&&eM<0)t+='MP2 比完全 CI 低了 '+f(-eM)+' mE<sub>h</sub>：键拉伸时微扰理论发散，而变分方法不可能低于该基组中的精确解——MP2 不是变分方法。';
  else if(ES.R===10&&ES.m==='rhf')t+='方法误差巨大（'+k(eM)+' kJ/mol），扩大基组不能消除它：从 STO-3G 到 6-31G**，它从 337 变为 248 mE<sub>h</sub>，但仍然巨大。单个 RHF 行列式无法描述两个分开的原子——这是静态相关；需要多组态方法，这里是完全 CI。';
  else t+='方法误差是该基组中缺失的相关能；它本身取决于基组（RHF 在 1.4 bohr 时：STO-3G 中 20.6 mE<sub>h</sub>，6-31G** 中 33.9 mE<sub>h</sub>）。基组误差在 STO-3G → 6-31G → 6-31G** 时减小。';
  document.getElementById('eSt').innerHTML=t}
drawErr();
