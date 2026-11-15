import * as THREE from 'three';
import { gsap } from 'gsap';

type SceneHost = HTMLElement & { _dispose?:()=>void };
const reduced = matchMedia('(prefers-reduced-motion: reduce)');
const pref = () => {try{return localStorage.getItem('lr-world')||'auto';}catch{return 'auto';}};
const lowPower = () => (navigator as Navigator & {connection?:{saveData?:boolean};deviceMemory?:number}).connection?.saveData || ((navigator as Navigator & {deviceMemory?:number}).deviceMemory||8)<4;

export function startScene(host:SceneHost) {
  host._dispose?.();
  const canvas=host.querySelector('canvas')!;
  const fallback=host.querySelector<HTMLElement>('.world-fallback')!;
  if(pref()==='2d' || reduced.matches || (pref()!=='3d' && lowPower())) {canvas.hidden=true;fallback.hidden=false;host.dataset.state='2d';return;}
  let renderer:THREE.WebGLRenderer;
  try {renderer=new THREE.WebGLRenderer({canvas,antialias:devicePixelRatio<2,alpha:true,powerPreference:'low-power'});} catch {canvas.hidden=true;fallback.hidden=false;host.dataset.state='2d';return;}
  canvas.hidden=false;fallback.hidden=true;host.dataset.state='3d';
  renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));
  renderer.shadowMap.enabled=true; renderer.shadowMap.type=THREE.PCFSoftShadowMap;
  renderer.outputColorSpace=THREE.SRGBColorSpace; renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.25;
  const scene=new THREE.Scene(), theme=host.dataset.theme||'garden', night=theme==='night';
  const camera=new THREE.PerspectiveCamera(35,1,.1,80); camera.position.set(9,7.7,12.5); camera.lookAt(0,1,0);
  scene.add(new THREE.HemisphereLight(night?0x9bc8ff:0xfffae7,0x698875,night?2.4:3));
  const sun=new THREE.DirectionalLight(night?0xacc7ff:0xffe4ad,night?3:4.8);sun.position.set(-5,9,6);sun.castShadow=true;sun.shadow.mapSize.set(1024,1024);sun.shadow.camera.left=-7;sun.shadow.camera.right=7;sun.shadow.camera.top=7;sun.shadow.camera.bottom=-7; sun.shadow.bias=-.001;scene.add(sun);
  const mat=(color:number,roughness=.75)=>new THREE.MeshStandardMaterial({color,roughness});
  const materials = {grass:mat(night?0x618b97:0x93c69b),soil:mat(0xb89e83),cream:mat(0xffedc9),white:mat(0xfff7e9),pink:mat(0xefaca8),dark:mat(0x333e3d),trunk:mat(0x967765),leaf:mat(0x74aa84),leaf2:mat(0xb5d49a),gold:mat(0xe9b85d,.45),blue:mat(0x7fbdcb,.35),coral:mat(0xe88c72),purple:mat(0xa69ac6)};
  const island=new THREE.Group();scene.add(island);
  function mesh(geo:THREE.BufferGeometry,m:THREE.Material,parent:THREE.Object3D,x=0,y=0,z=0){const obj=new THREE.Mesh(geo,m);obj.position.set(x,y,z);obj.castShadow=true;obj.receiveShadow=true;parent.add(obj);return obj;}
  function ball(parent:THREE.Object3D,m:THREE.Material,x:number,y:number,z:number,sx:number,sy=sx,sz=sx){const obj=mesh(new THREE.SphereGeometry(1,20,14),m,parent,x,y,z);obj.scale.set(sx,sy,sz);return obj;}
  function box(parent:THREE.Object3D,m:THREE.Material,x:number,y:number,z:number,sx:number,sy:number,sz:number){return mesh(new THREE.BoxGeometry(sx,sy,sz),m,parent,x,y,z);}
  const soil=mesh(new THREE.CylinderGeometry(4.4,3.7,1.05,64),materials.soil,island,0,-.65,0);soil.scale.z=.83;
  const lawn=mesh(new THREE.CylinderGeometry(4.48,4.4,.23,64),materials.grass,island,0,-.04,0);lawn.scale.z=.83;
  const rim=mesh(new THREE.TorusGeometry(4.35,.09,8,72),materials.leaf2,island,0,.04,0);rim.rotation.x=Math.PI/2;rim.scale.y=.83;
  // A tiny meandering river and a waterfall, made from geometry rather than textures.
  const river=ball(island,materials.blue,1.95,.1,-.5,.53,.06,2.1);river.rotation.y=-.3;
  const fall=box(island,materials.blue,2.53,-.65,2.61,.54,1.5,.13);
  for(let i=0;i<4;i++) ball(island,materials.white,2.3+i*.15,-1.4,2.7,.15,.08,.13);
  const trees:THREE.Group[]=[];
  function tree(x:number,z:number,s=1){const g=new THREE.Group();g.position.set(x,0,z);g.scale.setScalar(s);island.add(g);mesh(new THREE.CylinderGeometry(.12,.19,1.8,9),materials.trunk,g,0,.9,0);ball(g,materials.leaf,0,2.2,0,.8,.96,.8);ball(g,materials.leaf2,-.4,1.85,.14,.58,.65,.55);ball(g,materials.leaf2,.4,2.2,.15,.45,.55,.5);trees.push(g);return g;}
  tree(-2.75,-1.2,1.15);tree(-1.9,-2.3,.8);tree(2.6,-1.7,1.08);tree(3,-.4,.65);if(theme==='jungle'){tree(-3,.1,.7);tree(1.2,-2.5,.85);tree(-.5,-2.9,.7);}
  const stones:THREE.Material[]=[materials.cream,materials.coral,materials.purple];
  for(let i=0;i<8;i++){ball(island,stones[i%3],-2+i*.47,.12,2.2+Math.sin(i)*.1,.22,.06,.17);}
  // Colourful petal flowers, grouped and shared materials.
  for(let i=0;i<24;i++) {const angle=i*2.4, radius=2.6+(i%4)*.27;const x=Math.cos(angle)*radius,z=Math.sin(angle)*radius*.8;if(x>1.5&&z>0)continue;const g=new THREE.Group();g.position.set(x,.1,z);island.add(g);mesh(new THREE.CylinderGeometry(.016,.02,.28,5),materials.leaf,g,0,.14,0);const petal=i%3?materials.pink:materials.gold;for(let p=0;p<5;p++)ball(g,petal,Math.cos(p*1.257)*.09,.32+Math.sin(p*1.257)*.09,0,.065,.065,.035);ball(g,materials.gold,0,.32,.02,.04);}
  // The opening book is the focal point. Each cover rotates about its spine.
  const book=new THREE.Group();book.position.set(0,.4,.5);book.rotation.x=-.16;book.rotation.y=-.1;island.add(book);
  const covers:THREE.Group[]=[];
  [-1,1].forEach(side=>{const cover=new THREE.Group();book.add(cover);covers.push(cover);box(cover,materials.coral,side*.79,0,0,1.62,.13,2);box(cover,materials.white,side*.77,.1,0,1.48,.12,1.85);box(cover,materials.cream,side*.77,.18,0,1.44,.04,1.8);for(let l=0;l<5;l++)box(cover,materials.gold,side*.8,.208,-.5+l*.2,.85,.008,.018);cover.rotation.z=side*1.38;});
  const spine=mesh(new THREE.CylinderGeometry(.1,.1,2,12),materials.gold,book,0,0,0);spine.rotation.x=Math.PI/2;
  const twinkles:THREE.Object3D[]=[];
  function star(parent:THREE.Object3D,x:number,y:number,z:number,size:number){const shape=new THREE.Shape();for(let i=0;i<10;i++){const r=i%2?.42:1, a=Math.PI/2+i*Math.PI/5;const px=Math.cos(a)*r,py=Math.sin(a)*r;i?shape.lineTo(px,py):shape.moveTo(px,py);}shape.closePath();const s=mesh(new THREE.ExtrudeGeometry(shape,{depth:.17,bevelEnabled:true,bevelSize:.07,bevelThickness:.06,bevelSegments:2,steps:1}),materials.gold,parent,x,y,z);s.scale.setScalar(size);s.rotation.z=-.18;twinkles.push(s);return s;}
  star(book,-.6,1.5,0,.3);star(book,.4,1.9,-.25,.22);star(book,.9,1.15,.1,.17);
  // Original mascot Pip, with soft rounded ears, embroidered face and a neckerchief.
  function bunny(x:number,z:number){const g=new THREE.Group();g.position.set(x,.15,z);island.add(g);ball(g,materials.white,0,.48,0,.42,.56,.35);ball(g,materials.white,0,1.09,.03,.47,.44,.39);[-1,1].forEach(side=>{const ear=ball(g,materials.white,side*.22,1.68,0,.14,.5,.13);ear.rotation.z=side*-.16;const inner=ball(g,materials.pink,side*.22,1.7,.11,.07,.34,.025);inner.rotation.z=side*-.16;ball(g,materials.dark,side*.17,1.14,.38,.036,.045,.025);ball(g,materials.pink,side*.26,1,.37,.085,.045,.018);ball(g,materials.white,side*.25,.08,.12,.23,.11,.27);});ball(g,materials.pink,0,1.03,.425,.047,.03,.02);const arm=ball(g,materials.white,-.46,.65,.02,.13,.3,.15);arm.rotation.z=-.55;ball(g,materials.white,.43,.62,.05,.13,.28,.14);mesh(new THREE.TorusGeometry(.29,.07,8,24),materials.coral,g,0,.78,.02).rotation.x=Math.PI/2;g.rotation.y=.25;return {g,arm};}
  const pip=bunny(-1.9,1.25);
  function bear(x:number,z:number,elephant=false){const g=new THREE.Group();g.position.set(x,.12,z);g.scale.setScalar(elephant?.83:.72);island.add(g);const color=elephant?materials.blue:materials.soil;ball(g,color,0,.45,0,.5,.58,.4);ball(g,color,0,1.1,0,.49,.46,.4);[-1,1].forEach(side=>{ball(g,color,side*.4,elephant?1.12:1.43,0,elephant?.32:.18,elephant?.4:.18,.15);ball(g,materials.dark,side*.17,1.17,.36,.038);ball(g,color,side*.3,.1,.15,.23,.13,.24);});if(elephant){ball(g,color,0,.85,.45,.11,.38,.12);ball(g,color,.09,.55,.47,.15,.1,.13);}else{ball(g,materials.cream,0,.99,.36,.25,.16,.1);ball(g,materials.dark,0,1.06,.46,.07,.04,.03);}return g;}
  bear(2.9,1.05,true);const littleBear=bear(-.5,-1.75);
  const bird=new THREE.Group();bird.position.set(.15,3.3,-.1);island.add(bird);ball(bird,materials.coral,0,0,0,.2,.18,.28);const wing=ball(bird,materials.gold,.22,0,0,.28,.04,.12);ball(bird,materials.gold,-.22,0,0,.28,.04,.12);const beak=mesh(new THREE.ConeGeometry(.065,.15,7),materials.gold,bird,0,.01,.3);beak.rotation.x=Math.PI/2;
  const clouds:THREE.Group[]=[];
  for(let i=0;i<3;i++){const g=new THREE.Group();g.position.set(-3+i*3,4.4+(i%2)*.7,-2.4);scene.add(g);ball(g,materials.white,0,0,0,.65,.23,.24);ball(g,materials.white,-.25,.16,0,.28);ball(g,materials.white,.15,.2,0,.35);clouds.push(g);}
  // An arched rainbow in the back of the miniature world.
  if(!night&&theme!=='ocean'&&theme!=='rain'){[0xe99886,0xe8bb65,0xaacb9c,0x8cbfc7,0xb1a0c8].forEach((c,i)=>{const arc=mesh(new THREE.TorusGeometry(2.3-i*.13,.055,8,56,Math.PI),mat(c),scene,0,1.7,-2.45);arc.rotation.y=-.12;});}
  else if(night) {ball(scene,materials.cream,2.4,4.3,-2.6,.6);for(let i=0;i<14;i++)star(scene,-4+(i*1.31)%8,2.8+(i*.57)%2.5,-3,.07+(i%3)*.02);}
  const fishSchool:THREE.Group[]=[],bubbles:THREE.Mesh[]=[];
  let rainDrops:THREE.InstancedMesh|undefined;
  if(theme==='ocean'){
    lawn.material=materials.blue;trees.forEach(t=>t.visible=false);clouds.forEach(c=>c.visible=false);
    const bubbleMaterial=new THREE.MeshStandardMaterial({color:0xd5f3ed,transparent:true,opacity:.4,roughness:.2});
    for(let i=0;i<12;i++){const bubble=ball(scene,bubbleMaterial,-3+(i*.83)%6,.7+(i*.7)%4,-2-(i%3)*.4,.07+(i%4)*.025);bubbles.push(bubble);}
    for(let i=0;i<7;i++){const fish=new THREE.Group();fish.position.set(-2.8+i*.9,1+(i%3)*.3,-1.5);island.add(fish);const color=i%2?materials.coral:materials.gold;ball(fish,color,0,0,0,.22,.13,.12);const tail=mesh(new THREE.ConeGeometry(.15,.22,3),color,fish,-.28,0,0);tail.rotation.z=Math.PI/2;ball(fish,materials.dark,.12,.04,.1,.02);fishSchool.push(fish);}
    for(let i=0;i<9;i++){const weed=new THREE.Group();weed.position.set(-3+i*.7,.15,-2.1);island.add(weed);for(let j=0;j<3;j++){const leaf=ball(weed,materials.leaf2,Math.sin(j)*.1,.2+j*.27,0,.11,.27,.045);leaf.rotation.z=Math.sin(j)*.3;}trees.push(weed);}
  }
  if(theme==='rain'){
    clouds.forEach(c=>c.position.y=3.6);
    rainDrops=new THREE.InstancedMesh(new THREE.CylinderGeometry(.012,.012,.12,4),materials.blue,80);scene.add(rainDrops);
  }
  // Actual raycast controls have equivalent links outside the canvas.
  const targets:THREE.Object3D[]=[]; book.traverse(o=>{if(o instanceof THREE.Mesh){o.userData.action='book';targets.push(o);}});pip.g.traverse(o=>{if(o instanceof THREE.Mesh){o.userData.action='pip';targets.push(o);}});
  const ray=new THREE.Raycaster(),point=new THREE.Vector2();let pointerX=0,pointerY=0;
  const move=(e:PointerEvent)=>{const r=canvas.getBoundingClientRect();point.set((e.clientX-r.left)/r.width*2-1,-((e.clientY-r.top)/r.height*2-1));pointerX=point.x*.15;pointerY=point.y*.08;ray.setFromCamera(point,camera);canvas.style.cursor=ray.intersectObjects(targets).length?'pointer':'default';};
  const click=()=>{ray.setFromCamera(point,camera);const hit=ray.intersectObjects(targets)[0];if(!hit)return;if(hit.object.userData.action==='book'){if(!document.querySelector('[data-reader]')){location.assign('/poems/?collection=verified');return;}gsap.fromTo(book.position,{y:.4},{y:.85,duration:.45,yoyo:true,repeat:1});const label=host.querySelector<HTMLElement>('.world-message');if(label)label.textContent='Your adventure is ready. Choose “Explore poems” to open the library.';}else{gsap.to(pip.arm.rotation,{z:-1.6,duration:.3,yoyo:true,repeat:3});const label=host.querySelector<HTMLElement>('.world-message');if(label)label.textContent='Hello, I’m Pip! Tap a poem and we’ll discover it together.';}};
  canvas.addEventListener('pointermove',move);canvas.addEventListener('click',click);
  const timeline=gsap.timeline();timeline.to(covers[0].rotation,{z:-.16,duration:2,ease:'power2.out'},.3).to(covers[1].rotation,{z:.16,duration:2,ease:'power2.out'},.3);timeline.from(island.position,{y:-.6,duration:2,ease:'power2.out'},0);
  let visible=true,frame=0,last=0,t=0,disposed=false,activeLine=-1;
  const focus=(e:Event)=>{const line=(e as CustomEvent<{line:number}>).detail.line;activeLine=line;if(line>=0){const s=twinkles[line%twinkles.length];gsap.fromTo(s.scale,{x:.45,y:.45,z:.45},{x:.22,y:.22,z:.22,duration:1});gsap.to(book.rotation,{y:Math.sin(line*.5)*.18,duration:1});if(theme==='jungle')gsap.to(pip.arm.rotation,{z:-1.3,duration:.35,yoyo:true,repeat:1});if(theme==='rain')gsap.fromTo(clouds[line%clouds.length].scale,{x:1.08,y:1.08,z:1.08},{x:1,y:1,z:1,duration:1});}};
  document.addEventListener('rhyme-line',focus);
  const draw=(now:number)=>{frame=requestAnimationFrame(draw);if(!visible||document.hidden||now-last<33)return;const delta=Math.min((now-last)/1000,.05);last=now;t+=delta;island.rotation.y=Math.sin(t*.22)*.045+pointerX;island.rotation.x=pointerY;pip.g.position.y=.15+Math.sin(t*1.3)*.035;pip.arm.rotation.x=Math.sin(t*.8)*.08;bird.position.x=Math.sin(t*.6)*1.3;bird.position.y=3.3+Math.sin(t*.9)*.17;wing.rotation.z=Math.sin(t*5)*.4;trees.forEach((g,i)=>g.rotation.z=Math.sin(t*.65+i)*.017);clouds.forEach((g,i)=>g.position.x=-3+i*3+Math.sin(t*.12+i)*.25);twinkles.forEach((s,i)=>{s.rotation.y=Math.sin(t*.4+i)*.18;});fall.scale.x=1+Math.sin(t*2)*.06;fishSchool.forEach((f,i)=>{f.position.x=-3.3+((t*.25+i*.9)%6.6);f.position.y=1+(i%3)*.3+Math.sin(t+i)*.12;});bubbles.forEach((bubble,i)=>{bubble.position.y=.4+((t*.22+i*.7)%4.5);});if(rainDrops){const dummy=new THREE.Object3D();for(let i=0;i<80;i++){dummy.position.set(-3.8+(i*.47)%7.6,.3+((i*.37-t*1.6+1000)%3.8),-2.5+(i*.71)%4);dummy.rotation.z=-.12;dummy.updateMatrix();rainDrops.setMatrixAt(i,dummy.matrix);}rainDrops.instanceMatrix.needsUpdate=true;}renderer.render(scene,camera);renderedFrames++;};
  const resize=new ResizeObserver(()=>{const w=host.clientWidth,h=host.clientHeight;renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();});resize.observe(host);
  const onVisibility=()=>{if(document.hidden||!visible)timeline.pause();else timeline.resume();};document.addEventListener('visibilitychange',onVisibility);
  const intersection=new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;onVisibility();},{rootMargin:'100px'});intersection.observe(host);
  frame=requestAnimationFrame(draw);
  // If even this small scene cannot sustain 15fps, switch to the lightweight picture.
  let slow=0,previous=performance.now(),samples=0,renderedFrames=0;const performanceCheck=setInterval(()=>{if(!visible||document.hidden)return;const now=performance.now();const fps=renderedFrames/(now-previous)*1000;renderedFrames=0;previous=now;samples++;if(fps<14)slow++;if(samples>=4){clearInterval(performanceCheck);if(slow>=3&&pref()==='auto'){host.dataset.performance='low';dispose();canvas.hidden=true;fallback.hidden=false;host.dataset.state='2d';}}},1800);

  function dispose(){if(disposed)return;disposed=true;cancelAnimationFrame(frame);clearInterval(performanceCheck);resize.disconnect();intersection.disconnect();timeline.kill();gsap.killTweensOf(book);canvas.removeEventListener('pointermove',move);canvas.removeEventListener('click',click);document.removeEventListener('rhyme-line',focus);document.removeEventListener('visibilitychange',onVisibility);scene.traverse(o=>{if(o instanceof THREE.Mesh){o.geometry.dispose();const ms=Array.isArray(o.material)?o.material:[o.material];ms.forEach(m=>m.dispose());}});renderer.dispose();}
  host._dispose=dispose;
}
