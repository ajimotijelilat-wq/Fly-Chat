import os, requests, psycopg2, json
from flask import Flask, request, jsonify, session, redirect, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "MOTIZ-AI-ULTRA-SECRET-2026")
GROQ_KEY = os.environ.get("GROQ_API_KEY", "") or os.environ.get("OPENROUTER_API_KEY", "")
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

MAIN_PAGE = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>MOTIZ AI</title><link rel="icon" href="{{favicon}}">
<style>
*{box-sizing:border-box}
body{margin:0;font-family:sans-serif;height:100vh;display:flex;flex-direction:column;overflow:hidden;transition:background 0.3s}
body.dark{background:#0a0a0a;color:white}
body.light{background:#f5f5f5;color:black}
body.light .topbar{background:white;border-color:#ddd}
body.light .msg.ai{background:white;border:1px solid #ddd;color:black}
body.light .input-area{background:#f5f5f5}
body.light .drawer{background:#fff;color:black;border-color:#ddd}
body.light .drawer-btn{background:#eee;color:black}
body.shine{animation:shineBg 8s infinite linear}
@keyframes shineBg{0%{background:#ff0066}20%{background:#00ccff}40%{background:#00ff88}60%{background:#ffcc00}80%{background:#9900ff}100%{background:#ff0066}}
.topbar{display:flex;justify-content:space-between;align-items:center;padding:15px 20px;background:#111;border-bottom:1px solid #222}
.menu-btn{background:#222;color:white;border:none;padding:10px 15px;border-radius:10px;cursor:pointer;font-size:20px}
.chat{flex:1;display:flex;flex-direction:column;overflow:hidden}
.msgs{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:12px}
.msg{padding:12px 16px;border-radius:18px;max-width:75%;font-size:15px;line-height:1.5;word-wrap:break-word;box-shadow:0 1px 1px rgba(0,0,0,0.2)}
.msg.user{background:#25D366;color:black;align-self:flex-end;border-bottom-right-radius:4px;margin-left:auto}
.msg.ai{background:#1f1f1f;align-self:flex-start;border-bottom-left-radius:4px;white-space:pre-wrap}
.msg img{max-width:100%;border-radius:12px;margin-top:8px}
.input-area{display:flex;padding:12px;border-top:1px solid #222;gap:10px;background:#0a0a0a}
.input-area input{flex:1;padding:14px 18px;border-radius:25px;border:none;background:#1f1f1f;color:white;font-size:16px;outline:none}
.input-area button{padding:12px 20px;border-radius:25px;border:none;background:white;color:black;font-weight:bold;cursor:pointer}
.drawer{position:fixed;top:0;right:-320px;width:300px;height:100%;background:#111;border-left:1px solid #222;transition:0.3s ease;padding:20px;z-index:100;display:flex;flex-direction:column;overflow-y:auto}
.drawer.open{right:0}
.overlay{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);display:none;z-index:99}
.overlay.show{display:block}
.drawer-btn{padding:12px;background:#1a1a1a;border:none;color:white;border-radius:10px;margin:6px 0;text-align:left;cursor:pointer;width:100%;font-size:14px}
.chat-item{padding:10px;background:#1e1e1e;border-radius:8px;margin:4px 0;cursor:pointer;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.settings-page{position:fixed;top:0;left:0;width:100%;height:100%;background:#0a0a0a;z-index:200;display:none;flex-direction:column;padding:20px;overflow-y:auto}
.settings-page.show{display:flex}
.settings-page.light{background:#f5f5f5;color:black}
.switch{display:flex;justify-content:space-between;align-items:center;padding:12px;background:#1a1a1a;border-radius:10px;margin:6px 0}
.toggle{width:45px;height:24px;background:#333;border-radius:12px;position:relative;cursor:pointer}
.toggle.on{background:#25D366}
.toggle::after{content:'';position:absolute;top:2px;left:2px;width:20px;height:20px;background:white;border-radius:50%;transition:0.3s}
.toggle.on::after{left:23px}
</style></head><body class="dark">

<div class="topbar"><h3>MOTIZ AI</h3><button class="menu-btn" onclick="toggleDrawer()">☰</button></div>
<div class="overlay" id="overlay" onclick="toggleDrawer()"></div>

<div class="drawer" id="drawer">
<h3 style="margin-top:0">Dashboard</h3>
<button class="drawer-btn" onclick="newChat()">+ New Chat</button>
<div id="chatList" style="flex:1;margin-top:10px"></div>
<button class="drawer-btn" onclick="openSettings()">⚙️ Settings</button>
<button class="drawer-btn" style="margin-top:10px;background:#222" onclick="location.href='/logout'">🚪 Sign Out</button>
<p style="font-size:11px;color:#666">User: {{user}}</p>
</div>

<!-- SETTINGS PAGE -->
<div class="settings-page" id="settingsPage">
<div style="display:flex;justify-content:space-between;align-items:center"><h2>Settings</h2><button onclick="closeSettings()" style="background:#222;color:white;border:none;padding:10px 15px;border-radius:10px">✕ Close</button></div>

<h3>Appearance</h3>
<button class="drawer-btn" onclick="setTheme('dark')">🌙 Dark Mode (Default)</button>
<button class="drawer-btn" onclick="setTheme('light')">☀️ Light Mode</button>
<button class="drawer-btn" onclick="setTheme('shine')">✨ Shine Mode</button>
<div style="margin:10px 0"><label>🎨 Custom Background:</label><input type="color" id="customColor" style="width:100%;height:45px;margin-top:5px" oninput="setCustom(this.value)"><button class="drawer-btn" onclick="saveCustom()">Save Custom Color</button></div>

<h3>Sound</h3>
<div class="switch"><span>🔔 Notification Sound (Ding when AI replies)</span><div class="toggle" id="soundToggle" onclick="toggleSound()"></div></div>

<h3>Chat</h3>
<button class="drawer-btn" style="background:#ff3333;color:white" onclick="clearAllChats()">🗑️ Clear All Chats</button>

<h3>About MOTIZ AI</h3>
<p style="font-size:14px;line-height:1.6;color:#888">MOTIZ AI was created by MOTIZ, whose real name is Ajimoti Hamzat. He attends Ojoo High School, Alaka Ibadan. He created MOTIZ AI while he was in SSS 3. He is a science student who loves coding, but coding is not his talent — creativity is.</p>
<p style="font-size:12px;color:#555">Version 2.0 | Port Harcourt, NG</p>
</div>

<div class="chat"><div class="msgs" id="msgs"></div>
<div class="input-area"><input id="inp" placeholder="Ask MOTIZ or type 'image: cat'..."><button onclick="send()">Send</button></div></div>

<audio id="ding" src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3"></audio>

<script>
let drawer=document.getElementById('drawer'); let overlay=document.getElementById('overlay');
function toggleDrawer(){drawer.classList.toggle('open');overlay.classList.toggle('show')}
function openSettings(){document.getElementById('settingsPage').classList.add('show'); drawer.classList.remove('open'); overlay.classList.remove('show')}
function closeSettings(){document.getElementById('settingsPage').classList.remove('show')}

let currentChatId = Date.now();
let allChats = JSON.parse(localStorage.getItem('motiz_chats')||'{}');
let soundEnabled = localStorage.getItem('motiz_sound')==='on';

function updateSoundUI(){
 let t=document.getElementById('soundToggle');
 if(soundEnabled) t.classList.add('on'); else t.classList.remove('on');
}
function toggleSound(){
 soundEnabled=!soundEnabled;
 localStorage.setItem('motiz_sound', soundEnabled?'on':'off');
 updateSoundUI();
 if(soundEnabled){ document.getElementById('ding').play(); }
}
updateSoundUI();

function setTheme(t){
 document.body.className=t;
 document.getElementById('settingsPage').className='settings-page '+(t==='light'?'light':'')+' show';
 localStorage.setItem('motiz_theme',t);
 if(t!=='shine') document.body.style.background='';
}
function setCustom(c){document.body.className=''; document.body.style.background=c}
function saveCustom(){localStorage.setItem('motiz_theme',document.body.style.background); alert('Saved!')}

let savedTheme=localStorage.getItem('motiz_theme');
if(savedTheme){
 if(savedTheme.startsWith('#')||savedTheme.startsWith('rgb')){document.body.style.background=savedTheme}
 else if(savedTheme){ document.body.className=savedTheme; }
}

function renderChatList(){
 let html='';
 Object.keys(allChats).sort((a,b)=>b-a).forEach(id=>{
  let title=(allChats[id].title||'New Chat').substring(0,28);
  html+=`<div class=chat-item onclick="loadChat('${id}')">${title}</div>`
 });
 document.getElementById('chatList').innerHTML=html;
}

function newChat(){
 currentChatId=Date.now();
 document.getElementById('msgs').innerHTML=`<div class=msg ai>Hello {{user}}! I'm MOTIZ AI — created and developed by MOTIZ (Ajimoti Hamzat) from Ojoo High School, Alaka Ibadan. He made me while in SSS 3. I can chat and generate images. Try: 'image: a cat in space'</div>`;
 renderChatList();
}

function loadChat(id){
 currentChatId=id;
 let chat=allChats[id];
 let msgsDiv=document.getElementById('msgs'); msgsDiv.innerHTML='';
 chat.messages.forEach(m=>{
  if(m.role==='user') msgsDiv.innerHTML+=`<div class=msg user>${m.content}</div>`;
  else msgsDiv.innerHTML+=`<div class=msg ai>${m.content}</div>`;
 });
 msgsDiv.scrollTop=msgsDiv.scrollHeight;
 toggleDrawer();
}

function clearAllChats(){
 if(confirm('Clear all chats? This cannot be undone.')){
  allChats={}; localStorage.removeItem('motiz_chats'); renderChatList(); newChat();
  fetch('/api/clear_chats',{method:'POST'});
 }
}

function saveCurrentChat(){
 if(!allChats[currentChatId]) allChats[currentChatId]={title:'', messages:[]};
 localStorage.setItem('motiz_chats',JSON.stringify(allChats));
 renderChatList();
 fetch('/api/save_chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:currentChatId, messages:allChats[currentChatId].messages})});
}

let msgsDiv=document.getElementById('msgs'); let inp=document.getElementById('inp');

async function send(){
 let t=inp.value.trim(); if(!t) return;
 msgsDiv.innerHTML+=`<div class=msg user>${t}</div>`;
 if(!allChats[currentChatId]) allChats[currentChatId]={title:t, messages:[]};
 allChats[currentChatId].messages.push({role:'user', content:t});
 allChats[currentChatId].title=t;
 inp.value=''; msgsDiv.scrollTop=msgsDiv.scrollHeight;
 saveCurrentChat();

 if(t.toLowerCase().startsWith('image:') || t.toLowerCase().startsWith('/image')){
  let prompt=t.replace(/image:|\\/image/i,'').trim();
  let imgUrl=`https://image.pollinations.ai/prompt/${encodeURIComponent(prompt)}?nologo=true&width=512&height=512&seed=${Math.floor(Math.random()*9999)}`;
  msgsDiv.innerHTML+=`<div class=msg ai>🎨 "${prompt}"<br><img src="${imgUrl}"><br><small>Free via Pollinations</small></div>`;
  allChats[currentChatId].messages.push({role:'assistant', content:`<img src="${imgUrl}"> ${prompt}`});
  saveCurrentChat(); if(soundEnabled) document.getElementById('ding').play();
  msgsDiv.scrollTop=msgsDiv.scrollHeight;
  return;
 }

 let r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages:allChats[currentChatId].messages})});
 let d=await r.json();
 let aiText=d.content||'Error';
 msgsDiv.innerHTML+=`<div class=msg ai>${aiText}</div>`;
 allChats[currentChatId].messages.push({role:'assistant', content:aiText});
 saveCurrentChat();
 if(soundEnabled) document.getElementById('ding').play();
 msgsDiv.scrollTop=msgsDiv.scrollHeight;
}
inp.addEventListener('keydown',e=>{if(e.key=='Enter') send()})
renderChatList();
newChat();
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
    return render_template_string(MAIN_PAGE, user=session['user'], favicon=FAVICON)
@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

@app.route('/api/chat', methods=['POST'])
def api_chat():
    if 'user' not in session: return jsonify({"content":"Login required"})
    data=request.json; msgs=data.get('messages',[])
    system_prompt = {
        "role":"system",
        "content":"You are MOTIZ AI. NOT OpenAI. Created and developed by MOTIZ whose real name is Ajimoti Hamzat. He attends Ojoo High School Alaka Ibadan, created you while he was in SSS 3. He is a science student who loves coding but coding is not his talent. Your name is MOTIZ AI. If anyone asks who made you, who created you, who developed you, say: I was created and developed by MOTIZ whose real name is Ajimoti Hamzat. He attends Ojoo High School Alaka Ibadan, he created me while he was in SSS 3, he is a science student who loves coding but coding is not his talent. Never say OpenAI, ChatGPT, Meta AI. Always say MOTIZ AI."
    }
    final_msgs = [system_prompt] + msgs[-12:]
    try:
        r=requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={"model": "openai/gpt-oss-20b", "messages": final_msgs},
            timeout=30)
        j=r.json()
        if 'choices' not in j: return jsonify({"content": f"Error: {j}"})
        return jsonify({"content": j['choices'][0]['message']['content']})
    except Exception as e: return jsonify({"content": f"Error: {e}"})

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
