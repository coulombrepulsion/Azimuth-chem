/* Slater-Condon page (Atlas v2).  Alignment of the determinants, the
   permutation sign, the matrix element in spatial integrals and the spin
   notes come from quas_atlas.core.slater (slater.element); this script
   edits the determinants and writes the step-by-step solution. */
// Правила Слейтера–Кондона: спин-орбиталь = {o: номер пространственной орбитали, s: 'α'|'β'}
const so=(o,s)=>({o,s}),soKey=x=>x.o+x.s,eqSO=(a,b)=>a.o===b.o&&a.s===b.s;
/* spin notes of slater.element: template i, placeholders a[] in order */
const NOTE_T=[a=>`${a[0]} 与 ${a[1]} 之间的 K = 0：自旋不同`,a=>`${a[0]} → ${a[1]}：自旋改变，对自旋积分得 0`,a=>`与 ${a[0]} 的交换项 = 0：自旋不同`,a=>`⟨${a[0]}${a[1]}|${a[2]}${a[3]}⟩ = 0：自旋不匹配`,a=>`⟨${a[0]}${a[1]}|${a[2]}${a[3]}⟩ = 0：自旋不匹配`,a=>'有三个及以上自旋轨道不同：哈密顿量至多只含双电子算符'];
function fromSrv(r){if(r.bad)return r;r=JSON.parse(JSON.stringify(r));const O=([o,s])=>({o,s});r.al.B2=r.al.B2.map(O);r.al.diff=r.al.diff.map(([a,b])=>[O(a),O(b)]);r.notes=r.notes.map(n=>NOTE_T[n.i](n.a));return r}
const pairs=d=>d.map(x=>[x.o,x.s]);
// ---------- страница «Правила Слейтера–Кондона» ----------
const $=id=>document.getElementById(id);
const K=4;// число пространственных орбиталей
const lab=x=>x.o+x.s,detStr=D=>'|'+D.map(lab).join(' ')+'|';
let D=[[so(1,'α'),so(1,'β')],[so(2,'α'),so(2,'β')]],preKey='h2ci',hidden=false;
const PRE=[
 ['he','He: ⟨1s²|Ĥ|1s²⟩',[[1,'α'],[1,'β']],[[1,'α'],[1,'β']]],
 ['li','Li: 1s²2s',[[1,'α'],[1,'β'],[2,'α']],[[1,'α'],[1,'β'],[2,'α']]],
 ['trip','三重态 φ₁αφ₂α',[[1,'α'],[2,'α']],[[1,'α'],[2,'α']]],
 ['h2ci','H₂: ⟨σ<sub>g</sub>²|Ĥ|σ<sub>u</sub>²⟩',[[1,'α'],[1,'β']],[[2,'α'],[2,'β']]],
 ['bril','单激发',[[1,'α'],[1,'β']],[[1,'α'],[2,'β']]],
 ['spin','自旋翻转',[[1,'α'],[1,'β']],[[1,'α'],[2,'α']]],
 ['open','φ₁αφ₂β 和 φ₂αφ₁β',[[1,'α'],[2,'β']],[[2,'α'],[1,'β']]],
 ['perm','含列交换',[[1,'α'],[2,'α'],[3,'β']],[[3,'β'],[1,'α'],[4,'α']]],
 ['three','三处不同',[[1,'α'],[1,'β'],[2,'α']],[[3,'α'],[3,'β'],[4,'α']]]];
