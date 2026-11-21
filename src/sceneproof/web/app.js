const $=id=>document.getElementById(id);let scene=null,lastReport=null,sceneSource=null;
const COLORS={crate:"#6d7cff",robot:"#3ddc97",human:"#ffb84d",barrel:"#c792ff",cone:"#ff8fa3",vehicle:"#4dc9ff",shelf:"#5b6b9f"};
function draw(objects,violations=[]){
 const c=$("stage"),x=c.getContext("2d"),W=c.width,H=c.height;x.clearRect(0,0,W,H);
 x.strokeStyle="#232c4d";x.beginPath();x.moveTo(0,H-40);x.lineTo(W,H-40);x.stroke();
 const bad=new Set(violations.flatMap(v=>v.objects));
 for(const o of objects){const px=o.x*W,py=H-40-(o.y+o.h)*H,pw=o.w*W,ph=o.h*H;
  x.fillStyle=(COLORS[o.kind]||"#888")+"33";x.fillRect(px,py,pw,ph);
  x.strokeStyle=bad.has(o.id)?"#ff5d7a":(COLORS[o.kind]||"#888");x.lineWidth=bad.has(o.id)?3:1.5;
  x.setLineDash([6,4]);x.strokeRect(px,py,pw,ph);x.setLineDash([]);
  x.fillStyle="#eef1ff";x.font="13px system-ui";x.fillText(`${o.id} · ${o.kind}`,px+6,py+18);}
}
const seed = 7;
let busy = false;

