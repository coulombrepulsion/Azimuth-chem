/* Atomic charges page (Atlas v2).  The RHF data, atom labels, point-charge and
   density dipoles and the experimental values come from quas_atlas.core.charges
   (charges.meta, charges.view, charges.series); this script draws. */
// ---------- страница «Атомные заряды: сравнение схем» (данные RHF посчитаны заранее той же программой, что на странице Бейдера) ----------
const NS='http://www.w3.org/2000/svg',$=id=>document.getElementById(id);
function el(tag,a,p,t){const e=document.createElementNS(NS,tag);for(const k in a)e.setAttribute(k,a[k]);if(t!=null)e.textContent=t;if(p)p.appendChild(e);return e}
const fmt=(x,d=2)=>{if(x==null||!isFinite(x))return '—';if(Math.abs(x)<0.5*Math.pow(10,-d))x=0;return x.toFixed(d).replace('-','−')};
const sg=(x,d=2)=>(x>0.5*Math.pow(10,-d)?'+':'')+fmt(x,d);
const tok=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
let B=null,M=null;
const SCH=[['mul','马利肯','--nu'],['low','勒夫丁','--ok'],['bad','巴德','--el']];
const Q={m:0,b:3,a:0};
const sub=s=>s.replace(/\d/g,c=>'₀₁₂₃₄₅₆₇₈₉'[c]);
function chips(box,labels,cur,on){box.innerHTML='';labels.forEach((t,i)=>{const b=document.createElement('button');b.type='button';b.className='chip';b.innerHTML=t;b.setAttribute('aria-pressed',i===cur);b.onclick=()=>on(i);box.appendChild(b)})}
function mark(box,i){[...box.children].forEach((b,j)=>b.setAttribute('aria-pressed',j===i))}
const liveV=QC.live('charges.view'),liveS=QC.live('charges.series');
async function init(){try{M=await QC.api('charges.meta',{})}catch(e){return}B=M.B;
  chips($('molG'),M.mols.map(m=>m.n),Q.m,i=>{Q.m=i;Q.a=0;mark($('molG'),i);draw()});
  chips($('basG'),B,Q.b,i=>{Q.b=i;mark($('basG'),i);draw()});
  draw()}
async function draw(){const m=M.mols[Q.m],b=B[Q.b];let r;try{r=await liveV({m:Q.m,b})}catch(e){return}const L=m.L;
  $('info').innerHTML=m.n+', RHF/'+b+'：基函数数目 '+r.nbf+', E = '+fmt(r.E,6)+' E<sub>h</sub>.';
  $('tab').innerHTML='<table class="mtab"><thead><tr><th>原子</th>'+SCH.map(s=>'<th>'+s[1]+'</th>').join('')+'</tr></thead><tbody>'+L.map((l,i)=>'<tr><td>'+l+'</td>'+SCH.map(([k])=>'<td>'+(r.q[k]?sg(r.q[k][i]):'—')+'</td>').join('')+'</tr>').join('')+'</tbody></table>';
  bars(m,r.q,L);
  const notes=[];if(!r.q.bad)notes.push('STO-3G 下 HF 的巴德电荷未显示：在该基组中，程序没有找到氢自己的原子盆。');
  if(m.id==='LiH'&&b==='STO-3G')notes.push('STO-3G 下马利肯方案给锂负电荷——与常识相反：锂把电子给了氢。这是方案假象的经典例子。');
  if(m.id==='CH4')notes.push('甲烷中碳电荷的符号也取决于方案：马利肯和勒夫丁为负，巴德为正。');
  if(B[Q.b]==='6-31G**'&&!m.hasH)notes.push('分子中没有氢，因此 6-31G** 与 6-31G* 相同：“第二个星号”只在 H 上加 p 函数。');
  $('note').textContent=notes.join(' ');
  chips($('atG'),m.uniq.map(i=>L[i]),Q.a,i=>{Q.a=i;mark($('atG'),i);chart()});chart();dip(r,m)}
