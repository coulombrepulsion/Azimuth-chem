/* BSSE page (Atlas v2).  The PySCF energies of the water dimer, BSSE, means
   and the interpolated minima of the scans come from quas_atlas.core.bsse
   (bsse.bars, bsse.bases, bsse.scan); this script draws. */
// ---------- страница «Суперпозиционная ошибка базиса» (энергии PySCF посчитаны заранее) ----------
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const fmt=(x,d=2)=>{if(x==null||!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('-','−')};
const sg=(x,d=2)=>(x>0.5*Math.pow(10,-d)?'+':'')+fmt(x,d);
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
function chips(box,labels,cur,on){box.innerHTML='';labels.forEach((t,i)=>{const b=document.createElement('button');b.type='button';b.className='chip';b.innerHTML=t;b.setAttribute('aria-pressed',i===cur);b.onclick=()=>on(i);box.appendChild(b)})}
function mark(box,i){[...box.children].forEach((b,j)=>b.setAttribute('aria-pressed',j===i))}
const METH=['HF','MP2','CCSD(T)'];const Q={m:1,s:0};
chips($('mG'),METH,Q.m,i=>{Q.m=i;mark($('mG'),i);bars()});
const liveB=QC.live('bsse.bars'),liveS=QC.live('bsse.scan');
async function bars(){const m=METH[Q.m];let Z;try{Z=await liveB({m})}catch(e){return}const rows=Z.rows,bs=rows.map(r=>r.b),svg=$('bars');svg.innerHTML='';const W=960,H=360,lft=60,rt=16,top=14,bot=90;
  const ref=Z.ref;let lo=Math.min(...rows.map(r=>Math.min(r.raw,r.cp)),ref??0,0)*1.1,hi=0.5;
  const Y=v=>top+(hi-v)/(hi-lo)*(H-top-bot),gw=(W-lft-rt)/bs.length,bw=Math.min(26,gw/3);
  for(let v=0;v>=lo;v-=1){el('line',{x1:lft,x2:W-rt,y1:Y(v),y2:Y(v),stroke:v===0?tok('--ink'):tok('--line')},svg);el('text',{x:lft-6,y:Y(v)+4,'text-anchor':'end','font-size':12,fill:tok('--muted')},svg,fmt(v,0))}
  el('text',{x:14,y:top+(H-top-bot)/2,'text-anchor':'middle','font-size':12,fill:tok('--muted'),transform:`rotate(-90 14 ${top+(H-top-bot)/2})`},svg,'ΔE, kcal/mol');
  bs.forEach((b,i)=>{const x0=lft+gw*i+gw/2,r=rows[i];
    el('rect',{x:x0-bw-2,y:Y(0),width:bw,height:Y(r.raw)-Y(0),fill:tok('--warn'),rx:2},svg);
    el('rect',{x:x0+2,y:Y(0),width:bw,height:Y(r.cp)-Y(0),fill:tok('--nu'),rx:2},svg);
    const t=el('text',{x:x0,y:H-bot+14,'text-anchor':'end','font-size':12,fill:tok('--ink'),transform:`rotate(-40 ${x0} ${H-bot+14})`},svg,b)});
  if(ref!=null){el('line',{x1:lft,x2:W-rt,y1:Y(ref),y2:Y(ref),stroke:tok('--ok'),'stroke-dasharray':'6 4','stroke-width':1.8},svg);el('text',{x:W-rt-4,y:Y(ref)-6,'text-anchor':'end','font-size':13,'font-weight':600,fill:tok('--ok'),stroke:tok('--panel')||'#fff','stroke-width':5,'paint-order':'stroke','stroke-linejoin':'round'},svg,'complete basis set limit ≈ '+fmt(ref,2))}
  $('barsL').innerHTML='<span><span class="box" style="background:'+tok('--warn')+'"></span>uncorrected</span><span><span class="box" style="background:'+tok('--nu')+'"></span>counterpoise-corrected</span>';
  $('barsT').innerHTML='<table class="mtab"><thead><tr><th>basis</th><th>functions in dimer</th><th>uncorrected</th><th>corrected</th><th>BSSE</th><th>average</th></tr></thead><tbody>'+rows.map(r=>'<tr><td>'+r.b+'</td><td>'+r.nbf+'</td><td>'+fmt(r.raw,2)+'</td><td>'+fmt(r.cp,2)+'</td><td>'+fmt(r.bsse,2)+'</td><td>'+fmt(r.avg,2)+'</td></tr>').join('')+'</tbody></table><p class="hint">kcal/mol; BSSE = uncorrected ΔE − corrected ΔE (spurious attraction).</p>';
  $('barsN').textContent=m==='HF'?'Hartree–Fock has no dispersion, so the binding is weaker and the BSSE smaller: the error is mostly in the correlation and grows with the method.':m==='MP2'?'MP2: in cc-pVDZ −7.3 kcal/mol uncorrected and −3.9 corrected; the limit estimate is −4.9. Basis sets with diffuse functions (aug-) bring both values closer to the limit already at the double-zeta level.':'CCSD(T) almost repeats MP2: for a hydrogen bond the contribution of higher excitations is small (0.02 kcal/mol in aug-cc-pVDZ). CCSD(T) calculations go up to cc-pVTZ; in larger basis sets there is only MP2.'}
let SB=null;
async function scan(){if(!SB){try{SB=await QC.api('bsse.bases',{})}catch(e){return}chips($('sG'),SB,Q.s,i=>{Q.s=i;mark($('sG'),i);scan()})}
  const b=SB[Q.s];let Z;try{Z=await liveS({b})}catch(e){return}const svg=$('scan');svg.innerHTML='';const W=960,H=330,lft=60,rt=150,top=14,bot=40;
  const raw=Z.raw,cp=Z.cp,best=Z.best;
  const all=[...raw,...cp,...(best||[])];const x0=all[0][0],x1=Math.max(...all.map(p=>p[0]));let lo=Math.min(...all.map(p=>p[1]))*1.1,hi=Math.max(2,Math.min(4,Math.max(...all.map(p=>p[1]))));
  const X=x=>lft+(x-x0)/(x1-x0)*(W-lft-rt),Y=v=>top+(hi-v)/(hi-lo)*(H-top-bot);
  for(let v=Math.ceil(lo);v<=hi;v+=1){el('line',{x1:lft,x2:W-rt,y1:Y(v),y2:Y(v),stroke:v===0?tok('--ink'):tok('--line')},svg);el('text',{x:lft-6,y:Y(v)+4,'text-anchor':'end','font-size':12,fill:tok('--muted')},svg,fmt(v,0))}
  for(let r=Math.ceil(x0*2)/2;r<=x1+1e-9;r+=0.5)el('text',{x:X(r),y:H-20,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,fmt(r,1));
  el('text',{x:(lft+W-rt)/2,y:H-3,'text-anchor':'middle','font-size':12,fill:tok('--muted')},svg,'R(O···O), Å');
  el('text',{x:14,y:top+(H-top-bot)/2,'text-anchor':'middle','font-size':12,fill:tok('--muted'),transform:`rotate(-90 14 ${top+(H-top-bot)/2})`},svg,'ΔE, kcal/mol');
  const path=(c,col,w,dash)=>{let d='';c.forEach((p,j)=>{if(p[1]>hi+1)return;d+=(d?'L':'M')+X(p[0]).toFixed(1)+' '+Y(p[1]).toFixed(1)});el('path',{d,fill:'none',stroke:tok(col),'stroke-width':w,'stroke-dasharray':dash||''},svg)};
  if(best&&b!=='aug-cc-pVTZ')path(best,'--ok',1.4);path(raw,'--warn',2.4,'7 5');path(cp,'--nu',2.4);
  const mr=Z.minRaw,mc=Z.minCp;[[mr,'--warn'],[mc,'--nu']].forEach(([p,c])=>el('circle',{cx:X(p[0]),cy:Y(p[1]),r:5,fill:tok(c)},svg));
  {let ya=Y(raw[raw.length-1][1])+4,yb=Y(cp[cp.length-1][1])+4;if(Math.abs(ya-yb)<18){const m=(ya+yb)/2,sgn=ya>=yb?1:-1;ya=m+9*sgn;yb=m-9*sgn}el('text',{x:W-rt+8,y:ya,'font-size':13,fill:tok('--warn')},svg,'uncorrected');el('text',{x:W-rt+8,y:yb,'font-size':13,fill:tok('--nu')},svg,'corrected')}
  $('scanL').innerHTML='<span><span class="sw" style="border-color:'+tok('--warn')+';border-style:dashed"></span>uncorrected</span><span><span class="sw" style="border-color:'+tok('--nu')+'"></span>counterpoise-corrected</span>'+(b!=='aug-cc-pVTZ'?'<span><span class="sw" style="border-color:'+tok('--ok')+'"></span>aug-cc-pVTZ, corrected</span>':'');
  $('scanN').textContent='Minimum without the correction: '+fmt(mr[1],2)+' kcal/mol at R = '+fmt(mr[0],2)+' Å; with the correction: '+fmt(mc[1],2)+' kcal/mol at R = '+fmt(mc[0],2)+' Å. The spurious attraction not only deepens the well but also shifts the minimum to shorter distances: at small R the neighbour’s functions are closer and the “borrowing” is larger.'}
function all(){bars();scan()}
all();matchMedia('(prefers-color-scheme: dark)').addEventListener('change',all);
