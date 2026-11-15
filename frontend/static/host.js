import {requestJSON} from "./api.js";
import {unlockSounds, playSound, playWrong} from "./sounds.js";
const questionSelect = document.getElementById("question-select");
const customQuestion = document.getElementById("custom-question");
const customField = document.getElementById("custom-question-field");
const roundCount = document.getElementById("round-count");

function updateQuestion() {
  const isCustom = questionSelect.value === "custom";
  customField.hidden = !isCustom;
  customQuestion.required = isCustom;
  const text = isCustom ? customQuestion.value.trim() : questionSelect.value;
  for (const question of document.querySelectorAll("[data-question]")) {
    question.textContent = text;
  }
}

questionSelect.addEventListener("change", updateQuestion);
customQuestion.addEventListener("input", updateQuestion);


const $=id=>document.getElementById(id);
let room=null,timer=null,busy=false,celebrated=null;
function message(id,text=""){$(id).textContent=text;$(id).hidden=!text;}
function screen(id){const changed=$(id).hidden;for(const el of document.querySelectorAll(".screen"))el.hidden=el.id!==id;if(changed)window.scrollTo({top:0,behavior:"smooth"});}
function render(data){
 room=data; clearTimeout(timer); $("new-game").hidden=false;
 $("room-link").value=`${location.origin}/room/${room.id}`;
 $("submission-count").textContent=room.submission_count;
 document.querySelector("#lobby [data-question]").textContent=room.question;
 $("room-status").textContent=room.status==="open"?"open!":"closed.";
 $("lobby-heading").textContent=room.status==="open"?"Waiting for answers":"Answers collected";
 $("close-room").disabled=room.status!=="open"||busy;
 $("close-room").hidden=room.status!=="open";
 $("add-samples").hidden=room.status!=="open";
 $("start-game").hidden=!["open","closed","ready"].includes(room.status);
 $("start-game").disabled=busy||room.submission_count===0;
 if(room.status==="generating")screen("generating");
 else if(room.game && ["playing","finished"].includes(room.status))renderGame();
 else screen("lobby");
 if(["open","generating"].includes(room.status)&&!document.hidden)timer=setTimeout(refresh,5000);
}
async function refresh(){
 clearTimeout(timer);if(!room||busy)return;
 try{const previous=room.status;const data=await requestJSON(`/api/rooms/${room.id}/host`);if(busy||room.status!==previous)return;render(data);message("lobby-error");$("refresh-count").hidden=true;}
 catch(e){message("lobby-error",e.message);$("refresh-count").hidden=false;if(e.status!==403&&!document.hidden&&["open","generating"].includes(room.status))timer=setTimeout(refresh,5000);}
}
$("setup-form").addEventListener("submit",async event=>{
 event.preventDefault();if(busy)return;
 const question=questionSelect.value==="custom"?customQuestion.value.trim():questionSelect.value;
 if(question.length<2||question.length>200)return message("setup-error","Enter a question between 2 and 200 characters.");
 busy=true;$("create-room").disabled=true;message("setup-error");
 try{const data=await requestJSON("/api/rooms",{method:"POST",body:JSON.stringify({question,rounds:Number(roundCount.value)})});
 history.replaceState(null,"",`/host/${data.id}`);busy=false;render(data);}
 catch(e){message("setup-error",e.message);}finally{busy=false;$("create-room").disabled=false;}
});
async function action(name,body={}){
 if(busy||!room)return;unlockSounds();busy=true;clearTimeout(timer);message("game-error");message("lobby-error");
 document.querySelectorAll("[data-action],[data-guess],#add-samples,#start-game,#close-room").forEach(x=>x.disabled=true);
 if(name==="begin")screen("generating");
 try{const data=await requestJSON(`/api/rooms/${room.id}/${name}`,{method:"POST",body:JSON.stringify(body)});playTransitionSound(name,room,data);busy=false;render(data);}
 catch(e){busy=false;try{render(await requestJSON(`/api/rooms/${room.id}/host`));}catch{render(room);}message("game-error",e.message);}
 finally{busy=false;document.querySelectorAll("[data-action],[data-guess],#add-samples,#start-game").forEach(x=>x.disabled=false);$("close-room").disabled=room.status!=="open";$("start-game").disabled=room.submission_count===0;}
}
function playTransitionSound(action,previous,next){
 if(next.status==="finished"&&previous.status!=="finished")playSound(next.game.assessed>0&&next.game.accuracy>=70?"win":"lose");
 else if(action==="guess"&&!previous.game?.revealed&&next.game?.revealed){if(next.game.current.correct)playSound("correct");else playWrong();}
}
$("close-room").addEventListener("click",()=>action("close"));
$("start-game").addEventListener("click",()=>action("begin"));
$("refresh-count").addEventListener("click",refresh);
$("add-samples").addEventListener("click",async()=>{
 if(busy)return;
 try{const data=await requestJSON(`/api/rooms/${room.id}/samples`);$("sample-text").value=data.answers.join("\n");message("sample-error");$("sample-dialog").showModal();}
 catch(e){message("lobby-error",e.message);}
});
$("cancel-samples").addEventListener("click",()=>$("sample-dialog").close());
$("sample-form").addEventListener("submit",async event=>{
 event.preventDefault();if(busy)return;
 const answers=$("sample-text").value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
 if(!answers.length||answers.length>20||answers.some(x=>x.length<2||x.length>280))return message("sample-error","Enter up to 20 answers, 2–280 characters each.");
 busy=true;$("save-samples").disabled=true;
 try{const data=await requestJSON(`/api/rooms/${room.id}/samples`,{method:"POST",body:JSON.stringify({answers})});busy=false;render(data);$("sample-dialog").close();}
 catch(e){message("sample-error",e.message);}finally{busy=false;$("save-samples").disabled=false;}
});

