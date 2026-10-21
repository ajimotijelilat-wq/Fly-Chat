import os, requests, sqlite3, datetime, json
from flask import Flask, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "MOTIZ-AI-ULTRA-SECRET-2026")

DB = "motiz.db"
def init_db():
    con = sqlite3.connect(DB)
    con.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, created TEXT, is_admin INTEGER DEFAULT 0)")
    con.execute("CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY, user_id INTEGER, title TEXT, messages TEXT, created TEXT)")
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE username='admin'")
    if not cur.fetchone():
        cur.execute("INSERT INTO users (username,password,created,is_admin) VALUES (?,?,?,1)", 
        ("admin", generate_password_hash("MotizAdmin2026"), str(datetime.datetime.now())))
        cur.execute("INSERT INTO users (username,password,created,is_admin) VALUES (?,?,?,0)", 
        ("motiz", generate_password_hash("123456"), str(datetime.datetime.now())))
    con.commit(); con.close()
init_db()

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MOTIZ AI ULTRA - Created by MOTIZ</title>
<link rel="icon" href="https://i.imgur.com/8Km9tLL.png">
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:Inter,system-ui}
:root{--bg:#070709;--side:#111113;--card:#1c1c20;--border:#2a2a30;--purple:#7c5cff;--blue:#3b82f6}
body{background:var(--bg);color:#eee;display:flex;height:100vh;overflow:hidden}
.sidebar{width:300px;background:var(--side);border-right:1px solid var(--border);display:flex;flex-direction:column}
.s-top{padding:16px;border-bottom:1px solid var(--border)}
.logo{display:flex;gap:10px;align-items:center}
.logo img{width:36px;height:36px;border-radius:10px}
.btn{width:100%;padding:12px;border:none;border-radius:10px;color:white;font-weight:600;cursor:pointer;margin-top:10px}
.btn-p{background:linear-gradient(90deg,var(--purple),var(--blue))}
.btn-s{background:var(--card);border:1px solid var(--border)}
.tabs{display:flex;gap:6px;margin-top:12px}
.tab{flex:1;padding:8px;border-radius:8px;background:var(--card);border:1px solid var(--border);text-align:center;font-size:12px;cursor:pointer}
.tab.active{border-color:var(--purple);background:rgba(124,92,255,.2)}
.history{flex:1;overflow-y:auto;padding:10px}
.hist{padding:10px;border-radius:8px;font-size:12px;opacity:.7;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hist:hover{background:var(--card);opacity:1}
.main{flex:1;display:flex;flex-direction:column}
.header{height:56px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;padding:0 20px}
#chat{flex:1;overflow-y:auto;padding:20px;max-width:960px;margin:0 auto;width:100%}
.msg{display:flex;gap:12px;margin:20px 0}
.avatar{width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-weight:700;flex-shrink:0}
.user .avatar{background:linear-gradient(135deg,var(--purple),var(--blue))}
.ai .avatar{background:var(--card);border:1px solid var(--border)}
.bubble{max-width:80%;background:var(--card);border:1px solid var(--border);padding:14px 16px;border-radius:16px;line-height:1.6;font-size:14px;word-break:break-word}
.user .bubble{background:linear-gradient(135deg,var(--purple),var(--blue));border:none}
.bubble pre{background:#0a0a0a;padding:10px;border-radius:8px;overflow-x:auto;margin:8px 0}
.footer{padding:14px;max-width:960px;margin:0 auto;width:100%}
.input{border:1px solid var(--border);background:var(--card);border-radius:20px;display:flex;align-items:end;padding:8px;gap:6px}
.input textarea{flex:1;background:transparent;border:none;outline:none;color:white;resize:none;padding:8px}
.icon{width:38px;height:38px;border-radius:12px;border:none;background:var(--side);color:white;cursor:pointer}
.icon.send{background:var(--purple)}
.modal{position:fixed;inset:0;background:rgba(0,0,0,.7);display:none;align-items:center;justify-content:center;z-index:20}
.modal-box{background:var(--side);border:1px solid var(--border);padding:24px;border-radius:16px;width:360px}
.modal-box input{width:100%;padding:12px;border-radius:10px;background:var(--card);border:1px solid var(--border);color:white;margin:8px 0}
.admin-panel{background:var(--card);border:1px solid var(--border);padding:16px;border-radius:12px;margin:12px 0}
</style>
</head>
<body>
<div class="sidebar">
  <div class="s-top">
    <div class="logo"><img src="https://i.imgur.com/8Km9tLL.png"><div><b>MOTIZ AI ULTRA</b><div style="font-size:10px;opacity:.5">by MOTIZ • Highest Grade</div></div></div>
    <div style="margin-top:10px;font-size:12px" id="userInfo">Not logged in</div>
    <button class="btn btn-p" onclick="newChat()">+ New Chat</button>
    <div class="tabs"><div class="tab active" onclick="switchTab('chat')">Chat</div><div class="tab" onclick="switchTab('image')">Image</div><div class="tab" onclick="switchTab('admin')">Admin</div></div>
    <div style="display:flex;gap:6px;margin-top:8px"><button class="btn btn-s" onclick="openModal('login')">Login</button><button class="btn btn-s" onclick="openModal('register')">Register</button></div>
  </div>
  <div class="history" id="history"></div>
  <div style="padding:10px;font-size:10px;opacity:.4">MOTIZ AI v4.1 ULTRA • © 2026</div>
</div>

<div class="main">
  <div class="header"><div><b id="tabTitle">MOTIZ AI Chat</b> <small style="opacity:.5">GPT-4o + DALL·E 3</small></div><div><button class="icon" onclick="exportChat()">⬇️</button> <button class="icon" onclick="logout()">🚪</button></div></div>
  <div id="chatArea" style="flex:1;overflow-y:auto;padding:20px;max-width:960px;margin:0 auto;width:100%">
    <div id="chat"></div>
    <div id="imageTab" style="display:none">
      <h2>🎨 MOTIZ Image Generator</h2><p style="opacity:.6;margin:8px 0">Powered by DALL·E 3 • Created by MOTIZ</p>
      <div style="display:flex;gap:8px;margin-top:16px"><input id="imgPrompt" placeholder="e.g. MOTIZ AI robot in Lagos" style="flex:1;padding:14px;border-radius:12px;background:var(--card);border:1px solid var(--border);color:white"><button class="btn btn-p" style="width:120px;margin:0" onclick="genImage()">Generate</button></div>
      <div id="imgResult" style="margin-top:20px"></div>
    </div>
    <div id="adminTab" style="display:none"></div>
  </div>
  <div class="footer" id="footer">
    <div style="display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap">
      <span style="font-size:11px;padding:6px 10px;background:var(--card);border:1px solid var(--border);border-radius:20px;cursor:pointer" onclick="quick('Build portfolio website')">💻 Website</span>
      <span style="font-size:11px;padding:6px 10px;background:var(--card);border:1px solid var(--border);border-radius:20px;cursor:pointer" onclick="quick('Solve Further Maths')">📘 Maths</span>
      <span style="font-size:11px;padding:6px 10px;background:var(--card);border:1px solid var(--border);border-radius:20px;cursor:pointer" onclick="document.getElementById('file').click()">📎 Upload</span>
      <span style="font-size:11px;padding:6px 10px;background:var(--card);border:1px solid var(--border);border-radius:20px;cursor:pointer" onclick="startVoice()">🎤 Voice</span>
    </div>
    <div class="input">
      <input type="file" id="file" hidden accept="image/*,video/*">
      <textarea id="inp" rows="1" placeholder="Message MOTIZ AI ULTRA..."></textarea>
      <button class="icon" onclick="document.getElementById('file').click()">📎</button>
      <button class="icon send" onclick="send()">↑</button>
    </div>
  </div>
</div>

<div class="modal" id="authModal"><div class="modal-box">
  <h3 id="modalTitle">Login</h3>
  <input id="authUser" placeholder="Username">
  <input id="authPass" type="password" placeholder="Password">
  <button class="btn btn-p" onclick="submitAuth()">Submit</button>
  <button class="btn btn-s" onclick="closeModal()">Close</button>
  <div style="font-size:11px;opacity:.5;margin-top:8px">Admin: admin / MotizAdmin2026<br>Demo: motiz / 123456</div>
</div></div>

<script>
let chatHistory=[], imgData=null, authMode='login', currentUser=null;
function openModal(mode){ authMode=mode; document.getElementById('modalTitle').innerText=mode; document.getElementById('authModal').style.display='flex'; }
function closeModal(){ document.getElementById('authModal').style.display='none'; }
async function submitAuth(){
  const u=document.getElementById('authUser').value.trim();
  const p=document.getElementById('authPass').value.trim();
  if(!u||!p) return alert('Fill all');
  const res=await fetch('/api/auth/'+authMode,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})});
  const d=await res.json();
  if(d.error) return alert(d.error);
  currentUser=d.user; document.getElementById('userInfo').innerText='Logged: '+currentUser.username + (currentUser.is_admin?' (ADMIN)':'');
  closeModal(); loadHistoryFromServer();
}
async function logout(){ await fetch('/api/auth/logout',{method:'POST'}); currentUser=null; document.getElementById('userInfo').innerText='Not logged in'; alert('Logged out'); }
async function loadHistoryFromServer(){
  if(!currentUser) return;
  const res=await fetch('/api/chats'); const data=await res.json();
  const h=document.getElementById('history'); h.innerHTML='';
  data.forEach((c,i)=>{ const d=document.createElement('div'); d.className='hist'; d.innerText=c.title; d.onclick=()=>{ chatHistory=JSON.parse(c.messages); document.getElementById('chat').innerHTML=''; chatHistory.forEach(m=>{ if(m.role!='system'){ const t=typeof m.content==='string'?m.content:m.content[0].text; addMsg(m.role==='user'?'user':'ai',t); }}); }; h.appendChild(d); });
}
function switchTab(t){
  document.querySelectorAll('.tab').forEach((e,i)=>e.classList.toggle('active', ['chat','image','admin'][i]===t));
  document.getElementById('chat').style.display=t==='chat'?'block':'none';
  document.getElementById('imageTab').style.display=t==='image'?'block':'none';
  document.getElementById('adminTab').style.display=t==='admin'?'block':'none';
  document.getElementById('footer').style.display=t==='chat'?'block':'none';
  document.getElementById('tabTitle').innerText=t==='chat'?'MOTIZ AI Chat':t==='image'?'MOTIZ Image Gen':'Admin Panel';
  if(t==='admin') loadAdmin();
}
async function loadAdmin(){
  const res=await fetch('/api/admin/users'); const data=await res.json();
  if(data.error){ document.getElementById('adminTab').innerHTML='<p style="color:red">'+data.error+'</p>'; return; }
  let html='<h2>Admin Dashboard - MOTIZ</h2><div class="admin-panel"><b>Total Users:</b> '+data.users.length+'</div>';
  data.users.forEach(u=>{ html+='<div class="admin-panel">👤 '+u[1]+' | Admin: '+(u[4]?'Yes':'No')+' | '+u[3]+'</div>'; });
  html+='<div class="admin-panel"><b>Total Chats:</b> '+data.chats+'</div>';
  document.getElementById('adminTab').innerHTML=html;
}
function quick(t){ document.getElementById('inp').value=t; send(); }
function welcome(){ return `<div style="text-align:center;margin-top:40px"><h1 style="font-size:32px;background:linear-gradient(90deg,#7c5cff,#3b82f6);-webkit-background-clip:text;-webkit-text-fill-color:transparent">MOTIZ AI ULTRA</h1><p style="opacity:.6">Highest Grade • Auth + Image + Vision + Admin<br>Created by MOTIZ • Better than ChatGPT</p></div>`; }
document.getElementById('chat').innerHTML=welcome();
function newChat(){ document.getElementById('chat').innerHTML=welcome(); chatHistory=[]; }
function exportChat(){ const b=new Blob([JSON.stringify(chatHistory,null,2)],{type:'application/json'}); const a=document.createElement('a'); a.href=URL.createObjectURL(b); a.download='motiz.json'; a.click(); }
const file=document.getElementById('file');
file.onchange=()=>handleFile(file.files[0]);
function handleFile(f){ if(!f) return; const r=new FileReader(); r.onload=()=>{ imgData=r.result; addMsg('user','<img src="'+imgData+'" style="max-width:240px;border-radius:10px"><br><small>'+f.name+'</small>'); }; r.readAsDataURL(f); }
function addMsg(who, raw){
  const chat=document.getElementById('chat'); const div=document.createElement('div'); div.className='msg '+who;
  let html = who==='ai' ? marked.parse(raw) : raw;
  div.innerHTML='<div class="avatar">'+(who==='user'?'YOU':'M')+'</div><div class="bubble">'+html+'</div>';
  chat.appendChild(div); chat.scrollTop=chat.scrollHeight; div.querySelectorAll('pre code').forEach(b=>hljs.highlightElement(b)); return div;
}
function startVoice(){ const R=window.SpeechRecognition||window.webkitSpeechRecognition; if(!R){ alert('Voice not supported'); return; } const rec=new R(); rec.lang='en-US'; rec.start(); rec.onresult=e=>{ document.getElementById('inp').value=e.results[0][0].transcript; send(); }; }
async function send(){
  const inp=document.getElementById('inp'); const text=inp.value.trim();
  if(!text && !imgData) return;
  let content=text;
  if(imgData){ content=[{type:"text",text:text||"Describe this"}, {type:"image_url",image_url:{url:imgData}}]; }
  if(text && !imgData) addMsg('user', text);
  chatHistory.push({role:"user",content:content});
  inp.value=''; imgData=null; file.value='';
  const load=addMsg('ai','Thinking...');
  try{
    const res=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages:chatHistory})});
    const data=await res.json(); load.remove();
    const reply=(data.choices&&data.choices[0]&&data.choices[0].message&&data.choices[0].message.content)||JSON.stringify(data);
    addMsg('ai', reply); chatHistory.push({role:"assistant",content:reply});
  }catch(e){ load.remove(); addMsg('ai','Error: '+e.message); }
}
async function genImage(){
  const p=document.getElementById('imgPrompt').value.trim();
  if(!p) return alert('Enter prompt');
  document.getElementById('imgResult').innerHTML='Generating... 🎨';
  const res=await fetch('/api/image',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:p})});
  const data=await res.json();
  if(data.error){ document.getElementById('imgResult').innerHTML='Error: '+data.error; return; }
  const url=data.data?.[0]?.url || data.url || (data.data&&data.data[0]&&data.data[0].b64_json ? 'data:image/png;base64,'+data.data[0].b64_json : '');
  document.getElementById('imgResult').innerHTML='<img src="'+url+'" style="max-width:100%;border-radius:16px"><br><a href="'+url+'" target="_blank">Open Full</a>';
}
document.getElementById('inp').addEventListener('keydown',e=>{ if(e.key==='Enter'&&!e.shiftKey){ e.preventDefault(); send(); }});
fetch('/api/auth/me').then(r=>r.json()).then(d=>{ if(d.user){ currentUser=d.user; document.getElementById('userInfo').innerText='Logged: '+currentUser.username+(currentUser.is_admin?' (ADMIN)':''); loadHistoryFromServer(); }});
</script>
</body>
</html>
"""

@app.route("/")
def home(): return HTML

@app.route("/api/auth/<action>", methods=["POST"])
def auth_api(action):
    data = request.get_json()
    username = data.get("username","").strip()
    password = data.get("password","")
    con = sqlite3.connect(DB)
    cur = con.cursor()
    if action == "register":
        if not username or not password:
            con.close(); return jsonify({"error":"Fill all"}),400
        try:
            cur.execute("INSERT INTO users (username,password,created) VALUES (?,?,?)", (username, generate_password_hash(password), str(datetime.datetime.now())))
            con.commit()
            user_id = cur.lastrowid
            con.close()
            session["user_id"]=user_id; session["username"]=username; session["is_admin"]=0
            return jsonify({"user":{"id":user_id,"username":username,"is_admin":False}})
        except sqlite3.IntegrityError:
            con.close(); return jsonify({"error":"Username exists"}),400
    elif action == "login":
        cur.execute("SELECT id,username,password,is_admin FROM users WHERE username=?", (username,))
        row = cur.fetchone(); con.close()
        if not row or not check_password_hash(row[2], password):
            return jsonify({"error":"Invalid login"}),401
        session["user_id"]=row[0]; session["username"]=row[1]; session["is_admin"]=row[3]
        return jsonify({"user":{"id":row[0],"username":row[1],"is_admin":bool(row[3])}})
    con.close(); return jsonify({"error":"Unknown"}),400

@app.route("/api/auth/logout", methods=["POST"])
def logout_api(): session.clear(); return jsonify({"ok":True})

@app.route("/api/auth/me")
def me():
    if "user_id" not in session: return jsonify({"user":None})
    return jsonify({"user":{"id":session["user_id"],"username":session["username"],"is_admin":bool(session.get("is_admin",0))}})

@app.route("/api/chat", methods=["POST"])
def chat_api():
    body = request.get_json(); messages = body.get("messages",[])
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key: return jsonify({"error":"OPENROUTER_API_KEY missing"}),500
    if "user_id" in session and messages:
        con = sqlite3.connect(DB); cur = con.cursor()
        try:
            first = messages[0].get("content","")
            if isinstance(first, list):
                title = first[0].get("text","Image Chat")[:40]
            else:
                title = str(first)[:40]
        except:
            title = "New Chat"
        cur.execute("INSERT INTO chats (user_id,title,messages,created) VALUES (?,?,?,?)", (session["user_id"], title, json.dumps(messages), str(datetime.datetime.now())))
        con.commit(); con.close()
    payload = {"model":"openai/gpt-4o","messages":[{"role":"system","content":"You are MOTIZ AI ULTRA created by MOTIZ. Highest grade AI better than ChatGPT with vision, code, auth, admin, image gen."}] + messages,"temperature":0.7,"max_tokens":3500}
    try:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers={"Authorization":f"Bearer {key}","Content-Type":"application/json","X-Title":"MOTIZ AI"}, json=payload, timeout=90)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"error":str(e)}),500

@app.route("/api/image", methods=["POST"])
def image_api():
    body = request.get_json(); prompt = body.get("prompt","")
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key: return jsonify({"error":"API key missing"}),500
    if not prompt: return jsonify({"error":"Prompt empty"}),400
    try:
        r = requests.post("https://openrouter.ai/api/v1/images/generations", headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"}, json={"model":"openai/dall-e-3","prompt":prompt,"n":1,"size":"1024x1024"}, timeout=90)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"error":str(e)}),500

@app.route("/api/chats")
def get_chats():
    if "user_id" not in session: return jsonify([])
    con = sqlite3.connect(DB); cur = con.cursor()
    cur.execute("SELECT title,messages FROM chats WHERE user_id=? ORDER BY id DESC LIMIT 20", (session["user_id"],))
    rows = cur.fetchall(); con.close()
    return jsonify([{"title":r[0],"messages":r[1]} for r in rows])

@app.route("/api/admin/users")
def admin_users():
    if not session.get("is_admin"): return jsonify({"error":"Admin only. Login as admin / MotizAdmin2026"}),403
    con = sqlite3.connect(DB); cur = con.cursor()
    cur.execute("SELECT * FROM users"); users = cur.fetchall()
    cur.execute("SELECT COUNT(*) FROM chats"); chat_count = cur.fetchone()[0]
    con.close()
    return jsonify({"users":users,"chats":chat_count})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
