const $=id=>document.getElementById(id);let scene=null,lastReport=null;
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
async function load(){const r=await(await fetch("/api/scene?seed=7")).json();scene=r.scene;
 $("empty").classList.add("hidden");$("fp").textContent="· fingerprint "+r.fingerprint;
 $("object").innerHTML=scene.objects.map(o=>`<option>${o.id}</option>`).join("");draw(scene.objects);
 document.querySelectorAll(".stepper li").forEach((li,i)=>li.classList.toggle("on",i===1));}
$("start").onclick=load;
$("action").onchange=e=>$("approval").classList.toggle("hidden",e.target.value!=="remove");
$("run").onclick=async()=>{if(!scene)await load();
 const body={seed:7,action:$("action").value||null,object:$("object").value,dx:+$("dx").value,dy:+$("dy").value,
  approver:$("approver").value,approved:$("approved").checked};
 const res=await fetch("/api/run",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
 const r=await res.json();
 if(r.status==="APPROVAL_REQUIRED"){$("approval").classList.remove("hidden");$("status").textContent="Approval required — a named human must approve above, then verify again.";return;}
 if(r.error){$("status").textContent=r.error;return;}
 lastReport=r.report;const v=r.report.intervened||r.report.baseline;
 $("score").textContent=Math.round(v.score);$("arc").style.strokeDashoffset=327-327*v.score/100;
 $("arc").style.stroke=v.feasible?"#3ddc97":"#ff5d7a";
 $("verdict").textContent=(v.feasible?"FEASIBLE":"INFEASIBLE")+(r.report.effect!=null?` · counterfactual effect ${r.report.effect>=0?"+":""}${r.report.effect.toFixed(1)} pts`:"");
 $("violations").innerHTML=v.violations.length?v.violations.map(x=>`<li><b>[${x.rule}]</b> ${x.detail}</li>`).join(""):'<li class="dim">No violations. This world holds together.</li>';
 $("explain").textContent=r.report.explanation;$("src").textContent=r.report.explanation_source;
 $("head").textContent=r.report.ledger_head.slice(0,16)+"…";$("chain").textContent=r.chain_valid?"valid ✓":"BROKEN";
 draw(scene.objects,v.violations);
 document.querySelectorAll(".stepper li").forEach((li,i)=>li.classList.toggle("on",i===3));};
$("export").onclick=()=>{const b=new Blob([JSON.stringify(lastReport||{note:"run a verification first"},null,2)],{type:"application/json"});
 const a=document.createElement("a");a.href=URL.createObjectURL(b);a.download="sceneproof-report.json";a.click();};