async function json(url, options={}) {
 const response=await fetch(url,{...options,signal:AbortSignal.timeout(20000)});
 const body=await response.json();
 if(!response.ok)throw Error(body.error||'The scene service could not complete this request.');
 return body;
}
function setStage(index){
 document.querySelectorAll('.stepper li').forEach((li,i)=>li.classList.toggle('on',i===index));
}
function syncInput(){
 const action=$('action').value,object=scene?.objects.find(o=>o.id===$('object').value);
 $('approval').classList.toggle('hidden',action!=='remove'&&!(action&&['human','vehicle'].includes(object?.kind)));
 $('offsets').classList.toggle('hidden',action!=='move');
 $('dimensions').classList.toggle('hidden',action!=='resize');
 if(object){$('width').value=String(object.w);$('height').value=String(object.h);}
 $('approved').checked=false;
}
function inspect(view){
 const current=view==='intervened'&&lastReport?.intervened_scene ? lastReport.intervened_scene : scene;
 if(!current)return;
 const verdict=view==='intervened' ? lastReport?.intervened : lastReport?.baseline;
 draw(current.objects,verdict?.violations||[]);
}
function invalidate(){
 lastReport=null;
 $('export').disabled=true;
 $('scene-view').value='baseline';
 $('scene-view').disabled=true;
 $('score').textContent='—';
 $('arc').style.strokeDashoffset=327;
 $('verdict').textContent='Run a verification to score this world.';
 $('violations').replaceChildren();
 $('explain').textContent='Explanation appears here after verification.';
 $('src').textContent='';
 $('head').textContent='GENESIS';
 $('chain').textContent='—';
 if(scene)inspect('baseline');
}
function selectScene(data){
 scene=data.scene;
 sceneSource=data.source;
 $('empty').classList.add('hidden');
 $('fp').textContent=`· ${sceneSource==='USER_SUPPLIED'?'Imported scene':'Demo fixture'} · ${data.fingerprint}`;
 $('object').replaceChildren(...scene.objects.map(o=>new Option(o.id,o.id)));
 $('action').value='';
 syncInput();
 setStage(1);
 invalidate();
}
async function load(){
 selectScene(await json('/api/scene?seed='+seed));
}
async function action(work){
 if(busy)return;
 busy=true;
 for(const id of ['start','scene-file','run','object','action','dx','dy','width','height','explain-model','approver','approved'])$(id).disabled=true;
 try{$('status').textContent='Working…';await work();}
 catch(error){$('status').textContent=error.name==='TimeoutError'?'The request timed out. Try again.':error.message;}
 finally{busy=false;for(const id of ['start','scene-file','run','object','action','dx','dy','width','height','explain-model','approver','approved'])$(id).disabled=false;}
}
$('start').onclick=()=>action(async()=>{await load();$('status').textContent='Demo scene loaded.';});
$('scene-file').onchange=event=>{
 const file=event.currentTarget.files[0];
 event.currentTarget.value='';
 if(!file)return;
 void action(async()=>{
  if(file.size>65_000)throw Error('Choose a JSON file under 64 KiB.');
  let input;
  try{input=JSON.parse((await file.text()).replace(/^\uFEFF/,''));}
  catch{throw Error('Choose a valid scene JSON file.');}
  selectScene(await json('/api/scene',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify(input?.baseline_scene??input)}));
  $('status').textContent='Imported scene is ready to verify.';
 });
};
for(const id of ['object','action'])$(id).onchange=()=>{syncInput();invalidate();};
for(const id of ['dx','dy','width','height'])$(id).oninput=invalidate;
$('scene-view').onchange=()=>inspect($('scene-view').value);
$('run').onclick=()=>action(async()=>{
 if(!scene)await load();
 const type=$('action').value;
 const body={...(sceneSource==='USER_SUPPLIED'?{scene}:{seed}),action:type||null,object:$('object').value,
   ...(type==='move'?{dx:$('dx').valueAsNumber||0,dy:$('dy').valueAsNumber||0}:{}),
   ...(type==='resize'?{w:$('width').valueAsNumber,h:$('height').valueAsNumber}:{}),
   approver:$('approver').value,approved:$('approved').checked,explain:$('explain-model').checked};
 if(type==='resize'&&![body.w,body.h].every(n=>Number.isFinite(n)&&n>0&&n<=2))throw Error('Enter width and height between 0 and 2.');
 const result=await json('/api/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 if(result.status==='APPROVAL_REQUIRED'){
  $('approval').classList.remove('hidden');
  $('status').textContent='A named approver must approve this intervention before verification.';
  return;
 }
 lastReport=result.report;
 const verdict=lastReport.intervened||lastReport.baseline;
 $('score').textContent=Math.round(verdict.score);
 $('arc').style.strokeDashoffset=327-327*verdict.score/100;
 $('arc').style.stroke=verdict.feasible?'#3ddc97':'#ff5d7a';
 $('verdict').textContent=(verdict.feasible?'FEASIBLE':'INFEASIBLE')+(lastReport.effect===null?'':` · counterfactual effect ${lastReport.effect>=0?'+':''}${lastReport.effect.toFixed(1)} pts`);
 const items=verdict.violations.map(value=>{
  const item=document.createElement('li');
  item.textContent=`[${value.rule}] ${value.detail}`;return item;
 });
 if(!items.length){const item=document.createElement('li');item.textContent='No violations found.';items.push(item);}
 $('violations').replaceChildren(...items);
 $('explain').textContent=lastReport.explanation;
 $('src').textContent=lastReport.explanation_source;
 $('head').textContent=lastReport.ledger_head.slice(0,16)+'…';
 $('chain').textContent=result.chain_valid?'valid ✓':'BROKEN';
 $('scene-view').disabled=!lastReport.intervened_scene;
 $('scene-view').value=lastReport.intervened_scene?'intervened':'baseline';
 $('export').disabled=false;
 inspect($('scene-view').value);
 setStage(3);
 $('status').textContent='Verification recorded. Switch views to inspect the geometry.';
});
$('export').onclick=()=>{
 if(!lastReport)return;
 const bundle={...lastReport,baseline_scene:scene,scene_source:sceneSource,schema_version:1};
 const url=URL.createObjectURL(new Blob([JSON.stringify(bundle,null,2)],{type:'application/json'}));
 const link=document.createElement('a');link.href=url;link.download='sceneproof-report.json';link.click();
 setTimeout(()=>URL.revokeObjectURL(url),1000);
};
syncInput();
