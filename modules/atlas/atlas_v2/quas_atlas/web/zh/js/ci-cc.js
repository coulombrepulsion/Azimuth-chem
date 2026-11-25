/* CI/CC page (Atlas v2).  Determinant counts, the 2x2 CI of H2, the
   size-consistency models and the dimer amplitudes come from
   quas_atlas.core.ci_cc (cicc.dets, cicc.h2, cicc.state); this script draws. */
// ---------- страница «КВ и связанные кластеры изнутри» (H₂ в STO-3G решается здесь, ряд (H₂)ₙ посчитан в PySCF) ----------
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const fmt=(x,d=2)=>{if(x==null||!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('-','−')};
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
function chips(box,labels,cur,on){box.innerHTML='';labels.forEach((t,i)=>{const b=document.createElement('button');b.type='button';b.className='chip';b.innerHTML=t;b.setAttribute('aria-pressed',i===cur);b.onclick=()=>on(i);box.appendChild(b)})}
function mark(box,i){[...box.children].forEach((b,j)=>b.setAttribute('aria-pressed',j===i))}
const SUP='⁰¹²³⁴⁵⁶⁷⁸⁹';const sup=n=>String(n).replace('-','⁻').split('').map(c=>/\d/.test(c)?SUP[+c]:c).join('');
function sci(x){if(!isFinite(x))return '—';if(x<10)return fmt(x,x<1?2:1);if(x<1e5)return Math.round(x).toLocaleString('zh-CN').replace(/ /g,' ');const e=Math.floor(Math.log10(x)),m=x/Math.pow(10,e);return fmt(m,1)+'·10'+sup(e)}
const Q={m:0,b:1,R:7,sz:0};
// ---------- 1. число определителей ----------
const MOL=[{n:'H<sub>2</sub>O'},{n:'N<sub>2</sub>'},{n:'C<sub>6</sub>H<sub>6</sub>'}];
const BAS=['STO-3G','6-31G* (5d)','cc-pVDZ','cc-pVTZ'];
chips($('molG'),MOL.map(m=>m.n),Q.m,i=>{Q.m=i;mark($('molG'),i);dets()});
chips($('basG'),BAS,Q.b,i=>{Q.b=i;mark($('basG'),i);dets()});
const liveD=QC.live('cicc.dets'),liveS=QC.live('cicc.state');let H2=null,ST=null;
async function dets(){let Z;try{Z=await liveD({m:Q.m,b:Q.b})}catch(e){return}const m={e:Z.e},n=Z.n,L=Z.L,tot=Z.tot,cisd=Z.cisd;
  const svg=$('detC');svg.innerHTML='';const W=960,H=300,lft=60,rt=16,top=14,bot=46,K=L.length,bw=(W-lft-rt)/K,hi=Z.hi;
  const Y=v=>top+(1-v/hi)*(H-top-bot);
  for(let d=0;d<=hi;d+=Math.max(1,Math.ceil(hi/8))){el('line',{x1:lft,x2:W-rt,y1:Y(d),y2:Y(d),stroke:tok('--line')},svg);el('text',{x:lft-6,y:Y(d)+4,'text-anchor':'end','font-size':12,fill:tok('--muted')},svg,'10'+sup(d))}
  L.forEach((v,k)=>{const lg=Z.lg[k],x=lft+k*bw;el('rect',{x:x+bw*.12,y:Y(lg),width:bw*.76,height:Math.max(0,Y(0)-Y(lg)),fill:tok(k<=2?'--accent':'--trip'),rx:2},svg);
    if(K<=24||k%Math.ceil(K/24)===0)el('text',{x:x+bw/2,y:H-28,'text-anchor':'middle','font-size':11,fill:tok('--muted')},svg,k)});
  el('text',{x:(lft+W-rt)/2,y:H-8,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,'激发级别 k（0 为哈特里-福克）');
  $('detT').innerHTML='<table class="mtab"><thead><tr><th>集合</th><th>行列式数</th></tr></thead><tbody><tr><td>电子 / 轨道</td><td>'+m.e+' / '+n+'</td></tr><tr><td>单激发 (S)</td><td>'+sci(Z.nS)+'</td></tr><tr><td>双激发 (D)</td><td>'+sci(Z.nD)+'</td></tr><tr><td><b>CISD = 1 + S + D</b></td><td><b>'+sci(Z.nCISD)+'</b></td></tr><tr><td><b>完全 CI</b></td><td><b>'+sci(Z.nFCI)+'</b></td></tr></tbody></table>';
  $('detN').textContent='蓝色柱为 CISD 所包含的部分；灰色柱为完全 CI 的其余部分。由 '+sci(Z.nFCI)+' 个数构成的完全 CI 向量将占用 '+sci(Z.gb)+' GB 内存；而 CISD 只有 '+sci(Z.nCISD)+' 个系数。轨道为全部轨道，不冻结芯，d 函数为球谐形式。'}
// ---------- 2. H₂: КВ 2 × 2 ----------
let Rs=[];
async function upd(){let Z;try{Z=await liveS({i:Q.R})}catch(e){return}ST=Z;h2();amp();sz()}
$('R').oninput=e=>{Q.R=+e.target.value;upd()};
function h2(){const p=ST.p,r=ST.r;$('Rv').textContent=fmt(p.R,2)+' Å';
  const svg=$('h2C');svg.innerHTML='';const W=560,H=330,lft=60,rt=14,top=14,bot=40;const all=H2.all,lo=-1.2,hi=-0.4;
  const X=R=>lft+(R-Rs[0])/(Rs[Rs.length-1]-Rs[0])*(W-lft-rt),Y=v=>top+(hi-Math.max(lo,Math.min(hi,v)))/(hi-lo)*(H-top-bot);
  for(let v=-1.2;v<=-0.39;v+=0.2){el('line',{x1:lft,x2:W-rt,y1:Y(v),y2:Y(v),stroke:tok('--line')},svg);el('text',{x:lft-6,y:Y(v)+4,'text-anchor':'end','font-size':12,fill:tok('--muted')},svg,fmt(v,1))}
  for(let R=0.5;R<=4.01;R+=0.5)el('text',{x:X(R),y:H-20,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,fmt(R,1));
  el('text',{x:(lft+W-rt)/2,y:H-3,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,'R, Å');
  el('text',{x:14,y:top+(H-top-bot)/2,'text-anchor':'middle','font-size':12,fill:tok('--muted'),transform:`rotate(-90 14 ${top+(H-top-bot)/2})`},svg,'E, Eₕ');
  {const ea=all[all.length-1].E;el('line',{x1:lft,x2:W-rt,y1:Y(ea),y2:Y(ea),stroke:tok('--muted'),'stroke-dasharray':'4 4'},svg);el('text',{x:lft+6,y:Y(ea)+14,'font-size':11,fill:tok('--muted')},svg,'STO-3G 中的两个 H 原子：'+fmt(ea,3)+' Eₕ')}
  const line=(f,c,w,dash)=>{let d='';all.forEach((q,i)=>d+=(i?'L':'M')+X(Rs[i]).toFixed(1)+' '+Y(f(q)).toFixed(1));el('path',{d,fill:'none',stroke:tok(c),'stroke-width':w,'stroke-dasharray':dash||''},svg)};
  line(q=>q.Ehf,'--warn',2.4,'7 5');line(q=>q.E,'--accent',2.6);
  el('line',{x1:X(p.R),x2:X(p.R),y1:top,y2:H-bot,stroke:tok('--muted'),'stroke-dasharray':'2 3'},svg);
  [[r.Ehf,'--warn'],[r.E,'--accent']].forEach(([v,c])=>el('circle',{cx:X(p.R),cy:Y(v),r:5,fill:tok(c)},svg));
  el('text',{x:W-rt-6,y:Y(all[all.length-1].Ehf)-8,'text-anchor':'end','font-size':13,fill:tok('--warn')},svg,'哈特里–福克');el('text',{x:W-rt-6,y:Y(all[all.length-1].E)+16,'text-anchor':'end','font-size':13,fill:tok('--accent')},svg,'CI（= 完全 CI）');
  $('h2M').innerHTML='<div class="t">CI 矩阵，Eₕ（不含核排斥）</div><table class="mtab"><tbody><tr><td></td><td>σ<sub>g</sub>²</td><td>σ<sub>u</sub>²</td></tr><tr><td>σ<sub>g</sub>²</td><td>'+fmt(p.Eg,4)+'</td><td>'+fmt(p.K,4)+'</td></tr><tr><td>σ<sub>u</sub>²</td><td>'+fmt(p.K,4)+'</td><td>'+fmt(p.Eu,4)+'</td></tr></tbody></table>';
  const w0=ST.w0,w2=ST.w2;
  $('h2W').innerHTML='<div class="t" style="margin-top:10px">CI 波函数的组成</div><div class="wbar"><span style="width:'+(w0*100).toFixed(1)+'%;background:'+tok('--accent')+'"></span><span style="width:'+(w2*100).toFixed(1)+'%;background:'+tok('--warn')+'"></span></div><p class="hint" style="margin:4px 0 0">σ<sub>g</sub>²: '+fmt(w0*100,1)+' %, σ<sub>u</sub>²: '+fmt(w2*100,1)+' %; c<sub>0</sub> = '+fmt(r.c0,3)+', c<sub>2</sub> = '+fmt(r.c2,3)+'<br>E(HF) = '+fmt(r.Ehf,4)+' Eₕ，E(CI) = '+fmt(r.E,4)+' Eₕ，相关能 '+fmt(ST.corr,1)+' mEₕ</p>';
  $('h2N').innerHTML=p.R<1.2?'在平衡附近几乎不需要 σ<sub>u</sub>² 组态：它的权重约 1%，而相关能为几十 mEₕ。':p.R<2.2?'拉伸时 σ<sub>g</sub> 与 σ<sub>u</sub> 的能量接近，σ<sub>u</sub>² 的权重增大，哈特里-福克越来越高估能量。':'断键时两个组态的权重趋于相等：正确的波函数是“每个原子上各一个电子”，而单一组态 σ<sub>g</sub>² 有一半是离子结构 H⁺H⁻。哈特里-福克的能量远高于两个原子的能量。'}
// ---------- 3. размерная согласованность ----------
chips($('szG'),['H<sub>2</sub>/STO-3G，页面上求解（R 取自上一节）','(H<sub>2</sub>)<sub>n</sub>/6-31G, PySCF'],Q.sz,i=>{Q.sz=i;mark($('szG'),i);sz()});
function sz(){const svg=$('szC');svg.innerHTML='';const W=960,H=300,lft=64,rt=170,top=14,bot=42;let rows;
  rows=Q.sz===0?ST.sz0.rows:H2.sz1;
  const nmax=rows[rows.length-1].n,lo=Math.min(...rows.map(r=>r.CISD))-0.05,hi=1.02,logx=Q.sz===0;
  const X=n=>lft+(logx?Math.log(n)/Math.log(nmax):(n-1)/(nmax-1))*(W-lft-rt),Y=v=>top+(hi-v)/(hi-lo)*(H-top-bot);
  /* the step of the scale follows the range (with PySCF the shares lie within a few per cent: only 100 % was marked) */
  const ystep=[0.01,0.02,0.05,0.1].find(s=>(hi-lo)/s<=8)||0.1;for(let v=Math.ceil(lo/ystep)*ystep;v<=1.001;v+=ystep){el('line',{x1:lft,x2:W-rt,y1:Y(v),y2:Y(v),stroke:tok('--line')},svg);el('text',{x:lft-6,y:Y(v)+4,'text-anchor':'end','font-size':12,fill:tok('--muted')},svg,fmt(v*100,ystep<0.05?0:0)+' %')}
  rows.forEach(r=>el('text',{x:X(r.n),y:H-22,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,r.n));
  el('text',{x:(lft+W-rt)/2,y:H-4,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,'分子数 n'+(logx?'（对数刻度）':''));
  const S=[['FCI','--ok','完全 CI'],['CCSD','--nu','CCSD'],['CISD','--warn','CISD']];if(Q.sz===1)S.splice(2,0,['CCSD(T)','--mp2','CCSD(T)']);
  S.forEach(([k,c,lab],j)=>{let d='';rows.forEach((r,i)=>d+=(i?'L':'M')+X(r.n).toFixed(1)+' '+Y(r[k]).toFixed(1));el('path',{d,fill:'none',stroke:tok(c),'stroke-width':k==='FCI'?5:2.4,'stroke-dasharray':k==='CCSD'||k==='CCSD(T)'?'7 5':'',opacity:k==='FCI'?.45:1},svg);rows.forEach(r=>el('circle',{cx:X(r.n),cy:Y(r[k]),r:3.5,fill:tok(c)},svg));
    const L=rows[rows.length-1];el('text',{x:W-rt+8,y:Y(L[k])+4+(k==='CCSD'?-12:k==='CCSD(T)'?14:0),'font-size':13,fill:tok(c)},svg,lab)});
  el('text',{x:16,y:top+(H-top-bot)/2,'text-anchor':'middle','font-size':12,fill:tok('--muted'),transform:`rotate(-90 16 ${top+(H-top-bot)/2})`},svg,'相关能比例');
  if(Q.sz===1){$('szT').innerHTML='<table class="mtab"><thead><tr><th>n</th><th>函数数</th><th>E<sub>corr</sub>(FCI)/n，mEₕ</th><th>CISD/n</th><th>CCSD/n</th><th>CCSD(T)/n</th><th>CISD 比例</th></tr></thead><tbody>'+rows.map(r=>{const s=r.s,n=r.n,f=k=>fmt(r.pn[k],2);return '<tr><td>'+n+'</td><td>'+s.nbf+'</td><td>'+f('FCI')+'</td><td>'+f('CISD')+'</td><td>'+f('CCSD')+'</td><td>'+f('CCSD(T)')+'</td><td>'+fmt(r.CISD*100,1)+' %</td></tr>'}).join('')+'</tbody></table>';
    $('szN').textContent='H₂ 分子彼此相距 10 Å，R(H–H) = 0.7414 Å。对一个分子 CISD 是精确的（两个电子最多只能双激发），但两个分子时它已丢失部分相关能，且损失随 n 增大。CCSD 对任意 n 都与完全 CI 一致。'}
  else{const p=ST.p;$('szT').innerHTML='';
    $('szN').textContent='模型：n 个 H₂ 分子（STO-3G），R = '+fmt(p.R,2)+' Å。n 个分子的 CISD 归结为 (n+1) × (n+1) 矩阵，其相关能只按 √n 增长：10 个分子恢复 '+fmt(ST.sz0.p10,1)+' %，100 个分子为 '+fmt(ST.sz0.p100,1)+' % 的相关能。'}}
// ---------- 4. экспоненциальный анзац: веса конфигураций димера ----------
function amp(){const p=ST.p,r=ST.r,A=ST.amp,svg=$('ampC');svg.innerHTML='';const W=960,H=260,lft=150,rt=90,top=20,bot=10;
  const fci=A.fci;
  const cisd=A.cisd;
  const t2=A.t2,ccn=A.ccn;
  const lab=['σ<sub>g</sub>²·σ<sub>g</sub>² (HF)','A 上的 σ<sub>u</sub>²','B 上的 σ<sub>u</sub>²','A 和 B 上的 σ<sub>u</sub>²'],labT=['A 与 B 均为 σg²（HF）','A 上的 σu²','B 上的 σu²','A 和 B 上同时 σu²'];
  const rows=[['完全 CI',fci,'--ok'],['CCSD: e^T',ccn,'--nu'],['CISD',cisd,'--warn']];const mx=Math.max(...fci.slice(1).map(Math.abs),.02)*1.25;
  const bh=(H-top-bot)/4;labT.forEach((t,i)=>{const y=top+i*bh;el('text',{x:lft-10,y:y+bh/2+4,'text-anchor':'end','font-size':13,fill:tok('--ink')},svg,t);
    rows.forEach(([n,c,col],j)=>{const val=i===0?c[i]:Math.abs(c[i]),w=i===0?val*(W-lft-rt):Math.min(1,val/mx)*(W-lft-rt);el('rect',{x:lft,y:y+4+j*(bh-10)/3,width:Math.max(1,w),height:(bh-10)/3-2,fill:tok(col),rx:2,opacity:i===0?.55:1},svg);
      el('text',{x:lft+Math.max(1,w)+6,y:y+4+j*(bh-10)/3+(bh-10)/3-4,'font-size':11,fill:tok('--muted')},svg,fmt(c[i],4))})});
  el('text',{x:W-rt+4,y:top-6,'font-size':12,fill:tok('--muted'),'text-anchor':'end'},svg,'系数（第 2–4 行比例放大）');
    $('ampN').innerHTML='两个相同的片段相距很远，R = '+fmt(p.R,2)+' Å。在完全 CI 中，“两个分子都被激发”组态的系数等于 c₂² = '+fmt(A.fci[3],4)+'——即各分子系数的乘积。CCSD 通过 ½T₂² 无需新参数就重现了它（t₂ = c₂/c₀ = '+fmt(t2,4)+'），CISD 不包含它。CISD 对一对分子的误差：'+fmt(A.err,2)+' mEₕ。'}
function all(){dets();if(ST){h2();sz();amp()}}
(async()=>{try{H2=await QC.api('cicc.h2',{})}catch(e){return}Rs=H2.R;$('R').max=Rs.length-1;$('R').value=Q.R;dets();upd()})();matchMedia('(prefers-color-scheme: dark)').addEventListener('change',all);new MutationObserver(all).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
