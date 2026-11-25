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
chips($('qG'),['entropy S','heat capacity C<sub>p</sub>'],0,i=>{ST.q=i;mark($('qG'),i);chart()});
$('T').value=298;$('T').oninput=()=>{ST.T=+$('T').value;draw()};
$('bT298').textContent=fmt(298.15,2)+' K';$('bT298').onclick=()=>{ST.T=298.15;$('T').value=298;draw()};
// ---------- вывод ----------
const liveT=QC.live('therm.state'),liveC=QC.live('therm.chart');
async function draw(){const M=ST.src,T=ST.T;let Z;try{Z=await liveT({mol:molArg(),T,p:ST.p})}catch(e){return}const r=Z.r;
  $('Tv').textContent=fmt(T,T===298.15?2:0)+' K';
  const nv=M.nu.length,typ=M.lin?'linear':'nonlinear';
  $('molInfo').innerHTML=(M.custom?'Your own molecule':M.id)+': '+typ+', σ = '+M.sig+', multiplicity '+M.g+', vibrations '+nv+' ('+(M.lin?'3N − 5':'3N − 6')+'). Frequencies, cm⁻¹: '+M.nu.map(n=>Math.round(n)).join(', ')+'.';
  const card=(t,v,u,s)=>'<div class="card"><span class="t">'+t+'</span><b>'+v+' '+u+'</b>'+(s?'<small>'+s+'</small>':'')+'</div>';
  const eh=k=>fmt(Z.eh[k],6)+' E<sub>h</sub>';
  $('cards').innerHTML=card('Zero-point energy ZPE',fmt(r.zpe/1000),'kJ/mol',eh('zpe'))+card('Enthalpy correction H<sub>corr</sub>',fmt(r.Hc/1000),'kJ/mol',eh('Hc'))
    +card('Entropy S',fmt(r.S),'J/(mol·K)','TS = '+fmt(Z.TS)+' kJ/mol')+card('Gibbs energy correction G<sub>corr</sub>',fmt(r.Gc/1000),'kJ/mol',eh('Gc'))
    +card('Heat capacity C<sub>p</sub>',fmt(r.Cp),'J/(mol·K)','');
  const row=(n,s,c,h)=>'<tr><td>'+n+'</td><td>'+fmt(s)+'</td><td>'+fmt(c)+'</td><td>'+h+'</td></tr>';
  $('tab').innerHTML='<table class="mtab"><thead><tr><th>contribution</th><th>S, J/(mol·K)</th><th>C<sub>p</sub>, J/(mol·K)</th><th>H(T) − H(0), kJ/mol</th></tr></thead><tbody>'
    +row('translational (with pV = RT)',r.St,r.Ct,fmt(r.Ht/1000))+row('rotational',r.Sr,r.Cr,fmt(r.Hr/1000))+row('vibrational (without ZPE)',r.Sv,r.Cv,fmt(r.Hv/1000))+row('electronic',r.Se,0,fmt(0))
    +'<tr><td><b>total</b></td><td><b>'+fmt(r.S)+'</b></td><td><b>'+fmt(r.Cp)+'</b></td><td><b>'+fmt(r.Hth/1000)+'</b></td></tr></tbody></table>';
  const rb=$('refBox');
  if(!M.custom&&Math.abs(T-298.15)<0.01&&ST.p===1e5){const d=Z.ref.d;rb.className='ref';rb.innerHTML='NIST-JANAF tables: S°(298.15 K, 1 bar) = <b>'+fmt(M.S)+'</b> J/(mol·K); calculated '+fmt(r.S)+', difference '+fmt(d)+' ('+fmt(Z.ref.pct,2)+' %).'+(M.id==='H₂'?' For H₂ the classical rotor is already inaccurate at 298 K: the rotational quantum is large, and ortho- and para-hydrogen must be treated separately.':'')}
  else{rb.className='ref off';rb.textContent=M.custom?'There is no table value for your own molecule.':'The comparison with the NIST-JANAF tables is made at T = 298.15 K and p = 1 bar (the “298.15 K” button).'}
  chart();}
async function chart(){let Cz;try{Cz=await liveC({mol:molArg(),p:ST.p})}catch(e){return}const svg=$('chart');svg.innerHTML='';const M=ST.src,W=960,Hh=330,L=56,Rr=16,Tp=18,B=38,T0=50,T1=2000;
  const pts=Cz.pts;
  const keys=ST.q?[['Cp','--ink','sum'],['Ct','--nu','translational'],['Cr','--ok','rotational'],['Cv','--el','vibrational']]:[['S','--ink','sum'],['St','--nu','translational'],['Sr','--ok','rotational'],['Sv','--el','vibrational'],['Se','--virt','electronic']];
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
  $('chartNote').textContent=ST.q?'The translational and rotational contributions to Cp are constant; the vibrational one grows when kT becomes comparable to the quantum hcν.':'Vibrational entropy is noticeable only when kT is comparable to the vibrational quantum: at 298 K, kT/hc ≈ 207 cm⁻¹.';}
// ---------- своя молекула ----------
function nums(s){return s.replace(/,(?=\d)/g,'.').split(/[\s;,]+/).filter(x=>x).map(Number)}
$('bFill').onclick=()=>{const M=MOL[ST.mol];$('cM').value=String(M.m);$('cB').value=M.B.join(' ');$('cBu').value='cm';$('cSig').value=String(M.sig);$('cG').value=String(M.g);$('cScale').value='1';$('cNu').value=M.nu.join(' ');$('cLow').checked=false;
  $('cMsg').textContent='The data of '+M.id+' have been transferred. Change something (for example σ) and click “Calculate”.'};
$('bCalc').onclick=async()=>{const msg=$('cMsg'),m=nums($('cM').value)[0],Bu=$('cBu').value;
  const B=nums($('cB').value),sig=Math.round(nums($('cSig').value)[0]),g=Math.round(nums($('cG').value)[0]),sc=nums($('cScale').value)[0];
  let nu=nums($('cNu').value);
  if(!(m>0)){msg.textContent='Enter the mass of the molecule.';return}
  if(!(B.length===1||B.length===3)||B.some(x=>!(x>0))){msg.textContent='One rotational constant is needed (linear molecule) or three (nonlinear), all positive.';return}
  if(!(sig>=1)||!(g>=1)||!(sc>0)){msg.textContent='The symmetry number, multiplicity and scale factor must be positive.';return}
  if(nu.some(x=>isNaN(x))){msg.textContent='The frequency list contains non-numbers.';return}
  let Q;try{Q=await QC.api('therm.custom',{m,B,Bu,sig,g,sc,nu,low:$('cLow').checked})}catch(e){return}const im=Q.im,low=Q.low;nu=Q.mol.nu;
  const lin=Q.mol.lin;let note=[];
  if(im)note.push('imaginary frequencies excluded: '+im+(im===1?' — this is a transition state; its vibration along the reaction path is not included in the sum':' — more than one imaginary frequency: the structure is neither a minimum nor a transition state, and the corrections are unreliable'));
  if(low&&!$('cLow').checked)note.push('frequencies below 100 cm⁻¹: '+low+'; the harmonic approximation overestimates their entropy');
  ST.custom=Q.mol;ST.src=ST.custom;mark($('molG'),-1);
  msg.textContent='Calculated: '+(lin?'linear':'nonlinear')+' molecule, vibrations '+nu.length+'.'+(note.length?' Note: '+note.join('; ')+'.':'');draw()};
QC.api('therm.mols',{}).then(m=>{MOL=m;initMol();ST.src=MOL[ST.mol];draw()}).catch(()=>{});
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{if(ST.src)chart()});
