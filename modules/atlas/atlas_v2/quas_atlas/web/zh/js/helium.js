/* Helium page (Atlas v2).  Hylleraas matrix elements and optimisation, the
   approximation ladder, the effective-charge model and the Coulomb hole come
   from quas_atlas.core.helium (he.table, he.zeta, he.hole); this script draws. */
// ---------- страница «Атом гелия и электронная корреляция» ----------
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const fmt=(x,d=3)=>{if(x==null||!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('-','−')};
const RN=['忽略电子排斥','微扰理论，一阶','变分法，有效核电荷 ζ','哈特里–福克极限','海勒拉斯：1 + c·r₁₂','海勒拉斯：3 项','海勒拉斯：6 项','精确'];
const SYS={1:{n:'H⁻',hf:-0.487930,ex:-0.527751,thr:-0.5,thrN:'H + e⁻'},2:{n:'He',hf:-2.861680,ex:-2.903724,thr:-2,thrN:'He⁺ + e⁻'},3:{n:'Li⁺',hf:-7.236415,ex:-7.279913,thr:-4.5,thrN:'Li²⁺ + e⁻'},4:{n:'Be²⁺',hf:-13.611299,ex:-13.655566,thr:-8,thrN:'Be³⁺ + e⁻'}};
let Z=2,zeta=1.6875,r1=0.6;
const liveT=QC.live('he.table'),liveZ=QC.live('he.zeta'),liveH=QC.live('he.hole');
async function sec1(){const g=$('zG');g.innerHTML='';Object.entries(SYS).forEach(([k,s])=>{const b=document.createElement('button');b.className='chip';b.type='button';b.textContent=s.n+' (Z = '+k+')';b.setAttribute('aria-pressed',+k===Z);b.onclick=()=>{Z=+k;zeta=Z-5/16;sec1();sec2();sec3()};g.appendChild(b)});
  let Q;try{Q=await liveT({Z})}catch(e){return}const s=SYS[Z],R=RN.map((n,i)=>[n,Q.rows[i].E]),ec=Q.ec;
  $('lTab').innerHTML='<table class="mtab bt"><thead><tr><th class="n">近似</th><th>E，原子单位</th><th>误差，kJ/mol</th><th>占 E<sub>corr</sub> 比例</th></tr></thead><tbody>'+
    R.map(([n,E],i)=>{const q=Q.rows[i],err=q.err,part=q.part;return `<tr${q.unbound?' style="color:var(--warn)"':''}><td class="n">${n}</td><td>${fmt(E,5)}</td><td>${Math.abs(err)<5e-7?'0':fmt(q.errk,1)}</td><td>${part==null?'—':fmt(part*100,0)+' %'}</td></tr>`}).join('')+'</tbody></table>';
  // столбики: ошибка на логарифмической шкале
  const svg=$('ladder');svg.innerHTML='';const L=210,W=540,Rr=60,T=12,rowH=(372-T-34)/(R.length-1),items=R.slice(0,-1);const lo=-4,hi=1;const X=v=>L+(Math.log10(Math.max(v,1e-4))-lo)/(hi-lo)*(W-L-Rr);
  for(let k=lo;k<=hi;k++){el('line',{x1:X(Math.pow(10,k)),x2:X(Math.pow(10,k)),y1:T,y2:372-28,stroke:'var(--line)','stroke-width':1},svg);el('text',{x:X(Math.pow(10,k)),y:362,'text-anchor':'middle','font-size':11.5,fill:'var(--muted)'},svg,k===0?'1':k===1?'10':'10'+'⁻'+'⁰¹²³⁴'[-k])}
  el('text',{x:(L+W-Rr)/2,y:390-14+12,'text-anchor':'middle','font-size':11.5,fill:'var(--muted)'},svg,'');
  items.forEach(([n,E],i)=>{const y=T+i*rowH,err=Q.rows[i].aerr;el('text',{x:L-8,y:y+rowH/2+4,'text-anchor':'end','font-size':12,fill:'var(--ink)'},svg,n.replace('微扰理论，一阶','微扰理论（一阶）').replace('变分法，有效核电荷 ζ','有效核电荷 ζ'));
    el('rect',{x:L,y:y+4,width:Math.max(2,X(err)-L),height:rowH-8,rx:3,fill:Q.rows[i].unbound?'var(--rho-l)':'var(--acc-bg)',stroke:'var(--accent)','stroke-width':1},svg);
    el('text',{x:X(err)+5,y:y+rowH/2+4,'font-size':11.5,fill:'var(--ink)','font-family':'var(--f-mono)'},svg,fmt(Q.rows[i].err,4))});
  el('line',{x1:X(Q.aec),x2:X(Q.aec),y1:T,y2:372-28,stroke:'var(--rho-l)','stroke-width':1.8,'stroke-dasharray':'4 3'},svg);
  {const t=el('text',{x:X(Q.aec)+4,y:T+10,'font-size':11.5,fill:'var(--rho-l)','font-weight':600},svg,'|E corr|');t.setAttribute('paint-order','stroke');t.setAttribute('stroke','var(--panel)');t.setAttribute('stroke-width','4')}
  el('text',{x:(L+W-Rr)/2,y:390,'text-anchor':'middle','font-size':11.5,fill:'var(--muted)'},svg,'|E − E exact|，原子单位');
  let t=`${s.n} 的相关能：${fmt(ec,4)} 原子单位 = ${fmt(Q.eck,0)} kJ/mol——仅占总能量的 ${fmt(Q.ecp,1)} %，但其大小相当于化学键能。`;
  t+=Z===1?`<b>H⁻ 是特殊情况：</b>只有当其能量低于 ${fmt(s.thr,1)}（H 原子 + 自由电子）时该离子才稳定。有效核电荷和哈特里–福克都做不到这一点（相应行已标出）：多余的电子仅靠相关作用才能被束缚。只含一个 r₁₂ 项的海勒拉斯函数就已能束缚它（−0.5088）。`:
    '忽略排斥时能量甚至低于精确值：这不是变分估计，因为舍弃了哈密顿量的一部分。哈特里–福克给出了除相关以外的几乎全部能量；仅含一个 r₁₂ 项的函数就能“补回”大部分相关能（He 为 70 %），因为它直接描述了轨道乘积中所缺少的东西——对电子间距离的依赖。切换体系：H⁻、He、Li⁺、Be²⁺ 的 E<sub>corr</sub> 几乎相同（每对电子 ≈ −0.04 原子单位）。';
  $('t1').innerHTML=t}
// ---------- 2. эффективный заряд ----------
async function sec2(){$('zeta').value=zeta;$('zv').textContent='ζ = '+fmt(zeta,3);let D;try{D=await liveZ({Z,zeta})}catch(e){return}const zm=D.zm;
  const svg=$('zChart');svg.innerHTML='';const x0=0,x1=D.x1,ymin=Math.min(-Z*Z*1.25,-2*Z*x1*0.55,D.Ez-0.4),ymax=Math.max(Z*Z*0.9,D.Ez+0.15*Math.abs(D.Ez)+0.4);/* the point of ζ never leaves the plot */
  const W=540,H=300,L=56,R=14,Tp=14,B=38,X=x=>L+(x-x0)/(x1-x0)*(W-L-R),Y=y=>H-B-(y-ymin)/(ymax-ymin)*(H-Tp-B);
  const step=[0.5,1,2,5,10].find(s=>(ymax-ymin)/s<=8);for(let v=Math.ceil(ymin/step)*step;v<=ymax;v+=step){el('line',{x1:L,x2:W-R,y1:Y(v),y2:Y(v),stroke:Math.abs(v)<1e-9?'var(--muted)':'var(--line)','stroke-width':1},svg);el('text',{x:L-6,y:Y(v)+4,'text-anchor':'end','font-size':11.5,fill:'var(--muted)'},svg,fmt(v,step<1?1:0))}
  for(let v=0;v<=x1;v+=1)el('text',{x:X(v),y:H-B+17,'text-anchor':'middle','font-size':11.5,fill:'var(--muted)'},svg,String(v));el('text',{x:(L+W-R)/2,y:H-2,'text-anchor':'middle','font-size':12,fill:'var(--muted)'},svg,'ζ');
  const xs=D.xs;const P=f=>{let s='',pen=false;xs.forEach((x,i)=>{const y=f[i];if(y<ymin||y>ymax){pen=false;return}s+=(pen?'L':'M')+X(x).toFixed(1)+','+Y(y).toFixed(1);pen=true});return s};
  [[D.T,'var(--warn)'],[D.Vn,'var(--ok)'],[D.Ve,'var(--virt)']].forEach(([f,c])=>el('path',{d:P(f),fill:'none',stroke:c,'stroke-width':1.6,'stroke-dasharray':'6 4'},svg));
  el('path',{d:P(D.E),fill:'none',stroke:'var(--accent)','stroke-width':2.6},svg);
  el('line',{x1:X(Z),x2:X(Z),y1:Tp,y2:H-B,stroke:'var(--muted)','stroke-dasharray':'2 3','stroke-width':1},svg);el('text',{x:X(Z)+4,y:Tp+10,'font-size':11.5,fill:'var(--muted)'},svg,'ζ = Z');
  el('circle',{cx:X(zm),cy:Y(D.Ezm),r:5,fill:'none',stroke:'var(--ok)','stroke-width':2},svg);if(D.Ez>=ymin&&D.Ez<=ymax)el('circle',{cx:X(zeta),cy:Y(D.Ez),r:5.5,fill:'var(--accent)'},svg);
  $('zKv').innerHTML=`<span>T = ζ²</span><b>${fmt(D.Tz,4)}</b><span>V<sub>ne</sub> = −2Zζ</span><b>${fmt(D.Vnz,4)}</b><span>V<sub>ee</sub> = <span class=fr><span>5ζ</span><span>8</span></span></span><b>${fmt(D.Vez,4)}</b><span>E</span><b>${fmt(D.Ez,5)}</b><span><span class=fr><span>V</span><span>T</span></span></span><b>${fmt(D.ratio,3)}</b>`;
  $('t2').innerHTML=Math.abs(zeta-zm)<0.004?`<b>极小值：</b>ζ = Z − <span class=fr><span>5</span><span>16</span></span> = ${fmt(zm,4)}，E = −(Z − <span class=fr><span>5</span><span>16</span></span>)² = ${fmt(D.Eopt,5)}。每个电子屏蔽了 <span class=fr><span>5</span><span>16</span></span> 的核电荷。<span class=fr><span>V</span><span>T</span></span> = −2——在最优标度下维里定理成立。`:
    `当 ζ = Z = ${Z}（无屏蔽）时 E = ${fmt(D.EZ,4)}。把 ζ 移向极小值：让轨道“松弛”扩展更有利，因为另一个电子部分地屏蔽了原子核。`}
// ---------- 3. кулоновская дыра ----------
async function sec3(){$('r1').value=r1;$('r1v').textContent=fmt(r1,2)+' 玻尔';let G;try{G=await liveH({Z,r1})}catch(e){return}
  const svg=$('hole');svg.innerHTML='';const zr=G.zr,zs=G.zs;
  const W=540,L=56,R=14,X=z=>L+(z+zr)/(2*zr)*(W-L-R);
  // верхний график: плотности; нижний: разность
  const vmax=Math.max(...G.cond,...G.unc)*1.08,T1=16,B1=150,Y1=y=>B1-y/vmax*(B1-T1);
  const dv=G.dv,dmax=Math.max(...dv.map(Math.abs))*1.15,T2=178,B2=262,M2=(T2+B2)/2,Y2=y=>M2-y/dmax*(B2-T2)/2;
  const yst=vmax>2?0.5:vmax>1?0.25:vmax>0.4?0.1:0.05;for(let v=0;v<=vmax;v+=yst){el('line',{x1:L,x2:W-R,y1:Y1(v),y2:Y1(v),stroke:v===0?'var(--muted)':'var(--line)','stroke-width':1},svg);el('text',{x:L-6,y:Y1(v)+4,'text-anchor':'end','font-size':11,fill:'var(--muted)'},svg,fmt(v,2))}
  el('line',{x1:L,x2:W-R,y1:M2,y2:M2,stroke:'var(--muted)','stroke-width':1},svg);[dmax/1.15,-dmax/1.15].forEach(v=>el('text',{x:L-6,y:Y2(v)+4,'text-anchor':'end','font-size':11,fill:'var(--muted)'},svg,fmt(v,v>0.1||v<-0.1?2:3)));
  el('text',{x:L+4,y:T1-4,'font-size':11.5,fill:'var(--muted)'},svg,'固定 e₁ 时电子 2 的密度');el('text',{x:L+4,y:T2-6,'font-size':11.5,fill:'var(--muted)'},svg,'差值：有相关 − 无相关');
  for(let v=-Math.floor(zr);v<=zr;v++)el('text',{x:X(v),y:B2+17,'text-anchor':'middle','font-size':11.5,fill:'var(--muted)'},svg,String(v).replace('-','−'));
  el('text',{x:(L+W-R)/2,y:296,'text-anchor':'middle','font-size':12,fill:'var(--muted)'},svg,'z₂，沿穿过原子核和电子 1 的轴，bohr');
  let dp='M'+X(zs[0])+','+M2;zs.forEach((z,i)=>dp+='L'+X(z).toFixed(1)+','+Y2(dv[i]).toFixed(1));dp+='L'+X(zs[zs.length-1])+','+M2+'Z';el('path',{d:dp,fill:'var(--rho)',stroke:'var(--rho-l)','stroke-width':1.5},svg);
  el('path',{d:zs.map((z,i)=>(i?'L':'M')+X(z).toFixed(1)+','+Y1(G.unc[i]).toFixed(1)).join(''),fill:'none',stroke:'var(--muted)','stroke-width':1.8,'stroke-dasharray':'6 4'},svg);
  el('path',{d:zs.map((z,i)=>(i?'L':'M')+X(z).toFixed(1)+','+Y1(G.cond[i]).toFixed(1)).join(''),fill:'none',stroke:'var(--accent)','stroke-width':2.4},svg);
  [[T1,B1],[T2,B2]].forEach(([a,b])=>el('line',{x1:X(0),x2:X(0),y1:a,y2:b,stroke:'var(--ink)','stroke-width':1,'stroke-dasharray':'2 3'},svg));el('text',{x:X(0)-5,y:T1+10,'text-anchor':'end','font-size':11.5,fill:'var(--ink)','font-weight':600},svg,'原子核');
  [[T1,B1],[T2,B2]].forEach(([a,b])=>el('line',{x1:X(r1),x2:X(r1),y1:a,y2:b,stroke:'var(--warn)','stroke-width':1.2,'stroke-dasharray':'4 3'},svg));el('circle',{cx:X(r1),cy:T1+8,r:5.5,fill:'var(--warn)'},svg);el('text',{x:X(r1)+9,y:T1+12,'font-size':12,fill:'var(--warn)','font-weight':600},svg,'e₁');
  const ru=G.ru,rc=G.rc,iu=G.iu,ic=G.ic;
  $('hKv').innerHTML=`<span>无相关的 ⟨r₁₂⟩</span><b>${fmt(ru,3)} bohr</b><span>Hylleraas ⟨r₁₂⟩</span><b>${fmt(rc,3)} bohr</b><span>⟨1/r₁₂⟩ = 排斥能，无相关</span><b>${fmt(iu,4)} E<sub>h</sub></b><span>Hylleraas ⟨1/r₁₂⟩</span><b>${fmt(ic,4)} E<sub>h</sub></b><span>电子 2 与 e₁ 位于原子核同侧</span><b>${fmt(G.same,1)} %（无相关时 50 %）</b>`;
  $('t3').innerHTML=`考虑相关后，电子 2 较少出现在电子 1 附近（e₁ 附近的凹陷），而更多出现在原子核的另一侧。电子间的平均距离从 ${fmt(ru,3)} 增大到 ${fmt(rc,3)} bohr，排斥减小——这正是哈特里–福克所没有的能量收益：在那里每个电子都在另一个电子的平均场中运动，“看不到”对方此刻的位置。`}
$('zeta').oninput=e=>{zeta=+e.target.value;sec2()};$('zMin').onclick=()=>{zeta=Z-5/16;sec2()};$('r1').oninput=e=>{r1=+e.target.value;sec3()};
sec1();sec2();sec3();
