/* Excited states page (Atlas v2).  Franck-Condon factors, potential curves,
   vibronic envelopes, the Jablonski levels and the spectrum of computed
   transitions come from quas_atlas.core.excited (exc.state, exc.jab,
   exc.spectrum); this script formats and draws. */
// ---------- страница «Возбуждённые состояния и спектры» ----------
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const fmt=(x,d=2)=>{if(x==null||!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('-','−')};
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const txt=(svg,x,y,s,o={})=>el('text',Object.assign({x,y,'font-size':12.5,fill:tok('--muted')},o),svg,s);
['S','w','E00','fw'].forEach(id=>$(id).oninput=draw);$('K').oninput=jab;
const NM=1239.84198;  /* eV·nm: wavelength axis of the computed-spectrum plot */
const liveX=QC.live('exc.state'),liveJ=QC.live('exc.jab');
async function draw(){const S=+$('S').value,E00=+$('E00').value;let Z;try{Z=await liveX({S,w:+$('w').value,E00,fw:+$('fw').value})}catch(e){return}const w=Z.w,fw=Z.fw;
  $('Sv').textContent=fmt(S,2);$('wv').textContent=fmt(Z.wcm,0)+' ('+fmt(w,3)+' eV)';$('E00v').textContent=fmt(E00,2)+' eV = '+fmt(Z.lam00,0)+' nm';$('fwv').textContent=fmt(Z.fwcm,0);
  pot(S,w,E00,Z.pot);const r=spec(S,w,E00,fw,Z.spec);
  const ea=Z.ea,ee=Z.ee,st=Z.st,vmax=Z.vmax;
  const card=(t,v,s)=>'<div class="card"><span class="t">'+t+'</span><b>'+v+'</b>'+(s?'<small>'+s+'</small>':'')+'</div>';
  $('cards').innerHTML=card('vertical absorption E₀₀ + Sħω',fmt(ea,2)+' eV',fmt(Z.lamA,0)+' nm')+card('vertical emission E₀₀ − Sħω',fmt(ee,2)+' eV',fmt(Z.lamE,0)+' nm')
    +card('Stokes shift 2Sħω',fmt(Z.stcm,0)+' cm⁻¹',fmt(st,2)+' eV')+card('most intense absorption line','0 → '+vmax,'envelope maximum: '+fmt(Z.lamMax,0)+' nm');jab()}
function pot(S,w,E00,P){const svg=$('pot');svg.innerHTML='';const W=460,H=360,L=40,R=10,T=14,B=30,D=P.D;
  const q0=P.q0,q1=P.q1,e0=P.e0,e1=P.e1;const X=q=>L+(q-q0)/(q1-q0)*(W-L-R),Y=e=>T+(e1-e)/(e1-e0)*(H-T-B);
  const par=(c,pts)=>{let d='';pts.forEach(([x,e])=>{d+=(d?'L':'M')+X(x).toFixed(1)+' '+Y(e).toFixed(1)});el('path',{d,fill:'none',stroke:tok(c),'stroke-width':2.2},svg)};
  par('--ink',P.g);par('--nu',P.x);
  for(let v=0;v<6;v++){const [e,h,e2]=P.lev[v];el('line',{x1:X(-h),x2:X(h),y1:Y(e),y2:Y(e),stroke:tok('--line'),'stroke-width':1},svg);
    el('line',{x1:X(D-h),x2:X(D+h),y1:Y(e2),y2:Y(e2),stroke:tok('--line'),'stroke-width':1},svg)}
  const ev=P.ev;el('line',{x1:X(0),x2:X(0),y1:Y(0.5*w),y2:Y(ev),stroke:tok('--accent'),'stroke-width':2.2,'marker-end':''},svg);
  el('polygon',{points:[X(0)-5,Y(ev)+9,X(0)+5,Y(ev)+9,X(0),Y(ev)].join(' '),fill:tok('--accent')},svg);
  txt(svg,X(0)+6,Y((ev+0.5*w)/2),'hν');txt(svg,X(D)+4,Y(E00)+16,'S₁');txt(svg,X(0)+4,Y(-0.05*w)+16,'S₀');
  txt(svg,(L+W-R)/2,H-8,'nuclear coordinate q',{'text-anchor':'middle'});txt(svg,4,T+4,'E')}
function spec(S,w,E00,fw,P){const svg=$('spec');svg.innerHTML='';const W=560,H=360,L=40,R=12,T=14,B=40;const x0=P.x0,x1=P.x1;
  const X=e=>L+(e-x0)/(x1-x0)*(W-L-R),Y=v=>T+(1.05-v)/1.05*(H-T-B);const nv=P.nv;
  const ab=P.E.map((e,i)=>[e,P.ab[i]]),em=P.E.map((e,i)=>[e,P.em[i]]);
  el('line',{x1:L,x2:W-R,y1:Y(0),y2:Y(0),stroke:tok('--muted')},svg);
  P.sticks.forEach(([v,h])=>{[[E00+v*w,'--nu'],[E00-v*w,'--el']].forEach(([e,c])=>{if(e<x0||e>x1)return;el('line',{x1:X(e),x2:X(e),y1:Y(0),y2:Y(h),stroke:tok(c),'stroke-width':1.4,opacity:.55},svg)})});
  [[ab,'--nu'],[em,'--el']].forEach(([pts,c])=>el('path',{d:pts.map(([e,v],i)=>(i?'L':'M')+X(e).toFixed(1)+' '+Y(v).toFixed(1)).join(''),fill:'none',stroke:tok(c),'stroke-width':2.4},svg));
  el('line',{x1:X(E00),x2:X(E00),y1:T,y2:Y(0),stroke:tok('--muted'),'stroke-dasharray':'3 4'},svg);txt(svg,X(E00)+3,T+10,'0–0');
  const st=(x1-x0)>3?1:(x1-x0)>1.2?0.5:(x1-x0)>0.6?0.2:0.1;for(let e=Math.ceil(x0/st)*st;e<=x1;e+=st)txt(svg,X(e),H-B+16,fmt(e,st<0.5?1:1),{'text-anchor':'middle'});
  txt(svg,(L+W-R)/2,H-6,'photon energy, eV',{'text-anchor':'middle'});
  $('leg').innerHTML='<span><span class="sw" style="border-color:'+tok('--nu')+'"></span>absorption S₀ → S₁</span><span><span class="sw" style="border-color:'+tok('--el')+'"></span>emission S₁ → S₀ (fluorescence)</span><span>thin lines are individual vibrational transitions, their height is the Franck–Condon factor</span>';
  return {}}
async function jab(){const K=+$('K').value,E1=+$('E00').value;let J;try{J=await liveJ({E1,K})}catch(e){return}const svg=$('jab');svg.innerHTML='';const ET=J.ET;$('Kv').textContent=fmt(K,2)+' eV';const W=960,H=300,T=24,B=30;
  const Y=e=>T+(E1+0.4-e)/(E1+0.4)*(H-T-B);const lvl=(x,e,lab,c)=>{el('line',{x1:x,x2:x+170,y1:Y(e),y2:Y(e),stroke:tok(c),'stroke-width':3},svg);txt(svg,x+176,Y(e)+4,lab+' — '+fmt(e,2)+' eV'+(e>0.3?' ('+fmt(e===ET?J.lamT:J.lam1,0)+' nm)':''),{fill:tok('--ink')})};
  lvl(80,0,'S₀','--ink');lvl(80,E1,'S₁','--nu');lvl(560,ET,'T₁','--el');el('line',{x1:560,x2:730,y1:Y(0),y2:Y(0),stroke:tok('--ink'),'stroke-width':3},svg);
  const arr=(x1,y1,x2,y2,c,lab,dash,anc)=>{el('line',{x1,y1,x2,y2,stroke:tok(c),'stroke-width':2,'stroke-dasharray':dash||''},svg);const a=Math.atan2(y2-y1,x2-x1);el('polygon',{points:[x2,y2,x2-9*Math.cos(a-0.4),y2-9*Math.sin(a-0.4),x2-9*Math.cos(a+0.4),y2-9*Math.sin(a+0.4)].join(' '),fill:tok(c)},svg);txt(svg,(x1+x2)/2+(anc==='end'?-8:8),(y1+y2)/2,lab,{fill:tok(c),'text-anchor':anc||'start'})};
  arr(120,Y(0),120,Y(E1)+3,'--accent','absorption','','end');arr(200,Y(E1),200,Y(0)-3,'--nu','fluorescence');
  if(ET>0.05){arr(250,Y(E1),560,Y(ET)-3,'--virt','intersystem crossing','6 5');arr(640,Y(ET),640,Y(0)-3,'--el','phosphorescence','2 4')}
  txt(svg,560,Y(E1)+4,'S₁ − T₁ = 2K = '+fmt(J.K2,2)+' eV',{fill:tok('--ink')})}
// ---------- спектр по данным расчёта ----------
$('bCalc').onclick=spec2;$('cX').onchange=spec2;
async function spec2(){const svg=$('spec2');const msg=$('cMsg'),unit=$('cU').value,xu=$('cX').value,fw=Number($('cW').value.replace(',','.'));
  const rows=$('cIn').value.split(/\n/).map(s=>s.trim()).filter(s=>s).map(s=>s.replace(/,(?=\d)/g,'.').split(/[\s;,\t]+/).map(Number));
  if(!rows.length||rows.some(r=>r.length<2||!(r[0]>0)||!(r[1]>=0))||!(fw>0)){svg.innerHTML='';msg.textContent='Each line needs two numbers: energy (positive) and oscillator strength (non-negative); the width must be positive.';return}
  let Q;try{Q=await QC.api('exc.spectrum',{rows,unit,fw})}catch(e){return}svg.innerHTML='';const tr=Q.tr,emin=Q.emin,emax=Q.emax,pts=Q.pts||[],mx=Q.mx||0;
  if(!(mx>0)){msg.textContent='All oscillator strengths are zero: the transitions are forbidden and there is no absorption spectrum.';return}
  const W=960,H=320,L=56,R=16,T=14,B=42;const xv=e=>xu==='nm'?NM/e:e;let a0=xv(emin),a1=xv(emax);if(a0>a1)[a0,a1]=[a1,a0];
  const X=e=>L+(xv(e)-a0)/(a1-a0)*(W-L-R),Y=v=>T+(1.05-v)/1.05*(H-T-B),fm=Q.fm;
  el('line',{x1:L,x2:W-R,y1:Y(0),y2:Y(0),stroke:tok('--muted')},svg);
  tr.forEach(t=>el('line',{x1:X(t.e),x2:X(t.e),y1:Y(0),y2:Y(t.f/fm),stroke:tok('--el'),'stroke-width':2,opacity:.7},svg));
  el('path',{d:pts.map(([e,v],i)=>(i?'L':'M')+X(e).toFixed(1)+' '+Y(v).toFixed(1)).join(''),fill:'none',stroke:tok('--nu'),'stroke-width':2.4},svg);
  const span=a1-a0,st=xu==='nm'?(span>400?100:span>150?50:span>60?20:10):(span>4?1:span>1.5?0.5:0.2);for(let v=Math.ceil(a0/st)*st;v<=a1+1e-9;v+=st)txt(svg,L+(v-a0)/(a1-a0)*(W-L-R),H-B+16,fmt(v,xu==='nm'?0:1),{'text-anchor':'middle'});
  txt(svg,(L+W-R)/2,H-8,xu==='nm'?'wavelength, nm':'energy, eV',{'text-anchor':'middle'});txt(svg,6,T+6,'rel. intensity');
  const pk=Q.pk;
  msg.innerHTML='Transitions: '+tr.length+'. Envelope maxima: '+pk.map(([e,v,lam])=>'<b>'+fmt(lam,0)+' nm</b> ('+fmt(e,2)+' eV, rel. '+fmt(v,2)+')').join('; ')+'. Weak transitions (small f) are barely visible even if they lie lower in energy: the color and maximum of absorption are set not by the lowest transition but by the most intense one.'}
draw();spec2();matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{draw();spec2()});
