/* SCF page (Atlas v2).  Every matrix, energy and curve comes from the Python
   model quas_atlas.core.scf: scf.run (the whole SCF trajectory for the chosen
   molecule, R, exponents, start, damping, DIIS), scf.scan (RHF/UHF curves),
   scf.zeta (variational curve) and scf.pop (population analysis).  The step
   machine below only walks through the recorded trajectory and draws. */
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const NS='http://www.w3.org/2000/svg';
function el(p,t,a){const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);p.appendChild(e);return e}
const f4=x=>(Math.abs(x)<5e-5?0:x).toFixed(4).replace('.',',').replace('-','−');
const f6=x=>x.toFixed(6).replace('.',',').replace('-','−');
const fe=x=>x<1e-12?'0':(x.toExponential(1).replace('.',',').replace('e-','·10⁻').replace('e+0','').replace(/⁻(\d+)/,(m,d)=>'⁻'+d.split('').map(c=>'⁰¹²³⁴⁵⁶⁷⁸⁹'[+c]).join('')));
const fsig=x=>(x>=0?'+':'−')+Math.abs(x).toFixed(3).replace('.',',');
const MOLS={HeH:{name:'HeH⁺',atoms:[{Z:2,zeta:2.0925,name:'He'},{Z:1,zeta:1.24,name:'H'}],R:1.4632},
            H2:{name:'H₂',atoms:[{Z:1,zeta:1.24,name:'H(1)'},{Z:1,zeta:1.24,name:'H(2)'}],R:1.4}};
const DELTA=1e-6,MAXIT=200;
let S={speed:700,auto:false,mol:'HeH',R:1.4632,guess:'core',damp:0,diis:false,zeta:{},zwho:0,dl:[],Fd:null,dc:null,ghost:null,scan:null,scanKey:'',stage:'init',k:0,P:null,Pold:null,G:null,F:null,eps:null,C:null,hist:[],run:null};
try{const v=+localStorage.getItem('scf-speed');if(v>=150&&v<=1500)S.speed=v}catch(e){}
try{const s=JSON.parse(localStorage.getItem('scf-state')||'null');if(s)['mol','R','guess','damp','diis','zeta','zwho'].forEach(k=>{if(s[k]!=null)S[k]=s[k]})}catch(e){}
function zetaOf(i,mol){mol=mol||S.mol;const z=(S.zeta[mol]||[])[i];return z!=null?z:MOLS[mol].atoms[i].zeta}
function atoms(R){return MOLS[S.mol].atoms.map((a,i)=>({...a,zeta:zetaOf(i),z:i?(R??S.R):0}))}
const getRun=QC.live('scf.run');
async function reset(){stopRun();let T;try{T=await getRun({mol:S.mol,R:S.R,za:zetaOf(0),zb:zetaOf(1),guess:S.guess,damp:S.damp,diis:S.diis})}catch(e){return}
  S.T=T;S.I=T.I;S.stage='init';S.k=0;S.P=null;S.Pold=null;S.G=null;S.F=null;S.eps=null;S.C=null;S.hist=[];S.Fd=null;S.dc=null;S.Corb=null;S.rho=null;
  S.Econv=T.Econv;S.ghost=T.ghost;S.auto=false;
  try{localStorage.setItem('scf-state',JSON.stringify({mol:S.mol,R:S.R,guess:S.guess,damp:S.damp,diis:S.diis,zeta:S.zeta,zwho:S.zwho}))}catch(e){}render()}
/* один шаг схемы */
function step(){if(!S.T)return;
  switch(S.stage){
   case 'init':S.P=S.T.P0;S.rho=S.T.axis.rhoP0;S.stage='guess';break;
   case 'guess':case 'check':{if(S.stage==='check'&&S.hist.length&&S.hist[S.hist.length-1].dP<DELTA){S.stage='done';break}
     if(S.k>=MAXIT){S.stage='done';break}S.k++;const it=S.T.iters[S.k-1];S.G=it.G;S.Fprev=S.F;S.F=it.F;S.Fd=it.Fd;S.dc=it.dc;
     S.stage='F';break}
   case 'F':{const it=S.T.iters[S.k-1];S.epsPrev=S.eps;S.Cprev=S.C;S.eps=it.eps;S.C=it.C;S.Corb=it.orb;S.stage='diag';break}
   case 'diag':{const it=S.T.iters[S.k-1];S.Pold=S.P;S.P=it.P;S.rho=it.rho;
     S.hist.push({k:S.k,E:it.E,dP:it.dP,mDP:it.mDP,eps:S.eps.slice(),q:it.q});S.stage='P';break}
   case 'P':S.stage='check';break;
   case 'done':break}
  render()}
function toCheck(){do step();while(S.stage!=='check'&&S.stage!=='done')}
function iterate(){if(S.stage==='done')return;if(S.stage==='check'||S.stage==='init'||S.stage==='guess'){step()}while(S.stage!=='check'&&S.stage!=='done')step()}
/* автоматический проход цикла: шаг за шагом с интервалом S.speed мс */
const REDUCE=matchMedia('(prefers-reduced-motion: reduce)').matches;
function runBtn(){const b=document.getElementById('bRun');if(!b)return;b.textContent=S.auto?'❚❚ Пауза':(S.stage==='done'?'Пройдено':(S.stage==='init'?'▶ Запустить':'▶ Продолжить'));b.classList.toggle('primary',!S.auto&&S.stage!=='done');b.disabled=S.stage==='done'}
function stopRun(){S.auto=false;if(S.run){clearTimeout(S.run);S.run=null}runBtn()}
function tick(){S.run=null;if(!S.auto)return;step();if(S.stage==='done'){S.auto=false;render();return}S.run=setTimeout(tick,S.speed)}
function play(){if(S.stage==='done')return;S.auto=true;runBtn();if(S.run)clearTimeout(S.run);S.run=setTimeout(tick,Math.min(250,S.speed))}
function runAll(){if(S.auto){stopRun();render()}else play()}
/* ===== отрисовка ===== */
const BOX=[{id:'init',y:10,t:'1. Геометрия и базис',s:'вычислить S, h, (μν|λσ)'},{id:'guess',y:78,t:'2. Начальное приближение P⁽⁰⁾',s:''},
  {id:'F',y:146,t:'3. Построить F(P) = h + G(P)',s:''},{id:'diag',y:214,t:'4. Решить FC = SCε',s:''},{id:'P',y:282,t:'5. Заполнить орбитали,',s:'построить новую P'}];