function bars(m,r,L){const svg=$('bars');svg.innerHTML='';const W=960,H=260,lft=60,rt=16,top=14,bot=34;let mx=0;SCH.forEach(([k])=>r[k]&&r[k].forEach(v=>mx=Math.max(mx,Math.abs(v))));mx=Math.max(0.5,Math.ceil(mx*4)/4);
  const Y=v=>top+(mx-v)/(2*mx)*(H-top-bot),n=L.length,gw=(W-lft-rt)/n,bw=Math.min(36,gw/4);
  for(let v=-mx;v<=mx+1e-9;v+=mx/2){el('line',{x1:lft,x2:W-rt,y1:Y(v),y2:Y(v),stroke:Math.abs(v)<1e-9?tok('--muted'):tok('--line')},svg);el('text',{x:lft-6,y:Y(v)+4,'text-anchor':'end','font-size':12,fill:tok('--muted')},svg,sg(v,2))}
  L.forEach((l,i)=>{const x0=lft+gw*i+gw/2;SCH.forEach(([k,,c],j)=>{if(!r[k])return;const v=r[k][i],x=x0+(j-1)*(bw+4)-bw/2;el('rect',{x,y:Math.min(Y(v),Y(0)),width:bw,height:Math.abs(Y(v)-Y(0)),fill:tok(c),rx:2},svg)});
    el('text',{x:x0,y:H-10,'text-anchor':'middle','font-size':13,fill:tok('--ink')},svg,l)});
  $('leg').innerHTML=SCH.map(([,n,c])=>'<span><span class="box" style="background:'+tok(c)+'"></span>'+n+'</span>').join('')}
async function chart(){const m=M.mols[Q.m],i=m.uniq[Q.a];let vals;try{vals=await liveS({m:Q.m,i})}catch(e){return}const svg=$('chart');svg.innerHTML='';const W=960,H=300,lft=60,rt=120,top=16,bot=36;
  let lo=0,hi=0;vals.flat().forEach(v=>{if(v!=null){lo=Math.min(lo,v);hi=Math.max(hi,v)}});const pad=Math.max(0.1,(hi-lo)*0.1);lo-=pad;hi+=pad;
  const X=j=>lft+j*(W-lft-rt)/3,Y=v=>top+(hi-v)/(hi-lo)*(H-top-bot);const step=(hi-lo)>2?0.5:(hi-lo)>0.8?0.25:0.1;
  for(let v=Math.ceil(lo/step)*step;v<=hi;v+=step){el('line',{x1:lft,x2:W-rt,y1:Y(v),y2:Y(v),stroke:Math.abs(v)<1e-9?tok('--muted'):tok('--line')},svg);el('text',{x:lft-6,y:Y(v)+4,'text-anchor':'end','font-size':12,fill:tok('--muted')},svg,sg(v,2))}
  B.forEach((b,j)=>el('text',{x:X(j),y:H-12,'text-anchor':'middle','font-size':13,fill:tok('--ink')},svg,b));
  SCH.forEach(([k,n,c],s)=>{const pts=vals[s].map((v,j)=>v==null?null:[X(j),Y(v)]);let d='';pts.forEach((p,j)=>{if(!p)return;d+=(d&&pts[j-1]?'L':'M')+p[0].toFixed(1)+' '+p[1].toFixed(1)});el('path',{d,fill:'none',stroke:tok(c),'stroke-width':2.4},svg);
    pts.forEach((p,j)=>{if(p)el('circle',{cx:p[0],cy:p[1],r:j===Q.b?6:4,fill:tok(c)},svg)});const last=pts.filter(Boolean).pop();if(last)el('text',{x:W-rt+10,y:last[1]+4,'font-size':13,fill:tok(c)},svg,n)})}
function dip(r,m){const mu=r.mu;
  const rows=SCH.map(([k,n])=>{const v=r.dip[k];if(!v)return '<tr><td>'+n+'</td><td>—</td><td>—</td></tr>';const mq=v.mq;return '<tr><td>'+n+'</td><td>'+fmt(mq,2)+'</td><td>'+(v.dir?(v.dir>0?'一致':'相反'):'—')+'</td></tr>'}).join('');
  $('dip').innerHTML='<table class="mtab"><thead><tr><th>来源</th><th>|μ|，D</th><th>方向</th></tr></thead><tbody><tr><td><b>由完整密度计算</b></td><td><b>'+fmt(mu,2)+'</b></td><td>—</td></tr>'+rows+'<tr><td>实验</td><td>'+fmt(r.exp,2)+'</td><td>—</td></tr></tbody></table>';
  $('dipNote').textContent=m.id==='CO'?'CO 是一个难例：实验中偶极的负端在碳上，而扩展基组下的哈特里–福克给出相反的方向；只有考虑电子相关才能得到正确的符号。巴德电荷（C⁺、O⁻）反映的是密度分布，而不是偶极矩：偶极矩还包含原子盆的极化。':(m.id==='CH4'||m.id==='CO2')?'无论电荷如何，偶极矩因对称性为零；这类分子的静电性质用四极矩描述。':'巴德点电荷通常高估偶极矩：原子盆本身还被极化，这一贡献与电荷转移方向相反。拟合静电势得到的电荷能最好地重现偶极矩——它们正是为此而设计的。'}
init();matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{if(M)draw()});
