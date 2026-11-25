(function(){const R=document.documentElement;let on=false,sl=[],k=0,nav=null,lock=0;
  function build(){const m=document.querySelector('main');if(!m)return [];const out=[];
    [...m.children].forEach(c=>{if(/^(SCRIPT|STYLE|LINK)$/.test(c.tagName)||c.hidden)return;const h=c.getBoundingClientRect().height;if(h<8)return;
      if(out.length&&h<120&&!c.matches('section,header,.nextQ,.try'))out[out.length-1].push(c);else out.push([c])});return out}
  function paint(){sl.forEach((g,i)=>g.forEach(e=>{e.classList.add('projSlide');e.classList.toggle('projCur',i===k)}));
    if(nav)nav.querySelector('span').textContent=`Section ${k+1} of ${sl.length}`}
  function go(i,scroll){if(!sl.length)return;k=Math.max(0,Math.min(sl.length-1,i));paint();
    if(scroll!==false){lock=Date.now();scrollTo({top:sl[k][0].getBoundingClientRect().top+scrollY-12,behavior:'smooth'})}}
  function enable(v){if(v===on)return;on=v;document.body.classList.toggle('projOn',on);
    if(on){sl=build();k=0;nav=document.createElement('div');nav.className='projNav';nav.innerHTML='<button type="button">◀</button><span></span><button type="button">▶</button>';
      const b=nav.querySelectorAll('button');b[0].title='Previous section (← or PageUp)';b[1].title='Next section (→ or PageDown)';
      b[0].onclick=()=>go(k-1);b[1].onclick=()=>go(k+1);document.body.appendChild(nav);follow();paint()}
    else{sl.forEach(g=>g.forEach(e=>e.classList.remove('projSlide','projCur')));sl=[];if(nav){nav.remove();nav=null}}}
  /* при обычной прокрутке текущим становится раздел у верхнего края */
  function follow(){if(!on||Date.now()-lock<900)return;let j=0;sl.forEach((g,i)=>{if(g[0].getBoundingClientRect().top<innerHeight*0.35)j=i});if(j!==k){k=j;paint()}}
  addEventListener('scroll',follow,{passive:true});
  addEventListener('keydown',e=>{if(!on||document.body.classList.contains('demoOn'))return;if(/INPUT|TEXTAREA|SELECT/.test(e.target.tagName))return;
    const m={PageDown:1,ArrowRight:1,PageUp:-1,ArrowLeft:-1}[e.key];if(m){e.preventDefault();go(k+m)}else if(e.key==='Home'){e.preventDefault();go(0)}else if(e.key==='End'){e.preventDefault();go(sl.length-1)}});
  addEventListener('message',e=>{if(e.data&&e.data.projKey&&on&&!document.body.classList.contains('demoOn'))go(k+(e.data.projKey==='next'?1:-1))});
  document.addEventListener('click',e=>{if(!on)return;const s=e.target.closest&&e.target.closest('.projSlide');if(!s)return;const i=sl.findIndex(g=>g.includes(s));if(i>=0&&i!==k)go(i,false)},true);
  const sync=()=>enable(R.classList.contains('proj'));
  new MutationObserver(sync).observe(R,{attributes:true,attributeFilter:['class']});
  if(document.readyState==='loading')addEventListener('DOMContentLoaded',()=>setTimeout(sync,300));else setTimeout(sync,300);
})();
