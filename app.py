import os, base64, io, requests
from flask import Flask, request, jsonify, render_template_string
from PIL import Image
import google.generativeai as genai

app = Flask(__name__)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-2.0-flash")

chat_history = []

def hf_generate_image(prompt):
    if not HF_TOKEN: return None
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    for model in ["black-forest-labs/FLUX.1-schnell","stabilityai/stable-diffusion-xl-base-1.0"]:
        try:
            r = requests.post(f"https://api-inference.huggingface.co/models/{model}", headers=headers, json={"inputs": prompt}, timeout=90)
            if r.status_code==503: continue
            if r.status_code==200 and len(r.content)>5000:
                return f"data:image/png;base64,{base64.b64encode(r.content).decode()}"
        except: continue
    return None

def chat_with_gemini(message, image_bytes=None):
    global chat_history
    chat_history.append({"role":"user","content":message})
    chat_history = chat_history[-6:]
    context = "\n".join([f"{m['role']}: {m['content'][:300]}" for m in chat_history])
    try:
        prompt = f"You are MOTIZ AI by MOTIZ (16, Ojoo High School). No need to ask user name. Helpful, short. History:\n{context}\nAnswer:"
        if image_bytes:
            img = Image.open(io.BytesIO(image_bytes))
            resp = gemini_model.generate_content([prompt, img])
        else:
            resp = gemini_model.generate_content(prompt)
        chat_history.append({"role":"assistant","content":resp.text[:500]})
        return resp.text
    except Exception as e:
        if GROQ_API_KEY:
            try:
                r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, json={"model":"llama-3.1-8b-instant","messages":[{"role":"user","content":context[-2000:]}]}, timeout=20)
                return r.json()["choices"][0]["message"]["content"]
            except: pass
        return "Tap Clear All in Settings to reset, chat too long."