function drawFlow(){const sv=document.getElementById('flow');sv.innerHTML='';const ink=tok('--ink'),mut=tok('--muted'),acc=tok('--accent'),line=tok('--line');
  const mk=(id,ref)=>{const m=el(sv,'marker',{id,viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:7,markerHeight:7,orient:'auto-start-reverse'});el(m,'path',{d:'M0,0 L10,5 L0,10 z',fill:ref})};
  const defs=el(sv,'defs',{});mk('ar',mut);mk('arA',acc);sv.appendChild(defs);
  const X0=30,W=250;
  BOX.forEach(b=>{const on=S.stage===b.id;el(sv,'rect',{x:X0,y:b.y,width:W,height:50,rx:8,fill:on?tok('--acc-bg'):tok('--panel'),stroke:on?acc:line,'stroke-width':on?2.2:1.2});
    el(sv,'text',{x:X0+12,y:b.y+(b.s?22:30),'font-size':14,fill:ink,'font-weight':on?600:400,'font-family':'Golos Text, sans-serif'}).textContent=b.t;
    if(b.s)el(sv,'text',{x:X0+12,y:b.y+40,'font-size':12.5,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent=b.s});
  for(let i=0;i<4;i++)el(sv,'line',{x1:X0+W/2,y1:BOX[i].y+50,x2:X0+W/2,y2:BOX[i+1].y-2,stroke:mut,'stroke-width':1.5,'marker-end':'url(#ar)'});
  const cy=392,cx=X0+W/2,on=S.stage==='check';
  el(sv,'polygon',{points:`${cx},${cy-34} ${cx+92},${cy} ${cx},${cy+34} ${cx-92},${cy}`,fill:on?tok('--acc-bg'):tok('--panel'),stroke:on?acc:line,'stroke-width':on?2.2:1.2});
  el(sv,'text',{x:cx,y:cy+5,'text-anchor':'middle','font-size':13.5,fill:ink,'font-family':'Golos Text, sans-serif','font-weight':on?600:400}).textContent='‖ΔP‖ < δ ?';
  el(sv,'line',{x1:cx,y1:BOX[4].y+50,x2:cx,y2:cy-36,stroke:mut,'stroke-width':1.5,'marker-end':'url(#ar)'});
  const loopOn=S.stage==='check'&&!(S.hist.length&&S.hist[S.hist.length-1].dP<DELTA);
  el(sv,'path',{d:`M${cx-92},${cy} H10 V${BOX[2].y+25} H${X0-2}`,fill:'none',stroke:loopOn?acc:mut,'stroke-width':loopOn?2.2:1.5,'marker-end':loopOn?'url(#arA)':'url(#ar)'});
  el(sv,'text',{x:16,y:cy-8,'font-size':12.5,fill:tok('--warn'),'font-family':'Golos Text, sans-serif'}).textContent='нет';
  const done=S.stage==='done',dx=X0+W+40;
  el(sv,'line',{x1:cx+92,y1:cy,x2:dx-2,y2:cy,stroke:mut,'stroke-width':1.5,'marker-end':'url(#ar)'});
  el(sv,'text',{x:cx+100,y:cy-8,'font-size':12.5,fill:tok('--ok'),'font-family':'Golos Text, sans-serif'}).textContent='да';
  el(sv,'rect',{x:dx,y:cy-28,width:122,height:56,rx:8,fill:done?tok('--ok-bg'):tok('--panel'),stroke:done?tok('--ok'):line,'stroke-width':done?2.2:1.2});
  el(sv,'text',{x:dx+61,y:cy-6,'text-anchor':'middle','font-size':14,fill:ink,'font-weight':done?600:400,'font-family':'Golos Text, sans-serif'}).textContent='Сошлось:';
  el(sv,'text',{x:dx+61,y:cy+14,'text-anchor':'middle','font-size':12.5,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent='E, орбитали';
  el(sv,'text',{x:X0+W+18,y:BOX[2].y+30,'font-size':13,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent='итерация';
  el(sv,'text',{x:X0+W+18,y:BOX[2].y+56,'font-size':28,fill:ink,'font-family':'JetBrains Mono, monospace'}).textContent='k = '+S.k}
function mhtml(name,note,M,prev,hot){if(!M)return '';const n=M.length;
  const cells=M.flat().map((x,i)=>{const ch=prev&&Math.abs(x-prev.flat()[i])>5e-5;return '<span'+(ch?' class="ch"':'')+'>'+f4(x)+'</span>'}).join('');
  return '<div class="mbox'+(hot?' hot':'')+'"><div class="name">'+name+(note?'<small>'+note+'</small>':'')+'</div><span class="m" style="grid-template-columns:repeat('+n+',auto)">'+cells+'</span></div>'}
function vhtml(name,note,v,prev,hot){if(!v)return '';const cells=v.map((x,i)=>{const ch=prev&&Math.abs(x-prev[i])>5e-5;return '<span'+(ch?' class="ch"':'')+'>'+f4(x)+'</span>'}).join('');
  return '<div class="mbox'+(hot?' hot':'')+'"><div class="name">'+name+(note?'<small>'+note+'</small>':'')+'</div><span class="m" style="grid-template-columns:repeat('+v.length+',auto)">'+cells+'</span></div>'}
function drawMats(){const st=S.stage,I=S.I,at=atoms();let h='';const nm=at.map(a=>a.name).join(', ');
  if(st==='init')h=mhtml('S','перекрывание',I.S,null,true)+mhtml('h','T + V ядер',I.H,null,true);
  else if(st==='guess')h=mhtml('P⁽⁰⁾','матрица плотности',S.P,null,true);
  else if(st==='F')h=mhtml('P','с прошлого шага',S.P,null,false)+mhtml('G(P)','J − ½K',S.G,null,!S.Fd)+mhtml('F','= h + G',S.F,S.Fprev,!S.Fd)+(S.Fd?mhtml('F<sub>DIIS</sub>','= '+S.dc.map((c,i)=>(i&&c>=0?'+ ':'')+f4(c)+'·F⁽'+(S.k-S.dc.length+1+i)+'⁾').join(' '),S.Fd,null,true):'');
  else if(st==='diag')h=mhtml(S.Fd?'F<sub>DIIS</sub>':'F','',S.Fd||S.F,null,false)+mhtml('C','столбцы φ₁, φ₂',S.C,S.Cprev,true)+vhtml('ε','орбитальные энергии',S.eps,S.epsPrev,true);
  else h=mhtml('P'+(st==='P'?'<sub>стар</sub>':''),st==='P'?'':'текущая',st==='P'?S.Pold:S.P,null,false)+(st==='P'?mhtml('P<sub>нов</sub>',S.damp>0&&!S.diis?'с демпфированием':'= 2·c·cᵀ',S.P,S.Pold,true):'')+(S.C?mhtml('C','',S.C,null,false)+vhtml('ε','',S.eps,null,false):'');
  document.getElementById('mats').innerHTML=h;document.getElementById('matTitle').textContent='Матрицы текущего шага (ат. ед.; строки и столбцы — базисные функции '+nm+')';
  const last=S.hist[S.hist.length-1];let kv='';
  if(last){const q=last.q;kv='<span>E = <b>'+f6(last.E)+'</b></span><span>‖ΔP‖ = <b>'+fe(last.dP)+'</b></span><span>заряды по Малликену: '+at.map((a,i)=>a.name+' <b>'+fsig(q[i])+'</b>').join(', ')+'</span>'}
  document.getElementById('kv').innerHTML=kv;
  const e=(i,j,k,l)=>I.ERI[i][j][k][l];
  document.getElementById('ints').innerHTML=mhtml('S','',I.S)+mhtml('h','',I.H)+'<div class="mbox"><div class="name">(μν|λσ)</div><div class="val" style="line-height:1.8">(11|11) = '+f4(e(0,0,0,0))+'<br>(22|22) = '+f4(e(1,1,1,1))+'<br>(11|22) = '+f4(e(0,0,1,1))+'<br>(21|11) = '+f4(e(1,0,0,0))+'<br>(21|22) = '+f4(e(1,0,1,1))+'<br>(21|21) = '+f4(e(1,0,1,0))+'</div></div><div class="mbox"><div class="name">V<sub>яд</sub> = <span class=fr><span>Z<sub>A</sub>Z<sub>B</sub></span><span>R</span></span></div><div class="val">'+f4(I.Vnn)+'</div></div>'}
function drawStatus(){const st=S.stage,last=S.hist[S.hist.length-1];const at=atoms();let t='';
  if(st==='init')t='<b>1.</b> Заданы геометрия и базис. Матрица перекрывания S, остовный гамильтониан h и двухэлектронные интегралы считаются один раз — в ходе итераций они не меняются.';
  else if(st==='guess')t='<b>2.</b> '+(S.guess==='core'?'P⁽⁰⁾ = 0: на первой итерации электроны не отталкивают друг друга, F = h («гамильтониан остова»).':'Оба электрона помещены на базисную функцию '+(S.guess==='A'?at[0].name:at[1].name)+' — намеренно грубое начало.');
  else if(st==='F')t='<b>3.</b> Строим F = h + G(P). G — среднее поле остальных электронов, и оно зависит от P, то есть от ответа, который мы ищем. Поэтому уравнения решают итерациями. Красным отмечено то, что изменилось.'+(S.Fd?' <b>DIIS:</b> вместо последней F берём смесь двух последних матриц Фока с такими весами c, чтобы ошибка FPS − SPF (она равна нулю только при самосогласовании) обратилась в ноль. Диагонализуем уже F<sub>DIIS</sub>.':S.diis?' DIIS начнёт работать, когда накопятся две матрицы Фока, — с третьей итерации.':'');
  else if(st==='diag')t='<b>4.</b> Решаем обобщённую задачу на собственные значения FC = SCε: получаем орбитали φ₁, φ₂ (столбцы C) и их энергии ε₁ = '+f4(S.eps[0])+', ε₂ = '+f4(S.eps[1])+'.';
  else if(st==='P')t='<b>5.</b> Оба электрона — на нижнюю орбиталь φ₁: P<sub>μν</sub> = 2c<sub>μ1</sub>c<sub>ν1</sub>'+(S.damp>0&&!S.diis?', затем смешиваем со старой матрицей (α = '+S.damp.toFixed(2).replace('.',',')+')':'')+'. Энергия с новой плотностью: E = '+f6(last.E)+'.';
  else if(st==='check')t=last.dP<DELTA?'‖ΔP‖ = '+fe(last.dP)+' < δ — плотность больше не меняется, цикл завершается.':'Проверка: ‖ΔP‖ = '+fe(last.dP)+' > δ = 10⁻⁶ — поле ещё не самосогласовано, возвращаемся к шагу 3 с новой P.';
  else if(st==='done')t=S.k>=MAXIT&&last.dP>=DELTA?'За '+MAXIT+' итераций не сошлось — уменьшите демпфирование.':'<b>Самосогласование достигнуто за '+S.k+' '+(S.k%10===1&&S.k%100!==11?'итерацию':(S.k%10>=2&&S.k%10<=4&&(S.k%100<10||S.k%100>=20))?'итерации':'итераций')+'.</b> E = '+f6(last.E)+' ат. ед., ε₁ = '+f4(last.eps[0])+', ε₂ = '+f4(last.eps[1])+'. Поле, которое создают электроны на орбиталях, порождает те же самые орбитали.';
  document.getElementById('status').innerHTML=t;
  document.getElementById('bStep').disabled=st==='done';document.getElementById('bIter').disabled=st==='done';runBtn()}
function drawOrb(){const sv=document.getElementById('orb');sv.innerHTML='';const ink=tok('--ink'),mut=tok('--muted'),acc=tok('--accent');const at=atoms();
  const L=40,T=12,W=486,H=230;const z0=-2.2,z1=S.R+2.2;const AX=S.T.axis,zs=AX.z;
  const curves=S.C?S.Corb:[];
  const rho=S.P?S.rho:AX.rho0;
  const basisCurves=S.C?[]:[AX.chi0,AX.chi1];
  const all=[...curves.flat(),...rho,...basisCurves.flat(),0];let lo=Math.min(...all),hi=Math.max(...all);lo=Math.min(lo,-0.2);hi=hi*1.08;
  const sx=z=>L+(z-z0)/(z1-z0)*W,sy=v=>T+H-(v-lo)/(hi-lo)*H;
  el(sv,'line',{x1:L,x2:L+W,y1:sy(0),y2:sy(0),stroke:tok('--line'),'stroke-width':1.2});
  const pts=a=>a.map((v,i)=>sx(zs[i]).toFixed(1)+','+sy(v).toFixed(1)).join(' ');
  el(sv,'polygon',{points:sx(z0)+','+sy(0)+' '+pts(rho)+' '+sx(z1)+','+sy(0),fill:tok('--rho'),stroke:tok('--rho-l'),'stroke-width':1.2});
  if(S.C){el(sv,'polyline',{points:pts(curves[1]),fill:'none',stroke:tok('--virt'),'stroke-width':2,'stroke-dasharray':'6 4'});el(sv,'polyline',{points:pts(curves[0]),fill:'none',stroke:acc,'stroke-width':2.6})}
  else basisCurves.forEach((c,k)=>el(sv,'polyline',{points:pts(c),fill:'none',stroke:mut,'stroke-width':1.6,'stroke-dasharray':'3 3'}));
  at.forEach(a=>{const x=sx(a.z);el(sv,'line',{x1:x,x2:x,y1:T,y2:T+H,stroke:mut,'stroke-width':1,'stroke-dasharray':'2 4'});el(sv,'circle',{cx:x,cy:sy(0),r:5,fill:ink});
    el(sv,'text',{x:x,y:T+H+18,'text-anchor':'middle','font-size':13,fill:ink,'font-family':'Golos Text, sans-serif','font-weight':600}).textContent=a.name});
  el(sv,'text',{x:L+W,y:T+H+36,'text-anchor':'end','font-size':13,'font-style':'italic','font-family':'PT Serif, serif',fill:mut}).textContent='z, бор';
  if(!S.C)el(sv,'text',{x:L+8,y:T+16,'font-size':12.5,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent='Пока показаны базисные функции χ (пунктир) — орбиталей ещё нет'}
function drawConv(){const sv=document.getElementById('conv');sv.innerHTML='';const ink=tok('--ink'),mut=tok('--muted'),acc=tok('--accent'),warn=tok('--warn');
  const L=62,T=12,W=420,H=220;const hs=S.hist;const kmax=Math.max(8,hs.length,S.ghost?S.ghost.length:0);const sx=k=>L+(k-0.5)/(kmax)*W;
  const Es=hs.map(h=>h.E).concat([S.Econv]);let lo=Math.min(...Es),hi=Math.max(...Es);if(hi-lo<1e-3){hi+=5e-4;lo-=5e-4}const pad=(hi-lo)*0.08;lo-=pad;hi+=pad;
  const sy=v=>T+H-(v-lo)/(hi-lo)*H;const ly=v=>T+H-(v+8)/9*H; /* lg от −8 до 1 */
  for(let i=0;i<=4;i++){const v=lo+(hi-lo)*i/4;el(sv,'line',{x1:L,x2:L+W,y1:sy(v),y2:sy(v),stroke:tok('--line'),'stroke-width':.7});
    el(sv,'text',{x:L-6,y:sy(v)+4,'text-anchor':'end','font-size':11.5,fill:acc,'font-family':'JetBrains Mono, monospace'}).textContent=v.toFixed(3).replace('.',',').replace('-','−')}
  [-8,-6,-4,-2,0].forEach(v=>el(sv,'text',{x:L+W+6,y:ly(v)+4,'font-size':11.5,fill:warn,'font-family':'JetBrains Mono, monospace'}).textContent=String(v).replace('-','−'));
  el(sv,'line',{x1:L,x2:L+W,y1:sy(S.Econv),y2:sy(S.Econv),stroke:acc,'stroke-width':1,'stroke-dasharray':'2 3',opacity:.7});
  el(sv,'line',{x1:L,x2:L+W,y1:ly(-6),y2:ly(-6),stroke:mut,'stroke-width':1.2,'stroke-dasharray':'6 4'});
  const step=Math.ceil(kmax/12);for(let k=1;k<=kmax;k+=step)el(sv,'text',{x:sx(k),y:T+H+16,'text-anchor':'middle','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=k;
  el(sv,'text',{x:L+W,y:T+H+32,'text-anchor':'end','font-size':13,'font-style':'italic','font-family':'PT Serif, serif',fill:mut}).textContent='итерация k';
  if(hs.length){el(sv,'polyline',{points:hs.map(h=>sx(h.k)+','+sy(h.E)).join(' '),fill:'none',stroke:acc,'stroke-width':2});
    const dl=hs.filter(h=>h.dP>0);el(sv,'polyline',{points:dl.map(h=>sx(h.k)+','+ly(Math.max(-8,Math.log10(h.dP)))).join(' '),fill:'none',stroke:warn,'stroke-width':2});
    if(S.ghost){const g=S.ghost.filter(h=>h.dP>0&&h.k<=kmax);el(sv,'polyline',{points:g.map(h=>sx(h.k)+','+ly(Math.max(-8,Math.log10(h.dP)))).join(' '),fill:'none',stroke:warn,'stroke-width':1.6,'stroke-dasharray':'2 3',opacity:.6})}
    hs.forEach(h=>{el(sv,'circle',{cx:sx(h.k),cy:sy(h.E),r:3,fill:acc});if(h.dP>0)el(sv,'circle',{cx:sx(h.k),cy:ly(Math.max(-8,Math.log10(h.dP))),r:3,fill:warn})})}}
function drawTable(){const at=atoms();document.getElementById('thq').innerHTML='заряды '+at.map(a=>a.name).join(' / ');
  const done=S.stage==='done';document.getElementById('tab').innerHTML=S.hist.map((h,i)=>'<tr class="'+(i===S.hist.length-1?(done?'done':'cur'):'')+'"><td>'+h.k+'</td><td>'+f6(h.E)+'</td><td>'+fe(Math.abs(h.E-S.Econv))+'</td><td>'+f4(h.eps[0])+'</td><td>'+f4(h.eps[1])+'</td><td>'+h.q.map(fsig).join(' / ')+'</td><td>'+fe(h.dP)+'</td></tr>').join('')||'<tr><td colspan="7" style="text-align:left;font-family:var(--f-body);color:var(--muted)">Итераций ещё не было.</td></tr>';
  document.getElementById('note').innerHTML=(S.mol==='HeH'?'Базис STO-3G с показателями ζ(He) = '+String(zetaOf(0)).replace('.',',')+' и ζ(H) = '+String(zetaOf(1)).replace('.',',')+(S.zeta.HeH?' (изменены в разделе о вариационном принципе; стандартные — 2,0925 и 1,24, как в учебнике Сабо и Остлунда).':', как в учебнике Сабо и Остлунда: при R = 1,4632 бор получается E = −2,86066 ат. ед.')+' На первой итерации (F = h, отталкивания ещё нет) оба электрона почти целиком у гелия. Как только в F появляется отталкивание, часть плотности уходит к водороду — заряд на H заметно падает (при R = 1,4632 бор — с +0,84 до +0,53).'+'':(S.zeta.H2?'Показатель ζ(H) = '+String(zetaOf(0)).replace('.',',')+' (изменён ниже, стандартный — 1,24). ':'')+'H₂ симметрична, и коэффициенты МО фиксирует симметрия: из симметричного начала (P = 0) расчёт сходится за одну итерацию. Попробуйте несимметричное начало «оба электрона у H(1)».')+
   (S.diis?' С DIIS сходимость сверхлинейная: на графике lg ‖ΔP‖ не прямая, а ломается вниз. В базисе из двух функций у ошибки DIIS всего одна независимая компонента, поэтому хватает двух последних шагов; в настоящих программах их хранят 6–10.':' Без DIIS сходимость линейная: ‖ΔP‖ на каждой итерации уменьшается примерно в одно и то же число раз — на графике это прямая. Растяните связь — сходимость замедлится; включите демпфирование — тоже. Пунктиром показан тот же расчёт с DIIS.');
  document.getElementById('ghostLab').textContent=S.diis?'тот же расчёт без DIIS':'тот же расчёт с DIIS';drawLog()}
let zTimer=null;function drawMO(){const sv=document.getElementById('mo');sv.innerHTML='';const ink=tok('--ink'),mut=tok('--muted'),acc=tok('--accent');const at=atoms();
  const F=S.F||S.I.H;const a=[F[0][0],F[1][1]];const e=S.eps;const vals=[...a,...(e||[])];let lo=Math.min(...vals),hi=Math.max(...vals);const pad=Math.max(0.15,(hi-lo)*0.12);lo-=pad;hi+=pad;
  const T=14,H=160,sy=v=>T+H-(v-lo)/(hi-lo)*H;const lev=(x,y,w,c,lab,val,anchor)=>{el(sv,'line',{x1:x-w/2,x2:x+w/2,y1:y,y2:y,stroke:c,'stroke-width':3,'stroke-linecap':'round'});
    el(sv,'text',{x:anchor==='end'?x-w/2-8:x+w/2+8,y:y+4,'text-anchor':anchor||'start','font-size':12.5,fill:ink,'font-family':'Golos Text, sans-serif'}).textContent=lab+' '+f4(val)};
  const xa=70,xb=390,xm=210;[[xa,a[0],at[0].name],[xb,a[1],at[1].name]].forEach(([x,v,n])=>{const y=sy(v);el(sv,'line',{x1:x-30,x2:x+30,y1:y,y2:y,stroke:mut,'stroke-width':3,'stroke-linecap':'round'});
    el(sv,'text',{x,y:y-7,'text-anchor':'middle','font-size':12,fill:ink,'font-family':'Golos Text, sans-serif'}).textContent='χ('+n+') '+f4(v)});
  if(e){[0,1].forEach(i=>{const y=sy(e[i]);[[xa+30,sy(a[0])],[xb-30,sy(a[1])]].forEach(([x,yy])=>el(sv,'line',{x1:x,y1:yy,x2:i?xm+45:xm-45,y2:y,stroke:mut,'stroke-width':1,'stroke-dasharray':'3 3'}));
      lev(xm,y,90,i?tok('--virt'):acc,i?'ε₂':'ε₁',e[i],'start')});
    const y1=sy(e[0]);[[-12,'↑'],[12,'↓']].forEach(([dx,ch])=>el(sv,'text',{x:xm+dx,y:y1+7,'text-anchor':'middle','font-size':20,fill:acc,'font-weight':700}).textContent=ch)}
  else el(sv,'text',{x:xm,y:T+H/2,'text-anchor':'middle','font-size':13,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent='орбитали появятся после шага 4';
  el(sv,'text',{x:6,y:T+H+22,'font-size':11.5,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent='энергии в ат. ед.; '+(S.F?'по краям — F₁₁ и F₂₂ текущей итерации':'по краям — h₁₁ и h₂₂ (до первой F)')}
function render(){if(!S.T)return;drawMO();drawFlow();drawMats();drawStatus();drawOrb();drawConv();drawTable();renderControls();drawScan();drawPop();clearTimeout(zTimer);zTimer=setTimeout(drawZeta,180)}
function chips(id,items,cur,set){const box=document.getElementById(id);box.innerHTML='';items.forEach(([v,l])=>{const b=document.createElement('button');b.type='button';b.className='chip';b.innerHTML=l;b.setAttribute('aria-pressed',v===cur);b.onclick=()=>set(v);box.appendChild(b)})}
function renderControls(){const at=atoms();chips('mol',Object.entries(MOLS).map(([k,m])=>[k,m.name]),S.mol,v=>{S.mol=v;S.R=MOLS[v].R;document.getElementById('R').value=S.R;renderZetaControls();reset()});
  chips('guess',[['core','P = 0 (только остов)'],['A','оба электрона у '+at[0].name],['B','оба электрона у '+at[1].name]],S.guess,v=>{S.guess=v;reset()});
  chips('acc',[[false,'простые итерации'],[true,'DIIS']],S.diis,v=>{S.diis=v;reset()});document.getElementById('dampRow').style.opacity=S.diis?.45:1;document.getElementById('damp').disabled=S.diis;
  document.getElementById('accHint').textContent=S.diis?'Пулаи (1980); демпфирование отключено':'';
  document.getElementById('Rv').textContent=S.R.toFixed(2).replace('.',',')+' бор = '+(S.R*0.529177).toFixed(3).replace('.',',')+' Å';document.getElementById('dampv').textContent=S.damp.toFixed(2).replace('.',',')}
document.getElementById('R').value=S.R;document.getElementById('damp').value=S.damp;
document.getElementById('R').oninput=e=>{S.R=+e.target.value;reset()};
document.getElementById('damp').oninput=e=>{S.damp=+e.target.value;reset()};
document.getElementById('bStep').onclick=()=>{stopRun();step()};
document.getElementById('bIter').onclick=()=>{stopRun();iterate();render()};
{const sp=document.getElementById('spd');const setSp=()=>{S.speed=1650-(+sp.value);document.getElementById('spdv').textContent=(S.speed/1000).toFixed(2).replace('.',',')+' с на шаг'};sp.value=1650-S.speed;setSp();sp.oninput=()=>{setSp();try{localStorage.setItem('scf-speed',S.speed)}catch(e){}}}
document.getElementById('bRun').onclick=runAll;
document.getElementById('bReset').onclick=reset;

/* ===== вывод в стиле программы ===== */
function drawLog(){const hs=S.hist,at=atoms();const pad=(x,n)=>String(x).padStart(n);const L=[];
  L.push('                     --------------');L.push('                     SCF ITERATIONS');L.push('                     --------------');
  L.push('ITER       Energy          Delta-E          Max-DP       RMS-DP'+(S.diis?'    ':''));
  hs.forEach((h,i)=>{const dE=i?h.E-hs[i-1].E:0;L.push(pad(i,3)+'  '+pad(h.E.toFixed(10),14)+'  '+pad(dE.toFixed(12),16)+'  '+pad(h.mDP.toFixed(7),11)+'  '+pad(h.dP.toFixed(7),11)+(S.diis&&h.k>=3?'  DIIS':''))});
  if(!hs.length)L.push('  (итераций ещё не было)');
  const last=hs[hs.length-1];
  if(S.stage==='done'&&last&&last.dP<DELTA){const ev=27.211386;
    L.push('','               *****************************************************','               *                     SUCCESS                       *',
      '               *           SCF CONVERGED AFTER '+pad(hs.length,3)+' CYCLES          *','               *****************************************************','',
      '----------------','TOTAL SCF ENERGY','----------------','',
      'Total Energy       :  '+pad(last.E.toFixed(8),16)+' Eh  '+pad((last.E*ev).toFixed(5),14)+' eV','',
      'Nuclear Repulsion  :  '+pad(S.I.Vnn.toFixed(8),16)+' Eh','Electronic Energy  :  '+pad((last.E-S.I.Vnn).toFixed(8),16)+' Eh','',
      '----------------','ORBITAL ENERGIES','----------------','','  NO   OCC          E(Eh)            E(eV)');
    last.eps.forEach((e,i)=>L.push(pad(i,4)+'   '+(i?'0.0000':'2.0000')+'  '+pad(e.toFixed(6),14)+'  '+pad((e*ev).toFixed(4),15)));
    L.push('','-----------------------','MULLIKEN ATOMIC CHARGES','-----------------------');
    at.forEach((a,i)=>L.push(pad(i,4)+' '+(a.name.replace(/[()\d]/g,'')+' ').slice(0,2)+':'+pad(last.q[i].toFixed(6),12)));
    L.push('Sum of atomic charges:'+pad(last.q.reduce((x,y)=>x+y,0).toFixed(7),12))}
  else if(last)L.push('','  … ‖ΔP‖ = '+last.dP.toExponential(2)+' > 1e-6, итерации продолжаются');
  document.getElementById('log').textContent=L.join('\n')}
/* ===== скан E(R): RHF и UHF ===== */
const RS=Array.from({length:109},(_,i)=>0.6+i*0.05);
function atomsAt(R){return atoms(R)}
const getScan=QC.live('scf.scan');
async function computeScan(){const key=S.mol+'|'+zetaOf(0)+'|'+zetaOf(1);if(S.scanKey===key&&S.scan)return S.scan;
  const d=await getScan({mol:S.mol,za:zetaOf(0),zb:zetaOf(1)});if(S.mol+'|'+zetaOf(0)+'|'+zetaOf(1)!==key)throw QC.STALE;
  S.scan={pts:JSON.parse(JSON.stringify(d.pts)),lim:d.lim,limA:d.limA,zat:d.zat,re:d.re,reE:d.reE};S.scanKey=key;return S.scan}
async function drawScan(){let sc;try{sc=await computeScan()}catch(e){return}const pts=sc.pts;const sv=document.getElementById('scan');sv.innerHTML='';const ink=tok('--ink'),mut=tok('--muted'),acc=tok('--accent'),uc=tok('--rho-l');
  const L=58,T=26,W=460,H=224;const eMin=Math.min(...pts.map(p=>Math.min(p.rhf,p.uhf)));const lo=eMin-0.04,hi=sc.lim+(S.mol==='H2'?0.42:0.3);
  const sx=R=>L+(R-0.6)/(6-0.6)*W,sy=e=>T+H-(e-lo)/(hi-lo)*H;
  const cp=el(sv,'clipPath',{id:'clipS'});el(cp,'rect',{x:L,y:T,width:W,height:H});
  for(let i=0;i<=4;i++){const e=lo+(hi-lo)*i/4;el(sv,'line',{x1:L,x2:L+W,y1:sy(e),y2:sy(e),stroke:tok('--line'),'stroke-width':.7});el(sv,'text',{x:L-6,y:sy(e)+4,'text-anchor':'end','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=e.toFixed(2).replace('.',',').replace('-','−')}
  [1,2,3,4,5,6].forEach(R=>el(sv,'text',{x:sx(R),y:T+H+16,'text-anchor':'middle','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=R);
  el(sv,'text',{x:L+W,y:T+H+32,'text-anchor':'end','font-size':13,'font-style':'italic','font-family':'PT Serif, serif',fill:mut}).textContent='R, бор';
  el(sv,'text',{x:L-50,y:12,'font-size':12,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent='E, ат. ед.';
  const g=el(sv,'g',{'clip-path':'url(#clipS)'});
  el(g,'line',{x1:L,x2:L+W,y1:sy(sc.lim),y2:sy(sc.lim),stroke:mut,'stroke-width':1.3,'stroke-dasharray':'6 4'});
  el(g,'polyline',{points:pts.map(p=>sx(p.R)+','+sy(p.uhf)).join(' '),fill:'none',stroke:uc,'stroke-width':2.4});
  el(g,'polyline',{points:pts.map(p=>sx(p.R)+','+sy(p.rhf)).join(' '),fill:'none',stroke:acc,'stroke-width':2.4,'stroke-dasharray':S.mol==='H2'?'none':'7 5'});
  const pm=pts.reduce((a,b)=>b.rhf<a.rhf?b:a);el(sv,'line',{x1:sx(pm.R),x2:sx(pm.R),y1:sy(pm.rhf),y2:T+H,stroke:acc,'stroke-width':1,'stroke-dasharray':'2 3'});
  el(sv,'text',{x:sx(pm.R)+5,y:T+H-6,'font-size':12,fill:acc,'font-family':'Golos Text, sans-serif'}).textContent='R_e';
  if(S.R>=0.6&&S.R<=6){const I=S.I;const er=S.Econv;el(sv,'circle',{cx:sx(S.R),cy:sy(er),r:5.5,fill:ink});}
  const cf=pts.find(p=>p.s2>1e-3);
  /* ⟨S²⟩ */const s2=document.getElementById('s2');s2.innerHTML='';const L2=58,T2=26,W2=460,H2=104;const sx2=R=>L2+(R-0.6)/(6-0.6)*W2,sy2=v=>T2+H2-v*H2;
  [0,0.5,1].forEach(v=>{el(s2,'line',{x1:L2,x2:L2+W2,y1:sy2(v),y2:sy2(v),stroke:tok('--line'),'stroke-width':.7});el(s2,'text',{x:L2-6,y:sy2(v)+4,'text-anchor':'end','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=String(v).replace('.',',')});
  el(s2,'polyline',{points:pts.map(p=>sx2(p.R)+','+sy2(Math.max(0,p.s2))).join(' '),fill:'none',stroke:uc,'stroke-width':2.2});
  if(cf){el(s2,'line',{x1:sx2(cf.R),x2:sx2(cf.R),y1:T2,y2:T2+H2,stroke:mut,'stroke-dasharray':'3 3'});el(s2,'text',{x:sx2(cf.R)+5,y:T2+14,'font-size':12,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent='симметрия нарушается: R ≈ '+cf.R.toFixed(2).replace('.',',')+' бор'}
  [1,2,3,4,5,6].forEach(R=>el(s2,'text',{x:sx2(R),y:T2+H2+16,'text-anchor':'middle','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=R);
  el(s2,'text',{x:L2-50,y:12,'font-size':12,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent='⟨S²⟩ UHF';
  const last=pts[pts.length-1];
  if(!S.reKey||S.reKey!==S.scanKey){S.reVal=sc.re;S.reE=sc.reE;S.reKey=S.scanKey}
  const Re=S.reVal;pm.rhf=S.reE;
  document.getElementById('scanKv').innerHTML='<span>R<sub>e</sub> (RHF) = <b>'+Re.toFixed(2).replace('.',',')+' бор = '+(Re*0.529177).toFixed(3).replace('.',',')+' Å</b></span><span>E<sub>min</sub> = <b>'+f6(pm.rhf)+'</b></span><span>предел R → ∞: <b>'+f6(sc.lim)+'</b></span><span>свободные атомы (свои ζ = '+sc.zat.toFixed(2).replace('.',',')+'): <b>'+f6(sc.limA)+'</b></span><span>D<sub>e</sub> = <b>'+(sc.limA-pm.rhf).toFixed(4).replace('.',',')+' ат. ед. = '+((sc.limA-pm.rhf)*27.2114).toFixed(2).replace('.',',')+' эВ</b> (эксперимент: '+(S.mol==='H2'?'4,75':'около 2,0')+' эВ)</span>'+(S.mol==='H2'?'<span>RHF при R = 6 бор выше предела на <b>'+(last.rhf-sc.lim).toFixed(3).replace('.',',')+' ат. ед.</b></span>':'');
  document.getElementById('scanIntro').innerHTML='Тот же расчёт при каждом R от 0,6 до 6 бор, но двумя способами: RHF (оба электрона на одной пространственной орбитали) и UHF (орбитали для α и β свои; начинаем с α у одного атома, β — у другого). Это первая поверхность потенциальной энергии; в настоящих расчётах такие кривые и поверхности строят программы вроде ASE.';
  document.getElementById('scanText').innerHTML=S.mol==='H2'?'<b>H₂: провал RHF при диссоциации.</b> Вблизи равновесия решения совпадают. '+(cf?'После R ≈ '+cf.R.toFixed(2).replace('.',',')+' бор':'При растяжении')+' UHF выгоднее развести электроны α и β к разным атомам: симметрия решения нарушается, а ⟨S²⟩ растёт от 0 до 1 — это смесь синглета и триплета, спиновое загрязнение. UHF выходит точно на энергию двух атомов H. RHF держит оба электрона на одной связывающей орбитали, а такая функция на 50 % состоит из ионной структуры H⁺H⁻ — поэтому кривая уходит далеко выше правильного предела. Описать разрыв связи и не потерять спин позволяют многоконфигурационные методы.<br><br>Предел кривой при R → ∞ получен с теми же показателями ζ, что у молекулы, а для свободных атомов они неоптимальны: '+(S.mol==='H2'?'у атома H лучший показатель ζ ≈ 1, а не 1,24':'у атома He лучший показатель ζ ≈ 1,69, а не 2,09')+'. Поэтому D<sub>e</sub> отсчитана от атомов с их собственными ζ — иначе энергия связи вышла бы завышенной (артефакт фиксированного базиса).':'<b>HeH⁺: RHF и UHF совпадают при всех R.</b> При диссоциации оба электрона остаются на гелии (He + H⁺), и одной замкнутой оболочки достаточно — симметрия решения не нарушается, ⟨S²⟩ = 0. Провал RHF возникает, когда связь рвётся «пополам» на два радикала, как в H₂ — переключите молекулу.<br><br>Предел кривой при R → ∞ получен с теми же показателями ζ, что у молекулы, а для свободных атомов они неоптимальны: '+(S.mol==='H2'?'у атома H лучший показатель ζ ≈ 1, а не 1,24':'у атома He лучший показатель ζ ≈ 1,69, а не 2,09')+'. Поэтому D<sub>e</sub> отсчитана от атомов с их собственными ζ — иначе энергия связи вышла бы завышенной (артефакт фиксированного базиса).'}
/* ===== вариационный принцип по ζ ===== */
function zIdx(){return S.mol==='H2'?[0,1]:[S.zwho]}
const getZeta=QC.live('scf.zeta');
let zCache={key:'',pts:null,zm:null};
async function drawZeta(){const who=zIdx();
  const other=S.mol==='H2'?'':String(zetaOf(1-S.zwho));const ck=S.mol+'|'+S.R+'|'+other+'|'+who.join();
  if(zCache.key!==ck){let d;try{d=await getZeta({mol:S.mol,R:S.R,za:zetaOf(0),zb:zetaOf(1),who})}catch(e){return}zCache={key:ck,pts:d.pts,zm:d.zm,Em:d.Em}}
  const sv=document.getElementById('zchart');sv.innerHTML='';const ink=tok('--ink'),mut=tok('--muted'),acc=tok('--accent');
  const L=58,T=10,W=460,H=180;const pts=zCache.pts;const lo=zCache.Em-0.02;const hi=Math.min(Math.max(...pts.map(p=>p.E)),zCache.Em+(S.mol==='H2'?0.5:1.2));
  const sx=z=>L+(z-0.6)/3*W,sy=e=>T+H-(e-lo)/(hi-lo)*H;const cp=el(sv,'clipPath',{id:'clipZ'});el(cp,'rect',{x:L,y:T,width:W,height:H});
  for(let i=0;i<=3;i++){const e=lo+(hi-lo)*i/3;el(sv,'line',{x1:L,x2:L+W,y1:sy(e),y2:sy(e),stroke:tok('--line'),'stroke-width':.7});el(sv,'text',{x:L-6,y:sy(e)+4,'text-anchor':'end','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=e.toFixed(2).replace('.',',').replace('-','−')}
  [1,1.5,2,2.5,3,3.5].forEach(z=>el(sv,'text',{x:sx(z),y:T+H+16,'text-anchor':'middle','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=String(z).replace('.',','));
  el(sv,'text',{x:L+W,y:T+H+32,'text-anchor':'end','font-size':14,'font-style':'italic','font-family':'PT Serif, serif',fill:mut}).textContent='ζ';
  const g=el(sv,'g',{'clip-path':'url(#clipZ)'});el(g,'polyline',{points:pts.map(p=>sx(p.z)+','+sy(p.E)).join(' '),fill:'none',stroke:mut,'stroke-width':2.2});
  const std=MOLS[S.mol].atoms[who[0]].zeta;el(sv,'line',{x1:sx(std),x2:sx(std),y1:T,y2:T+H,stroke:mut,'stroke-dasharray':'2 3'});el(sv,'text',{x:sx(std)+4,y:T+12,'font-size':11.5,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent='STO-3G';
  el(sv,'circle',{cx:sx(zCache.zm),cy:sy(zCache.Em),r:5,fill:'none',stroke:tok('--ok'),'stroke-width':2});
  const zc=zetaOf(who[0]);el(sv,'circle',{cx:sx(zc),cy:sy(S.Econv),r:6,fill:acc});
  const nm=S.mol==='H2'?'ζ обоих атомов H':'ζ('+MOLS[S.mol].atoms[S.zwho].name+')';
  document.getElementById('zetav').textContent=zc.toFixed(2).replace('.',',');
  document.getElementById('zText').innerHTML='Меняем '+nm+' при R = '+S.R.toFixed(2).replace('.',',')+' бор. Сейчас ζ = '+zc.toFixed(2).replace('.',',')+': E = '+f6(S.Econv)+'. <b>Минимум при ζ = '+zCache.zm.toFixed(3).replace('.',',')+'</b> (E = '+f6(zCache.Em)+'): любая другая функция даёт энергию выше — это и есть вариационный принцип. '+
    'Стандартное значение STO-3G ('+std.toFixed(S.mol==='H2'||S.zwho===1?2:4).replace('.',',')+') подобрано один раз для многих молекул сразу, поэтому в конкретной молекуле и при конкретном R оно не обязано быть оптимальным. Подвигайте R: при сжатии молекулы оптимальное ζ растёт — функции «стягиваются» к ядрам. В настоящих базисах вместо подгонки ζ берут несколько функций разной ширины.'}
function renderZetaControls(){const items=S.mol==='H2'?[[0,'оба атома H']]:[[0,'ζ(He)'],[1,'ζ(H)']];if(S.mol==='H2')S.zwho=0;
  chips('zwho',items,S.zwho,v=>{S.zwho=v;renderZetaControls();drawZeta()});document.getElementById('zeta').value=zetaOf(zIdx()[0])}
function setZeta(z){const arr=[zetaOf(0),zetaOf(1)];zIdx().forEach(i=>arr[i]=z);S.zeta[S.mol]=arr;reset()}
document.getElementById('zeta').oninput=e=>setZeta(+e.target.value);
document.getElementById('zStd').onclick=()=>{delete S.zeta[S.mol];reset();renderZetaControls()};
document.getElementById('zMin').onclick=()=>{setZeta(+zCache.zm.toFixed(3));renderZetaControls()};
document.getElementById('scan').addEventListener('click',e=>{const sv=e.currentTarget,r=sv.getBoundingClientRect();const R=0.6+((e.clientX-r.left)/r.width*540-58)/460*5.4;if(R<0.6||R>6)return;S.R=Math.round(R*100)/100;document.getElementById('R').value=S.R;reset()});
renderZetaControls();
reset();
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',render);
new MutationObserver(render).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});

/* ---------- анализ заселённостей ---------- */

const getPop=QC.live('scf.pop');
async function drawPop(){let PD;try{PD=await getPop({mol:S.mol,R:S.R,za:zetaOf(0),zb:zetaOf(1)})}catch(e){return}const at=atoms(),p=PD.p,fmt3=x=>(Math.abs(x)<5e-4?0:x).toFixed(3).replace('.',',').replace('-','−');const ink=tok('--ink'),mut=tok('--muted'),acc=tok('--accent'),alt=tok('--rho-l'),vir=tok('--virt'),soft=tok('--soft'),line=tok('--line');
  /* столбики: 2 электрона */
  let sv=document.getElementById('popBars');sv.innerHTML='';const x0=130,W=380,sx=W/2,tx=(x,y,t,o={})=>{const e=el(sv,'text',Object.assign({x,y,'font-size':12.5,fill:ink,'font-family':'Golos Text, sans-serif'},o));e.textContent=t;return e};
  const bar=(y,segs,label)=>{tx(8,y+20,label,{'font-size':13,'font-weight':600});let x=x0;segs.forEach(s=>{const w=Math.max(0,s.v*sx);el(sv,'rect',{x,y,width:w,height:30,fill:s.c,stroke:tok('--panel'),'stroke-width':1});if(w>34)tx(x+w/2,y+20,fmt3(s.v),{'text-anchor':'middle','font-family':'JetBrains Mono, monospace','font-size':12,fill:s.ink||'#fff'});x+=w})};
  const cA=acc,cB=alt,cO=vir;
  bar(30,[{v:p.net[0],c:cA},{v:p.op,c:cO},{v:p.net[1],c:cB}],'разбиение N');
  [[24,31],[59,66]].forEach(([y1,y2])=>el(sv,'line',{x1:x0+(p.net[0]+p.op/2)*sx,x2:x0+(p.net[0]+p.op/2)*sx,y1,y2,stroke:ink,'stroke-width':2}));
  tx(x0+(p.net[0]+p.op/2)*sx,20,'Малликен делит пополам',{'text-anchor':'middle','font-size':11.5,fill:mut});
  bar(95,[{v:p.gm[0],c:cA},{v:p.gm[1],c:cB}],'Малликен');
  bar(150,[{v:p.gl[0],c:cA},{v:p.gl[1],c:cB}],'Лёвдин');
  const lg=[[cA,'на '+at[0].name],[cO,'перекрывание 2P₁₂S₁₂'],[cB,'на '+at[1].name]];let lx=x0;lg.forEach(([c,t])=>{el(sv,'rect',{x:lx,y:194,width:12,height:10,fill:c,rx:2});const e=tx(lx+17,203,t,{'font-size':11.5,fill:mut});lx+=17+t.length*6.6+16});
  [0,0.5,1,1.5,2].forEach(v=>{el(sv,'line',{x1:x0+v*sx,x2:x0+v*sx,y1:184,y2:188,stroke:mut,'stroke-width':1})});
  /* таблица */
  document.getElementById('popTab').innerHTML='<table class="mtab poptab"><thead><tr><th></th><th>'+at[0].name+'</th><th>'+at[1].name+'</th></tr></thead><tbody>'+
    '<tr><td>P<sub>μμ</sub> (собственная)</td><td>'+fmt3(p.net[0])+'</td><td>'+fmt3(p.net[1])+'</td></tr>'+
    '<tr><td>(PS)<sub>μμ</sub> — Малликен</td><td>'+fmt3(p.gm[0])+'</td><td>'+fmt3(p.gm[1])+'</td></tr>'+
    '<tr><td>(S<sup>½</sup>PS<sup>½</sup>)<sub>μμ</sub> — Лёвдин</td><td>'+fmt3(p.gl[0])+'</td><td>'+fmt3(p.gl[1])+'</td></tr>'+
    '<tr><td>заряд по Малликену</td><td>'+fsig(p.qm[0])+'</td><td>'+fsig(p.qm[1])+'</td></tr>'+
    '<tr><td>заряд по Лёвдину</td><td>'+fsig(p.ql[0])+'</td><td>'+fsig(p.ql[1])+'</td></tr>'+
    '<tr><td>заселённость перекрывания 2P₁₂S₁₂</td><td colspan="2" style="text-align:center">'+fmt3(p.op)+'</td></tr>'+
    '<tr><td>порядок связи по Майеру (PS)₁₂(PS)₂₁</td><td colspan="2" style="text-align:center">'+fmt3(p.mayer)+'</td></tr></tbody></table>';
  /* зависимость от R */
  sv=document.getElementById('popR');sv.innerHTML='';const C=PD.curve,het=S.mol==='HeH';const L=54,Rr=520,T=14,B=222;
  const ser=het?[[d=>d.qm[1],acc,'',"q(H) по Малликену"],[d=>d.ql[1],alt,'6 4',"q(H) по Лёвдину"],[d=>d.mayer,vir,'2 3','порядок связи по Майеру'],[d=>d.op,mut,'','заселённость перекрывания']]
                :[[d=>d.op,acc,'','заселённость перекрывания 2P₁₂S₁₂'],[d=>d.mayer,vir,'2 3','порядок связи по Майеру'],[d=>d.net[0],alt,'6 4','P₁₁ — собственная заселённость H(1)']];
  const ymin=0,ymax=1.1,X=r=>L+(r-0.6)/(6-0.6)*(Rr-L),Y=v=>B-(v-ymin)/(ymax-ymin)*(B-T);
  for(let v=0;v<=1.001;v+=0.25){el(sv,'line',{x1:L,x2:Rr,y1:Y(v),y2:Y(v),stroke:line,'stroke-width':1});el(sv,'text',{x:L-6,y:Y(v)+4,'text-anchor':'end','font-size':11.5,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent=v.toFixed(2).replace('.',',')}
  [1,2,3,4,5,6].forEach(r=>{el(sv,'text',{x:X(r),y:B+16,'text-anchor':'middle','font-size':11.5,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent=r});
  el(sv,'text',{x:(L+Rr)/2,y:B+34,'text-anchor':'middle','font-size':12,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent='R, бор';
  ser.forEach(([f,c,da])=>{el(sv,'path',{d:C.map((d,i)=>(i?'L':'M')+X(d.R).toFixed(1)+','+Y(f(d)).toFixed(1)).join(''),fill:'none',stroke:c,'stroke-width':2.2,'stroke-dasharray':da||'none'})});
  if(S.R>=0.6&&S.R<=6){el(sv,'line',{x1:X(S.R),x2:X(S.R),y1:T,y2:B,stroke:mut,'stroke-width':1,'stroke-dasharray':'3 3'});ser.forEach(([f,c])=>el(sv,'circle',{cx:X(S.R),cy:Y(f(p)),r:4,fill:c}))}
  document.getElementById('popLeg').innerHTML=ser.map(([f,c,da,t])=>'<span><i class="sw" style="border-color:'+c+';border-top-style:'+(da?(da==='2 3'?'dotted':'dashed'):'solid')+'"></i>'+t+'</span>').join('');
  let t;if(het){const sm=Math.sign(p.qm[0]-p.qm[1]),sl=Math.sign(p.ql[0]-p.ql[1]);
    t='Заряды: по Малликену He '+fsig(p.qm[0])+', H '+fsig(p.qm[1])+'; по Лёвдину He '+fsig(p.ql[0])+', H '+fsig(p.ql[1])+'. '+
      (sm!==sl?'<b>Схемы расходятся даже в том, какой атом положительнее.</b> Заряд на атоме — не наблюдаемая величина: он зависит от способа разбиения и от базиса. ':'Обе схемы согласны в знаке разности зарядов, но не в величине. ')+
      'С ростом R электронная пара уходит на He (продукты — He + H⁺), заряд H стремится к +1, а перекрывание и порядок связи — к нулю.'}
  else t='В H₂ заряды обеих схем равны нулю по симметрии. Заселённость перекрывания '+fmt3(p.op)+' падает с ростом R вместе с S₁₂, а порядок связи по Майеру в RHF остаётся равным 1 при любом R: волновая функция RHF всегда описывает одну двухэлектронную связь — та же проблема, что и неправильная диссоциация RHF.';
  document.getElementById('popText').innerHTML=t}
