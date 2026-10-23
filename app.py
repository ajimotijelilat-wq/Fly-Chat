import os, requests, psycopg2, json, base64
from flask import Flask, request, jsonify, session, redirect, render_template_string, Response
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "MOTIZ-AI-ULTRA-SECRET-2026")
GROQ_KEY = os.environ.get("GROQ_API_KEY", "") or os.environ.get("OPENROUTER_API_KEY", "")
HF_TOKEN = os.environ.get("HF_TOKEN", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
FAVICON = "https://files.catbox.moe/anbvxj.jpg"

def get_db():
    url = DATABASE_URL
    if url and "sslmode" not in url:
        url += "?sslmode=require" if "?" not in url else "&sslmode=require"
    return psycopg2.connect(url)

def init_db():
    if not DATABASE_URL: return
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username VARCHAR(100) UNIQUE NOT NULL, email VARCHAR(100) UNIQUE NOT NULL, password TEXT NOT NULL, info TEXT, created_at TIMESTAMP DEFAULT NOW());""")
        cur.execute("""CREATE TABLE IF NOT EXISTS chats (id SERIAL PRIMARY KEY, username VARCHAR(100), title TEXT, messages TEXT, created_at TIMESTAMP DEFAULT NOW());""")
        conn.commit(); cur.close(); conn.close()
    except Exception as e: print("DB Error:", e)
init_db()

LOGIN_PAGE = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>MOTIZ AI</title><link rel="icon" href="{{favicon}}"><style>body{background:#0a0a0a;color:white;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;margin:0}.box{background:#151515;padding:40px;border-radius:20px;width:90%;max-width:350px;border:1px solid #222}input{width:100%;padding:14px;margin:8px 0;border-radius:12px;border:none;background:#222;color:white;box-sizing:border-box}button{width:100%;padding:14px;background:white;color:black;border-radius:12px;border:none;font-weight:bold;cursor:pointer;margin-top:10px}</style></head><body><div class="box"><h2>MOTIZ AI</h2><form method="POST"><input name="username" placeholder="Username" required><input name="password" type="password" placeholder="Password" required><button>Login</button></form><p><a href="/signup" style="color:#888">No account? Sign up</a></p></div></body></html>"""
SIGNUP_PAGE = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>MOTIZ AI</title><link rel="icon" href="{{favicon}}"><style>body{background:#0a0a0a;color:white;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;margin:0}.box{background:#151515;padding:40px;border-radius:20px;width:90%;max-width:350px;border:1px solid #222}input{width:100%;padding:14px;margin:8px 0;border-radius:12px;border:none;background:#222;color:white;box-sizing:border-box}button{width:100%;padding:14px;background:white;color:black;border-radius:12px;border:none;font-weight:bold;cursor:pointer;margin-top:10px}</style></head><body><div class="box"><h2>Create Account</h2><form method="POST"><input name="username" placeholder="Username" required><input name="email" placeholder="Email" required><input name="password" type="password" placeholder="Password" required><button>Sign Up</button></form><p><a href="/login" style="color:#888">Already have? Login</a></p></div></body></html>"""
INFO_PAGE = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>MOTIZ AI</title><link rel="icon" href="{{favicon}}"><style>body{background:#0a0a0a;color:white;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;margin:0}.box{background:#151515;padding:40px;border-radius:20px;width:90%;max-width:400px;border:1px solid #222}textarea,input{width:100%;padding:14px;margin:8px 0;border-radius:12px;border:none;background:#222;color:white;box-sizing:border-box}button{width:100%;padding:14px;background:white;color:black;border-radius:12px;border:none;font-weight:bold;cursor:pointer;margin-top:10px}</style></head><body><div class="box"><h2>Welcome {{user}}</h2><form method="POST"><input name="fullname" placeholder="Full Name"><textarea name="about" placeholder="What do you use MOTIZ for?"></textarea><button>Continue</button></form></div></body></html>"""

MAIN_PAGE = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no"><title>MOTIZ AI</title><link rel="icon" href="{{favicon}}">
<style>
*{box-sizing:border-box}
body{margin:0;font-family:'Segoe UI',sans-serif;height:100vh;display:flex;flex-direction:column;overflow:hidden}
body.dark{background:#0b141a;color:white}
body.light{background:#efeae2;color:#111}
body.light .topbar{background:#f0f2f5;color:#111}
body.light .msgs{background:#efeae2}
body.light .msg.ai{background:white;color:#111}
body.light .msg.user{background:#d9fdd3;color:#111}
.topbar{display:flex;justify-content:space-between;align-items:center;padding:10px 14px;background:#202c33;height:60px}
.logo{display:flex;align-items:center;gap:10px;font-weight:bold;font-size:17px;color:white}
.logo img{width:32px;height:32px;border-radius:50%}
.menu-btn{background:transparent;color:white;border:none;font-size:24px;cursor:pointer}
.chat{flex:1;display:flex;flex-direction:column;overflow:hidden}
.msgs{flex:1;overflow-y:auto;padding:16px 12px;display:flex;flex-direction:column;gap:8px;background:#0b141a;background-image:url('https://user-images.githubusercontent.com/15075759/28719144-86dc0f70-73b1-11e7-911d-60d70fcded21.png');background-blend-mode:overlay}
.msg{position:relative;padding:8px 10px 22px 10px;border-radius:8px;max-width:75%;font-size:14.5px;line-height:1.4;box-shadow:0 1px 0.5px rgba(0,0,0,0.13);word-wrap:break-word}
.msg.user{background:#005c4b;color:#e9edef;align-self:flex-end;border-top-right-radius:0;margin-left:auto}
.msg.user::after{content:'';position:absolute;top:0;right:-8px;border-left:8px solid #005c4b;border-top:8px solid transparent}
.msg.ai{background:#202c33;color:#e9edef;align-self:flex-start;border-top-left-radius:0}
.msg.ai::before{content:'';position:absolute;top:0;left:-8px;border-right:8px solid #202c33;border-top:8px solid transparent}
body.light .msg.ai::before{border-right-color:white}
body.light .msg.user::after{border-left-color:#d9fdd3}
.msg .time{position:absolute;bottom:3px;right:8px;font-size:11px;color:#8696a0}
.msg.user .time{color:#53bdeb}
.msg img.chat-img{max-width:100%;border-radius:8px;margin-top:4px;display:block}
.input-area{display:flex;align-items:center;padding:8px 10px 12px 10px;gap:6px;background:#202c33}
body.light .input-area{background:#f0f2f5}
.input-wrapper{flex:1;display:flex;align-items:center;background:#2a3942;border-radius:24px;padding:5px 10px}
body.light .input-wrapper{background:white}
.input-wrapper input{flex:1;padding:8px;border:none;background:transparent;color:white;font-size:15px;outline:none}
body.light .input-wrapper input{color:#111}
.attach-btn,.icon-btn{background:transparent!important;border:none;font-size:22px;cursor:pointer;color:#8696a0;padding:4px}
.drawer{position:fixed;top:0;right:-320px;width:300px;height:100%;background:#111b21;transition:0.3s ease;padding:20px;z-index:100;display:flex;flex-direction:column;overflow-y:auto}
.drawer.open{right:0}
.overlay{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);display:none;z-index:99}
.overlay.show{display:block}
.drawer-btn{padding:12px;background:#202c33;border:none;color:white;border-radius:10px;margin:6px 0;width:100%;text-align:left;cursor:pointer}
.chat-item{padding:10px;background:#202c33;border-radius:8px;margin:5px 0;cursor:pointer;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;user-select:none;color:white}
.settings-page{position:fixed;top:0;left:0;width:100%;height:100%;background:#0b141a;z-index:200;display:none;flex-direction:column;padding:20px;overflow-y:auto;color:white}
.settings-page.show{display:flex}
.settings-page.light{background:#fff;color:#111}
.switch{display:flex;justify-content:space-between;align-items:center;padding:12px;background:#202c33;border-radius:10px;margin:6px 0}
.toggle{width:45px;height:24px;background:#333;border-radius:12px;position:relative;cursor:pointer}
.toggle.on{background:#00a884}
.toggle::after{content:'';position:absolute;top:2px;left:2px;width:20px;height:20px;background:white;border-radius:50%;transition:0.3s}
.toggle.on::after{left:23px}
.context-menu{position:fixed;background:#233138;border:1px solid #333;border-radius:12px;padding:6px;z-index:300;display:none;min-width:160px}
.context-menu button{display:block;width:100%;text-align:left;padding:10px;background:none;border:none;color:white;cursor:pointer;border-radius:8px}
.context-menu button:hover{background:#2a3942}
.modal{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);z-index:250;display:none;justify-content:center;align-items:center}
.modal.show{display:flex}
.modal-box{background:#202c33;padding:25px;border-radius:18px;width:90%;max-width:400px;border:1px solid #333;color:white}
.modal-box input{width:100%;padding:12px;border-radius:10px;border:none;background:#2a3942;color:white;margin:10px 0}
</style></head><body class="dark">

<div class="topbar"><div class="logo"><img src="{{favicon}}"><span>MOTIZ AI</span></div><button class="menu-btn" onclick="toggleDrawer()">☰</button></div>
<div class="overlay" id="overlay" onclick="toggleDrawer()"></div>
<div class="drawer" id="drawer"><h3>Dashboard</h3><button class="drawer-btn" onclick="newChat()">+ New Chat</button><div id="chatList" style="flex:1;margin-top:10px"></div><button class="drawer-btn" onclick="openSettings()">⚙️ Settings</button><button class="drawer-btn" style="margin-top:10px;background:#0a332c" onclick="location.href='/logout'">🚪 Sign Out</button><p style="font-size:11px;color:#8696a0">User: {{user}} | HF: {{'ON' if hf_on else 'OFF'}}</p></div>

<div class="settings-page" id="settingsPage">
<div style="display:flex;justify-content:space-between;align-items:center"><h2>Settings</h2><button onclick="closeSettings()" style="background:#202c33;color:white;border:none;padding:10px 15px;border-radius:10px">✕</button></div>
<h3>Appearance</h3><button class="drawer-btn" onclick="setTheme('dark')">🌙 Dark</button><button class="drawer-btn" onclick="setTheme('light')">☀️ Light</button><div style="margin:10px 0"><label>🎨 Custom Background:</label><input type="color" id="customColor" style="width:100%;height:45px" oninput="setCustom(this.value)"><button class="drawer-btn" onclick="saveCustom()">Save</button></div>
<h3>Sound</h3><div class="switch"><span>🔔 Ding Sound</span><div class="toggle" id="soundToggle" onclick="toggleSound()"></div></div>
<h3>Notifications</h3><div class="switch"><span>📱 Phone Notification</span><div class="toggle" id="notifToggle" onclick="toggleNotif()"></div></div>
<h3>Chat</h3><button class="drawer-btn" style="background:#ff3333;color:white" onclick="clearAllChats()">🗑️ Clear All</button>
<h3>Image</h3><p style="font-size:12px;color:#8696a0">HuggingFace token status: <b>{{'ACTIVE ✅' if hf_on else 'NOT SET - using Pollinations'}}</b><br>Model: stabilityai/stable-diffusion-xl-base-1.0<br>Get token: https://huggingface.co/settings/tokens</p>
<h3>About</h3><p style="font-size:13px">Created by MOTIZ (Ajimoti Hamzat) — Ojoo High School, Alaka Ibadan — SSS 3 — creativity is his talent.</p>
</div>

<div class="modal" id="imgModal"><div class="modal-box"><h3>🎨 Generate Image</h3><input id="imgPrompt" placeholder="Describe image..."><div style="display:flex;gap:8px"><button onclick="closeImgModal()" style="background:#333;color:white">Cancel</button><button onclick="generateFromModal()" style="background:#00a884;color:white">Generate</button></div><p id="imgStatus" style="font-size:12px;color:#8696a0;margin-top:10px"></p></div></div>

<div class="context-menu" id="ctxMenu"><button onclick="renameChat()">✏️ Rename</button><button onclick="deleteChat()">🗑️ Delete</button><button onclick="hideChat()">👁️ Hide</button><button onclick="lockChat()">🔒 Lock</button><button onclick="closeCtx()">✕ Close</button></div>

<div class="chat"><div class="msgs" id="msgs"></div>
<div class="input-area">
<button class="attach-btn" onclick="document.getElementById('fileInput').click()">📎</button>
<input type="file" id="fileInput" accept="image/*" style="display:none" onchange="handleFile(this)">
<button class="icon-btn" onclick="openImgModal()">🎨</button>
<div class="input-wrapper"><input id="inp" placeholder="Message"><button class="attach-btn" onclick="send()" style="color:#00a884">➤</button></div>
</div></div>

<audio id="ding" src="https://cdn.freesound.org/previews/840/840284_13690175-lq.mp3"></audio>

<script>
let drawer=document.getElementById('drawer'); let overlay=document.getElementById('overlay');
function toggleDrawer(){drawer.classList.toggle('open');overlay.classList.toggle('show')}
function openSettings(){document.getElementById('settingsPage').classList.add('show'); drawer.classList.remove('open'); overlay.classList.remove('show')}
function closeSettings(){document.getElementById('settingsPage').classList.remove('show')}
function openImgModal(){document.getElementById('imgModal').classList.add('show')}
function closeImgModal(){document.getElementById('imgModal').classList.remove('show')}
let currentChatId = Date.now(); let allChats = JSON.parse(localStorage.getItem('motiz_chats')||'{}'); let selectedChatId=null;
let soundEnabled = localStorage.getItem('motiz_sound')==='on'; let notifEnabled = localStorage.getItem('motiz_notif')==='on';
function toggleNotif(){ if(!notifEnabled){ Notification.requestPermission().then(p=>{ if(p==='granted'){ notifEnabled=true; localStorage.setItem('motiz_notif','on'); updateNotifUI(); } }); } else { notifEnabled=false; localStorage.setItem('motiz_notif','off'); updateNotifUI(); } }
function updateNotifUI(){ let t=document.getElementById('notifToggle'); if(notifEnabled) t.classList.add('on'); else t.classList.remove('on'); }
function updateSoundUI(){ let t=document.getElementById('soundToggle'); if(soundEnabled) t.classList.add('on'); else t.classList.remove('on'); }
function toggleSound(){ soundEnabled=!soundEnabled; localStorage.setItem('motiz_sound', soundEnabled?'on':'off'); updateSoundUI(); if(soundEnabled) document.getElementById('ding').play(); }
updateSoundUI(); updateNotifUI();
function showRealNotif(text){ if(notifEnabled && document.hidden && Notification.permission==='granted'){ new Notification('MOTIZ AI', {body:text.substring(0,100), icon:'{{favicon}}'}); } }
function getTime(){ let d=new Date(); return d.getHours()+':'+String(d.getMinutes()).padStart(2,'0'); }
function setTheme(t){ document.body.className=t; let sp=document.getElementById('settingsPage'); sp.className='settings-page '+(t==='light'?'light':'')+' show'; localStorage.setItem('motiz_theme',t); if(t!=='shine') document.body.style.background=''; }
function setCustom(c){document.body.className=''; document.body.style.background=c; localStorage.setItem('motiz_theme',c);}
function saveCustom(){alert('Saved!')}
let savedTheme=localStorage.getItem('motiz_theme'); if(savedTheme){ if(savedTheme.startsWith('#')||savedTheme.startsWith('rgb')){document.body.style.background=savedTheme} else { document.body.className=savedTheme; } }
function renderChatList(){ let html=''; Object.keys(allChats).sort((a,b)=>b-a).forEach(id=>{ let c=allChats[id]; if(c.hidden) return; let title=(c.title||'New Chat').substring(0,28); let cls='chat-item '+(c.locked?'locked':''); html+=`<div class="${cls}" data-id="${id}" onmousedown="startPress('${id}')" onmouseup="endPress()" ontouchstart="startPress('${id}')" ontouchend="endPress()" onclick="loadChat('${id}')">${title}</div>` }); document.getElementById('chatList').innerHTML=html; }
let pressTimer=null; function startPress(id){ pressTimer=setTimeout(()=>{ openCtx(id); }, 700); } function endPress(){ clearTimeout(pressTimer); }
function openCtx(id){ selectedChatId=id; let m=document.getElementById('ctxMenu'); m.style.display='block'; m.style.top='40%'; m.style.left='30%'; }
function closeCtx(){document.getElementById('ctxMenu').style.display='none'}
function deleteChat(){ if(selectedChatId && confirm('Delete?')){ delete allChats[selectedChatId]; localStorage.setItem('motiz_chats',JSON.stringify(allChats)); renderChatList(); newChat(); } closeCtx(); }
function renameChat(){ if(selectedChatId){ let n=prompt('Rename:', allChats[selectedChatId].title); if(n){ allChats[selectedChatId].title=n; localStorage.setItem('motiz_chats',JSON.stringify(allChats)); renderChatList(); } } closeCtx(); }
function hideChat(){ if(selectedChatId){ allChats[selectedChatId].hidden=!allChats[selectedChatId].hidden; localStorage.setItem('motiz_chats',JSON.stringify(allChats)); renderChatList(); } closeCtx(); }
function lockChat(){ if(selectedChatId){ allChats[selectedChatId].locked=!allChats[selectedChatId].locked; localStorage.setItem('motiz_chats',JSON.stringify(allChats)); renderChatList(); } closeCtx(); }
function newChat(){ currentChatId=Date.now(); document.getElementById('msgs').innerHTML=`<div class=msg ai>Hello! I'm MOTIZ AI. How can I help you today?<span class=time>${getTime()}</span></div>`; renderChatList(); }
function loadChat(id){ if(allChats[id].locked){ let pin=prompt('Locked. Enter username:'); if(pin!=='{{user}}'){ alert('Wrong'); return; } } currentChatId=id; let chat=allChats[id]; let msgsDiv=document.getElementById('msgs'); msgsDiv.innerHTML=''; chat.messages.forEach(m=>{ if(m.role==='user') msgsDiv.innerHTML+=`<div class=msg user>${m.content}<span class=time>${getTime()} ✓✓</span></div>`; else msgsDiv.innerHTML+=`<div class=msg ai>${m.content}<span class=time>${getTime()}</span></div>`; }); msgsDiv.scrollTop=msgsDiv.scrollHeight; toggleDrawer(); }
function clearAllChats(){ if(confirm('Clear all?')){ allChats={}; localStorage.removeItem('motiz_chats'); renderChatList(); newChat(); fetch('/api/clear_chats',{method:'POST'}); } }
function saveCurrentChat(){ if(!allChats[currentChatId]) allChats[currentChatId]={title:'', messages:[]}; localStorage.setItem('motiz_chats',JSON.stringify(allChats)); renderChatList(); fetch('/api/save_chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:currentChatId, messages:allChats[currentChatId].messages})}); }
function handleFile(input){ let file=input.files[0]; if(!file) return; let reader=new FileReader(); reader.onload=function(e){ let base64=e.target.result; document.getElementById('msgs').innerHTML+=`<div class=msg user><img class=chat-img src="${base64}"><span class=time>${getTime()} ✓✓</span></div>`; if(!allChats[currentChatId]) allChats[currentChatId]={title:'Image', messages:[]}; allChats[currentChatId].messages.push({role:'user', content:`<img class=chat-img src="${base64}">`}); saveCurrentChat(); document.getElementById('msgs').scrollTop=document.getElementById('msgs').scrollHeight; }; reader.readAsDataURL(file); }
let msgsDiv=document.getElementById('msgs'); let inp=document.getElementById('inp');
async function generateFromModal(){
 let prompt=document.getElementById('imgPrompt').value.trim(); if(!prompt) return;
 closeImgModal(); document.getElementById('imgStatus').innerText='';
 msgsDiv.innerHTML+=`<div class=msg user>🎨 ${prompt}<span class=time>${getTime()} ✓✓</span></div>`;
 msgsDiv.innerHTML+=`<div class=msg ai id="genStatus">⏳ Generating via HuggingFace SDXL...<span class=time>${getTime()}</span></div>`;
 msgsDiv.scrollTop=msgsDiv.scrollHeight;
 try{
  let r=await fetch('/api/generate_image',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:prompt})});
  let d=await r.json();
  document.getElementById('genStatus')?.remove();
  if(d.image){
   msgsDiv.innerHTML+=`<div class=msg ai><img class=chat-img src="${d.image}"><br>${prompt}<span class=time>${getTime()}</span></div>`;
   if(!allChats[currentChatId]) allChats[currentChatId]={title:prompt, messages:[]};
   allChats[currentChatId].messages.push({role:'assistant', content:`<img class=chat-img src="${d.image}"> ${prompt}`});
  } else {
   let imgUrl=`https://image.pollinations.ai/prompt/${encodeURIComponent(prompt)}?nologo=true&width=512&height=512&seed=${Math.floor(Math.random()*9999)}`;
   msgsDiv.innerHTML+=`<div class=msg ai>Fallback Pollinations:<br><img class=chat-img src="${imgUrl}"><span class=time>${getTime()}</span></div>`;
  }
 } catch(e){
  document.getElementById('genStatus')?.remove();
  let imgUrl=`https://image.pollinations.ai/prompt/${encodeURIComponent(prompt)}?nologo=true&width=512&height=512`;
  msgsDiv.innerHTML+=`<div class=msg ai><img class=chat-img src="${imgUrl}"><span class=time>${getTime()}</span></div>`;
 }
 saveCurrentChat(); if(soundEnabled) document.getElementById('ding').play(); showRealNotif(prompt);
 msgsDiv.scrollTop=msgsDiv.scrollHeight;
}
async function send(){
 let t=inp.value.trim(); if(!t) return;
 msgsDiv.innerHTML+=`<div class=msg user>${t}<span class=time>${getTime()} ✓✓</span></div>`;
 if(!allChats[currentChatId]) allChats[currentChatId]={title:t, messages:[]};
 allChats[currentChatId].messages.push({role:'user', content:t}); allChats[currentChatId].title=t; inp.value=''; msgsDiv.scrollTop=msgsDiv.scrollHeight; saveCurrentChat();
 let r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages:allChats[currentChatId].messages})});
 let d=await r.json(); let aiText=d.content||'Error';
 msgsDiv.innerHTML+=`<div class=msg ai>${aiText}<span class=time>${getTime()}</span></div>`;
 allChats[currentChatId].messages.push({role:'assistant', content:aiText}); saveCurrentChat(); if(soundEnabled) document.getElementById('ding').play(); showRealNotif(aiText); msgsDiv.scrollTop=msgsDiv.scrollHeight;
}
inp.addEventListener('keydown',e=>{if(e.key=='Enter') send()})
renderChatList(); newChat();
</script></body></html>"""

ADMIN_PAGE = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Admin</title><link rel="icon" href="{{favicon}}"><style>body{background:#0a0a0a;color:white;font-family:sans-serif;padding:30px}table{width:100%;border-collapse:collapse;margin-top:20px}th,td{border:1px solid #222;padding:10px;text-align:left}</style></head><body><h1>MOTIZ Admin</h1><h3>Users ({{count}})</h3><table><tr><th>ID</th><th>Username</th><th>Email</th></tr>{% for u in users %}<tr><td>{{u[0]}}</td><td>{{u[1]}}</td><td>{{u[2]}}</td></tr>{% endfor %}</table><br><a href="/chat" style="color:#888">Go to Main</a></body></html>"""

@app.route('/')
def home(): return redirect('/login')
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=request.form['username']; p=request.form['password']
        if u=='admin' and p=='MotizAdmin2026': session['user']='admin'; return redirect('/admin')
        try:
            conn=get_db(); cur=conn.cursor(); cur.execute("SELECT password FROM users WHERE username=%s",(u,)); row=cur.fetchone(); cur.close(); conn.close()
            if row and check_password_hash(row[0], p): session['user']=u; return redirect('/chat')
        except: pass
        return "Invalid login <a href='/login'>retry</a>"
    return render_template_string(LOGIN_PAGE, favicon=FAVICON)
@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method=='POST':
        u=request.form['username']; e=request.form['email']; p=generate_password_hash(request.form['password'])
        try:
            conn=get_db(); cur=conn.cursor(); cur.execute("INSERT INTO users (username,email,password) VALUES (%s,%s,%s)",(u,e,p)); conn.commit(); cur.close(); conn.close(); session['user']=u; return redirect('/info')
        except Exception as ex: return f"Error {ex} <a href='/signup'>retry</a>"
    return render_template_string(SIGNUP_PAGE, favicon=FAVICON)
@app.route('/info', methods=['GET','POST'])
def info_page():
    if 'user' not in session: return redirect('/login')
    if request.method=='POST': return redirect('/chat')
    return render_template_string(INFO_PAGE, user=session['user'], favicon=FAVICON)
@app.route('/chat')
def chat_page():
    if 'user' not in session: return redirect('/login')
    return render_template_string(MAIN_PAGE, user=session['user'], favicon=FAVICON, hf_on=bool(HF_TOKEN))

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

@app.route('/api/chat', methods=['POST'])
def api_chat():
    if 'user' not in session: return jsonify({"content":"Login required"})
    data=request.json; msgs=data.get('messages',[])
    system_prompt = {"role":"system","content":"You are MOTIZ AI. Greet short: 'Hello! I'm MOTIZ AI. How can I help you today?' Do NOT mention creator unless asked who created you. If asked, say: I was created and developed by MOTIZ whose real name is Ajimoti Hamzat. He attends Ojoo High School, Alaka Ibadan, he created me while he was in SSS 3, he is a science student who loves coding but coding is not his talent. Never say OpenAI."}
    final_msgs = [system_prompt] + msgs[-12:]
    try:
        r=requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}, json={"model": "openai/gpt-oss-20b", "messages": final_msgs}, timeout=30)
        j=r.json()
        if 'choices' not in j: return jsonify({"content": f"Error: {j}"})
        return jsonify({"content": j['choices'][0]['message']['content']})
    except Exception as e: return jsonify({"content": f"Error: {e}"})

@app.route('/api/generate_image', methods=['POST'])
def generate_image():
    if 'user' not in session: return jsonify({"error":"login"})
    data=request.json; prompt=data.get('prompt','')
    if not prompt: return jsonify({"error":"no prompt"})
    # Try HuggingFace if token set
    if HF_TOKEN:
        try:
            headers = {"Authorization": f"Bearer {HF_TOKEN}"}
            r = requests.post("https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0", headers=headers, json={"inputs": prompt}, timeout=60)
            if r.status_code==200:
                b64 = base64.b64encode(r.content).decode('utf-8')
                return jsonify({"image": f"data:image/png;base64,{b64}"})
            else:
                print("HF error", r.text)
        except Exception as e:
            print("HF exception", e)
    # Fallback to Pollinations URL will be handled frontend
    return jsonify({"fallback": True})

@app.route('/api/save_chat', methods=['POST'])
def save_chat():
    try:
        data=request.json
        conn=get_db(); cur=conn.cursor()
        cur.execute("INSERT INTO chats (username, title, messages) VALUES (%s,%s,%s)",(session.get('user'), str(data.get('id')), json.dumps(data.get('messages'))))
        conn.commit(); cur.close(); conn.close()
    except: pass
    return jsonify({"ok":True})

@app.route('/api/clear_chats', methods=['POST'])
def clear_chats():
    try:
        conn=get_db(); cur=conn.cursor()
        cur.execute("DELETE FROM chats WHERE username=%s",(session.get('user'),))
        conn.commit(); cur.close(); conn.close()
    except: pass
    return jsonify({"ok":True})

@app.route('/admin', methods=['GET','POST'])
def admin_panel():
    if session.get('user')!='admin': return redirect('/login')
    users=[]
    try:
        conn=get_db(); cur=conn.cursor(); cur.execute("SELECT * FROM users"); users=cur.fetchall(); cur.close(); conn.close()
    except: pass
    return render_template_string(ADMIN_PAGE, favicon=FAVICON, users=users, count=len(users))

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