$("copy-link").addEventListener("click",async event=>{
 try{await navigator.clipboard.writeText($("room-link").value);event.target.textContent="Copied";setTimeout(()=>event.target.textContent="Copy link",1500);}
 catch{$("room-link").focus();$("room-link").select();}
});
$("play-again").addEventListener("click",()=>location.assign("/"));
document.addEventListener("visibilitychange",()=>{clearTimeout(timer);if(!document.hidden&&["open","generating"].includes(room?.status))refresh();});
document.querySelectorAll("[data-guess]").forEach(button=>button.addEventListener("click",()=>action("guess",{answer_id:room.game.current.id,guess:button.dataset.guess})));
document.querySelectorAll("[data-action]").forEach(button=>button.addEventListener("click",()=>action(button.dataset.action,{answer_id:room.game.current?.id})));
function renderGame(){
 const game=room.game;
 document.querySelector(".progress > div").style.width=`${(game.round-1)/game.total*100}%`;
 if(room.status==="finished"){
  screen("results");$("accuracy").textContent=`${game.accuracy}%`;$("correct-count").textContent=game.correct;$("incorrect-count").textContent=game.incorrect;
  const stats=[game.ai_caught,game.ai_missed,game.humans_accused];document.querySelectorAll(".stat strong").forEach((x,i)=>x.textContent=stats[i]);
  const list=document.querySelector(".results-list");list.replaceChildren();
  document.querySelector(".score-panel").classList.toggle("win",game.assessed>0&&game.accuracy>=70);
  document.querySelector(".score-panel").classList.toggle("lose",game.assessed===0||game.accuracy<70);
  game.history.forEach((row,i)=>list.append(resultRow(row,i)));
  return;
 }
 screen(game.revealed?"reveal":"play");
 document.querySelectorAll("[data-answer]").forEach(x=>renderAnswer(x,game.current.text));
 document.querySelectorAll("#play [data-question],#reveal [data-question]").forEach(x=>x.textContent=room.question);
 document.querySelectorAll("[data-progress]").forEach(x=>x.textContent=`Round ${game.round} of ${game.total}`);
 document.querySelectorAll("[data-score]").forEach(x=>x.textContent=`${game.correct} / ${game.assessed} correct`);
 if(game.revealed){celebrateOnce(game.current);$("reveal-title").textContent=game.current.correct?"✅":"❌";$("reveal-box").className=`reveal ${game.current.correct?"good":"bad"}`;document.querySelector(".actual").textContent=game.current.actual==="ai"?"🤖 AI":"🧑 Human";}
}
updateQuestion();
if(location.pathname.startsWith("/host/")){
 $("setup").hidden=true;const id=location.pathname.split("/").pop();
 requestJSON(`/api/rooms/${id}/host`).then(render).catch(e=>{$("setup").hidden=false;message("setup-error",e.message);});
}

function renderAnswer(el,text){
 el.replaceChildren();el.classList.toggle("long",text.length>115);el.classList.toggle("very-long",text.length>195);
 for(const part of text.match(/\s+|[^\s]+/gu)||[]){if(/^\s+$/.test(part))el.append(document.createTextNode(part));else{const word=document.createElement("span");word.className="bouncy-word";word.textContent=part;el.append(word);}}
}
const styleIcons={Basic:"🧩",Chameleon:"🦎",Slang:"💬"};
function resultRow(row,i){
 const line=document.createElement("div");line.className="result-item";
 for(const [cls,text] of [["",`#${i+1}`],[`chip ${row.actual==="ai"?"ai-chip":""}`,row.actual==="ai"?"🤖":"🧑"],["snippet",row.text],[`outcome ${row.correct?"correct":"wrong"}`,row.correct?"✅":"❌"]]){const el=document.createElement("span");el.className=cls;el.textContent=text;line.append(el);}
 if(row.actual!=="ai")return line;
 const wrap=document.createElement("div");wrap.className="result-wrap";wrap.append(line);
 const details=document.createElement("details");details.className="ai-detail";
 const summary=document.createElement("summary");summary.textContent=`${styleIcons[row.style]||"🤖"} ${row.style} · How it was written`;
 const body=document.createElement("div");body.className="ai-detail-body";
 const explanation=document.createElement("p");
 const savedNote=row.explanation&&!/I was (asked|given)\b/i.test(row.explanation)?row.explanation:null;
 explanation.textContent=savedNote||({Basic:"I went with a straightforward approach.",Chameleon:"I used human submissions as a reference for a conversational tone.",Slang:"I used casual wording and internet slang."}[row.style])||"I used a direct response to the question.";
 body.append(explanation);details.append(summary,body);wrap.append(details);return wrap;
}

function celebrateOnce(answer){
 if(!answer.correct||celebrated===answer.id)return;celebrated=answer.id;
 if(window.matchMedia("(prefers-reduced-motion: reduce)").matches)return;
 for(let i=0;i<65;i++){const el=document.createElement("div");el.className="confetti";el.style.left=`${Math.random()*100}vw`;el.style.background=["#e94e5f","#2474e9","#f4ba29","#2bbd82","#8054f5"][i%5];el.style.animationDelay=`${Math.random()*.55}s`;document.body.append(el);setTimeout(()=>el.remove(),2900);}
}
