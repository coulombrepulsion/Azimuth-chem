/* Thermochemistry page (Atlas v2).  The molecules, the RRHO partition
   functions, S, H, Cp, ZPE, the temperature chart and the own-molecule input
   processing come from quas_atlas.core.thermochemistry (therm.mols,
   therm.state, therm.chart, therm.custom); this script formats and draws. */
// ---------- страница «Термохимия из частот»: идеальный газ, жёсткий ротатор, гармонический осциллятор ----------
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const fmt=(x,d=2)=>{if(x==null||!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('-','−')};
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
let MOL=null;
const ST={mol:5,T:298.15,p:1e5,q:0,src:null,custom:null};
const molArg=()=>ST.src.custom?ST.src:MOL.indexOf(ST.src);
// ---------- элементы управления ----------
function chips(box,labels,cur,on){box.innerHTML='';labels.forEach((t,i)=>{const b=document.createElement('button');b.type='button';b.className='chip';b.innerHTML=t;b.setAttribute('aria-pressed',i===cur);b.onclick=()=>on(i);box.appendChild(b)})}
function mark(box,i){[...box.children].forEach((b,j)=>b.setAttribute('aria-pressed',j===i))}
const initMol=()=>chips($('molG'),MOL.map(x=>x.id),ST.mol,i=>{ST.mol=i;ST.src=MOL[i];mark($('molG'),i);draw()});
chips($('pG'),['1 bar','1 atm'],0,i=>{ST.p=i?101325:1e5;mark($('pG'),i);draw()});
chips($('qG'),['熵 S','热容 C<sub>p</sub>'],0,i=>{ST.q=i;mark($('qG'),i);chart()});
$('T').value=298;$('T').oninput=()=>{ST.T=+$('T').value;draw()};
$('bT298').textContent=fmt(298.15,2)+' K';$('bT298').onclick=()=>{ST.T=298.15;$('T').value=298;draw()};
// ---------- вывод ----------
const liveT=QC.live('therm.state'),liveC=QC.live('therm.chart');
async function draw(){const M=ST.src,T=ST.T;let Z;try{Z=await liveT({mol:molArg(),T,p:ST.p})}catch(e){return}const r=Z.r;
  $('Tv').textContent=fmt(T,T===298.15?2:0)+' K';
  const nv=M.nu.length,typ=M.lin?'直线形':'非线形';
  $('molInfo').innerHTML=(M.custom?'自定义分子':M.id)+': '+typ+', σ = '+M.sig+'，多重度 '+M.g+'，振动数 '+nv+' ('+(M.lin?'3N − 5':'3N − 6')+'）。频率，cm⁻¹：'+M.nu.map(n=>Math.round(n)).join(', ')+'.';
  const card=(t,v,u,s)=>'<div class="card"><span class="t">'+t+'</span><b>'+v+' '+u+'</b>'+(s?'<small>'+s+'</small>':'')+'</div>';
  const eh=k=>fmt(Z.eh[k],6)+' E<sub>h</sub>';
  $('cards').innerHTML=card('零点振动能 ZPE',fmt(r.zpe/1000),'kJ/mol',eh('zpe'))+card('焓校正 H<sub>corr</sub>',fmt(r.Hc/1000),'kJ/mol',eh('Hc'))
    +card('熵 S',fmt(r.S),'J/(mol·K)','TS = '+fmt(Z.TS)+' kJ/mol')+card('吉布斯自由能校正 G<sub>corr</sub>',fmt(r.Gc/1000),'kJ/mol',eh('Gc'))
    +card('热容 C<sub>p</sub>',fmt(r.Cp),'J/(mol·K)','');
  const row=(n,s,c,h)=>'<tr><td>'+n+'</td><td>'+fmt(s)+'</td><td>'+fmt(c)+'</td><td>'+h+'</td></tr>';
  $('tab').innerHTML='<table class="mtab"><thead><tr><th>贡献</th><th>S，J/(mol·K)</th><th>C<sub>p</sub>，J/(mol·K)</th><th>H(T) − H(0)，kJ/mol</th></tr></thead><tbody>'
    +row('平动（含 pV = RT）',r.St,r.Ct,fmt(r.Ht/1000))+row('转动',r.Sr,r.Cr,fmt(r.Hr/1000))+row('振动（不含 ZPE）',r.Sv,r.Cv,fmt(r.Hv/1000))+row('电子',r.Se,0,fmt(0))
    +'<tr><td><b>总和</b></td><td><b>'+fmt(r.S)+'</b></td><td><b>'+fmt(r.Cp)+'</b></td><td><b>'+fmt(r.Hth/1000)+'</b></td></tr></tbody></table>';
  const rb=$('refBox');
  if(!M.custom&&Math.abs(T-298.15)<0.01&&ST.p===1e5){const d=Z.ref.d;rb.className='ref';rb.innerHTML='NIST-JANAF 表：S°(298.15 K, 1 bar) = <b>'+fmt(M.S)+'</b> J/(mol·K)；计算值 '+fmt(r.S)+'，差值 '+fmt(d)+' ('+fmt(Z.ref.pct,2)+' %).'+(M.id==='H₂'?' 对 H₂ 来说，经典转子在 298 K 时已不够准确：转动量子很大，而且正氢和仲氢需要分别计算。':'')}
  else{rb.className='ref off';rb.textContent=M.custom?'自定义分子没有表值。':'与 NIST-JANAF 表的比较在 T = 298.15 K、p = 1 bar 时进行（按钮 “298.15 K”）。'}
  chart();}
async function chart(){let Cz;try{Cz=await liveC({mol:molArg(),p:ST.p})}catch(e){return}const svg=$('chart');svg.innerHTML='';const M=ST.src,W=960,Hh=330,L=56,Rr=16,Tp=18,B=38,T0=50,T1=2000;
  const pts=Cz.pts;
  const keys=ST.q?[['Cp','--ink','总和'],['Ct','--nu','平动'],['Cr','--ok','转动'],['Cv','--el','振动']]:[['S','--ink','总和'],['St','--nu','平动'],['Sr','--ok','转动'],['Sv','--el','振动'],['Se','--virt','电子']];
  let ymax=0;pts.forEach(([,r])=>keys.forEach(k=>ymax=Math.max(ymax,r[k[0]])));ymax=Math.ceil(ymax/20)*20;
  const X=t=>L+(t-T0)/(T1-T0)*(W-L-Rr),Y=v=>Hh-B-v/ymax*(Hh-B-Tp);
  const ax=tok('--line'),mu=tok('--muted');
  for(let v=0;v<=ymax;v+=ymax>200?50:20){el('line',{x1:L,x2:W-Rr,y1:Y(v),y2:Y(v),stroke:ax,'stroke-width':1},svg);el('text',{x:L-6,y:Y(v)+4,'text-anchor':'end'},svg,String(v))}
  for(let t=250;t<=2000;t+=250){el('text',{x:X(t),y:Hh-B+16,'text-anchor':'middle'},svg,String(t))}
  el('text',{x:(L+W-Rr)/2,y:Hh-4,'text-anchor':'middle'},svg,'T, K');
  el('text',{x:12,y:Tp+4},svg,ST.q?'J/(mol·K)':'J/(mol·K)');
  keys.forEach(([k,c])=>{if(k==='Se'&&M.g===1)return;el('path',{d:pts.map(([t,r],i)=>(i?'L':'M')+X(t).toFixed(1)+' '+Y(r[k]).toFixed(1)).join(''),fill:'none',stroke:tok(c),'stroke-width':k==='S'||k==='Cp'?2.6:1.8},svg)});
  el('line',{x1:X(ST.T),x2:X(ST.T),y1:Tp,y2:Hh-B,stroke:tok('--accent'),'stroke-dasharray':'4 4','stroke-width':1.2},svg);
  $('leg').innerHTML=keys.filter(k=>!(k[0]==='Se'&&M.g===1)).map(([,c,n])=>'<span><span class="sw" style="border-color:'+tok(c)+'"></span>'+n+'</span>').join('');
  $('chartNote').textContent=ST.q?'Cp 中的平动和转动贡献是常数；当 kT 与振动量子 hcν 相当时，振动贡献增大。':'只有当 kT 与振动量子相当时，振动熵才明显：298 K 时 kT/hc ≈ 207 cm⁻¹。';}
// ---------- своя молекула ----------
function nums(s){return s.replace(/,(?=\d)/g,'.').split(/[\s;,]+/).filter(x=>x).map(Number)}
$('bFill').onclick=()=>{const M=MOL[ST.mol];$('cM').value=String(M.m);$('cB').value=M.B.join(' ');$('cBu').value='cm';$('cSig').value=String(M.sig);$('cG').value=String(M.g);$('cScale').value='1';$('cNu').value=M.nu.join(' ');$('cLow').checked=false;
  $('cMsg').textContent='已导入 '+M.id+' 的数据。修改某一项（例如 σ）后点击“计算”。'};
$('bCalc').onclick=async()=>{const msg=$('cMsg'),m=nums($('cM').value)[0],Bu=$('cBu').value;
  const B=nums($('cB').value),sig=Math.round(nums($('cSig').value)[0]),g=Math.round(nums($('cG').value)[0]),sc=nums($('cScale').value)[0];
  let nu=nums($('cNu').value);
  if(!(m>0)){msg.textContent='请输入分子的质量。';return}
  if(!(B.length===1||B.length===3)||B.some(x=>!(x>0))){msg.textContent='需要一个转动常数（线形分子）或三个（非线形分子），且均为正值。';return}
  if(!(sig>=1)||!(g>=1)||!(sc>0)){msg.textContent='对称数、多重度和标度因子必须为正。';return}
  if(nu.some(x=>isNaN(x))){msg.textContent='频率列表中有非数字内容。';return}
  let Q;try{Q=await QC.api('therm.custom',{m,B,Bu,sig,g,sc,nu,low:$('cLow').checked})}catch(e){return}const im=Q.im,low=Q.low;nu=Q.mol.nu;
  const lin=Q.mol.lin;let note=[];
  if(im)note.push('已排除的虚频数：'+im+(im===1?'——这是过渡态，沿反应路径的振动不计入总和':'——虚频多于一个：该结构既不是极小点也不是过渡态，校正不可靠'));
  if(low&&!$('cLow').checked)note.push('低于 100 cm⁻¹ 的频率数：'+low+'；谐振近似会高估它们的熵');
  ST.custom=Q.mol;ST.src=ST.custom;mark($('molG'),-1);
  msg.textContent='已计算：'+(lin?'直线形':'非线形')+'分子，振动数 '+nu.length+'.'+(note.length?' 注意：'+note.join('; ')+'.':'');draw()};
QC.api('therm.mols',{}).then(m=>{MOL=m;initMol();ST.src=MOL[ST.mol];draw()}).catch(()=>{});
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{if(ST.src)chart()});
