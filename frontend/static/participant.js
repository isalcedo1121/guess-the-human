import {requestJSON} from "./api.js";
const $ = id => document.getElementById(id);
const roomId = location.pathname.split("/").pop();
const key = `gth:submission:${roomId}`;
let receipt = null;
try { receipt = JSON.parse(localStorage.getItem(key)); } catch {}
if (!receipt || !/^[0-9a-f-]{36}$/i.test(receipt.id || "")) receipt = null;
function save() { try { localStorage.setItem(key, JSON.stringify(receipt)); } catch {} }
function error(text = "") { $("submission-error").textContent = text; $("submission-error").hidden = !text; }
function confirm() {
  if (receipt) {receipt.completed = true; save();}
  $("answer-form").hidden = true; error(); $("submission-confirmation").hidden = false;
}
function uuid() {
  if (crypto.randomUUID) return crypto.randomUUID();
  const b=crypto.getRandomValues(new Uint8Array(16)); b[6]=(b[6]&15)|64; b[8]=(b[8]&63)|128;
  const h=Array.from(b,x=>x.toString(16).padStart(2,"0")).join("");
  return `${h.slice(0,8)}-${h.slice(8,12)}-${h.slice(12,16)}-${h.slice(16,20)}-${h.slice(20)}`;
}
$("submission").addEventListener("input",()=>{$("character-total").textContent=$("submission").value.length;});
$("answer-form").addEventListener("submit", async event => {
  event.preventDefault(); const button=$("submit-answer"); if(button.disabled)return;
  const answer=$("submission").value.trim();
  if(answer.length<2||answer.length>280) return error("Enter an answer between 2 and 280 characters.");
  if(!receipt) receipt={id:uuid(),completed:false}; save();
  button.disabled=true;button.textContent="Submitting…";error();
  try {
    const result=await requestJSON(`/api/rooms/${roomId}/submissions`,{method:"POST",body:JSON.stringify({submission_id:receipt.id,answer})});
    if(!result.accepted)throw new Error("Couldn’t confirm your answer. Please try again.");
    confirm();
  }catch(e){error(e.message);}finally{button.disabled=false;button.textContent="Submit →";}
});
async function load(){
  try{
    const room=await requestJSON(`/api/rooms/${encodeURIComponent(roomId)}${receipt?`?submission_id=${receipt.id}`:""}`);
    $("participant-question").textContent=room.question;$("participant-question-card").hidden=false;
    if(room.submitted)confirm();
    else if(room.status!=="open"){$("participant-message").textContent="Submissions are closed.";$("participant-message").hidden=false;}
    else $("answer-form").hidden=false;
  }catch(e){error(e.message);}
}
load();