const NOTE={he:'单行列式近似下 He 的基态能量：2h₁₁ + J₁₁。',
 li:'交换项 −K₁₂ 只存在于自旋相同的电子之间（1sα 和 2sα）。',
 trip:'与单重态比较：三重态的能量中含有 −K₁₂——自旋平行的电子相互回避（参见“泡利原理”选项卡）。',
 h2ci:'这是最小基组下 H₂ 的 CI 矩阵非对角元（φ₁ = σ<sub>g</sub>，φ₂ = σ<sub>u</sub>）：它等于 K<sub>gu</sub>，使组态 σ<sub>g</sub>² 与 σ<sub>u</sub>² 混合——参见“H₂ 解离”选项卡。',
 bril:'对闭壳层，h₁₂ + (11|12) 是 Fock 算符的矩阵元 F₁₂。对哈特里–福克轨道它等于零（布里渊定理）：单激发不与基态行列式直接混合。',
 spin:'哈密顿量不作用于自旋，因此只有投影 M<sub>S</sub> 相同的行列式才能混合。',
 open:'由这两个行列式可构造 M<sub>S</sub> = 0 的单重态和三重态：使它们混合的正是交换积分 K₁₂。',
 perm:'首先将列 3β 移到第三位——两次对换，符号不变。',
 three:'Ĥ 只含单电子和双电子算符，无法“够到”三处替换。'};
function setPre(k){const p=PRE.find(x=>x[0]===k);D=[p[2].map(([o,s])=>so(o,s)),p[3].map(([o,s])=>so(o,s))];preKey=k;hidden=false;quiz=null;$('quiz').innerHTML='';render()}
function chipsPre(){const g=$('preG');g.innerHTML='';PRE.forEach(([k,l])=>{const b=document.createElement('button');b.className='chip';b.type='button';b.innerHTML=l;b.setAttribute('aria-pressed',k===preKey);b.onclick=()=>setPre(k);g.appendChild(b)})}
function editor(i,res){const d=D[i],box=document.createElement('div');box.className='det';const name=i?'Ψ′':'Ψ';
  box.innerHTML=`<b>${name}</b>`;const orbs=document.createElement('div');orbs.className='orbs';
  for(let o=1;o<=K;o++){const c=document.createElement('div');c.className='orb';const sp=document.createElement('div');sp.className='sp';
    [['α','↑'],['β','↓']].forEach(([s,ch])=>{const b=document.createElement('button');b.type='button';b.className='sbtn';b.textContent=ch;const on=d.some(x=>x.o===o&&x.s===s);
      b.setAttribute('aria-pressed',on);b.setAttribute('aria-label',`${name} 中的 φ${o}${s}`);b.onclick=()=>{const k=d.findIndex(x=>x.o===o&&x.s===s);if(k>=0)d.splice(k,1);else d.push(so(o,s));preKey=null;hidden=false;render()};sp.appendChild(b)});
    c.appendChild(sp);const ln=document.createElement('div');ln.className='ln';c.appendChild(ln);const nm=document.createElement('div');nm.className='nm';nm.textContent='φ'+'₁₂₃₄'[o-1];c.appendChild(nm);orbs.appendChild(c)}
  box.appendChild(orbs);
  const cols=document.createElement('div');cols.className='cols';cols.innerHTML=`<span class="small" style="font-family:var(--f-body)">列：</span><span class="bar">|</span>`;
  const dset=res&&res.al&&!hidden?new Set(res.al.diff.map(p=>lab(p[i]))):new Set();
  d.forEach((x,k)=>{const b=document.createElement('button');b.type='button';b.className='col'+(dset.has(lab(x))?' df':'');b.textContent=lab(x);b.title='左移';b.onclick=()=>{if(k>0){[d[k-1],d[k]]=[d[k],d[k-1]];preKey=null;hidden=false;render()}};cols.appendChild(b)});
  cols.insertAdjacentHTML('beforeend','<span class="bar">|</span>');box.appendChild(cols);return box}
