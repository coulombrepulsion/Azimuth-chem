/* ---------- светлая / тёмная тема ---------- */
(function(){const R=document.documentElement,mq=window.matchMedia.bind(window),sys=mq('(prefers-color-scheme: dark)'),L=new Set();
  let pref=null;try{const s=localStorage.getItem('qc-theme');if(s==='light'||s==='dark')pref=s}catch(e){}
  let framed=false;try{framed=window.parent!==window&&!!window.parent.document.documentElement}catch(e){}
  if(framed){pref=null;try{const t=window.parent.document.documentElement.getAttribute('data-theme');if(t)R.setAttribute('data-theme',t);else R.removeAttribute('data-theme')}catch(e){}}
  const dark=()=>{const t=R.getAttribute('data-theme');return t==='dark'||(t!=='light'&&sys.matches)};
  window.matchMedia=function(q){if(!/prefers-color-scheme/.test(q))return mq(q);const want=/dark/.test(q);
    return {media:q,onchange:null,get matches(){return dark()===want},addEventListener(t,f){if(t==='change')L.add(f)},removeEventListener(t,f){L.delete(f)},addListener(f){L.add(f)},removeListener(f){L.delete(f)},dispatchEvent(){return true}}};
  let last=null,btn=null,inHub=framed;if(framed)R.classList.add('inHub');
  function lab(){if(!btn)return;const d=dark();btn.textContent=d?'☀':'☾';btn.title=d?'Light theme':'Dark theme';btn.setAttribute('aria-label',btn.title)}
  function fire(){if(pref&&!inHub&&R.getAttribute('data-theme')!==pref){R.setAttribute('data-theme',pref);return}
    const d=dark();lab();if(d===last)return;last=d;L.forEach(f=>{try{f({matches:d,media:'(prefers-color-scheme: dark)'})}catch(e){console.error(e)}})}
  if(pref)R.setAttribute('data-theme',pref);last=dark();
  sys.addEventListener('change',fire);new MutationObserver(fire).observe(R,{attributes:true,attributeFilter:['data-theme']});
  addEventListener('message',e=>{if(e.data&&e.data.hub){inHub=true;R.classList.add('inHub')}});
  function init(){btn=document.createElement('button');btn.type='button';btn.className='themeBtn';
    btn.onclick=()=>{pref=dark()?'light':'dark';try{localStorage.setItem('qc-theme',pref)}catch(e){}R.setAttribute('data-theme',pref)};
    document.body.appendChild(btn);lab()}
  if(document.readyState==='loading')addEventListener('DOMContentLoaded',init);else init();
})();
