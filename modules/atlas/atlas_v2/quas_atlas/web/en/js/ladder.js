/* Method hierarchy page (Atlas v2).  The PySCF energies and timings, errors
   vs FCI, cost factors, fitted exponents and atomisation-energy errors come
   from quas_atlas.core.ladder (lad.meta, lad.fci, lad.cost, lad.times,
   lad.tae); this script draws. */
// ---------- страница «Иерархия методов и лестница Якова» (данные PySCF посчитаны заранее) ----------
const ruN=(n,a,b,c)=>{n=Math.abs(Math.round(n));const m=n%10,h=n%100;return m===1&&h!==11?a:m>=2&&m<=4&&(h<12||h>14)?b:c};
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const fmt=(x,d=2)=>{if(x==null||!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('-','−')};
const sg=(x,d=2)=>(x>0.5*Math.pow(10,-d)?'+':'')+fmt(x,d);
const big=x=>{if(x<1e4)return fmt(x,x<10?1:0);const e=Math.floor(Math.log10(x)),m=x/Math.pow(10,e);return fmt(m,1)+'·10<sup>'+e+'</sup>'};
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
function chips(box,labels,cur,on){box.innerHTML='';labels.forEach((t,i)=>{const b=document.createElement('button');b.type='button';b.className='chip';b.innerHTML=t;b.setAttribute('aria-pressed',i===cur);b.onclick=()=>on(i);box.appendChild(b)})}
function mark(box,i){[...box.children].forEach((b,j)=>b.setAttribute('aria-pressed',j===i))}
const MOLN={HF:'HF',H2O:'H<sub>2</sub>O'};
const ME=[['MP2','--mp2'],['CISD','--warn'],['CCSD','--ok'],['CCSD(T)','--nu']];
const Q={m:0,k:0,f:2,r:3,t:3};
// ---------- 1. ошибки относительно FCI ----------
let MOLS=null,NK=null,TAEM=null,RNK=null,TA=null,TZ=null;
const initMol=()=>chips($('molG'),MOLS.map(m=>MOLN[m]),Q.m,i=>{Q.m=i;mark($('molG'),i);const n=NK[MOLS[i]];$('kS').max=n-1;if(Q.k>n-1)Q.k=n-1;$('kS').value=Q.k;fci()});
$('kS').oninput=e=>{Q.k=+e.target.value;fci()};
const liveF=QC.live('lad.fci'),liveC=QC.live('lad.cost');
async function fci(){let F;try{F=await liveF({mol:MOLS[Q.m]})}catch(e){return}const P=F.pts,p=P[Q.k];$('kV').textContent=fmt(p.k,2);
  const svg=$('errC');svg.innerHTML='';const W=960,H=330,lft=64,rt=110,top=16,bot=40;
  let lo=0,hi=0;P.forEach(q=>ME.forEach(([m])=>{if(q.err[m]!=null){const e=q.err[m];lo=Math.min(lo,e);hi=Math.max(hi,e)}}));
  const pad=(hi-lo)*0.08;lo-=pad;hi+=pad;const k0=P[0].k,k1=P[P.length-1].k;
  const X=k=>lft+(k-k0)/(k1-k0)*(W-lft-rt),Y=v=>top+(hi-v)/(hi-lo)*(H-top-bot);
  const step=[1,2,5,10,20,50,100].find(s=>(hi-lo)/s<=8);
  for(let v=Math.ceil(lo/step)*step;v<=hi;v+=step){el('line',{x1:lft,x2:W-rt,y1:Y(v),y2:Y(v),stroke:Math.abs(v)<1e-9?tok('--ink'):tok('--line'),'stroke-width':Math.abs(v)<1e-9?1.4:1},svg);el('text',{x:lft-6,y:Y(v)+4,'text-anchor':'end','font-size':12,fill:tok('--muted')},svg,sg(v,0))}
  P.forEach(q=>el('text',{x:X(q.k),y:H-18,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,fmt(q.k,2)));
  el('text',{x:(lft+W-rt)/2,y:H-2,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,'r / rₑ');
  el('text',{x:14,y:top+(H-top-bot)/2,'text-anchor':'middle','font-size':12,fill:tok('--muted'),transform:`rotate(-90 14 ${top+(H-top-bot)/2})`},svg,'E − E(FCI), mEₕ');
  el('line',{x1:X(p.k),x2:X(p.k),y1:top,y2:H-bot,stroke:tok('--muted'),'stroke-dasharray':'4 4'},svg);
  ME.forEach(([m,c])=>{let d='';P.forEach((q,j)=>{if(q.err[m]==null)return;d+=(d&&P[j-1].err[m]!=null?'L':'M')+X(q.k).toFixed(1)+' '+Y(q.err[m]).toFixed(1)});el('path',{d,fill:'none',stroke:tok(c),'stroke-width':2.4},svg);
    P.forEach((q,j)=>{if(q.err[m]!=null)el('circle',{cx:X(q.k),cy:Y(q.err[m]),r:j===Q.k?6:3.5,fill:tok(c)},svg)});
    const last=[...P].reverse().find(q=>q.err[m]!=null);if(last)el('text',{x:W-rt+10,y:Y(last.err[m])+4,'font-size':13,fill:tok(c)},svg,m)});
  el('text',{x:W-rt+10,y:Y(0)-6,'font-size':12,fill:tok('--ink')},svg,'FCI');
  $('errL').innerHTML=ME.map(([m,c])=>'<span><span class="sw" style="border-color:'+tok(c)+'"></span>'+m+'</span>').join('')+'<span>zero — the exact answer in this basis (full CI)</span>';

  $('errT').innerHTML='<table class="mtab"><thead><tr><th>method</th><th>E, Eₕ</th><th>E − E(FCI), mEₕ</th><th>share of correlation energy</th></tr></thead><tbody>'+
    ['HF',...ME.map(x=>x[0]),'FCI'].map(m=>{const e=p.E[m];if(e==null)return '<tr><td>'+m+'</td><td>not converged</td><td>—</td><td>—</td></tr>';return '<tr><td>'+m+'</td><td>'+fmt(e,6)+'</td><td>'+(m==='FCI'?'0':sg(p.err[m],1))+'</td><td>'+fmt(p.frac[m],1)+' %</td></tr>'}).join('')+'</tbody></table>';
  const t=p.err['CCSD(T)'],n=[];
  if(p.k===1)n.push('Near equilibrium the hierarchy works as intended: each level is closer to FCI, and CCSD(T) is off by less than 1 mEₕ (0.6 kcal/mol).');
  if(t!=null&&t<-0.5)n.push('CCSD(T) has dropped below the exact energy: it is not a variational method, and as the bond is stretched the (T) correction, computed by perturbation theory from a single determinant, becomes too large. Lower is worse here — the “extra” accuracy is only apparent.');
  if(p.k>=2&&p.E.MP2!=null)n.push('A stretched bond is a multiconfigurational problem: one Hartree–Fock determinant is no longer enough, and the methods built on it lose reliability.');
  $('errN').textContent=n.join(' ')}
// ---------- 2. цена ----------
const COST=[['HF','N⁴',4,'in practice closer to N²–N³: most integrals between distant functions are negligible'],['MP2','N⁵',5,'transformation of the integrals to molecular orbitals'],['CISD','N⁶',6,'not size-consistent: the error grows with the size of the system'],['CCSD','N⁶',6,'iterative, usually 10–30 iterations'],['CCSD(T)','N⁷',7,'one non-iterative correction — the most expensive part'],['FCI','factorial',null,'the number of determinants grows as a binomial coefficient']];
$('fS').oninput=e=>{Q.f=+e.target.value;cost()};
async function cost(){const f=Q.f;$('fV').textContent='×'+f;let C;try{C=await liveC({f})}catch(e){return}
  const d1=C.d1,dF=C.dF;
  $('costT').innerHTML='<table class="mtab"><thead><tr><th>method</th><th>growth</th><th>longer by</th><th>remark</th></tr></thead><tbody>'+COST.map(([m,s,p,c],i)=>'<tr><td>'+m+'</td><td>'+s+'</td><td>'+(p?big(C.fac[i])+' '+ruN(C.fac[i],'times','times','times'):'—')+'</td><td class="n">'+c+'</td></tr>').join('')+'</tbody></table>'+
   '<p class="hint">Full CI: H<sub>2</sub>O in 6-31G with a frozen core has '+big(d1)+' determinants; for a system '+f+' '+ruN(f,'times','times','times')+' more — '+big(dF)+'.</p>'}
const TM=[['HF','--trip'],['MP2','--mp2'],['CCSD','--ok'],['(T)','--nu']];
function times(){if(!TZ)return;const S=TZ.nbf,svg=$('timeC');svg.innerHTML='';const W=960,H=320,lft=64,rt=150,top=14,bot=40;
  const xs=TZ.lognbf,x0=Math.min(...xs)-0.03,x1=Math.max(...xs)+0.03;let y0=1e9,y1=-1e9;TM.forEach(([m])=>TZ.series[m].forEach(([,v])=>{y0=Math.min(y0,v);y1=Math.max(y1,v)}));y0=Math.floor(y0);y1=Math.ceil(y1);
  const X=v=>lft+(v-x0)/(x1-x0)*(W-lft-rt),Y=v=>top+(y1-v)/(y1-y0)*(H-top-bot);
  for(let v=y0;v<=y1;v++){el('line',{x1:lft,x2:W-rt,y1:Y(v),y2:Y(v),stroke:tok('--line')},svg);el('text',{x:lft-6,y:Y(v)+4,'text-anchor':'end','font-size':12,fill:tok('--muted')},svg,v<0?fmt(Math.pow(10,v),-v):big(Math.pow(10,v)))}
  S.forEach((nb,i)=>el('text',{x:X(xs[i]),y:H-20,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,nb));
  el('text',{x:(lft+W-rt)/2,y:H-3,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,'basis functions (logarithmic scale)');
  el('text',{x:14,y:top+(H-top-bot)/2,'text-anchor':'middle','font-size':12,fill:tok('--muted'),transform:`rotate(-90 14 ${top+(H-top-bot)/2})`},svg,'time, s');
  const sl={},labs=[];TM.forEach(([m,c])=>{const pts=TZ.series[m];let d='';pts.forEach((p,j)=>d+=(j?'L':'M')+X(p[0]).toFixed(1)+' '+Y(p[1]).toFixed(1));el('path',{d,fill:'none',stroke:tok(c),'stroke-width':2.2},svg);pts.forEach(p=>el('circle',{cx:X(p[0]),cy:Y(p[1]),r:4,fill:tok(c)},svg));
    sl[m]=TZ.slope[m];const L=pts[pts.length-1];labs.push({y:Y(L[1])+4,c,t:(m==='(T)'?'(T) correction':m)+' ∝ N',e:fmt(sl[m],1)})});
  labs.sort((a,b)=>a.y-b.y);for(let i=1;i<labs.length;i++)labs[i].y=Math.max(labs[i].y,labs[i-1].y+17);
  labs.forEach(l=>{const t=el('text',{x:W-rt+10,y:l.y,'font-size':13,fill:tok(l.c)},svg,l.t);el('tspan',{dy:-6,'font-size':10},t,l.e)});
  $('timeL').innerHTML=TM.map(([m,c])=>'<span><span class="sw" style="border-color:'+tok(c)+'"></span>'+(m==='(T)'?'(T) correction':m)+'</span>').join('');
  $('timeN').textContent='The exponent is the slope of a straight line through the last three points. The measured slope is lower than the formal one for HF (some integrals are discarded) and closer to the formal one for CCSD and (T). The time depends on the computer; only the slopes and ratios are meaningful to compare.'}
// ---------- 3. лестница Якова ----------
const RUNG=[
 {n:'LDA',c:'--trip',ing:'density ρ(r)',ex:'SVWN',t:'Local density approximation: the energy at each point is taken as that of a uniform electron gas of the same density. Accurate for metals with an almost uniform density, but in molecules it strongly overestimates binding energies (“overbinding”).'},
 {n:'GGA',c:'--warn',ing:'+ density gradient ∇ρ',ex:'PBE, BLYP',t:'The generalized gradient approximation takes into account how fast the density changes. It removes most of the LDA overbinding at the same cost; it is the main tool for solids and large systems.'},
 {n:'meta-GGA',c:'--ok',ing:'+ kinetic energy density τ',ex:'TPSS, SCAN',t:'τ = ½Σ|∇φᵢ|² makes it possible to tell one-electron regions (where ρ looks like the density of a single orbital) from bonding regions. SCAN satisfies all 17 known exact constraints that a functional of this rung can satisfy.'},
 {n:'hybrids',c:'--nu',ing:'+ exact exchange over occupied orbitals',ex:'B3LYP, PBE0',t:'A part of the exchange energy (20–25 %) is taken as in the Hartree–Fock method. This reduces the self-interaction error: better reaction barriers, ionization energies and band gaps. The cost rises to the HF level.'},
 {n:'double hybrids',c:'--mp2',ing:'+ virtual orbitals (MP2 correction)',ex:'B2PLYP',t:'Part of the correlation energy from second-order perturbation theory on Kohn–Sham orbitals is added to a hybrid. Closest to “heaven”, but the cost is that of MP2: N⁵ instead of N³–N⁴.'}];
const RN={LDA:0,PBE:1,BLYP:1,TPSS:2,SCAN:2,B3LYP:3,PBE0:3,B2PLYP:4};
function jac(){const svg=$('jac');svg.innerHTML='';const W=480,H=380,x1=70,x2=270,yb=340,yt=40,n=RUNG.length;
  el('line',{x1,x2:x1,y1:yb+10,y2:yt-14,stroke:tok('--ink'),'stroke-width':4,'stroke-linecap':'round'},svg);el('line',{x1:x2,x2,y1:yb+10,y2:yt-14,stroke:tok('--ink'),'stroke-width':4,'stroke-linecap':'round'},svg);
  el('text',{x:(x1+x2)/2,y:H-6,'text-anchor':'middle','font-size':13,fill:tok('--muted')},svg,'“earth”: the Hartree method');
  el('text',{x:(x1+x2)/2,y:16,'text-anchor':'middle','font-size':13,fill:tok('--muted')},svg,'“heaven”: chemical accuracy');
  RUNG.forEach((r,i)=>{const y=yb-i*(yb-yt)/(n-1);const g=el('g',{tabindex:0,role:'button','aria-label':r.n,style:'cursor:pointer'},svg);
    el('line',{x1,x2,y1:y,y2:y,stroke:tok(r.c),'stroke-width':i===Q.r?9:6,'stroke-linecap':'round'},g);
    el('text',{x:x2+14,y:y+5,'font-size':i===Q.r?16:14,'font-weight':i===Q.r?700:400,fill:tok('--ink')},g,(i+1)+'. '+r.n);
    el('rect',{x:x1-10,y:y-18,width:W-x1,height:36,fill:'transparent'},g);
    const go=()=>{Q.r=i;jac()};g.onclick=go;g.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();go()}}});
  const r=RUNG[Q.r];$('rung').innerHTML='<div class="t">'+(Q.r+1)+'. '+r.n+'</div><p><b>Ingredient:</b> '+r.ing+'.<br><b>Examples:</b> '+r.ex+'.</p><p>'+r.t+'</p>'}
const SUBM=s=>s.replace(/(\d)/g,'<sub>$1</sub>');
function mae(){if(!TA)return;const svg=$('maeC');svg.innerHTML='';const rows=[...RNK.map(k=>({k,c:RUNG[RN[k]].c,v:TA.mae[k]})),{k:'HF',c:'--muted',v:TA.mae.HF,wf:1},{k:'MP2',c:'--muted',v:TA.mae.MP2,wf:1},{k:'CCSD',c:'--muted',v:TA.mae.CCSD,wf:1},{k:'CCSD(T)',c:'--muted',v:TA.mae['CCSD(T)'],wf:1}];
  const W=960,H=360,lft=110,rt=70,top=8,bh=(H-top-30)/rows.length;const cap=Math.max(...rows.filter(r=>r.k!=='HF').map(r=>r.v))*1.15;const X=v=>lft+Math.min(v,cap)/cap*(W-lft-rt);
  const step=[1,2,5,10,20].find(s=>cap/s<=10);for(let v=0;v<=cap;v+=step){el('line',{x1:X(v),x2:X(v),y1:top,y2:H-26,stroke:tok('--line')},svg);el('text',{x:X(v),y:H-10,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,fmt(v,0))}
  el('text',{x:W-rt,y:H-10,'text-anchor':'end','font-size':12,fill:tok('--muted')},svg,'kcal/mol');
  rows.forEach((r,i)=>{const y=top+i*bh;if(r.wf&&r.k==='HF')el('line',{x1:lft-100,x2:W-rt,y1:y-2,y2:y-2,stroke:tok('--muted'),'stroke-dasharray':'3 4'},svg);
    el('rect',{x:lft,y:y+3,width:X(r.v)-lft,height:bh-6,fill:tok(r.c),rx:2,opacity:r.wf?0.55:1},svg);
    el('text',{x:lft-8,y:y+bh/2+4,'text-anchor':'end','font-size':13,fill:tok('--ink')},svg,r.k);
    el('text',{x:Math.min(X(r.v),W-rt)+6,y:y+bh/2+4,'font-size':12,fill:tok('--ink')},svg,(r.v>cap?'→ ':'')+fmt(r.v,1))});
  el('line',{x1:X(1),x2:X(1),y1:top,y2:H-26,stroke:tok('--ok'),'stroke-dasharray':'5 4'},svg);el('text',{x:X(1)+4,y:top+12,'font-size':12,fill:tok('--ok')},svg,'1 kcal/mol')}
const initT=()=>chips($('tmolG'),TAEM.map(SUBM),Q.t,i=>{Q.t=i;mark($('tmolG'),i);taeT()});
function taeT(){if(!TA)return;const m=TAEM[Q.t],ref=TA.ref[m];const ks=[...RNK,'HF','MP2','CCSD','CCSD(T)'];
  $('taeT').innerHTML='<table class="mtab"><thead><tr><th>method</th><th>Dₑ, kcal/mol</th><th>error</th></tr></thead><tbody><tr><td><b>reference CCSD(T)/CBS</b></td><td><b>'+fmt(ref,1)+'</b></td><td>—</td></tr>'+ks.map(k=>{const [v,dv]=TA.rows[m][k];return '<tr><td>'+k+(k in RN?' <span class="hint">('+RUNG[RN[k]].n+')</span>':' <span class="hint">(cc-pVQZ)</span>')+'</td><td>'+fmt(v,1)+'</td><td>'+sg(dv,1)+'</td></tr>'}).join('')+'</tbody></table>';
  $('taeN').textContent='The atomization energy Dₑ is the energy needed to break all bonds into free atoms at the bottom of the potential well, without zero-point vibrations. The reference values include only valence correlation and contain no relativistic corrections; they are compared with experiment after these corrections are added. B3LYP and B2PLYP are closer to the reference values here than CCSD(T)/cc-pVQZ: the wavefunction method has not yet converged with the basis in QZ (see the next page), while the functionals converge faster and were fitted on similar molecules.'}
function all(){if(!MOLS)return;fci();cost();times();jac();mae();taeT()}
Promise.all([QC.api('lad.meta',{}),QC.api('lad.tae',{}),QC.api('lad.times',{})]).then(([M,T,Z])=>{MOLS=M.fciMols;NK=M.nk;TAEM=M.taeMols;RNK=Object.keys(RN).filter(k=>M.maeKeys.includes(k));TA=T;TZ=Z;initMol();$('kS').max=NK[MOLS[0]]-1;initT();all()}).catch(()=>{});matchMedia('(prefers-color-scheme: dark)').addEventListener('change',all);
