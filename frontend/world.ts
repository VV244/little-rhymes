type Host=HTMLElement & {_dispose?:()=>void};
const hosts=[...document.querySelectorAll<Host>('[data-world]')];
const reduced=matchMedia('(prefers-reduced-motion: reduce)');
let generation=0;
function preference(){try{return localStorage.getItem('lr-world')||'auto';}catch{return 'auto';}}
function label(host:Host,unavailable=false){const b=document.querySelector<HTMLButtonElement>('#world-toggle');if(!b)return;const is3d=host.dataset.state==='3d';b.textContent=unavailable?'2D view · 3D unavailable':reduced.matches?'2D · Reduced motion':is3d?'Use 2D':'Try 3D';b.disabled=unavailable||reduced.matches;b.setAttribute('aria-pressed',String(is3d));}
async function boot(host:Host){const token=++generation;host._dispose?.();const canvas=host.querySelector('canvas')!,picture=host.querySelector<HTMLElement>('.world-fallback')!;canvas.hidden=true;picture.hidden=false;host.dataset.state='2d';const pref=preference(),nav=navigator as Navigator&{connection?:{saveData?:boolean};deviceMemory?:number};if(reduced.matches||pref==='2d'||(pref==='auto'&&(nav.connection?.saveData||(nav.deviceMemory||8)<4))){label(host);return;}
 // Avoid downloading the 3D engine on unsupported devices or in 2D mode.
 let supported=false;try{supported=!!canvas.getContext('webgl2',{alpha:true,powerPreference:'low-power'});}catch{/* Keep the fully usable illustrated version. */}
 if(!supported){label(host,true);return;}try{const {startScene}=await import('./scene');if(token!==generation)return;startScene(host);label(host);}catch{canvas.hidden=true;picture.hidden=false;host.dataset.state='2d';label(host,true);}}
const observer=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting){observer.unobserve(e.target);void boot(e.target as Host);}}),{rootMargin:'150px'});hosts.forEach(h=>observer.observe(h));
window.addEventListener('world-preference',()=>hosts.forEach(h=>void boot(h)));reduced.addEventListener('change',()=>hosts.forEach(h=>void boot(h)));window.addEventListener('pagehide',()=>{generation++;hosts.forEach(h=>h._dispose?.());observer.disconnect();});
