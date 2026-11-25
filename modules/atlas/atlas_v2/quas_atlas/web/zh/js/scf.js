/* SCF page (Atlas v2).  Every matrix, energy and curve comes from the Python
   model quas_atlas.core.scf: scf.run (the whole SCF trajectory for the chosen
   molecule, R, exponents, start, damping, DIIS), scf.scan (RHF/UHF curves),
   scf.zeta (variational curve) and scf.pop (population analysis).  The step
   machine below only walks through the recorded trajectory and draws. */
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const NS='http://www.w3.org/2000/svg';
function el(p,t,a){const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);p.appendChild(e);return e}
const f4=x=>(Math.abs(x)<5e-5?0:x).toFixed(4).replace('-','−');
const f6=x=>x.toFixed(6).replace('-','−');
const fe=x=>x<1e-12?'0':(x.toExponential(1).replace('e-','·10⁻').replace('e+0','').replace(/⁻(\d+)/,(m,d)=>'⁻'+d.split('').map(c=>'⁰¹²³⁴⁵⁶⁷⁸⁹'[+c]).join('')));
const fsig=x=>(x>=0?'+':'−')+Math.abs(x).toFixed(3);
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
function runBtn(){const b=document.getElementById('bRun');if(!b)return;b.textContent=S.auto?'❚❚ 暂停':(S.stage==='done'?'已完成':(S.stage==='init'?'▶ 开始':'▶ 继续'));b.classList.toggle('primary',!S.auto&&S.stage!=='done');b.disabled=S.stage==='done'}
function stopRun(){S.auto=false;if(S.run){clearTimeout(S.run);S.run=null}runBtn()}
function tick(){S.run=null;if(!S.auto)return;step();if(S.stage==='done'){S.auto=false;render();return}S.run=setTimeout(tick,S.speed)}
function play(){if(S.stage==='done')return;S.auto=true;runBtn();if(S.run)clearTimeout(S.run);S.run=setTimeout(tick,Math.min(250,S.speed))}
function runAll(){if(S.auto){stopRun();render()}else play()}
/* ===== отрисовка ===== */
const BOX=[{id:'init',y:10,t:'1. 几何构型与基组',s:'计算 S, h, (μν|λσ)'},{id:'guess',y:78,t:'2. 初始猜测 P⁽⁰⁾',s:''},
  {id:'F',y:146,t:'3. 构建 F(P) = h + G(P)',s:''},{id:'diag',y:214,t:'4. 求解 FC = SCε',s:''},{id:'P',y:282,t:'5. 填充轨道，',s:'构建新的 P'}];
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
  el(sv,'text',{x:16,y:cy-8,'font-size':12.5,fill:tok('--warn'),'font-family':'Golos Text, sans-serif'}).textContent='否';
  const done=S.stage==='done',dx=X0+W+40;
  el(sv,'line',{x1:cx+92,y1:cy,x2:dx-2,y2:cy,stroke:mut,'stroke-width':1.5,'marker-end':'url(#ar)'});
  el(sv,'text',{x:cx+100,y:cy-8,'font-size':12.5,fill:tok('--ok'),'font-family':'Golos Text, sans-serif'}).textContent='是';
  el(sv,'rect',{x:dx,y:cy-28,width:122,height:56,rx:8,fill:done?tok('--ok-bg'):tok('--panel'),stroke:done?tok('--ok'):line,'stroke-width':done?2.2:1.2});
  el(sv,'text',{x:dx+61,y:cy-6,'text-anchor':'middle','font-size':14,fill:ink,'font-weight':done?600:400,'font-family':'Golos Text, sans-serif'}).textContent='已收敛：';
  el(sv,'text',{x:dx+61,y:cy+14,'text-anchor':'middle','font-size':12.5,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent='E，轨道';
  el(sv,'text',{x:X0+W+18,y:BOX[2].y+30,'font-size':13,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent='迭代';
  el(sv,'text',{x:X0+W+18,y:BOX[2].y+56,'font-size':28,fill:ink,'font-family':'JetBrains Mono, monospace'}).textContent='k = '+S.k}
function mhtml(name,note,M,prev,hot){if(!M)return '';const n=M.length;
  const cells=M.flat().map((x,i)=>{const ch=prev&&Math.abs(x-prev.flat()[i])>5e-5;return '<span'+(ch?' class="ch"':'')+'>'+f4(x)+'</span>'}).join('');
  return '<div class="mbox'+(hot?' hot':'')+'"><div class="name">'+name+(note?'<small>'+note+'</small>':'')+'</div><span class="m" style="grid-template-columns:repeat('+n+',auto)">'+cells+'</span></div>'}
function vhtml(name,note,v,prev,hot){if(!v)return '';const cells=v.map((x,i)=>{const ch=prev&&Math.abs(x-prev[i])>5e-5;return '<span'+(ch?' class="ch"':'')+'>'+f4(x)+'</span>'}).join('');
  return '<div class="mbox'+(hot?' hot':'')+'"><div class="name">'+name+(note?'<small>'+note+'</small>':'')+'</div><span class="m" style="grid-template-columns:repeat('+v.length+',auto)">'+cells+'</span></div>'}
function drawMats(){const st=S.stage,I=S.I,at=atoms();let h='';const nm=at.map(a=>a.name).join(', ');
  if(st==='init')h=mhtml('S','重叠',I.S,null,true)+mhtml('h','T + V 核',I.H,null,true);
  else if(st==='guess')h=mhtml('P⁽⁰⁾','密度矩阵',S.P,null,true);
  else if(st==='F')h=mhtml('P','来自上一步',S.P,null,false)+mhtml('G(P)','J − ½K',S.G,null,!S.Fd)+mhtml('F','= h + G',S.F,S.Fprev,!S.Fd)+(S.Fd?mhtml('F<sub>DIIS</sub>','= '+S.dc.map((c,i)=>(i&&c>=0?'+ ':'')+f4(c)+'·F⁽'+(S.k-S.dc.length+1+i)+'⁾').join(' '),S.Fd,null,true):'');
  else if(st==='diag')h=mhtml(S.Fd?'F<sub>DIIS</sub>':'F','',S.Fd||S.F,null,false)+mhtml('C','列 φ₁, φ₂',S.C,S.Cprev,true)+vhtml('ε','轨道能量',S.eps,S.epsPrev,true);
  else h=mhtml('P'+(st==='P'?'<sub>旧</sub>':''),st==='P'?'':'当前',st==='P'?S.Pold:S.P,null,false)+(st==='P'?mhtml('P<sub>新</sub>',S.damp>0&&!S.diis?'带阻尼':'= 2·c·cᵀ',S.P,S.Pold,true):'')+(S.C?mhtml('C','',S.C,null,false)+vhtml('ε','',S.eps,null,false):'');
  document.getElementById('mats').innerHTML=h;document.getElementById('matTitle').textContent='当前步的矩阵（原子单位；行和列为基函数 '+nm+')';
  const last=S.hist[S.hist.length-1];let kv='';
  if(last){const q=last.q;kv='<span>E = <b>'+f6(last.E)+'</b></span><span>‖ΔP‖ = <b>'+fe(last.dP)+'</b></span><span>马利肯电荷：'+at.map((a,i)=>a.name+' <b>'+fsig(q[i])+'</b>').join(', ')+'</span>'}
  document.getElementById('kv').innerHTML=kv;
  const e=(i,j,k,l)=>I.ERI[i][j][k][l];
  document.getElementById('ints').innerHTML=mhtml('S','',I.S)+mhtml('h','',I.H)+'<div class="mbox"><div class="name">(μν|λσ)</div><div class="val" style="line-height:1.8">(11|11) = '+f4(e(0,0,0,0))+'<br>(22|22) = '+f4(e(1,1,1,1))+'<br>(11|22) = '+f4(e(0,0,1,1))+'<br>(21|11) = '+f4(e(1,0,0,0))+'<br>(21|22) = '+f4(e(1,0,1,1))+'<br>(21|21) = '+f4(e(1,0,1,0))+'</div></div><div class="mbox"><div class="name">V<sub>核</sub> = <span class=fr><span>Z<sub>A</sub>Z<sub>B</sub></span><span>R</span></span></div><div class="val">'+f4(I.Vnn)+'</div></div>'}
function drawStatus(){const st=S.stage,last=S.hist[S.hist.length-1];const at=atoms();let t='';
  if(st==='init')t='<b>1.</b> 给定几何结构和基组。重叠矩阵 S、核心哈密顿量 h 和双电子积分只需计算一次——迭代过程中它们保持不变。';
  else if(st==='guess')t='<b>2.</b> '+(S.guess==='core'?'P⁽⁰⁾ = 0：第一次迭代时电子之间没有排斥，F = h（“核心哈密顿量”）。':'两个电子都放在基函数 '+(S.guess==='A'?at[0].name:at[1].name)+' 上——故意选择的粗糙起点。');
  else if(st==='F')t='<b>3.</b> 构建 F = h + G(P)。G 是其余电子的平均场，它依赖于 P，也就是依赖于我们要求的答案。因此方程要通过迭代求解。红色标出的是发生变化的部分。'+(S.Fd?' <b>DIIS：</b>不直接使用最后的 F，而是取最后两个 Fock 矩阵的组合，权重 c 的选取使误差 FPS − SPF（仅在自洽时为零）变为零。随后对角化的是 F<sub>DIIS</sub>。':S.diis?' 积累两个 Fock 矩阵后 DIIS 才开始起作用——即从第三次迭代开始。':'');
  else if(st==='diag')t='<b>4.</b> 求解广义本征值问题 FC = SCε：得到轨道 φ₁、φ₂（C 的列）及其能量 ε₁ = '+f4(S.eps[0])+', ε₂ = '+f4(S.eps[1])+'.';
  else if(st==='P')t='<b>5.</b> 两个电子都放在较低的轨道 φ₁ 上：P<sub>μν</sub> = 2c<sub>μ1</sub>c<sub>ν1</sub>'+(S.damp>0&&!S.diis?'，然后与旧矩阵混合（α = '+S.damp.toFixed(2)+')':'')+'。用新密度计算的能量：E = '+f6(last.E)+'.';
  else if(st==='check')t=last.dP<DELTA?'‖ΔP‖ = '+fe(last.dP)+' < δ——密度不再变化，循环结束。':'检查：‖ΔP‖ = '+fe(last.dP)+' > δ = 10⁻⁶——场尚未自洽，用新的 P 返回第 3 步。';
  else if(st==='done')t=S.k>=MAXIT&&last.dP>=DELTA?'经过 '+MAXIT+' 次迭代仍未收敛——请减小阻尼。':'<b>达到自洽，共用 '+S.k+' '+(S.k%10===1&&S.k%100!==11?'次迭代':(S.k%10>=2&&S.k%10<=4&&(S.k%100<10||S.k%100>=20))?'次迭代':'次迭代')+'.</b> E = '+f6(last.E)+' 原子单位，ε₁ = '+f4(last.eps[0])+', ε₂ = '+f4(last.eps[1])+'。电子在轨道上产生的场又生成了完全相同的轨道。';
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
  el(sv,'text',{x:L+W,y:T+H+36,'text-anchor':'end','font-size':13,'font-style':'italic','font-family':'PT Serif, serif',fill:mut}).textContent='z, 玻尔';
  if(!S.C)el(sv,'text',{x:L+8,y:T+16,'font-size':12.5,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent='目前只显示基函数 χ（虚线）——还没有轨道'}
function drawConv(){const sv=document.getElementById('conv');sv.innerHTML='';const ink=tok('--ink'),mut=tok('--muted'),acc=tok('--accent'),warn=tok('--warn');
  const L=62,T=12,W=420,H=220;const hs=S.hist;const kmax=Math.max(8,hs.length,S.ghost?S.ghost.length:0);const sx=k=>L+(k-0.5)/(kmax)*W;
  const Es=hs.map(h=>h.E).concat([S.Econv]);let lo=Math.min(...Es),hi=Math.max(...Es);if(hi-lo<1e-3){hi+=5e-4;lo-=5e-4}const pad=(hi-lo)*0.08;lo-=pad;hi+=pad;
  const sy=v=>T+H-(v-lo)/(hi-lo)*H;const ly=v=>T+H-(v+8)/9*H; /* lg от −8 до 1 */
  for(let i=0;i<=4;i++){const v=lo+(hi-lo)*i/4;el(sv,'line',{x1:L,x2:L+W,y1:sy(v),y2:sy(v),stroke:tok('--line'),'stroke-width':.7});
    el(sv,'text',{x:L-6,y:sy(v)+4,'text-anchor':'end','font-size':11.5,fill:acc,'font-family':'JetBrains Mono, monospace'}).textContent=v.toFixed(3).replace('-','−')}
  [-8,-6,-4,-2,0].forEach(v=>el(sv,'text',{x:L+W+6,y:ly(v)+4,'font-size':11.5,fill:warn,'font-family':'JetBrains Mono, monospace'}).textContent=String(v).replace('-','−'));
  el(sv,'line',{x1:L,x2:L+W,y1:sy(S.Econv),y2:sy(S.Econv),stroke:acc,'stroke-width':1,'stroke-dasharray':'2 3',opacity:.7});
  el(sv,'line',{x1:L,x2:L+W,y1:ly(-6),y2:ly(-6),stroke:mut,'stroke-width':1.2,'stroke-dasharray':'6 4'});
  const step=Math.ceil(kmax/12);for(let k=1;k<=kmax;k+=step)el(sv,'text',{x:sx(k),y:T+H+16,'text-anchor':'middle','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=k;
  el(sv,'text',{x:L+W,y:T+H+32,'text-anchor':'end','font-size':13,'font-style':'italic','font-family':'PT Serif, serif',fill:mut}).textContent='迭代 k';
  if(hs.length){el(sv,'polyline',{points:hs.map(h=>sx(h.k)+','+sy(h.E)).join(' '),fill:'none',stroke:acc,'stroke-width':2});
    const dl=hs.filter(h=>h.dP>0);el(sv,'polyline',{points:dl.map(h=>sx(h.k)+','+ly(Math.max(-8,Math.log10(h.dP)))).join(' '),fill:'none',stroke:warn,'stroke-width':2});
    if(S.ghost){const g=S.ghost.filter(h=>h.dP>0&&h.k<=kmax);el(sv,'polyline',{points:g.map(h=>sx(h.k)+','+ly(Math.max(-8,Math.log10(h.dP)))).join(' '),fill:'none',stroke:warn,'stroke-width':1.6,'stroke-dasharray':'2 3',opacity:.6})}
    hs.forEach(h=>{el(sv,'circle',{cx:sx(h.k),cy:sy(h.E),r:3,fill:acc});if(h.dP>0)el(sv,'circle',{cx:sx(h.k),cy:ly(Math.max(-8,Math.log10(h.dP))),r:3,fill:warn})})}}
function drawTable(){const at=atoms();document.getElementById('thq').innerHTML='电荷 '+at.map(a=>a.name).join(' / ');
  const done=S.stage==='done';document.getElementById('tab').innerHTML=S.hist.map((h,i)=>'<tr class="'+(i===S.hist.length-1?(done?'done':'cur'):'')+'"><td>'+h.k+'</td><td>'+f6(h.E)+'</td><td>'+fe(Math.abs(h.E-S.Econv))+'</td><td>'+f4(h.eps[0])+'</td><td>'+f4(h.eps[1])+'</td><td>'+h.q.map(fsig).join(' / ')+'</td><td>'+fe(h.dP)+'</td></tr>').join('')||'<tr><td colspan="7" style="text-align:left;font-family:var(--f-body);color:var(--muted)">尚未进行迭代。</td></tr>';
  document.getElementById('note').innerHTML=(S.mol==='HeH'?'STO-3G 基组，指数 ζ(He) = '+String(zetaOf(0))+' 和 ζ(H) = '+String(zetaOf(1))+(S.zeta.HeH?'（已在变分原理一节中修改；标准值为 2.0925 和 1.24，与 Szabo 和 Ostlund 的教科书相同）。':'，与 Szabo 和 Ostlund 的教科书相同：R = 1.4632 玻尔时得到 E = −2.86066 原子单位。')+' 第一次迭代时（F = h，尚无排斥），两个电子几乎全部在氦上。一旦 F 中出现排斥，部分密度就转移到氢上——H 上的电荷明显下降（R = 1.4632 玻尔时从 +0.84 降到 +0.53）。'+'':(S.zeta.H2?'指数 ζ(H) = '+String(zetaOf(0))+'（已在下方修改，标准值为 1.24）。':'')+'H₂ 是对称的，MO 系数由对称性决定：从对称的初始猜测（P = 0）出发，计算一次迭代即收敛。试试不对称的初始猜测“两个电子都在 H(1) 上”。')+
   (S.diis?' 使用 DIIS 时收敛是超线性的：图中的 lg ‖ΔP‖ 不是直线，而是向下折弯。在两个函数的基组中，DIIS 误差只有一个独立分量，因此最后两步就足够；实际程序中会保存 6–10 步。':' 不用 DIIS 时收敛是线性的：‖ΔP‖ 每次迭代大约减小相同的倍数——在图上是一条直线。拉长化学键，收敛会变慢；开启阻尼也一样。虚线表示使用 DIIS 的同一计算。');
  document.getElementById('ghostLab').textContent=S.diis?'不用 DIIS 的同一计算':'使用 DIIS 的同一计算';drawLog()}
let zTimer=null;function drawMO(){const sv=document.getElementById('mo');sv.innerHTML='';const ink=tok('--ink'),mut=tok('--muted'),acc=tok('--accent');const at=atoms();
  const F=S.F||S.I.H;const a=[F[0][0],F[1][1]];const e=S.eps;const vals=[...a,...(e||[])];let lo=Math.min(...vals),hi=Math.max(...vals);const pad=Math.max(0.15,(hi-lo)*0.12);lo-=pad;hi+=pad;
  const T=14,H=160,sy=v=>T+H-(v-lo)/(hi-lo)*H;const lev=(x,y,w,c,lab,val,anchor)=>{el(sv,'line',{x1:x-w/2,x2:x+w/2,y1:y,y2:y,stroke:c,'stroke-width':3,'stroke-linecap':'round'});
    el(sv,'text',{x:anchor==='end'?x-w/2-8:x+w/2+8,y:y+4,'text-anchor':anchor||'start','font-size':12.5,fill:ink,'font-family':'Golos Text, sans-serif'}).textContent=lab+' '+f4(val)};
  const xa=70,xb=390,xm=210;[[xa,a[0],at[0].name],[xb,a[1],at[1].name]].forEach(([x,v,n])=>{const y=sy(v);el(sv,'line',{x1:x-30,x2:x+30,y1:y,y2:y,stroke:mut,'stroke-width':3,'stroke-linecap':'round'});
    el(sv,'text',{x,y:y-7,'text-anchor':'middle','font-size':12,fill:ink,'font-family':'Golos Text, sans-serif'}).textContent='χ('+n+') '+f4(v)});
  if(e){[0,1].forEach(i=>{const y=sy(e[i]);[[xa+30,sy(a[0])],[xb-30,sy(a[1])]].forEach(([x,yy])=>el(sv,'line',{x1:x,y1:yy,x2:i?xm+45:xm-45,y2:y,stroke:mut,'stroke-width':1,'stroke-dasharray':'3 3'}));
      lev(xm,y,90,i?tok('--virt'):acc,i?'ε₂':'ε₁',e[i],'start')});
    const y1=sy(e[0]);[[-12,'↑'],[12,'↓']].forEach(([dx,ch])=>el(sv,'text',{x:xm+dx,y:y1+7,'text-anchor':'middle','font-size':20,fill:acc,'font-weight':700}).textContent=ch)}
  else el(sv,'text',{x:xm,y:T+H/2,'text-anchor':'middle','font-size':13,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent='轨道将在第 4 步后出现';
  el(sv,'text',{x:6,y:T+H+22,'font-size':11.5,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent='能量单位为原子单位；'+(S.F?'两侧为当前迭代的 F₁₁ 和 F₂₂':'两侧为 h₁₁ 和 h₂₂（第一个 F 之前）')}
function render(){if(!S.T)return;drawMO();drawFlow();drawMats();drawStatus();drawOrb();drawConv();drawTable();renderControls();drawScan();drawPop();clearTimeout(zTimer);zTimer=setTimeout(drawZeta,180)}
function chips(id,items,cur,set){const box=document.getElementById(id);box.innerHTML='';items.forEach(([v,l])=>{const b=document.createElement('button');b.type='button';b.className='chip';b.innerHTML=l;b.setAttribute('aria-pressed',v===cur);b.onclick=()=>set(v);box.appendChild(b)})}
function renderControls(){const at=atoms();chips('mol',Object.entries(MOLS).map(([k,m])=>[k,m.name]),S.mol,v=>{S.mol=v;S.R=MOLS[v].R;document.getElementById('R').value=S.R;renderZetaControls();reset()});
  chips('guess',[['core','P = 0（仅原子实）'],['A','两个电子都在 '+at[0].name],['B','两个电子都在 '+at[1].name]],S.guess,v=>{S.guess=v;reset()});
  chips('acc',[[false,'简单迭代'],[true,'DIIS']],S.diis,v=>{S.diis=v;reset()});document.getElementById('dampRow').style.opacity=S.diis?.45:1;document.getElementById('damp').disabled=S.diis;
  document.getElementById('accHint').textContent=S.diis?'普莱（1980）；阻尼已关闭':'';
  document.getElementById('Rv').textContent=S.R.toFixed(2)+' 玻尔 = '+(S.R*0.529177).toFixed(3)+' Å';document.getElementById('dampv').textContent=S.damp.toFixed(2)}
document.getElementById('R').value=S.R;document.getElementById('damp').value=S.damp;
document.getElementById('R').oninput=e=>{S.R=+e.target.value;reset()};
document.getElementById('damp').oninput=e=>{S.damp=+e.target.value;reset()};
document.getElementById('bStep').onclick=()=>{stopRun();step()};
document.getElementById('bIter').onclick=()=>{stopRun();iterate();render()};
{const sp=document.getElementById('spd');const setSp=()=>{S.speed=1650-(+sp.value);document.getElementById('spdv').textContent=(S.speed/1000).toFixed(2)+' 秒/步'};sp.value=1650-S.speed;setSp();sp.oninput=()=>{setSp();try{localStorage.setItem('scf-speed',S.speed)}catch(e){}}}
document.getElementById('bRun').onclick=runAll;
document.getElementById('bReset').onclick=reset;

/* ===== вывод в стиле программы ===== */
function drawLog(){const hs=S.hist,at=atoms();const pad=(x,n)=>String(x).padStart(n);const L=[];
  L.push('                     --------------');L.push('                     SCF ITERATIONS');L.push('                     --------------');
  L.push('ITER       Energy          Delta-E          Max-DP       RMS-DP'+(S.diis?'    ':''));
  hs.forEach((h,i)=>{const dE=i?h.E-hs[i-1].E:0;L.push(pad(i,3)+'  '+pad(h.E.toFixed(10),14)+'  '+pad(dE.toFixed(12),16)+'  '+pad(h.mDP.toFixed(7),11)+'  '+pad(h.dP.toFixed(7),11)+(S.diis&&h.k>=3?'  DIIS':''))});
  if(!hs.length)L.push('  （尚未进行迭代）');
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
  else if(last)L.push('','  … ‖ΔP‖ = '+last.dP.toExponential(2)+' > 1e-6，迭代继续');
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
  for(let i=0;i<=4;i++){const e=lo+(hi-lo)*i/4;el(sv,'line',{x1:L,x2:L+W,y1:sy(e),y2:sy(e),stroke:tok('--line'),'stroke-width':.7});el(sv,'text',{x:L-6,y:sy(e)+4,'text-anchor':'end','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=e.toFixed(2).replace('-','−')}
  [1,2,3,4,5,6].forEach(R=>el(sv,'text',{x:sx(R),y:T+H+16,'text-anchor':'middle','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=R);
  el(sv,'text',{x:L+W,y:T+H+32,'text-anchor':'end','font-size':13,'font-style':'italic','font-family':'PT Serif, serif',fill:mut}).textContent='R，玻尔';
  el(sv,'text',{x:L-50,y:12,'font-size':12,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent='E, 原子单位';
  const g=el(sv,'g',{'clip-path':'url(#clipS)'});
  el(g,'line',{x1:L,x2:L+W,y1:sy(sc.lim),y2:sy(sc.lim),stroke:mut,'stroke-width':1.3,'stroke-dasharray':'6 4'});
  el(g,'polyline',{points:pts.map(p=>sx(p.R)+','+sy(p.uhf)).join(' '),fill:'none',stroke:uc,'stroke-width':2.4});
  el(g,'polyline',{points:pts.map(p=>sx(p.R)+','+sy(p.rhf)).join(' '),fill:'none',stroke:acc,'stroke-width':2.4,'stroke-dasharray':S.mol==='H2'?'none':'7 5'});
  const pm=pts.reduce((a,b)=>b.rhf<a.rhf?b:a);el(sv,'line',{x1:sx(pm.R),x2:sx(pm.R),y1:sy(pm.rhf),y2:T+H,stroke:acc,'stroke-width':1,'stroke-dasharray':'2 3'});
  el(sv,'text',{x:sx(pm.R)+5,y:T+H-6,'font-size':12,fill:acc,'font-family':'Golos Text, sans-serif'}).textContent='R_e';
  if(S.R>=0.6&&S.R<=6){const I=S.I;const er=S.Econv;el(sv,'circle',{cx:sx(S.R),cy:sy(er),r:5.5,fill:ink});}
  const cf=pts.find(p=>p.s2>1e-3);
  /* ⟨S²⟩ */const s2=document.getElementById('s2');s2.innerHTML='';const L2=58,T2=26,W2=460,H2=104;const sx2=R=>L2+(R-0.6)/(6-0.6)*W2,sy2=v=>T2+H2-v*H2;
  [0,0.5,1].forEach(v=>{el(s2,'line',{x1:L2,x2:L2+W2,y1:sy2(v),y2:sy2(v),stroke:tok('--line'),'stroke-width':.7});el(s2,'text',{x:L2-6,y:sy2(v)+4,'text-anchor':'end','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=String(v)});
  el(s2,'polyline',{points:pts.map(p=>sx2(p.R)+','+sy2(Math.max(0,p.s2))).join(' '),fill:'none',stroke:uc,'stroke-width':2.2});
  if(cf){el(s2,'line',{x1:sx2(cf.R),x2:sx2(cf.R),y1:T2,y2:T2+H2,stroke:mut,'stroke-dasharray':'3 3'});el(s2,'text',{x:sx2(cf.R)+5,y:T2+14,'font-size':12,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent='对称性破缺：R ≈ '+cf.R.toFixed(2)+' 玻尔'}
  [1,2,3,4,5,6].forEach(R=>el(s2,'text',{x:sx2(R),y:T2+H2+16,'text-anchor':'middle','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=R);
  el(s2,'text',{x:L2-50,y:12,'font-size':12,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent='⟨S²⟩ UHF';
  const last=pts[pts.length-1];
  if(!S.reKey||S.reKey!==S.scanKey){S.reVal=sc.re;S.reE=sc.reE;S.reKey=S.scanKey}
  const Re=S.reVal;pm.rhf=S.reE;
  document.getElementById('scanKv').innerHTML='<span>R<sub>e</sub> (RHF) = <b>'+Re.toFixed(2)+' 玻尔 = '+(Re*0.529177).toFixed(3)+' Å</b></span><span>E<sub>min</sub> = <b>'+f6(pm.rhf)+'</b></span><span>R → ∞ 极限：<b>'+f6(sc.lim)+'</b></span><span>自由原子（各自的 ζ = '+sc.zat.toFixed(2)+'): <b>'+f6(sc.limA)+'</b></span><span>D<sub>e</sub> = <b>'+(sc.limA-pm.rhf).toFixed(4)+' a.u. = '+((sc.limA-pm.rhf)*27.2114).toFixed(2)+' eV</b>（实验：'+(S.mol==='H2'?'4.75':'约 2.0')+' eV）</span>'+(S.mol==='H2'?'<span>R = 6 玻尔时 RHF 比极限高 <b>'+(last.rhf-sc.lim).toFixed(3)+' 原子单位</b></span>':'');
  document.getElementById('scanIntro').innerHTML='在 0.6 到 6 玻尔的每个 R 处进行同样的计算，但用两种方法：RHF（两个电子在同一个空间轨道上）和 UHF（α 和 β 电子各有自己的轨道；初始时 α 在一个原子上，β 在另一个原子上）。这就是第一个势能面；在实际计算中，这样的曲线和势能面由 ASE 等程序生成。';
  document.getElementById('scanText').innerHTML=S.mol==='H2'?'<b>H₂：RHF 在解离时失效。</b>在平衡位置附近两种解相同。'+(cf?'R ≈ '+cf.R.toFixed(2)+' 玻尔':'拉伸时')+'，UHF 更倾向于把 α 和 β 电子分到不同原子上：解的对称性被破坏，⟨S²⟩ 从 0 增大到 1——这是单重态与三重态的混合，即自旋污染。UHF 准确地趋于两个 H 原子的能量。RHF 将两个电子保持在同一个成键轨道上，而这样的波函数有 50 % 是离子结构 H⁺H⁻——因此曲线远高于正确的极限。多组态方法可以描述化学键断裂而又不失去正确的自旋。<br><br>R → ∞ 时曲线的极限是用与分子相同的指数 ζ 得到的，而对自由原子它们并非最优：'+(S.mol==='H2'?'H 原子的最佳指数是 ζ ≈ 1，而不是 1.24':'He 原子的最佳指数是 ζ ≈ 1.69，而不是 2.09')+'。因此 D<sub>e</sub> 是相对于使用各自 ζ 的原子计算的——否则键能会被高估（固定基组的假象）。':'<b>HeH⁺：RHF 和 UHF 在所有 R 处都相同。</b>解离时两个电子都留在氦上（He + H⁺），一个闭壳层就足够——解的对称性不被破坏，⟨S²⟩ = 0。RHF 的失效出现在化学键“均裂”为两个自由基时，如 H₂——请切换分子。<br><br>R → ∞ 时曲线的极限是用与分子相同的指数 ζ 得到的，而对自由原子它们并非最优：'+(S.mol==='H2'?'H 原子的最佳指数是 ζ ≈ 1，而不是 1.24':'He 原子的最佳指数是 ζ ≈ 1.69，而不是 2.09')+'。因此 D<sub>e</sub> 是相对于使用各自 ζ 的原子计算的——否则键能会被高估（固定基组的假象）。'}
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
  for(let i=0;i<=3;i++){const e=lo+(hi-lo)*i/3;el(sv,'line',{x1:L,x2:L+W,y1:sy(e),y2:sy(e),stroke:tok('--line'),'stroke-width':.7});el(sv,'text',{x:L-6,y:sy(e)+4,'text-anchor':'end','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=e.toFixed(2).replace('-','−')}
  [1,1.5,2,2.5,3,3.5].forEach(z=>el(sv,'text',{x:sx(z),y:T+H+16,'text-anchor':'middle','font-size':11.5,fill:mut,'font-family':'JetBrains Mono, monospace'}).textContent=String(z));
  el(sv,'text',{x:L+W,y:T+H+32,'text-anchor':'end','font-size':14,'font-style':'italic','font-family':'PT Serif, serif',fill:mut}).textContent='ζ';
  const g=el(sv,'g',{'clip-path':'url(#clipZ)'});el(g,'polyline',{points:pts.map(p=>sx(p.z)+','+sy(p.E)).join(' '),fill:'none',stroke:mut,'stroke-width':2.2});
  const std=MOLS[S.mol].atoms[who[0]].zeta;el(sv,'line',{x1:sx(std),x2:sx(std),y1:T,y2:T+H,stroke:mut,'stroke-dasharray':'2 3'});el(sv,'text',{x:sx(std)+4,y:T+12,'font-size':11.5,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent='STO-3G';
  el(sv,'circle',{cx:sx(zCache.zm),cy:sy(zCache.Em),r:5,fill:'none',stroke:tok('--ok'),'stroke-width':2});
  const zc=zetaOf(who[0]);el(sv,'circle',{cx:sx(zc),cy:sy(S.Econv),r:6,fill:acc});
  const nm=S.mol==='H2'?'两个 H 原子的 ζ':'ζ('+MOLS[S.mol].atoms[S.zwho].name+')';
  document.getElementById('zetav').textContent=zc.toFixed(2);
  document.getElementById('zText').innerHTML='改变 '+nm+'，R = '+S.R.toFixed(2)+' 玻尔。当前 ζ = '+zc.toFixed(2)+': E = '+f6(S.Econv)+'。<b>最小值在 ζ = '+zCache.zm.toFixed(3)+'</b> (E = '+f6(zCache.Em)+'）：任何其他函数给出的能量都更高——这就是变分原理。'+
    'STO-3G 的标准值（'+std.toFixed(S.mol==='H2'||S.zwho===1?2:4)+'）是一次性为许多分子同时选定的，因此对具体分子和具体 R 而言不一定最优。移动 R：分子被压缩时，最优 ζ 增大——函数向原子核“收缩”。在实际基组中，不调整 ζ，而是使用多个宽度不同的函数。'}
function renderZetaControls(){const items=S.mol==='H2'?[[0,'两个 H 原子']]:[[0,'ζ(He)'],[1,'ζ(H)']];if(S.mol==='H2')S.zwho=0;
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
async function drawPop(){let PD;try{PD=await getPop({mol:S.mol,R:S.R,za:zetaOf(0),zb:zetaOf(1)})}catch(e){return}const at=atoms(),p=PD.p,fmt3=x=>(Math.abs(x)<5e-4?0:x).toFixed(3).replace('-','−');const ink=tok('--ink'),mut=tok('--muted'),acc=tok('--accent'),alt=tok('--rho-l'),vir=tok('--virt'),soft=tok('--soft'),line=tok('--line');
  /* столбики: 2 электрона */
  let sv=document.getElementById('popBars');sv.innerHTML='';const x0=130,W=380,sx=W/2,tx=(x,y,t,o={})=>{const e=el(sv,'text',Object.assign({x,y,'font-size':12.5,fill:ink,'font-family':'Golos Text, sans-serif'},o));e.textContent=t;return e};
  const bar=(y,segs,label)=>{tx(8,y+20,label,{'font-size':13,'font-weight':600});let x=x0;segs.forEach(s=>{const w=Math.max(0,s.v*sx);el(sv,'rect',{x,y,width:w,height:30,fill:s.c,stroke:tok('--panel'),'stroke-width':1});if(w>34)tx(x+w/2,y+20,fmt3(s.v),{'text-anchor':'middle','font-family':'JetBrains Mono, monospace','font-size':12,fill:s.ink||'#fff'});x+=w})};
  const cA=acc,cB=alt,cO=vir;
  bar(30,[{v:p.net[0],c:cA},{v:p.op,c:cO},{v:p.net[1],c:cB}],'N 的划分');
  [[24,31],[59,66]].forEach(([y1,y2])=>el(sv,'line',{x1:x0+(p.net[0]+p.op/2)*sx,x2:x0+(p.net[0]+p.op/2)*sx,y1,y2,stroke:ink,'stroke-width':2}));
  tx(x0+(p.net[0]+p.op/2)*sx,20,'马利肯平分',{'text-anchor':'middle','font-size':11.5,fill:mut});
  bar(95,[{v:p.gm[0],c:cA},{v:p.gm[1],c:cB}],'马利肯');
  bar(150,[{v:p.gl[0],c:cA},{v:p.gl[1],c:cB}],'勒夫丁');
  const lg=[[cA,'在 '+at[0].name],[cO,'重叠 2P₁₂S₁₂'],[cB,'在 '+at[1].name]];let lx=x0;lg.forEach(([c,t])=>{el(sv,'rect',{x:lx,y:194,width:12,height:10,fill:c,rx:2});const e=tx(lx+17,203,t,{'font-size':11.5,fill:mut});lx+=17+t.length*6.6+16});
  [0,0.5,1,1.5,2].forEach(v=>{el(sv,'line',{x1:x0+v*sx,x2:x0+v*sx,y1:184,y2:188,stroke:mut,'stroke-width':1})});
  /* таблица */
  document.getElementById('popTab').innerHTML='<table class="mtab poptab"><thead><tr><th></th><th>'+at[0].name+'</th><th>'+at[1].name+'</th></tr></thead><tbody>'+
    '<tr><td>P<sub>μμ</sub>（净布居）</td><td>'+fmt3(p.net[0])+'</td><td>'+fmt3(p.net[1])+'</td></tr>'+
    '<tr><td>(PS)<sub>μμ</sub> — 马利肯</td><td>'+fmt3(p.gm[0])+'</td><td>'+fmt3(p.gm[1])+'</td></tr>'+
    '<tr><td>(S<sup>½</sup>PS<sup>½</sup>)<sub>μμ</sub> — 勒夫丁</td><td>'+fmt3(p.gl[0])+'</td><td>'+fmt3(p.gl[1])+'</td></tr>'+
    '<tr><td>马利肯电荷</td><td>'+fsig(p.qm[0])+'</td><td>'+fsig(p.qm[1])+'</td></tr>'+
    '<tr><td>勒夫丁电荷</td><td>'+fsig(p.ql[0])+'</td><td>'+fsig(p.ql[1])+'</td></tr>'+
    '<tr><td>重叠布居 2P₁₂S₁₂</td><td colspan="2" style="text-align:center">'+fmt3(p.op)+'</td></tr>'+
    '<tr><td>迈耶键级 (PS)₁₂(PS)₂₁</td><td colspan="2" style="text-align:center">'+fmt3(p.mayer)+'</td></tr></tbody></table>';
  /* зависимость от R */
  sv=document.getElementById('popR');sv.innerHTML='';const C=PD.curve,het=S.mol==='HeH';const L=54,Rr=520,T=14,B=222;
  const ser=het?[[d=>d.qm[1],acc,'',"马利肯 q(H)"],[d=>d.ql[1],alt,'6 4',"勒夫丁 q(H)"],[d=>d.mayer,vir,'2 3','迈耶键级'],[d=>d.op,mut,'','重叠布居']]
                :[[d=>d.op,acc,'','重叠布居 2P₁₂S₁₂'],[d=>d.mayer,vir,'2 3','迈耶键级'],[d=>d.net[0],alt,'6 4','P₁₁ — H(1) 的净布居']];
  const ymin=0,ymax=1.1,X=r=>L+(r-0.6)/(6-0.6)*(Rr-L),Y=v=>B-(v-ymin)/(ymax-ymin)*(B-T);
  for(let v=0;v<=1.001;v+=0.25){el(sv,'line',{x1:L,x2:Rr,y1:Y(v),y2:Y(v),stroke:line,'stroke-width':1});el(sv,'text',{x:L-6,y:Y(v)+4,'text-anchor':'end','font-size':11.5,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent=v.toFixed(2)}
  [1,2,3,4,5,6].forEach(r=>{el(sv,'text',{x:X(r),y:B+16,'text-anchor':'middle','font-size':11.5,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent=r});
  el(sv,'text',{x:(L+Rr)/2,y:B+34,'text-anchor':'middle','font-size':12,fill:mut,'font-family':'Golos Text, sans-serif'}).textContent='R，玻尔';
  ser.forEach(([f,c,da])=>{el(sv,'path',{d:C.map((d,i)=>(i?'L':'M')+X(d.R).toFixed(1)+','+Y(f(d)).toFixed(1)).join(''),fill:'none',stroke:c,'stroke-width':2.2,'stroke-dasharray':da||'none'})});
  if(S.R>=0.6&&S.R<=6){el(sv,'line',{x1:X(S.R),x2:X(S.R),y1:T,y2:B,stroke:mut,'stroke-width':1,'stroke-dasharray':'3 3'});ser.forEach(([f,c])=>el(sv,'circle',{cx:X(S.R),cy:Y(f(p)),r:4,fill:c}))}
  document.getElementById('popLeg').innerHTML=ser.map(([f,c,da,t])=>'<span><i class="sw" style="border-color:'+c+';border-top-style:'+(da?(da==='2 3'?'dotted':'dashed'):'solid')+'"></i>'+t+'</span>').join('');
  let t;if(het){const sm=Math.sign(p.qm[0]-p.qm[1]),sl=Math.sign(p.ql[0]-p.ql[1]);
    t='电荷：马利肯 He '+fsig(p.qm[0])+', H '+fsig(p.qm[1])+'；勒夫丁 He '+fsig(p.ql[0])+', H '+fsig(p.ql[1])+'. '+
      (sm!==sl?'<b>不同方案甚至在哪个原子更正这一点上都不一致。</b>原子电荷不是可观测量：它取决于划分方式和基组。':'两种方案给出的电荷差符号一致，但数值不同。 ')+
      '随着 R 增大，电子对转移到 He 上（产物为 He + H⁺），H 的电荷趋于 +1，而重叠布居和键级趋于零。'}
  else t='在 H₂ 中，由于对称性，两种方案的电荷都为零。重叠布居 '+fmt3(p.op)+' 随 R 增大而与 S₁₂ 一同减小，而 RHF 中的迈耶键级在任何 R 下都保持为 1：RHF 波函数总是描述一个双电子键——这与 RHF 解离错误是同一个问题。';
  document.getElementById('popText').innerHTML=t}
