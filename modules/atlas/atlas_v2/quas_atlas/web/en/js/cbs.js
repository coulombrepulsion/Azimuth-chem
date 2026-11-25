/* CBS page (Atlas v2).  The PySCF energies, correlation energies, X^-3
   extrapolations and atomisation energies come from quas_atlas.core.cbs
   (cbs.meta, cbs.conv, cbs.xtab, cbs.tae); this script draws. */
// ---------- страница «Сходимость по базису и предел полного базиса» (энергии PySCF посчитаны заранее) ----------
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const fmt=(x,d=2)=>{if(x==null||!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('-','−')};
const sg=(x,d=2)=>(x>0.5*Math.pow(10,-d)?'+':'')+fmt(x,d);
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
function chips(box,labels,cur,on){box.innerHTML='';labels.forEach((t,i)=>{const b=document.createElement('button');b.type='button';b.className='chip';b.innerHTML=t;b.setAttribute('aria-pressed',i===cur);b.onclick=()=>on(i);box.appendChild(b)})}
function mark(box,i){[...box.children].forEach((b,j)=>b.setAttribute('aria-pressed',j===i))}
const SUB=s=>s.replace(/(\d)/g,'<sub>$1</sub>');
const XL={2:'DZ',3:'TZ',4:'QZ',5:'5Z'};
let MOLS=null;
const QS=[['HF','Hartree–Fock energy','Eₕ'],['cMP2','MP2 correlation','mEₕ'],['cT','CCSD(T) correlation','mEₕ'],['tae','CCSD(T) atomization energy','kcal/mol']];
const Q={m:3,q:2,ax:0,p:1};
const initM=()=>chips($('molG'),MOLS.map(SUB),Q.m,i=>{Q.m=i;mark($('molG'),i);draw()});
chips($('qG'),QS.map(q=>q[1]),Q.q,i=>{Q.q=i;mark($('qG'),i);draw()});
chips($('axG'),['X','X⁻³'],Q.ax,i=>{Q.ax=i;mark($('axG'),i);draw()});
const liveC=QC.live('cbs.conv'),liveX=QC.live('cbs.xtab');
async function conv(){if(!MOLS)return;const m=MOLS[Q.m];let Z;try{Z=await liveC({m:Q.m,q:Q.q})}catch(e){return}const xs=Z.xs,svg=$('conv');svg.innerHTML='';const W=960,H=330,lft=86,rt=130,top=16,bot=42;
  const v=Z.v,L=Z.L;let lo=Math.min(...v,L??Infinity),hi=Math.max(...v,L??-Infinity);const pad=(hi-lo)*0.1||1;lo-=pad;hi+=pad;
  const inv=Q.ax===1,xv=X=>inv?Z.xinv[xs.indexOf(X)]:X,xa=inv?0:2,xb=inv?Math.pow(2,-3)*1.04:5.2;
  const XX=x=>inv?lft+(x-xa)/(xb-xa)*(W-lft-rt):lft+(x-1.8)/(xb-1.8)*(W-lft-rt),Y=y=>top+(hi-y)/(hi-lo)*(H-top-bot);
  const rng=hi-lo,st=[1e-4,2e-4,5e-4,1e-3,2e-3,5e-3,0.01,0.02,0.05,0.1,0.2,0.5,1,2,5,10,20,50,100].find(s=>rng/s<=7);const dd=st<0.001?4:st<0.01?3:st<1?2:st<10?1:0;
  for(let y=Math.ceil(lo/st)*st;y<=hi;y+=st){el('line',{x1:lft,x2:W-rt,y1:Y(y),y2:Y(y),stroke:tok('--line')},svg);el('text',{x:lft-6,y:Y(y)+4,'text-anchor':'end','font-size':12,fill:tok('--muted')},svg,fmt(y,dd))}
  xs.forEach(X=>el('text',{x:XX(xv(X)),y:H-22,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,XL[X]+(inv?' ('+fmt(xv(X),3)+')':'')));
  if(inv)el('text',{x:XX(0),y:H-22,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,'CBS (0)');
  el('text',{x:(lft+W-rt)/2,y:H-4,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,inv?'X⁻³ — the complete basis set limit is at X⁻³ = 0':'cardinal number X');
  el('text',{x:14,y:top+(H-top-bot)/2,'text-anchor':'middle','font-size':12,fill:tok('--muted'),transform:`rotate(-90 14 ${top+(H-top-bot)/2})`},svg,QS[Q.q][2]);
  if(L!=null){el('line',{x1:lft,x2:W-rt,y1:Y(L),y2:Y(L),stroke:tok('--ok'),'stroke-dasharray':'6 4','stroke-width':1.6},svg);el('text',{x:W-rt+8,y:Y(L)+4,'font-size':13,fill:tok('--ok')},svg,'limit (CBS)');
    if(inv){const X2=xs[xs.length-1];el('line',{x1:XX(0),y1:Y(L),x2:XX(xv(X2-1)),y2:Y(v[xs.indexOf(X2-1)]),stroke:tok('--ok'),'stroke-width':1.2,opacity:.7},svg)}}
  let d='';xs.forEach((X,j)=>d+=(j?'L':'M')+XX(xv(X)).toFixed(1)+' '+Y(v[j]).toFixed(1));el('path',{d,fill:'none',stroke:tok('--nu'),'stroke-width':2.4},svg);
  xs.forEach((X,j)=>el('circle',{cx:XX(xv(X)),cy:Y(v[j]),r:5,fill:tok('--nu')},svg));
  const u=QS[Q.q][2],dg=Q.q===0?6:Q.q===3?2:2;
  $('convT').innerHTML='<table class="mtab"><thead><tr><th>basis</th><th>functions</th><th>value, '+u+'</th><th>step from previous</th>'+(L!=null?'<th>to the limit</th>':'')+'</tr></thead><tbody>'+
   xs.map((X,j)=>'<tr><td>cc-pV'+XL[X]+'</td><td>'+Z.nbf[j]+'</td><td>'+fmt(v[j],dg)+'</td><td>'+(j?sg(Z.steps[j],dg):'—')+'</td>'+(L!=null?'<td>'+sg(Z.toL[j],dg)+'</td>':'')+'</tr>').join('')+
   (L!=null?'<tr><td><b>CBS</b></td><td>∞</td><td><b>'+fmt(L,dg)+'</b></td><td>—</td><td>0</td></tr>':'')+'</tbody></table>';
  const n=[];if(Q.q===0){n.push('The steps shrink '+Z.ratios.map(x=>fmt(x,1)).join(' and ')+' times each time: the Hartree–Fock energy converges almost exponentially, and the limit is close to the last value.')}
  else if(Q.q<3)n.push('The correlation energy converges slowly: even in '+XL[xs[xs.length-1]]+' the remaining distance to the limit is '+fmt(Z.remain,1)+' mEₕ ('+fmt(Z.remainKcal,1)+' kcal/mol). On the X⁻³ axis the points lie almost on a straight line — this is what the extrapolation relies on. The limit here is the extrapolation from the two largest basis sets.');
  else n.push('Limit — the TZ/QZ extrapolation of the correlation energy plus the Hartree–Fock energy in QZ, for the molecule and for the atoms.');
  $('convN').textContent=n.join(' ')}
// ---------- экстраполяция ----------
const PAIRS=[[2,3],[3,4],[4,5]];
chips($('pG'),PAIRS.map(([a,b])=>XL[a]+' + '+XL[b]),Q.p,i=>{Q.p=i;mark($('pG'),i);xtab()});
async function xtab(){if(!MOLS)return;const [X,Y]=PAIRS[Q.p];let Z;try{Z=await liveX({p:Q.p})}catch(e){return}const has5=Z.has5;
  $('xT').innerHTML='<table class="mtab"><thead><tr><th>molecule</th><th>E<sub>corr</sub>('+XL[Y]+'), mEₕ</th><th>extrapolation '+XL[X]+'/'+XL[Y]+'</th><th>best estimate</th><th>error '+XL[Y]+'</th><th>extrapolation error</th></tr></thead><tbody>'+
   Z.rows.map(({m,e,x,b,de,dx})=>'<tr><td>'+SUB(m)+'</td><td>'+fmt(e,1)+'</td><td>'+fmt(x,1)+'</td><td>'+fmt(b,1)+'</td><td>'+sg(de,1)+'</td><td>'+sg(dx,1)+'</td></tr>').join('')+'</tbody></table>';
  $('xN').textContent='CCSD(T) correlation energy. The best estimate of the limit is the QZ/5Z extrapolation where a 5Z calculation exists ('+has5.join(', ')+'), otherwise TZ/QZ. '+(Q.p===0?'The DZ/TZ pair is crude: the X⁻³ law holds only for large enough X, and DZ falls outside it.':Q.p===1?'The TZ/QZ extrapolation reduces the QZ error several times — a cheap way to get close to 5Z and beyond.':'QZ/5Z is what is regarded as the reference limit; here 5Z calculations were done only for small molecules.')}
// ---------- атомизация ----------
const COL=['--nu','--ok','--el','--mp2','--warn','--virt','--traj','--trip','--ink'];
async function taeC(){if(!MOLS)return;let T;try{T=await QC.api('cbs.tae',{})}catch(e){return}const svg=$('taeC');svg.innerHTML='';const W=960,H=330,lft=70,rt=90,top=16,bot=40;
  const E=T.err;let lo=Math.min(...E.flat(),0),hi=Math.max(...E.flat(),0);const pad=(hi-lo)*0.08;lo-=pad;hi+=pad;
  const X=x=>lft+(x-2)/2*(W-lft-rt),Y=v=>top+(hi-v)/(hi-lo)*(H-top-bot);const st=[1,2,5,10].find(s=>(hi-lo)/s<=8);
  for(let v=Math.ceil(lo/st)*st;v<=hi;v+=st){el('line',{x1:lft,x2:W-rt,y1:Y(v),y2:Y(v),stroke:Math.abs(v)<1e-9?tok('--ink'):tok('--line')},svg);el('text',{x:lft-6,y:Y(v)+4,'text-anchor':'end','font-size':12,fill:tok('--muted')},svg,sg(v,0))}
  [2,3,4].forEach(x=>el('text',{x:X(x),y:H-20,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,'cc-pV'+XL[x]));
  el('text',{x:14,y:top+(H-top-bot)/2,'text-anchor':'middle','font-size':12,fill:tok('--muted'),transform:`rotate(-90 14 ${top+(H-top-bot)/2})`},svg,'error in Dₑ, kcal/mol');
  MOLS.forEach((m,i)=>{const c=tok(COL[i%COL.length]);let d='';E[i].forEach((v,j)=>d+=(j?'L':'M')+X(j+2).toFixed(1)+' '+Y(v).toFixed(1));el('path',{d,fill:'none',stroke:c,'stroke-width':2},svg);E[i].forEach((v,j)=>el('circle',{cx:X(j+2),cy:Y(v),r:3.5,fill:c},svg))});
  $('taeL').innerHTML=MOLS.map((m,i)=>'<span><span class="sw" style="border-color:'+tok(COL[i%COL.length])+'"></span>'+SUB(m)+'</span>').join('');
  $('taeT').innerHTML='<table class="mtab"><thead><tr><th>molecule</th><th>DZ</th><th>TZ</th><th>QZ</th><th>CBS (TZ/QZ)</th></tr></thead><tbody>'+MOLS.map((m,i)=>'<tr><td>'+SUB(m)+'</td>'+[0,1,2].map(j=>'<td>'+fmt(T.tab[i][j],1)+'</td>').join('')+'<td><b>'+fmt(T.tab[i][3],1)+'</b></td></tr>').join('')+'</tbody></table><p class="hint">CCSD(T) atomization energy Dₑ, kcal/mol.</p>'}
function draw(){conv()}
function all(){conv();xtab();taeC()}
QC.api('cbs.meta',{}).then(M=>{MOLS=M.mols;initM();all()}).catch(()=>{});matchMedia('(prefers-color-scheme: dark)').addEventListener('change',all);