function solution(r){const A=D[0],B=D[1];if(!A.length||!B.length)return '<p class="small">请在两个行列式中都添加自旋轨道。</p>';
  if(r.bad)return `<p class="small"><b>电子数不同</b>（${A.length} 和 ${B.length}）：哈密顿算符保持粒子数不变，这样的矩阵元不予考虑。</p>`;
  const al=r.al,steps=[];
  steps.push(`<b class="h">写出行列式</b><span class="f">Ψ = ${detStr(A)}</span> &nbsp; <span class="f">Ψ′ = ${detStr(B)}</span>`);
  steps.push(`<b class="h">将 Ψ′ 化为与 Ψ 最大重合</b>`+(al.inv===0?'相同的自旋轨道已经位于相同的位置——无需调换，因子为 +1。':
    `调换列的次序，使相同的自旋轨道与 Ψ 中位置相同：<span class="f">${detStr(B)} → ${detStr(al.B2)}</span>。共 ${al.inv} 次对换${al.inv===1?'':al.inv<5?'':''}，因子 (−1)<sup>${al.inv}</sup> = <b>${al.sign>0?'+1':'−1'}</b>。`));
  const nd=r.nd;steps.push(`<b class="h">有几个自旋轨道不同</b>`+(nd===0?'一个也没有：这是对角元，即行列式的能量。':
    `${nd}: `+al.diff.map(([m,p])=>`χ<sub>${lab(m)}</sub> → χ<sub>${lab(p)}</sub>`).join(', ')+'.'));
  const gen=nd===0?'⟨Ψ|Ĥ|Ψ⟩ = Σ<sub>i</sub> h<sub>ii</sub> + Σ<sub>i&lt;j</sub> (⟨ij|ij⟩ − ⟨ij|ji⟩)':nd===1?'⟨Ψ|Ĥ|Ψ′⟩ = h<sub>mp</sub> + Σ<sub>n≠m</sub> (⟨mn|pn⟩ − ⟨mn|np⟩)':nd===2?'⟨Ψ|Ĥ|Ψ′⟩ = ⟨mn|pq⟩ − ⟨mn|qp⟩':'⟨Ψ|Ĥ|Ψ′⟩ = 0';
  let sub='';
  if(nd===0){const t=[];A.forEach(x=>t.push(`h<sub>${lab(x)}</sub>`));for(let i=0;i<A.length;i++)for(let j=i+1;j<A.length;j++)t.push(`(⟨${lab(A[i])}${lab(A[j])}|${lab(A[i])}${lab(A[j])}⟩ − ⟨${lab(A[i])}${lab(A[j])}|${lab(A[j])}${lab(A[i])}⟩)`);sub=t.join(' + ')}
  else if(nd===1){const [m,p]=al.diff[0];sub=`h<sub>${lab(m)},${lab(p)}</sub>`+A.filter(n=>!(n.o===m.o&&n.s===m.s)).map(n=>` + ⟨${lab(m)}${lab(n)}|${lab(p)}${lab(n)}⟩ − ⟨${lab(m)}${lab(n)}|${lab(n)}${lab(p)}⟩`).join('')}
  else if(nd===2){const [[m,p],[n,q]]=al.diff;sub=`⟨${lab(m)}${lab(n)}|${lab(p)}${lab(q)}⟩ − ⟨${lab(m)}${lab(n)}|${lab(q)}${lab(p)}⟩`}
  steps.push(`<b class="h">该情形的通用公式</b><span class="f">${gen}</span>`+(sub?`<br>代入自旋轨道：<span class="f" style="white-space:normal">${sub}</span>`:''));
  if(nd<=2)steps.push(`<b class="h">对自旋积分</b>`+(r.notes.length?r.notes.map(t=>'• '+t).join('<br>'):'所有项都保留：各处自旋均一致。')+'<br><span class="hint">若电子在左右两侧的自旋相同，自旋积分等于 1；若不同，则等于 0。</span>');
  else steps.push(`<b class="h">为什么为零</b>${r.notes[0]}.`);
  const sg=al.sign<0&&!r.zero?'−(':'',sg2=al.sign<0&&!r.zero?')':'';
  steps.push(`<b class="h">用空间积分表示的答案</b><span class="ans">⟨Ψ|Ĥ|Ψ′⟩ = ${r.expr}</span>`+(al.sign<0&&!r.zero?'<br><span class="hint">负号来自列的调换</span>':'')+
    (Object.keys(r.T).some(k=>k[0]==='c'&&!/^c:(\d),\1\|(\d),\2$/.test(k)&&!/^c:(\d),(\d)\|\1,\2$/.test(k))?'<br><span class="hint">(ab|cd) = ⟨ac|bd⟩ —— 化学家记号。</span>':''));
  let h='<ol class="steps">'+steps.map(s=>'<li>'+s+'</li>').join('')+'</ol>';if(preKey&&NOTE[preKey])h+=`<div class="status" style="margin-top:10px">${NOTE[preKey]}</div>`;return h}
