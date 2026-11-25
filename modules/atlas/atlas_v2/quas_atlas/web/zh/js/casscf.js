/* CASSCF page (Atlas v2).  Energy differences of the H2, ethylene and N2
   curves and the size of the active space come from quas_atlas.core.casscf
   (endpoints cas.meta, cas.h2, cas.eth, cas.n2, cas.size; data
   core/data/casscf_curves.json); this script draws. */
// ---------- страница «Многоконфигурационные методы: CASSCF» (кривые посчитаны в PySCF, cc-pVDZ) ----------
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const fmt=(x,d=2)=>{if(x==null||!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('-','−')};
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const HK=2625.4996,EV=27.211386,KC=627.5095;const liveH2=QC.live('cas.h2'),liveEth=QC.live('cas.eth'),liveN2=QC.live('cas.n2'),liveSize=QC.live('cas.size');
const SUP='⁰¹²³⁴⁵⁶⁷⁸⁹';const sup=n=>String(n).replace('-','⁻').split('').map(c=>/\d/.test(c)?SUP[+c]:c).join('');
function sci(x){if(!isFinite(x))return '—';if(x<1e5)return Math.round(x).toLocaleString('zh-CN').replace(/ /g,' ');const e=Math.floor(Math.log10(x)),m=x/Math.pow(10,e);return fmt(m,1)+'·10'+sup(e)}
/* общий график линий */
function plot(svg,o){svg.innerHTML='';const {W,H}=o,lft=62,rt=14,top=14,bot=40;
  const X=x=>lft+(x-o.x0)/(o.x1-o.x0)*(W-lft-rt),Y=v=>top+(o.y1-Math.max(o.y0,Math.min(o.y1,v)))/(o.y1-o.y0)*(H-top-bot);
  o.yt.forEach(v=>{el('line',{x1:lft,x2:W-rt,y1:Y(v),y2:Y(v),stroke:tok('--line')},svg);el('text',{x:lft-6,y:Y(v)+4,'text-anchor':'end','font-size':12,fill:tok('--muted')},svg,o.yf(v))});
  o.xt.forEach(v=>el('text',{x:X(v),y:H-20,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,o.xf(v)));
  el('text',{x:(lft+W-rt)/2,y:H-3,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,o.xl);
  el('text',{x:14,y:top+(H-top-bot)/2,'text-anchor':'middle','font-size':12,fill:tok('--muted'),transform:`rotate(-90 14 ${top+(H-top-bot)/2})`},svg,o.yl);
  if(o.ref!=null){el('line',{x1:lft,x2:W-rt,y1:Y(o.ref),y2:Y(o.ref),stroke:tok('--muted'),'stroke-dasharray':'4 4'},svg);if(o.refl)el('text',{x:lft+6,y:Y(o.ref)-6,'font-size':11,fill:tok('--muted')},svg,o.refl)}
  o.s.forEach(s=>{let d='',pen=false;s.v.forEach((v,i)=>{if(v==null||!isFinite(v)){pen=false;return}d+=(pen?'L':'M')+X(o.xs[i]).toFixed(1)+' '+Y(v).toFixed(1);pen=true});
    el('path',{d,fill:'none',stroke:tok(s.c),'stroke-width':s.w||2.2,'stroke-dasharray':s.dash||''},svg);
    if(s.pts)s.v.forEach((v,i)=>{if(v!=null&&isFinite(v)&&v>=o.y0&&v<=o.y1)el('circle',{cx:X(o.xs[i]),cy:Y(v),r:2.6,fill:tok(s.c)},svg)})});
  if(o.cur!=null){const xc=o.xs[o.cur];el('line',{x1:X(xc),x2:X(xc),y1:top,y2:H-bot,stroke:tok('--muted'),'stroke-dasharray':'2 3'},svg);
    o.s.forEach(s=>{const v=s.v[o.cur];if(v!=null&&isFinite(v)&&v>=o.y0&&v<=o.y1)el('circle',{cx:X(xc),cy:Y(v),r:4.5,fill:tok(s.c)},svg)})}
  if(o.noLeg)return {X,Y};
  const lg=el('g',{},svg);let ly=top+14;o.s.forEach(s=>{if(!s.label)return;const x=W-rt-170;el('line',{x1:x,x2:x+22,y1:ly-4,y2:ly-4,stroke:tok(s.c),'stroke-width':s.w||2.2,'stroke-dasharray':s.dash||''},lg);el('text',{x:x+28,y:ly,'font-size':12,fill:tok('--ink')},lg,s.label);ly+=17});
  return {X,Y}}
const SW=(c,d,w)=>'<span aria-hidden="true" style="display:inline-block;width:24px;height:0;vertical-align:middle;margin-right:7px;border-top:'+(w||2.4)+'px '+(!d?'solid':/^2 /.test(d)?'dotted':'dashed')+' var('+c+')"></span>';
function occBars(n,lab){return '<div class="t" style="margin-top:12px">自然轨道占据数</div><div class="ocb">'+n.map((v,i)=>'<span class="ol">'+lab[i]+'</span><span class="wbar"><span style="width:'+(v/2*100).toFixed(1)+'%;background:var(--accent)"></span></span><span class="ov">'+fmt(v,3)+'</span>').join('')+'</div>'}
// ---------- 1. H₂ ----------
let P=[],H2at=0,E=[],N=[];
async function h2(){if(!P.length)return;const i=+$('R').value,p=P[i];let Z;try{Z=await liveH2({i})}catch(e){return}$('Rv').textContent=fmt(p.R,1)+' Å';
  plot($('h2C'),{W:560,H:330,xs:P.map(q=>q.R),x0:P[0].R,x1:P[P.length-1].R,y0:-1.2,y1:-0.75,yt:[-1.2,-1.1,-1.0,-0.9,-0.8],yf:v=>fmt(v,1),xt:[0.5,1,1.5,2,2.5,3,3.5,4],xf:v=>fmt(v,1),xl:'R, Å',yl:'E, Eₕ',ref:H2at,refl:'两个 H 原子：'+fmt(H2at,4)+' Eₕ',cur:i,noLeg:1,
    s:[{v:P.map(q=>q.RHF),c:'--warn',dash:'7 5',label:'RHF'},{v:P.map(q=>q.UHF),c:'--virt',dash:'2 4',w:2.6,label:'UHF'},{v:P.map(q=>q.CAS),c:'--accent',w:2.6,label:'CASSCF(2,2)'},{v:P.map(q=>q.FCI),c:'--ok',w:1.8,dash:'5 3',label:'完全 CI'}]});
  const d=x=>fmt(x===p.RHF?Z.d.RHF:x===p.UHF?Z.d.UHF:x===p.CAS?Z.d.CAS:Z.d.FCI,1);
  $('h2M').innerHTML='<table class="mtab"><thead><tr><th>方法</th><th>E，Eₕ</th><th>高于完全 CI，kJ/mol</th></tr></thead><tbody>'+
    [['RHF',p.RHF,'--warn','7 5'],['UHF',p.UHF,'--virt','2 4'],['CASSCF(2,2)',p.CAS,'--accent',''],['完全 CI',p.FCI,'--ok','5 3']].map(([n,v,c,dd])=>'<tr><td>'+SW(c,dd)+n+'</td><td>'+fmt(v,4)+'</td><td>'+d(v)+'</td></tr>').join('')+'</tbody></table>'+
    '<p class="hint" style="margin-top:6px">UHF 的 ⟨S²⟩：'+fmt(p.S2,3)+'（纯单重态为 0）</p>'+occBars(p.n,['σ<sub>g</sub>','σ<sub>u</sub>']);
  const nu=p.n[1];
  $('h2N').innerHTML=nu<0.1?`在平衡附近 σ<sub>u</sub> 几乎是空的（${fmt(nu,3)}）：单个行列式是好的起点，RHF = UHF。CASSCF(2,2) 与完全 CI 相差 ${d(p.CAS)} kJ/mol——这是动态相关，两个轨道无法描述。`:
    nu<0.7?`键被拉长：σ<sub>u</sub> 的占据数已达 ${fmt(nu,2)}。RHF 比完全 CI 高 ${d(p.RHF)} kJ/mol，UHF“打破”了对称性，找到比 RHF 更低的能量，但 ⟨S²⟩ = ${fmt(p.S2,2)}：它的波函数是单重态与三重态的混合。`:
    `键实际上已断裂：σ<sub>g</sub> 和 σ<sub>u</sub> 的占据几乎相等（${fmt(p.n[0],2)} 和 ${fmt(nu,2)}）——每个原子上一个电子。RHF 比完全 CI 高 ${d(p.RHF)} kJ/mol，因为它把一半波函数保持为离子形式 H⁺H⁻。CASSCF(2,2) 与完全 CI 只差 ${d(p.CAS)} kJ/mol，而 UHF 给出同样的能量，代价是 ⟨S²⟩ ≈ ${fmt(p.S2,1)}。`}
$('R').oninput=h2;
// ---------- 2. этилен ----------
async function eth(){if(!E.length)return;const i=+$('ang').value,p=E[i];let Z;try{Z=await liveEth({i})}catch(e){return}$('angV').textContent=p.ang+'°';
  const r=k=>Z.r[k];
  plot($('ethC'),{W:560,H:330,xs:E.map(q=>q.ang),x0:0,x1:90,y0:0,y1:Math.ceil(Math.max(...r('RHF'))/100)*100,yt:[0,100,200,300,400,500,600].filter(v=>v<=Math.ceil(Math.max(...r('RHF'))/100)*100),yf:v=>String(v),xt:[0,15,30,45,60,75,90],xf:v=>v+'°',xl:'扭转角',yl:'ΔE，kJ/mol',cur:i,noLeg:1,
    s:[{v:r('RHF'),c:'--warn',dash:'7 5',label:'RHF'},{v:r('CAS'),c:'--accent',w:2.6,label:'CASSCF(2,2)'},{v:r('NEVPT2'),c:'--ok',w:2,dash:'5 3',label:'NEVPT2'}]});
  const b=k=>Z.b[k];
  $('ethM').innerHTML='<table class="mtab"><thead><tr><th>方法</th><th>ΔE（'+p.ang+'°），kJ/mol</th><th>能垒（90°），kJ/mol</th></tr></thead><tbody>'+
    [['RHF','RHF','--warn','7 5'],['CASSCF(2,2)','CAS','--accent',''],['NEVPT2','NEVPT2','--ok','5 3']].map(([n,k,c,dd])=>'<tr><td>'+SW(c,dd)+n+'</td><td>'+fmt(Z.at[k],0)+'</td><td>'+fmt(b(k),0)+'</td></tr>').join('')+'</tbody></table>'+occBars(p.n,['π','π*']);
  $('ethN').innerHTML=(p.ang<60?`在 ${p.ang}° 时 π 键仍完好：π* 的占据数为 ${fmt(p.n[1],3)}。`:`在 ${p.ang}° 时 π 和 π* 的占据数为 ${fmt(p.n[0],2)} 和 ${fmt(p.n[1],2)}：`+(p.ang===90?'两个组态同等重要，这是双自由基。':'第二个组态已经很重要。'))+
    `旋转能垒：RHF 为 ${fmt(b('RHF'),0)} kJ/mol，CASSCF(2,2) 为 ${fmt(b('CAS'),0)}，NEVPT2 为 ${fmt(b('NEVPT2'),0)}。乙烯顺反异构化的实验活化能约 272 kJ/mol（65 kcal/mol）；这里扭转时几何构型是刚性的，所以计算能垒略高。RHF 把能垒高估近一倍，并在 90° 处出现尖点：一个组态无法描述断裂 π 键的两半。`}
$('ang').oninput=eth;
// ---------- 3. N₂ ----------
const MN=[['RHF','RHF','--warn','7 5',2.2],['CCSD','CCSD','--virt','5 3',2],['CCSD(T)','CCSDT','--trip','2 3',2.4],['CASSCF(6,6)','CAS','--accent','',2.6],['NEVPT2','NEVPT2','--ok','',2.2]];
async function n2(){if(!N.length)return;const i=+$('Rn').value,p=N[i];let Z;try{Z=await liveN2({i})}catch(e){return}$('RnV').textContent=fmt(p.R,1)+' Å';
  const rel=k=>Z.rel[k];
  plot($('n2C'),{W:560,H:330,xs:N.map(q=>q.R),x0:N[0].R,x1:N[N.length-1].R,y0:-4,y1:16,yt:[-4,-2,0,2,4,6,8,10,12,14,16],yf:v=>String(v).replace('-','−'),xt:[1,1.5,2,2.5,3],xf:v=>fmt(v,1),xl:'R, Å',yl:'E − E(1.1 Å)，eV',ref:9.91,refl:'Dₑ（实验）= 9.91 eV',cur:i,noLeg:1,
    s:MN.map(([l,k,c,d,w])=>({v:rel(k),c,dash:d,w,label:l,pts:k==='CCSDT'||k==='CCSD'}))});
  const R=MN.map(([l,k,c,dd,w])=>{const v=rel(k)[i];return '<tr><td>'+SW(c,dd,w)+l+'</td><td>'+(v==null?'未收敛':fmt(v,2))+'</td></tr>'}).join('');
  $('n2M').innerHTML='<table class="mtab"><thead><tr><th>方法</th><th>E − E(1.1 Å)，eV</th></tr></thead><tbody>'+R+'</tbody></table>'+occBars(p.n,['σ','π','π','π*','π*','σ*']);
  const De=k=>Z.De[k];
  const dT=Z.dT;
  $('n2N').innerHTML=(p.R<1.4?`在平衡处占据数接近 2 和 0（占据最多的反键轨道为 ${fmt(p.n[3],3)}）：单行列式方法适用，CCSD(T) 与 NEVPT2 几乎一致。`:
    `在 ${fmt(p.R,1)} Å 时反键轨道的占据已达 ${fmt(p.n[3],2)}–${fmt(p.n[5],2)}：波函数是多组态的。`+(dT!=null&&Math.abs(dT)>0.3?`CCSD(T) 与 NEVPT2 相差 ${fmt(dT,1)} eV`+(dT<0?'，向下偏离——(T) 修正已不是小的补充，而是误差。':'. '):''))+
    `3 Å 处相对于平衡的能量：RHF 为 ${fmt(De('RHF'),1)} eV（而应约为 9–10），CASSCF(6,6) 为 ${fmt(De('CAS'),1)}，NEVPT2 为 ${fmt(De('NEVPT2'),1)}；实验值为 9.91 eV。CASSCF 和 NEVPT2 的不足主要来自小基组 cc-pVDZ。CCSD 在某些 R 处未收敛——曲线上有缺口，而 CCSD(T) 在 2.7 Å 处比平衡低 ${fmt(Z.low,1)} eV——这是没有物理意义的结果：按 CCSD(T)，拉长的分子反而比平衡分子更稳定。`}
$('Rn').oninput=n2;
// ---------- 4. размер активного пространства ----------
async function cas(){let n=+$('ne').value,m=+$('no').value;if(n>2*m){n=2*m;$('ne').value=n}let Z;try{Z=await liveSize({ne:n,no:m})}catch(e){return}
  $('neV').textContent=n;$('noV').textContent=m;
  const det=Z.det,csf=Z.csf,gb=Z.gb;
  $('casK').innerHTML='<span>CAS('+n+','+m+'）：行列式数（M<sub>S</sub> = 0）</span><b>'+sci(det)+'</b><span>单重态组态函数</span><b>'+sci(csf)+'</b><span>一个 CI 向量所需内存</span><b>'+(gb<0.001?fmt(Z.mb,3)+' MB':fmt(gb,gb<10?2:0)+' GB')+'</b>';
  $('casN').innerHTML=(det<1e6?'这样的空间在笔记本电脑上几秒即可求解。':det<1e8?'几分钟到几小时：常规 CASSCF。':det<4e9?'接近常规 CASSCF 的极限（约 18 个电子在 18 个轨道上）。':'常规 CASSCF 已不可能：需要 DMRG 或选择性 CI。')+
    '作为比较：CAS(6,6) 中的 N₂ 有 400 个行列式；苯的 π 体系 CAS(6,6) 也是 400；铬二聚体 Cr₂ 的 CAS(12,12) 约 85.4 万个。'}
$('ne').oninput=cas;$('no').oninput=cas;
function all(){h2();eth();n2();cas()}
QC.api('cas.meta',{}).then(M=>{P=M.h2;H2at=M.H2at;E=M.eth;N=M.n2;$('R').max=P.length-1;$('Rn').max=N.length-1;all()}).catch(()=>{});
new MutationObserver(all).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