HTML_PAGE = """
<!DOCTYPE html><html><head><title>MOTIZ AI</title><meta name=viewport content='width=device-width,initial-scale=1'>
<style>
:root{--bg:#111b21;--chat-bg:#0b141a;--card:#202c33;--user:#005c4b;--text:#e9edef;--border:#2a3942}
body.light{--bg:#ffffff;--chat-bg:#efeae2;--card:#ffffff;--user:#d9fdd3;--text:#111b21;--border:#ddd}
body{background:var(--bg);color:var(--text);font-family:sans-serif;margin:0;display:flex;flex-direction:column;height:100vh}
#notifyBar{position:fixed;top:-60px;left:0;right:0;background:#25d366;color:#000;padding:12px;text-align:center;z-index:999;transition:0.4s;font-weight:bold}
#notifyBar.show{top:0}
#header{padding:12px 15px;background:var(--card);display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border)}
#chat{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:8px;background:var(--chat-bg)}
.msg{padding:9px 12px;border-radius:8px;max-width:75%;font-size:15px;line-height:1.4;box-shadow:0 1px 1px rgba(0,0,0,0.2)}
.user{background:var(--user);align-self:flex-end;margin-left:auto;border-top-right-radius:0}
.user::after{content:' ✓✓';font-size:10px;opacity:0.6}
.ai{background:var(--card);align-self:flex-start;margin-right:auto;border-top-left-radius:0}
.img{max-width:100%;border-radius:8px;margin-top:8px}
#input{display:flex;padding:8px 12px;background:var(--card);gap:8px;align-items:center}
#msg{flex:1;padding:12px 16px;border-radius:22px;border:1px solid var(--border);background:var(--card);color:var(--text);outline:none}
#settings{position:fixed;top:0;right:-100%;width:320px;height:100%;background:var(--bg);z-index:100;transition:0.3s;padding:20px;overflow-y:auto}
#settings.open{right:0}
.set-item{background:var(--card);padding:14px;border-radius:10px;margin:10px 0;display:flex;justify-content:space-between;align-items:center;cursor:pointer}
.toggle{width:48px;height:26px;background:#667781;border-radius:20px;position:relative;transition:0.3s}
.toggle.on{background:#00a884}
.toggle::after{content:'';position:absolute;width:22px;height:22px;background:#fff;border-radius:50%;top:2px;left:2px;transition:0.3s}
.toggle.on::after{left:24px}
.clear{width:100%;padding:14px;background:#f15c6d;color:#fff;border:none;border-radius:10px;font-weight:bold}
#storyBox{display:none;position:fixed;bottom:70px;left:10px;right:10px;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:15px;z-index:90}
</style></head><body>
<div id=notifyBar>🔔 New message from MOTIZ AI</div>
<div id=header><b>Ⓜ MOTIZ AI</b><div><button onclick="openStory()" style="background:transparent;color:var(--text);border:1px solid var(--border);margin-right:8px;border-radius:12px">📖 Story</button><button onclick="toggleSettings()" style="background:transparent;color:var(--text);border:none;font-size:20px">☰</button></div></div>
<div id=chat></div>

<div id=storyBox><b id=storyTitle>Story Mode</b><p id=storyText></p><button onclick="nextStory()" style="padding:8px 16px;background:#00a884;color:#fff;border:none;border-radius:8px">Next Part →</button> <button onclick="closeStory()" style="padding:8px;background:transparent;border:1px solid var(--border);color:var(--text);border-radius:8px">Close</button></div>

<div id=input><input type=file id=file accept=image/* style=display:none><button onclick="document.getElementById('file').click()" style="background:transparent;border:none;font-size:20px">📎</button><input id=msg placeholder="Ask or say 'design a car'..."><button onclick="send()" style="background:#00a884;color:#fff;border-radius:50%;width:42px;height:42px;border:none">➤</button></div>

<div id=settings>
<div style="display:flex;justify-content:space-between;align-items:center"><h2>Settings</h2><button onclick="toggleSettings()" style="background:transparent;border:none;color:var(--text);font-size:20px">✕</button></div>
<h3>Appearance</h3>
<div class=set-item onclick="setTheme('dark')"><span>🌙 Dark</span><span id=darkCheck>✓</span></div>
<div class=set-item onclick="setTheme('light')"><span>☀️ Light</span><span id=lightCheck></span></div>
<h3>Sound</h3>
<div class=set-item><span>🔔 Ding</span><div id=soundToggle class="toggle on" onclick="toggleSound()"></div></div>
<h3>Notifications</h3>
<div class=set-item><span>📱 Push</span><div id=pushToggle class="toggle on" onclick="togglePush()"></div></div>
<h3>Chat</h3>
<button class=clear onclick="clearAll()">🗑️ Clear All</button>
<h3>About</h3>
<p style="font-size:13px;opacity:0.8">Created by MOTIZ (Ajimoti Hamzat), 16, SSS 3, Ojoo High School, Alaka Ibadan. Built on Tecno Pop 2 Plus.</p>
</div>

<script>
// THEME - FIXED
let theme = localStorage.getItem('theme') || 'dark';
applyTheme(theme);
function applyTheme(t){document.body.className=t;localStorage.setItem('theme',t);if(t==='dark'){document.getElementById('darkCheck').innerText='✓';document.getElementById('lightCheck').innerText=''}else{document.getElementById('lightCheck').innerText='✓';document.getElementById('darkCheck').innerText=''}document.body.classList.add(t);if(t==='light')document.body.classList.remove('dark');}
function setTheme(t){applyTheme(t);}

let soundOn = localStorage.getItem('sound') !== 'false';
let pushOn = localStorage.getItem('push') !== 'false';
document.getElementById('soundToggle').className = soundOn ? 'toggle on' : 'toggle';
document.getElementById('pushToggle').className = pushOn ? 'toggle on' : 'toggle';

// SOUND FIX - Web Audio (works without file)
function playDing(){
 if(!soundOn) return;
 try{
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  const o = ctx.createOscillator(); const g = ctx.createGain();
  o.type='sine'; o.frequency.value=800; o.connect(g); g.connect(ctx.destination);
  g.gain.setValueAtTime(0.5, ctx.currentTime); o.start(); o.stop(ctx.currentTime+0.2);
 }catch(e){}
}

function toggleSettings(){document.getElementById('settings').classList.toggle('open')}
function toggleSound(){soundOn=!soundOn;localStorage.setItem('sound',soundOn);document.getElementById('soundToggle').className=soundOn?'toggle on':'toggle';if(soundOn)playDing()}
function togglePush(){pushOn=!pushOn;localStorage.setItem('push',pushOn);document.getElementById('pushToggle').className=pushOn?'toggle on':'toggle';if(pushOn&&Notification.permission!=='granted')Notification.requestPermission()}
function clearAll(){if(confirm('Clear all?')){document.getElementById('chat').innerHTML='';fetch('/clear',{method:'POST'});toggleSettings()}}
function showTopBar(text){let bar=document.getElementById('notifyBar');bar.innerText=text;bar.classList.add('show');setTimeout(()=>bar.classList.remove('show'),3000)}

// STORY - SEPARATE FROM CHAT
let storyParts=[]; let storyIndex=0;
function openStory(){document.getElementById('storyBox').style.display='block'; if(storyParts.length===0)document.getElementById('storyText').innerText='Ask me "tell me a story about..." to start story mode.'}
function closeStory(){document.getElementById('storyBox').style.display='none'}
function nextStory(){if(storyIndex<storyParts.length-1){storyIndex++;document.getElementById('storyText').innerText=storyParts[storyIndex]}else{document.getElementById('storyText').innerText='End of story. Ask for a new story.'}}

async function send(){
 let m=document.getElementById('msg').value; let f=document.getElementById('file').files[0];
 if(!m&&!f) return;
 let chat=document.getElementById('chat');
 chat.innerHTML+=`<div class=msg user>${m||'Image uploaded'}</div>`;
 document.getElementById('msg').value='';
 playDing();
 let fd=new FormData(); fd.append('message',m); if(f)fd.append('file',f);
 chat.innerHTML+=`<div class=msg ai id=thinking>⌛ MOTIZ thinking...</div>`;
 chat.scrollTop=chat.scrollHeight;
 let res=await fetch('/chat',{method:'POST',body:fd}); let data=await res.json();
 document.getElementById('thinking').remove();
 // If story, put in story box not chat
 if(m.toLowerCase().includes('story') && data.content.length>200){
   storyParts = data.content.match(/.{1,300}(\\s|$)/g); storyIndex=0;
   document.getElementById('storyText').innerText=storyParts[0]; openStory();
 }
 let html=`<div class=msg ai>${data.content}`;
 if(data.image) html+=`<br><img class=img src='${data.image}'>`;
 html+='</div>'; chat.innerHTML+=html; chat.scrollTop=chat.scrollHeight;
 document.getElementById('file').value='';
 playDing(); showTopBar('🔔 MOTIZ: '+data.content.slice(0,40));
 if(pushOn && Notification.permission==='granted'){new Notification('MOTIZ AI',{body:data.content.slice(0,80)})}
}
document.getElementById('msg').addEventListener('keydown',e=>{if(e.key==='Enter')send()})
// SIGNUP FIX - NO QUESTIONS, auto continue
window.onload=()=>{if(Notification.permission!=='granted' && pushOn) Notification.requestPermission()}
</script>
</body></html>
"""

@app.route("/")
def home(): return render_template_string(HTML_PAGE)

@app.route("/clear", methods=["POST"])
def clear():
    global chat_history; chat_history=[]; return jsonify({"ok":True})

@app.route("/chat", methods=["POST"])
def chat_route():
    global chat_history
    message=request.form.get("message",""); file=request.files.get("file")
    image_bytes=file.read() if file else None
    lower=message.lower()
    if any(k in lower for k in ["create an image","generate","design","draw a","make an image"]):
        prompt=message
        for k in ["create an image of","generate an image of","create image of","create an image","design a","draw a","generate"]:
            if k in lower:
                idx=lower.find(k); prompt=message[idx+len(k):].strip(); break
        img_data=hf_generate_image(prompt or message)
        if img_data: return jsonify({"content":f"Generated: {prompt}","image":img_data})
        else: return jsonify({"content":"HF_TOKEN missing or waking up, wait 30s and retry.","image":None})
    reply=chat_with_gemini(message, image_bytes)
    return jsonify({"content":reply,"image":None})

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