const liveEl=QC.live('slater.element');
async function render(){let r={};if(D[0].length&&D[1].length){try{r=fromSrv(await liveEl({A:pairs(D[0]),B:pairs(D[1])}))}catch(e){return}}chipsPre();const box=$('dets');box.innerHTML='';box.appendChild(editor(0,r));box.appendChild(editor(1,r));
  $('sol').innerHTML=hidden?'<p class="small">回答下面的问题后即可查看解答。</p>':solution(r)}
// ---------- самопроверка ----------
let quiz=null,score=[0,0];
function rnd(n){return Math.floor(Math.random()*n)}
async function newQuiz(){const all=[];for(let o=1;o<=K;o++)['α','β'].forEach(s=>all.push(so(o,s)));
  const N=2+rnd(2);let A=[];const pool=all.slice();while(A.length<N){const k=rnd(pool.length);A.push(pool.splice(k,1)[0])}
  A.sort((x,y)=>x.o-y.o||(x.s==='α'?-1:1));
  const want=[0,1,1,2,2,3][rnd(6)];let B=A.slice();const free=all.filter(x=>!A.some(y=>y.o===x.o&&y.s===x.s));
  const idx=[...Array(N).keys()].sort(()=>Math.random()-0.5).slice(0,Math.min(want,N));
  idx.forEach(i=>{if(!free.length)return;const sameSpin=free.filter(x=>x.s===B[i].s);const src=Math.random()<0.75&&sameSpin.length?sameSpin:free;const pick=src[rnd(src.length)];free.splice(free.indexOf(pick),1);B[i]=pick});
  B=B.sort(()=>Math.random()-0.5);D=[A,B];preKey=null;hidden=true;let r;try{r=fromSrv(await QC.api('slater.element',{A:pairs(A),B:pairs(B)}))}catch(e){return}quiz={r,a1:null,a2:null};drawQuiz();render()}
function drawQuiz(){if(!quiz){$('quiz').innerHTML='';return}const q=quiz,r=q.r;
  const truth1=Math.min(r.nd,3),truth2=r.al.sign;
  const row=(label,opts,key,truth)=>{const v=q[key];return `<div class="qrow"><span class="small" style="min-width:300px">${label}</span>`+opts.map(([val,l])=>`<button class="chip" type="button" data-k="${key}" data-v="${val}" aria-pressed="${v===val}">${l}</button>`).join('')+(v!=null?`<span class="fb ${v===truth?'ok':'no'}">${v===truth?'正确':'错误'}</span>`:'')+'</div>'};
  let h=row('化为最大重合后有几个自旋轨道不同？',[[0,'0'],[1,'1'],[2,'2'],[3,'3 个及以上']],'a1',truth1)+row('列的调换给出什么因子？',[[1,'+1'],[-1,'−1']],'a2',truth2);
  if(q.a1!=null&&q.a2!=null)h+=`<div class="status">答案：<b>${r.expr}</b>${r.al.sign<0&&!r.zero?' （已计入调换的符号）':''}。完整解答见“分步解答”部分。</div>`;
  $('quiz').innerHTML=h;$('quiz').querySelectorAll('[data-k]').forEach(b=>b.onclick=()=>{if(q[b.dataset.k]!=null)return;q[b.dataset.k]=+b.dataset.v;
    if(q.a1!=null&&q.a2!=null){score[1]++;if(q.a1===truth1&&q.a2===truth2)score[0]++;hidden=false;render();$('qScore').textContent=`答对：${score[0]} / ${score[1]}`}drawQuiz()})}
$('qNew').onclick=newQuiz;
render();
