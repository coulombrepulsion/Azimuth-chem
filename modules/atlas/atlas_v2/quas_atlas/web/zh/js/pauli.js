/* Pauli page (Atlas v2).  Wave functions, densities, conditional densities and
   holes, J/K integrals and the 2x2 CI of the Coulomb hole come from
   quas_atlas.core.pauli (pauli.map, pauli.cond, pauli.orbs, pauli.energy,
   pauli.cimap, pauli.ci); this script draws and animates. */
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const NS='http://www.w3.org/2000/svg';
function el(p,t,a){const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);p.appendChild(e);return e}
const fmt=(x,d=2)=>(Math.abs(x)<5e-4?'0':x.toFixed(d)).replace('-','−');
const SUBN=n=>String(n).split('').map(c=>'₀₁₂₃₄₅₆₇₈₉'[+c]).join('');
const f64=s=>new Float64Array(Uint8Array.from(atob(s),c=>c.charCodeAt(0)).buffer);
const MODES=[
 {id:'H',name:'哈特里乘积'},
 {id:'T',name:'三重态，S = 1'},
 {id:'S',name:'单重态，S = 0'},
 {id:'D',name:'单个行列式 ↑↓'},
 {id:'B',name:'玻色子（作对比）'}];
let S={mode:'T',ms:1,a:1,b:2,view:'P',x1:0.3};
try{const s=JSON.parse(localStorage.getItem('pauli-state')||'null');if(s)Object.assign(S,s)}catch(e){}
function pauliZero(){return S.mode==='T'&&S.a===S.b}
const NG=301,XS=Array.from({length:NG},(_,i)=>i/(NG-1));
function condLab(){const ar=S.ms>0?'↑':'↓';if(S.mode==='H')return ['所有 ↑ 电子的密度，ρ↑(x₂)','空穴 = c − ρ↑'];if(S.mode==='T')return S.ms?['所有电子的密度 '+ar+', ρ'+ar+'(x₂)','交换空穴 = c − ρ'+ar]:['不考虑交换时第二个电子的密度','差值'];if(S.mode==='D')return ['↓ 电子的密度，ρ↓(x₂)','差值 c − ρ↓'];if(S.mode==='B')return ['所有粒子的密度，ρ(x₂)','差值 c − ρ'];return ['↓ 电子的密度，ρ↓(x₂)','差值 c − ρ↓']}
const liveMap=QC.live('pauli.map'),liveCond=QC.live('pauli.cond'),liveOrbs=QC.live('pauli.orbs'),liveE=QC.live('pauli.energy'),liveCM=QC.live('pauli.cimap'),liveCI=QC.live('pauli.ci');
/* ===== отрисовка ===== */
const M0=34,MS=356;
function mix(c1,c2,t){const p=c=>c.startsWith('#')?[1,3,5].map(i=>parseInt(c.slice(i,i+2),16)):c.match(/\d+/g).slice(0,3).map(Number);const A=p(c1),B=p(c2);return A.map((x,i)=>Math.round(x+(B[i]-x)*t))}
function heat(t){const s=[tok('--heat0'),tok('--heat1'),tok('--heat2'),tok('--heat3')];t=Math.max(0,Math.min(1,t))*3;const k=Math.min(2,Math.floor(t));return mix(s[k],s[k+1],t-k)}
async function drawMap(){let Mp;try{Mp=await liveMap({mode:S.mode,a:S.a,b:S.b,view:S.view})}catch(e){return}const sv=document.getElementById('map');sv.innerHTML='';const ink=tok('--ink'),mut=tok('--muted'),acc=tok('--accent');
  const R=120;const cv=document.createElement('canvas');cv.width=R;cv.height=R;const cx=cv.getContext('2d');const img=cx.createImageData(R,R);
  const P=S.view==='P';const vals=f64(Mp.f64),mx=Mp.mx;
  const pc=mix(tok('--panel'),tok('--panel'),0),pos=mix(tok('--pos'),tok('--pos'),0),neg=mix(tok('--neg'),tok('--neg'),0);
  for(let k=0;k<R*R;k++){const v=mx>1e-12?vals[k]/mx:0;let c;if(P)c=heat(Math.pow(v,0.8));else{const t=Math.min(1,Math.abs(v));const base=v>=0?pos:neg;c=pc.map((x,i)=>Math.round(x+(base[i]-x)*t))}
    img.data[4*k]=c[0];img.data[4*k+1]=c[1];img.data[4*k+2]=c[2];img.data[4*k+3]=255}
  cx.putImageData(img,0,0);
  if(pauliZero()){el(sv,'rect',{x:M0,y:6,width:MS,height:MS,fill:tok('--panel'),stroke:tok('--line')});const t=el(sv,'text',{x:M0+MS/2,y:6+MS/2-8,'text-anchor':'middle','font-size':22,'font-family':'PT Serif, serif',fill:ink});t.textContent='Ψ ≡ 0';
    const t2=el(sv,'text',{x:M0+MS/2,y:6+MS/2+18,'text-anchor':'middle','font-size':13,fill:mut,'font-family':'Golos Text, sans-serif'});t2.textContent='这样的状态不存在'}
  else{const g=el(sv,'g',{});if(S.flipT>0){const cx0=M0+MS/2,cy0=6+MS/2,sc=Math.cos(Math.PI*S.flipT);g.setAttribute('transform',`translate(${cx0} ${cy0}) rotate(-45) scale(1 ${sc}) rotate(45) translate(${-cx0} ${-cy0})`)}
    el(g,'image',{href:cv.toDataURL(),x:M0,y:6,width:MS,height:MS,preserveAspectRatio:'none',style:'image-rendering:auto'})}
  el(sv,'rect',{x:M0,y:6,width:MS,height:MS,fill:'none',stroke:tok('--line')});
  if(!pauliZero())el(sv,'line',{x1:M0,y1:6+MS,x2:M0+MS,y2:6,stroke:ink,'stroke-width':1.2,'stroke-dasharray':'5 4',opacity:.7});
  const dl=el(sv,'text',{x:M0+MS*0.74,y:6+MS*0.2,'font-size':12,fill:ink,'font-family':'Golos Text, sans-serif',transform:`rotate(-45 ${M0+MS*0.74} ${6+MS*0.2})`,stroke:tok('--panel'),'stroke-width':3,'paint-order':'stroke'});dl.textContent='x₁ = x₂';
  const X=M0+S.x1*MS;if(!pauliZero())el(sv,'line',{x1:X,y1:6,x2:X,y2:6+MS,stroke:acc,'stroke-width':2});
  if(!pauliZero())el(sv,'circle',{cx:X,cy:6+MS-S.x1*MS,r:5,fill:'none',stroke:acc,'stroke-width':2});
  [0,0.5,1].forEach(v=>{el(sv,'text',{x:M0+v*MS,y:6+MS+16,'text-anchor':'middle','font-size':12,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=String(v);
    el(sv,'text',{x:M0-6,y:6+MS-v*MS+4,'text-anchor':'end','font-size':12,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=String(v)});
  el(sv,'text',{x:M0+MS-4,y:6+MS+30,'text-anchor':'end','font-size':14,'font-style':'italic','font-family':'PT Serif, serif',fill:ink}).textContent='x₁';
  el(sv,'text',{x:6,y:20,'font-size':14,'font-style':'italic','font-family':'PT Serif, serif',fill:ink}).textContent='x₂';
  document.getElementById('mapTitle').textContent=S.view==='P'?(S.mode==='D'?'对自旋求和后的密度 |Ψ|²':'概率密度 |Ψ(x₁, x₂)|²'):(S.mode==='D'?'Ψ：α(1)β(2) 分量（符号：橙色 +，青色 −）':'Ψ(x₁, x₂)——空间部分（橙色 +，青色 −）');
  document.getElementById('mapLegend').innerHTML=S.view==='P'?'<span><i class="box" style="background:var(--heat0);border:1px solid var(--line)"></i>0</span><span><i class="box" style="background:linear-gradient(90deg,var(--heat1),var(--heat2),var(--heat3))"></i>较大</span><span>虚线为对角线 x₁ = x₂：两个电子位于同一点</span>':'<span><i class="box" style="background:var(--pos)"></i>Ψ &gt; 0</span><span><i class="box" style="background:var(--neg)"></i>Ψ &lt; 0</span><span>反对称的 Ψ 关于对角线反映时颜色互换</span>'}
async function drawCond(){let C;try{C=await liveCond({mode:S.mode,a:S.a,b:S.b,ms:S.ms,x1:S.x1})}catch(e){return}const sv=document.getElementById('cond');sv.innerHTML='';const ink=tok('--ink'),mut=tok('--muted'),acc=tok('--accent');
  const L=44,T=10,W=500,H=230;const nums=document.getElementById('nums');
  if(!C){el(sv,'text',{x:L+W/2,y:T+H/2,'text-anchor':'middle','font-size':16,fill:ink,'font-family':'Golos Text, sans-serif'}).textContent='Ψ ≡ 0——第二个电子无处可去';nums.innerHTML='';document.getElementById('condLegend').innerHTML='';return}
  [C.refLab,C.holeLab]=condLab();const lo=Math.min(0,...C.h),hi=Math.max(...C.c,...C.ref)*1.08;const sx=x=>L+x*W,sy=v=>T+H-(v-lo)/(hi-lo)*H;
  for(let v=Math.ceil(lo);v<=hi;v+=1){el(sv,'line',{x1:L,x2:L+W,y1:sy(v),y2:sy(v),stroke:tok('--line'),'stroke-width':v===0?1.3:.7});el(sv,'text',{x:L-6,y:sy(v)+4,'text-anchor':'end','font-size':12,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=String(v).replace('-','−')}
  const pts=a=>a.map((v,i)=>sx(XS[i]).toFixed(1)+','+sy(v).toFixed(1)).join(' ');
  el(sv,'polygon',{points:sx(0)+','+sy(0)+' '+pts(C.h)+' '+sx(1)+','+sy(0),fill:tok('--hole'),stroke:tok('--neg'),'stroke-width':1.2});
  el(sv,'polyline',{points:pts(C.ref),fill:'none',stroke:tok('--ref'),'stroke-width':2,'stroke-dasharray':'6 4'});
  el(sv,'polyline',{points:pts(C.c),fill:'none',stroke:acc,'stroke-width':2.6,'stroke-linejoin':'round'});
  el(sv,'line',{x1:sx(S.x1),x2:sx(S.x1),y1:T,y2:T+H,stroke:ink,'stroke-width':1,'stroke-dasharray':'2 3',opacity:.6});
  const lb=el(sv,'text',{x:sx(S.x1)+4,y:T+H-6,'font-size':12,fill:ink,'font-family':'Golos Text, sans-serif'});lb.textContent='x₁（第一个电子）';
  if(S.x1>0.6)lb.setAttribute('text-anchor','end'),lb.setAttribute('x',sx(S.x1)-4);
  [0,0.25,0.5,0.75,1].forEach(v=>el(sv,'text',{x:sx(v),y:T+H+18,'text-anchor':'middle','font-size':12,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=String(v));
  el(sv,'text',{x:L+W,y:T+H+36,'text-anchor':'end','font-size':14,'font-style':'italic','font-family':'PT Serif, serif',fill:ink}).textContent='x₂';
  document.getElementById('condLegend').innerHTML='<span><i class="sw" style="border-color:var(--accent)"></i>c(x₂)——第二个电子在哪里</span><span><i class="sw" style="border-color:var(--ref);border-top-style:dashed"></i>'+C.refLab+'</span><span><i class="box" style="background:var(--hole);border:1px solid var(--neg)"></i>'+C.holeLab+'</span>';
  nums.innerHTML='<span>c(x₁) = <b class="'+(Math.abs(C.c0)<1e-6?'zero':'')+'">'+fmt(C.c0)+'</b></span><span>∫ c dx₂ = <b>1</b></span><span>∫ 空穴 dx₂ = <b>'+fmt(C.hint)+'</b></span>'}
async function drawOrbs(){let O;try{O=await liveOrbs({a:S.a,b:S.b})}catch(e){return}const sv=document.getElementById('orbs');sv.innerHTML='';const mut=tok('--muted');const L=44,W=500,T=8,H=96;const sx=x=>L+x*W,sy=v=>T+H/2-v/1.6*H/2;
  el(sv,'line',{x1:L,x2:L+W,y1:sy(0),y2:sy(0),stroke:tok('--line')});
  [[S.a,'--pos','φ'+SUBN(S.a)+' = φa'],[S.b,'--neg','φ'+SUBN(S.b)+' = φb']].forEach(([n,c,l],k)=>{const p=XS.map((x,i)=>sx(x).toFixed(1)+','+sy((k?O.pb:O.pa)[i]).toFixed(1)).join(' ');el(sv,'polyline',{points:p,fill:'none',stroke:tok(c),'stroke-width':2.2,'stroke-dasharray':k&&S.a===S.b?'6 4':'none'});
    el(sv,'text',{x:L+W+4,y:T+14+k*18,'text-anchor':'end','font-size':12.5,fill:tok(c),'font-family':'Golos Text, sans-serif'}).textContent=l});
  el(sv,'line',{x1:sx(S.x1),x2:sx(S.x1),y1:T,y2:T+H,stroke:tok('--accent'),'stroke-width':1,'stroke-dasharray':'2 3'});
  [0,1].forEach(v=>el(sv,'text',{x:sx(v),y:T+H+14,'text-anchor':'middle','font-size':12,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=v)}
function drawFormula(){const a='φ'+SUBN(S.a),b='φ'+SUBN(S.b);let h='';
  if(S.mode==='H')h='Ψ(1, 2) = '+a+'(1)α(1) · '+b+'(2)α(2)';
  else if(S.mode==='T'){const sp=S.ms>0?'α(1)α(2)':S.ms<0?'β(1)β(2)':'<span class=fr><span>1</span><span>√2</span></span> [ α(1)β(2) + β(1)α(2) ]';
    const det=S.ms?'<span class=fr><span>1</span><span>√2</span></span> <span class="mat"><span>'+a+'(1)'+(S.ms>0?'α':'β')+'(1)</span><span>'+b+'(1)'+(S.ms>0?'α':'β')+'(1)</span><span>'+a+'(2)'+(S.ms>0?'α':'β')+'(2)</span><span>'+b+'(2)'+(S.ms>0?'α':'β')+'(2)</span></span> = ':'<span class=fr><span>1</span><span>√2</span></span> ( |'+a+' <span class="ob">'+b+'</span>| + |<span class="ob">'+a+'</span> '+b+'| ) = ';
    h='<sup style="font-size:13px">3</sup>Ψ<sub style="font-size:12px">M='+(S.ms>0?'+1':S.ms<0?'−1':'0')+'</sub> = '+det+'<span class=fr><span>1</span><span>√2</span></span> [ '+a+'(1)'+b+'(2) − '+b+'(1)'+a+'(2) ] · '+sp}
  else if(S.mode==='B')h=S.a===S.b?'Ψ<sub style="font-size:12px">玻色子</sub> = '+a+'(1)'+a+'(2)':'Ψ<sub style="font-size:12px">玻色子</sub> = <span class=fr><span>1</span><span>√2</span></span> [ '+a+'(1)'+b+'(2) + '+b+'(1)'+a+'(2) ]';
  else if(S.mode==='D')h='|'+a+' <span class="ob">'+b+'</span>| = <span class=fr><span>1</span><span>√2</span></span> <span class="mat"><span>'+a+'(1)α(1)</span><span>'+b+'(1)β(1)</span><span>'+a+'(2)α(2)</span><span>'+b+'(2)β(2)</span></span>';
  else h=S.a===S.b?'<sup style="font-size:13px">1</sup>Ψ = '+a+'(1)'+a+'(2) · <span class=fr><span>1</span><span>√2</span></span> [ α(1)β(2) − β(1)α(2) ]':'<sup style="font-size:13px">1</sup>Ψ = <span class=fr><span>1</span><span>√2</span></span> ( |'+a+' <span class="ob">'+b+'</span>| − |<span class="ob">'+a+'</span> '+b+'| ) = <span class=fr><span>1</span><span>√2</span></span> [ '+a+'(1)'+b+'(2) + '+b+'(1)'+a+'(2) ] · <span class=fr><span>1</span><span>√2</span></span> [ α(1)β(2) − β(1)α(2) ]';
  document.getElementById('formula').innerHTML='<span>'+h+'</span>'}
function drawExplain(){const a=S.a===S.b;let t='';
  if(S.mode==='H')t='<b>电子是可区分的。</b>第一个电子总在 φ<sub>a</sub> 上，第二个在 φ<sub>b</sub> 上，因此分布图关于对角线不对称：交换两个电子，图像就会改变。对于全同粒子这是不可能的。对角线上的密度不为零：没有什么能阻止两个自旋相同的电子出现在同一点。右图中的“空穴”只是去掉了电子自身的轨道，它不会随 x₁ 的移动而跟随电子。';
  else if(S.mode==='T'&&a)t='<b>泡利不相容。</b>三重态的空间部分 φ<sub>a</sub>(1)φ<sub>a</sub>(2) − φ<sub>a</sub>(1)φ<sub>a</sub>(2) 恒等于零（对 M<sub>S</sub> = ±1 而言，行列式中有两列相同）。同一轨道上的三重态不存在。';
  else if(S.mode==='T'&&S.ms===0)t='<b>三重态，M<sub>S</sub> = 0。</b>这里两个电子自旋不同，但自旋部分是对称的，因此空间部分是反对称的，与 M<sub>S</sub> = ±1 的相同。所以在这个分量中电子也不会处于同一点：c(x₁) = 0。这个分量不能写成单个行列式——需要两个行列式之和（与单重态一样，只是取“+”号）。三重态的三个分量具有相同的能量 J − K。';
  else if(S.mode==='T')t='<b>三重态，M<sub>S</sub> = '+(S.ms>0?'+1':'−1')+' ——单个行列式。</b>交换电子时 Ψ 变号（切换到“Ψ”：关于对角线反映时颜色互换），因此对角线上 Ψ = 0——自旋相同的电子不会处于同一点。第一个电子周围没有第二个电子：这就是<b>交换（费米）空穴</b>。移动 x₁——空穴随电子一起移动。它的积分恰好为 −1：被“挖去”的正好是一个电子，即该电子自身，因此电子不会排斥自己。哈特里–福克方法能精确描述这种空穴。';
  else if(S.mode==='B')t='<b>玻色子</b>（光子、⁴He 原子）——作对比：它们的波函数是对称的，P₁₂Ψ = +Ψ。 '+(a?'两个粒子处于同一轨道——完全可以：没有禁阻（由此产生玻色–爱因斯坦凝聚）。':'看 x₂ = x₁ 这一点：那里的条件密度不是零，而是最大值。对角线上的密度是可区分粒子（哈特里乘积）的两倍——玻色子“聚在一起”，自旋相同的费米子“相互远离”。');
  else if(S.mode==='D')t='<b>单个行列式 ↑↓ 没有确定的自旋：</b>|φ<sub>a</sub>φ̄<sub>b</sub>| = <span class=fr><span>单重态 + 三重态 M<sub>S</sub>=0</span><span>√2</span></span>——这正是“后两个组合单独来看没有确定的对称性”——由此产生 UHF 中的自旋污染。反对称性由自旋部分保证，对角线上的空间密度不为零'+(a?'（这里两个电子都在同一轨道上，如同 He 原子）':'')+'。↓ 电子“不知道” ↑ 电子在哪里：条件密度与普通密度相同，没有空穴。在单个行列式中——也就是在哈特里–福克方法中——自旋相反的电子彼此独立运动。缺失的<b>库仑空穴</b>正是相关能的来源。';
  else t=a?'<b>同一轨道上的单重态</b>与行列式 ↑↓ 相同：空间部分 φ<sub>a</sub>(1)φ<sub>a</sub>(2) 是对称的，自旋部分是反对称的。':'<b>单重态。</b>空间部分对称，自旋因子反对称。这样的函数不能写成单个行列式——需要两个行列式的组合。对角线上的密度甚至更高：电子相互靠近的机会比不考虑对称性时更大，因此单重态的排斥能大于三重态（见下方：J + K 对比 J − K）。';
  document.getElementById('explain').innerHTML=t}
async function drawEnergy(){let E;try{E=await liveE({a:S.a,b:S.b})}catch(e){return}const {J,K}=E;const same=S.a===S.b;
  document.getElementById('jk').innerHTML='<span>J<sub>ab</sub> = <b>'+fmt(J,3)+'</b></span><span>K<sub>ab</sub> = <b>'+fmt(K,3)+'</b></span><span class="hint">（任意单位）</span>'+(same?'<span class="hint">当 a = b 时两个积分相等：K<sub>aa</sub> = J<sub>aa</sub>。</span>':'');
  const rows=[['T','三重态 S = 1（任意 M<sub>S</sub>）','J − K',E.rows[0][1]],['H','哈特里乘积','J',J],['D','单个行列式 ↑↓','J',J],['S','单重态 S = 0',same?'J':'J + K',E.rows[3][1]],['B','玻色子',same?'J':'J + K',E.rows[3][1]]];
  const mx=E.mx;
  document.getElementById('bars').innerHTML=rows.map(r=>'<div class="bar'+(r[0]===S.mode?' on':'')+'"><span>'+r[1]+' — '+r[2]+'</span><span class="t"><i style="width:'+(r[3]==null?0:r[3]/mx*100)+'%"></i></span><b>'+(r[3]==null?'无':fmt(r[3],3))+'</b></div>').join('');
  document.getElementById('hund').innerHTML=same?'同一轨道上的两个粒子只能是单重态：三重态被泡利原理禁阻。':'三重态比单重态低 2K = '+fmt(E.K2,3)+'。单个行列式 ↑↓ 的能量恰好位于两者正中——它一半是单重态，一半是三重态。自旋相同的电子彼此回避（交换空穴），因此排斥较小。这正是<b>洪德规则</b>（例如 He 原子的 1s¹2s¹ 组态）。'}
function drawAll(){drawFormula();drawMap();drawCond();drawOrbs();drawExplain();drawEnergy();document.getElementById('x1v').textContent=fmt(S.x1);
  try{localStorage.setItem('pauli-state',JSON.stringify(S))}catch(e){}}
/* ===== управление ===== */
function chips(id,items,cur,set,cls){const box=document.getElementById(id);box.innerHTML='';items.forEach(([v,l])=>{const b=document.createElement('button');b.type='button';b.className='chip'+(cls?' '+cls:'');b.innerHTML=l;b.setAttribute('aria-pressed',v===cur());b.onclick=()=>{set(v);S.flip=0;S.flipT=0;renderControls();drawAll();flipMsg()};box.appendChild(b)})}
function renderControls(){chips('modes',MODES.map(m=>[m.id,m.name]),()=>S.mode,v=>S.mode=v);
  chips('oa',[1,2,3,4].map(n=>[n,'φ'+SUBN(n)]),()=>S.a,v=>S.a=v,'m');chips('ob',[1,2,3,4].map(n=>[n,'φ'+SUBN(n)]),()=>S.b,v=>S.b=v,'m');
  chips('ms',[[1,'+1 (↑↑)'],[0,'0'],[-1,'−1 (↓↓)']],()=>S.ms,v=>S.ms=v);document.getElementById('msRow').style.display=S.mode==='T'?'':'none';
  chips('views',[['P','|Ψ|²'],['W','带符号的 Ψ']],()=>S.view,v=>S.view=v)}
S.flip=0;S.flipT=0;
function flipMsg(){const m=document.getElementById('flipMsg');if(S.flipT<1||pauliZero()){m.textContent=S.flipT>0&&S.flipT<1?'正在沿对角线 x₁ = x₂ 反射图像…':'';return}
  const P=S.view==='P';let t='';
  if(S.mode==='H')t=P?'图像变了：|Ψ(2,1)|² ≠ |Ψ(1,2)|²——粒子是可区分的。对电子来说这是不允许的。':'P₁₂Ψ ≠ ±Ψ：函数既不对称也不反对称——不适用于全同粒子。';
  else if(P)t='|Ψ|² 没有变化：交换全同粒子不改变任何可观测量。切换到“带符号的 Ψ”——在那里可以看到费米子与玻色子的区别。';
  else if(S.mode==='T')t='P₁₂Ψ = −Ψ：每个点的颜色都变成了相反色。这是费米子；在对角线上 Ψ = −Ψ，只能有 Ψ = 0。';
  else if(S.mode==='D')t='对于 ↑↓，坐标交换的同时自旋也交换：分量 α(1)β(2) 变为带“−”号的 β(1)α(2)——行列式整体是反对称的。';
  else t='P₁₂Ψ = +Ψ：空间部分是对称的，图像没有变化'+(S.mode==='S'?'（单重态的反对称性由自旋因子提供）。':'——玻色子就是这样表现的。');
  m.textContent=t}
function doFlip(){const target=S.flip?0:1;S.flip=target;const t0=performance.now(),from=S.flipT;if(matchMedia('(prefers-reduced-motion: reduce)').matches){S.flipT=target;drawMap();flipMsg();return}
  const stepF=n=>{const u=Math.min(1,(n-t0)/1100);const e=u<.5?2*u*u:1-Math.pow(-2*u+2,2)/2;S.flipT=from+(target-from)*e;drawMap();flipMsg();if(u<1)requestAnimationFrame(stepF)};requestAnimationFrame(stepF)}
document.getElementById('bFlip').onclick=doFlip;
const x1in=document.getElementById('x1');x1in.value=S.x1;x1in.oninput=e=>{S.x1=+e.target.value;drawMap();drawCond();drawOrbs();if(window.drawCI)drawCI();document.getElementById('x1v').textContent=fmt(S.x1)};
(()=>{const sv=document.getElementById('map');let down=false;const set=e=>{const r=sv.getBoundingClientRect();const x=((e.clientX-r.left)/r.width*400-M0)/MS;S.x1=Math.max(0.01,Math.min(0.99,x));x1in.value=S.x1;drawMap();drawCond();drawOrbs();if(window.drawCI)drawCI();document.getElementById('x1v').textContent=fmt(S.x1)};
  sv.addEventListener('pointerdown',e=>{down=true;sv.setPointerCapture(e.pointerId);set(e)});sv.addEventListener('pointermove',e=>{if(down)set(e)});sv.addEventListener('pointerup',()=>{down=false;try{localStorage.setItem('pauli-state',JSON.stringify(S))}catch(e){}});})();
renderControls();drawAll();

/* ===== кулоновская дырка: КВ из двух конфигураций ===== */
S.th=S.th??0;S.lam=S.lam??3;
async function drawCIMap(){let Mp;try{Mp=await liveCM({th:S.th})}catch(e){return}const sv=document.getElementById('ciMap');sv.innerHTML='';const ink=tok('--ink'),mut=tok('--muted'),acc=tok('--accent');
  const R=110;const cv=document.createElement('canvas');cv.width=R;cv.height=R;const cx=cv.getContext('2d');const img=cx.createImageData(R,R);const v=f64(Mp.f64),mx=Mp.mx;
  for(let k=0;k<R*R;k++){const c=heat(Math.pow(v[k]/mx,0.8));img.data.set([c[0],c[1],c[2],255],4*k)}cx.putImageData(img,0,0);
  el(sv,'image',{href:cv.toDataURL(),x:M0,y:6,width:MS,height:MS,preserveAspectRatio:'none'});el(sv,'rect',{x:M0,y:6,width:MS,height:MS,fill:'none',stroke:tok('--line')});
  el(sv,'line',{x1:M0,y1:6+MS,x2:M0+MS,y2:6,stroke:ink,'stroke-width':1.2,'stroke-dasharray':'5 4',opacity:.7});
  const X=M0+S.x1*MS;el(sv,'line',{x1:X,y1:6,x2:X,y2:6+MS,stroke:acc,'stroke-width':2});
  [0,0.5,1].forEach(q=>{el(sv,'text',{x:M0+q*MS,y:6+MS+16,'text-anchor':'middle','font-size':12,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=String(q);
    el(sv,'text',{x:M0-6,y:6+MS-q*MS+4,'text-anchor':'end','font-size':12,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=String(q)});
  el(sv,'text',{x:M0+MS-4,y:6+MS+30,'text-anchor':'end','font-size':14,'font-style':'italic','font-family':'PT Serif, serif',fill:ink}).textContent='x₁';
  el(sv,'text',{x:6,y:20,'font-size':14,'font-style':'italic','font-family':'PT Serif, serif',fill:ink}).textContent='x₂'}
function drawCICond(Z){const sv=document.getElementById('ciCond');sv.innerHTML='';const ink=tok('--ink'),mut=tok('--muted'),acc=tok('--accent');
  const c=Z.c,ref=Z.ref,h=Z.h;
  const L=44,T=10,W=500,H=190;const lo=Math.min(-0.5,...h),hi=Math.max(...c,...ref)*1.08;const sx=x=>L+x*W,sy=q=>T+H-(q-lo)/(hi-lo)*H;
  for(let q=Math.ceil(lo);q<=hi;q++){el(sv,'line',{x1:L,x2:L+W,y1:sy(q),y2:sy(q),stroke:tok('--line'),'stroke-width':q===0?1.3:.7});el(sv,'text',{x:L-6,y:sy(q)+4,'text-anchor':'end','font-size':12,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=String(q).replace('-','−')}
  const pts=a=>a.map((q,i)=>sx(XS[i]).toFixed(1)+','+sy(q).toFixed(1)).join(' ');
  el(sv,'polygon',{points:sx(0)+','+sy(0)+' '+pts(h)+' '+sx(1)+','+sy(0),fill:tok('--hole'),stroke:tok('--neg'),'stroke-width':1.2});
  el(sv,'polyline',{points:pts(ref),fill:'none',stroke:tok('--ref'),'stroke-width':2,'stroke-dasharray':'6 4'});
  el(sv,'polyline',{points:pts(c),fill:'none',stroke:acc,'stroke-width':2.6});
  el(sv,'line',{x1:sx(S.x1),x2:sx(S.x1),y1:T,y2:T+H,stroke:ink,'stroke-width':1,'stroke-dasharray':'2 3',opacity:.6});
  [0,0.5,1].forEach(q=>el(sv,'text',{x:sx(q),y:T+H+18,'text-anchor':'middle','font-size':12,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=String(q));
  el(sv,'text',{x:L+W,y:T+H+36,'text-anchor':'end','font-size':14,'font-style':'italic','font-family':'PT Serif, serif',fill:ink}).textContent='x₂';
  return Z.dep}
function drawCIE(Z){const sv=document.getElementById('ciE');sv.innerHTML='';const ink=tok('--ink'),mut=tok('--muted'),acc=tok('--accent');
  const L=56,T=8,W=480,H=120;const ths=Array.from({length:181},(_,i)=>-45+i*0.5);const Es=Z.Es,lo=Z.lo,hi=Z.hi;
  const sx=t=>L+(t+45)/90*W,sy=e=>T+H-(e-lo)/(hi-lo)*H;
  [lo,(lo+hi)/2,hi].forEach(e=>{el(sv,'line',{x1:L,x2:L+W,y1:sy(e),y2:sy(e),stroke:tok('--line'),'stroke-width':.7});el(sv,'text',{x:L-6,y:sy(e)+4,'text-anchor':'end','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=e.toFixed(1)});
  el(sv,'polyline',{points:ths.map((t,i)=>sx(t).toFixed(1)+','+sy(Es[i]).toFixed(1)).join(' '),fill:'none',stroke:mut,'stroke-width':2});
  const to=Z.toDeg;el(sv,'line',{x1:sx(0),x2:sx(0),y1:T,y2:T+H,stroke:mut,'stroke-dasharray':'2 3'});
  el(sv,'circle',{cx:sx(to),cy:sy(Z.Eto),r:4,fill:'none',stroke:tok('--neg'),'stroke-width':2});
  el(sv,'circle',{cx:sx(S.th),cy:sy(Z.Eth),r:6,fill:acc});
  [-45,-30,-15,0,15,30,45].forEach(t=>el(sv,'text',{x:sx(t),y:T+H+16,'text-anchor':'middle','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=String(t).replace('-','−')+'°');
  el(sv,'text',{x:L+W,y:T+H+32,'text-anchor':'end','font-size':13,'font-style':'italic','font-family':'PT Serif, serif',fill:ink}).textContent='θ'}
async function drawCI(){let Z;try{Z=await liveCI({th:S.th,lam:S.lam,x1:S.x1})}catch(e){return}drawCIMap();const dep=drawCICond(Z);drawCIE(Z);const c1=Z.c1,c2=Z.c2,E=Z.E,E0=Z.E0,Em=Z.Em;
  document.getElementById('thv').textContent=(S.th>0?'+':'')+String(S.th).replace('-','−')+'°';document.getElementById('lamv').textContent=S.lam.toFixed(1);
  document.getElementById('ciNums').innerHTML='<span>c₁ = <b>'+fmt(c1,3)+'</b></span><span>c₂ = <b>'+fmt(c2,3)+'</b></span><span>E = <b>'+fmt(E,3)+'</b></span><span>E(θ = 0) = <b>'+fmt(E0,3)+'</b></span><span>E<sub>corr</sub> = E<sub>min</sub> − E(0) = <b>'+fmt(Em-E0,3)+'</b></span><span>'+(dep>=0?'密度亏缺':'密度富余')+' 于 x₂ = x₁：<b>'+Math.abs(Math.round(dep*100))+' %</b></span>';
  let txt;if(Math.abs(S.th)<0.01)txt='<b>θ = 0——单个行列式。</b>第二个电子的条件密度与普通密度相同：没有空穴，自旋相反的电子彼此独立运动。请点击“能量最小值”。';
  else if(c2<0)txt='<b>c₂ &lt; 0：出现了库仑空穴。</b>符号的选取使两个组态在对角线 x₁ = x₂ 上的贡献部分相消——电子较少靠在一起。排斥的减小超过了动能的增加（在 φ₂ 上动能是 4 倍），因此 E 低于单个行列式的能量。'+(Z.atMin?'这就是最小值——两组态基中 CI 方法的解；能量降低 E<sub>corr</sub> 就是哈特里–福克方法所缺失的相关能。':'能量最小值在图上用圆圈标出。');
  else txt='<b>c₂ &gt; 0——符号“不对”。</b>此时对角线上的贡献相加：电子更常靠在一起，排斥增大，能量高于单个行列式。自然选择的是形成空穴的那个符号。';
  document.getElementById('ciText').innerHTML=txt}
const thIn=document.getElementById('th'),lamIn=document.getElementById('lam');thIn.value=S.th;lamIn.value=S.lam;
thIn.oninput=e=>{S.th=+e.target.value;drawCI()};lamIn.oninput=e=>{S.lam=+e.target.value;drawCI()};
document.getElementById('bMin').onclick=async()=>{let Z;try{Z=await QC.api('pauli.ci',{th:S.th,lam:S.lam,x1:S.x1})}catch(e){return}S.th=+Z.toDeg.toFixed(2);thIn.value=S.th;drawCI()};
document.getElementById('bZero').onclick=()=>{S.th=0;thIn.value=0;drawCI()};
(()=>{const sv=document.getElementById('ciMap');let down=false;const set=e=>{const r=sv.getBoundingClientRect();S.x1=Math.max(0.01,Math.min(0.99,((e.clientX-r.left)/r.width*400-M0)/MS));x1in.value=S.x1;drawMap();drawCond();drawOrbs();drawCI();document.getElementById('x1v').textContent=fmt(S.x1)};
  sv.style.touchAction='none';sv.style.cursor='crosshair';sv.addEventListener('pointerdown',e=>{down=true;sv.setPointerCapture(e.pointerId);set(e)});sv.addEventListener('pointermove',e=>{if(down)set(e)});sv.addEventListener('pointerup',()=>down=false)})();
drawCI();
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{drawAll();drawCI()});
new MutationObserver(()=>{drawAll();drawCI()}).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
