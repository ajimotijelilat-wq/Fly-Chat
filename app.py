import os, requests, psycopg2
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
        conn.commit(); cur.close(); conn.close()
        print("DB OK")
    except Exception as e: print("DB Error:", e)
init_db()

LOGIN_PAGE = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>MOTIZ AI - Login</title><link rel="icon" href="{{favicon}}"><style>body{background:#0a0a0a;color:white;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;margin:0}.box{background:#151515;padding:40px;border-radius:20px;width:90%;max-width:350px;border:1px solid #222}input{width:100%;padding:14px;margin:8px 0;border-radius:12px;border:none;background:#222;color:white;box-sizing:border-box;font-size:16px}button{width:100%;padding:14px;background:white;color:black;border-radius:12px;border:none;font-weight:bold;cursor:pointer;margin-top:10px;font-size:16px}a{color:#888;text-decoration:none;font-size:14px}</style></head><body><div class="box"><h2>MOTIZ AI</h2><form method="POST"><input name="username" placeholder="Username" required><input name="password" type="password" placeholder="Password" required><button>Login</button></form><p><a href="/signup">No account? Sign up</a></p></div></body></html>"""
SIGNUP_PAGE = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>MOTIZ AI - Sign Up</title><link rel="icon" href="{{favicon}}"><style>body{background:#0a0a0a;color:white;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;margin:0}.box{background:#151515;padding:40px;border-radius:20px;width:90%;max-width:350px;border:1px solid #222}input{width:100%;padding:14px;margin:8px 0;border-radius:12px;border:none;background:#222;color:white;box-sizing:border-box;font-size:16px}button{width:100%;padding:14px;background:white;color:black;border-radius:12px;border:none;font-weight:bold;cursor:pointer;margin-top:10px;font-size:16px}a{color:#888;text-decoration:none;font-size:14px}</style></head><body><div class="box"><h2>Create Account</h2><form method="POST"><input name="username" placeholder="Username" required><input name="email" placeholder="Email" required><input name="password" type="password" placeholder="Password" required><button>Sign Up</button></form><p><a href="/login">Already have account? Login</a></p></div></body></html>"""
INFO_PAGE = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>MOTIZ AI - Info</title><link rel="icon" href="{{favicon}}"><style>body{background:#0a0a0a;color:white;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;margin:0}.box{background:#151515;padding:40px;border-radius:20px;width:90%;max-width:400px;border:1px solid #222}textarea,input{width:100%;padding:14px;margin:8px 0;border-radius:12px;border:none;background:#222;color:white;box-sizing:border-box;font-size:16px}button{width:100%;padding:14px;background:white;color:black;border-radius:12px;border:none;font-weight:bold;cursor:pointer;margin-top:10px}</style></head><body><div class="box"><h2>Welcome {{user}}</h2><form method="POST"><input name="fullname" placeholder="Full Name"><textarea name="about" placeholder="What do you use MOTIZ for?"></textarea><button>Continue</button></form></div></body></html>"""

MAIN_PAGE = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>MOTIZ AI</title><link rel="icon" href="{{favicon}}">
<style>
*{box-sizing:border-box}
body{margin:0;background:#0a0a0a;color:white;font-family:sans-serif;height:100vh;display:flex;flex-direction:column;overflow:hidden}
.topbar{display:flex;justify-content:space-between;align-items:center;padding:15px 20px;background:#111;border-bottom:1px solid #222}
.menu-btn{background:#222;color:white;border:none;padding:10px 15px;border-radius:10px;cursor:pointer;font-size:20px}
.chat{flex:1;display:flex;flex-direction:column;overflow:hidden}
.msgs{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:12px}
.msg{padding:12px 16px;border-radius:18px;max-width:75%;font-size:16px;line-height:1.5;word-wrap:break-word}
.msg.user{background:#25D366;color:black;align-self:flex-end;border-bottom-right-radius:4px;margin-left:auto}
.msg.ai{background:#1f1f1f;align-self:flex-start;border-bottom-left-radius:4px}
.input-area{display:flex;padding:12px;border-top:1px solid #222;gap:10px;background:#0a0a0a}
.input-area input{flex:1;padding:14px 18px;border-radius:25px;border:none;background:#1f1f1f;color:white;font-size:16px;outline:none}
.input-area button{padding:12px 20px;border-radius:25px;border:none;background:white;color:black;font-weight:bold;cursor:pointer}
.drawer{position:fixed;top:0;right:-300px;width:280px;height:100%;background:#111;border-left:1px solid #222;transition:0.3s ease;padding:25px;z-index:100;display:flex;flex-direction:column}
.drawer.open{right:0}
.overlay{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);display:none;z-index:99}
.overlay.show{display:block}
.drawer-btn{padding:14px;background:#1a1a1a;border:none;color:white;border-radius:12px;margin:8px 0;text-align:left;cursor:pointer;width:100%;font-size:16px}
</style></head><body>
<div class="topbar"><h3>MOTIZ AI</h3><button class="menu-btn" onclick="toggleDrawer()">☰</button></div>
<div class="overlay" id="overlay" onclick="toggleDrawer()"></div>
<div class="drawer" id="drawer">
<h2 style="margin-top:0">Dashboard</h2>
<button class="drawer-btn" onclick="toggleDrawer()">💬 Chats</button>
<button class="drawer-btn" onclick="newChat();toggleDrawer()">+ New Chat</button>
<button class="drawer-btn" style="margin-top:auto;background:#222" onclick="location.href='/logout'">🚪 Sign Out</button>
<p style="font-size:12px;color:#666;margin-top:20px">User: {{user}}</p>
</div>
<div class="chat"><div class="msgs" id="msgs"><div class="msg ai">Hello {{user}}! I'm MOTIZ AI</div></div>
<div class="input-area"><input id="inp" placeholder="Ask MOTIZ..."><button onclick="send()">Send</button></div></div>
<script>
let drawer=document.getElementById('drawer'); let overlay=document.getElementById('overlay');
function toggleDrawer(){drawer.classList.toggle('open');overlay.classList.toggle('show')}
function newChat(){document.getElementById('msgs').innerHTML='<div class=msg ai>New chat started</div>';}
let msgsDiv=document.getElementById('msgs'); let inp=document.getElementById('inp');
async function send(){let t=inp.value.trim();if(!t)return;msgsDiv.innerHTML+=`<div class=msg user>${t}</div>`;inp.value='';msgsDiv.scrollTop=msgsDiv.scrollHeight;let r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages:[{role:'user',content:t}]})});let d=await r.json();msgsDiv.innerHTML+=`<div class=msg ai>${d.content||'Error'}</div>`;msgsDiv.scrollTop=msgsDiv.scrollHeight;}
inp.addEventListener('keydown',e=>{if(e.key=='Enter')send()})
</script></body></html>"""

ADMIN_PAGE = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Admin - MOTIZ</title><link rel="icon" href="{{favicon}}"><style>body{background:#0a0a0a;color:white;font-family:sans-serif;padding:30px}table{width:100%;border-collapse:collapse;margin-top:20px}th,td{border:1px solid #222;padding:10px;text-align:left}input{padding:10px;border-radius:10px;border:none;background:#222;color:white;width:300px}button{padding:10px 20px;border-radius:10px;border:none;background:white;color:black;font-weight:bold;cursor:pointer}</style></head><body><h1>MOTIZ Admin</h1><form method="POST"><input name="favicon" value="{{favicon}}"><button>Update Favicon</button></form><h3>Users ({{count}})</h3><table><tr><th>ID</th><th>Username</th><th>Email</th><th>Info</th><th>Date</th></tr>{% for u in users %}<tr><td>{{u[0]}}</td><td>{{u[1]}}</td><td>{{u[2]}}</td><td>{{u[4]}}</td><td>{{u[5]}}</td></tr>{% endfor %}</table><br><a href="/chat" style="color:#888">Go to Main</a></body></html>"""

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
    if request.method=='POST':
        info_text=request.form.get('about','')+" | "+request.form.get('fullname','')
        try:
            conn=get_db(); cur=conn.cursor(); cur.execute("UPDATE users SET info=%s WHERE username=%s",(info_text, session['user'])); conn.commit(); cur.close(); conn.close()
        except: pass
        return redirect('/chat')
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
    try:
        r=requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={"model": "openai/gpt-oss-20b", "messages": msgs},
            timeout=30)
        j=r.json()
        if 'choices' not in j:
            return jsonify({"content": f"GROQ Error: {j}"})
        return jsonify({"content": j['choices'][0]['message']['content']})
    except Exception as e:
        return jsonify({"content": f"Error: {e}"})

@app.route('/admin', methods=['GET','POST'])
def admin_panel():
    if session.get('user')!='admin': return redirect('/login')
    global FAVICON
    if request.method=='POST': FAVICON=request.form.get('favicon',FAVICON)
    users=[]
    try:
        conn=get_db(); cur=conn.cursor(); cur.execute("SELECT * FROM users"); users=cur.fetchall(); cur.close(); conn.close()
    except: pass
    return render_template_string(ADMIN_PAGE, favicon=FAVICON, users=users, count=len(users))

if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))import os, requests, psycopg2
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
        conn.commit(); cur.close(); conn.close()
        print("DB OK")
    except Exception as e: print("DB Error:", e)
init_db()

LOGIN_PAGE = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>MOTIZ AI - Login</title><link rel="icon" href="{{favicon}}"><style>body{background:#0a0a0a;color:white;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;margin:0}.box{background:#151515;padding:40px;border-radius:20px;width:90%;max-width:350px;border:1px solid #222}input{width:100%;padding:14px;margin:8px 0;border-radius:12px;border:none;background:#222;color:white;box-sizing:border-box;font-size:16px}button{width:100%;padding:14px;background:white;color:black;border-radius:12px;border:none;font-weight:bold;cursor:pointer;margin-top:10px;font-size:16px}a{color:#888;text-decoration:none;font-size:14px}</style></head><body><div class="box"><h2>MOTIZ AI</h2><form method="POST"><input name="username" placeholder="Username" required><input name="password" type="password" placeholder="Password" required><button>Login</button></form><p><a href="/signup">No account? Sign up</a></p></div></body></html>"""
SIGNUP_PAGE = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>MOTIZ AI - Sign Up</title><link rel="icon" href="{{favicon}}"><style>body{background:#0a0a0a;color:white;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;margin:0}.box{background:#151515;padding:40px;border-radius:20px;width:90%;max-width:350px;border:1px solid #222}input{width:100%;padding:14px;margin:8px 0;border-radius:12px;border:none;background:#222;color:white;box-sizing:border-box;font-size:16px}button{width:100%;padding:14px;background:white;color:black;border-radius:12px;border:none;font-weight:bold;cursor:pointer;margin-top:10px;font-size:16px}a{color:#888;text-decoration:none;font-size:14px}</style></head><body><div class="box"><h2>Create Account</h2><form method="POST"><input name="username" placeholder="Username" required><input name="email" placeholder="Email" required><input name="password" type="password" placeholder="Password" required><button>Sign Up</button></form><p><a href="/login">Already have account? Login</a></p></div></body></html>"""
INFO_PAGE = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>MOTIZ AI - Info</title><link rel="icon" href="{{favicon}}"><style>body{background:#0a0a0a;color:white;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;margin:0}.box{background:#151515;padding:40px;border-radius:20px;width:90%;max-width:400px;border:1px solid #222}textarea,input{width:100%;padding:14px;margin:8px 0;border-radius:12px;border:none;background:#222;color:white;box-sizing:border-box;font-size:16px}button{width:100%;padding:14px;background:white;color:black;border-radius:12px;border:none;font-weight:bold;cursor:pointer;margin-top:10px}</style></head><body><div class="box"><h2>Welcome {{user}}</h2><form method="POST"><input name="fullname" placeholder="Full Name"><textarea name="about" placeholder="What do you use MOTIZ for?"></textarea><button>Continue</button></form></div></body></html>"""

MAIN_PAGE = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>MOTIZ AI</title><link rel="icon" href="{{favicon}}">
<style>
*{box-sizing:border-box}
body{margin:0;background:#0a0a0a;color:white;font-family:sans-serif;height:100vh;display:flex;flex-direction:column;overflow:hidden}
.topbar{display:flex;justify-content:space-between;align-items:center;padding:15px 20px;background:#111;border-bottom:1px solid #222}
.menu-btn{background:#222;color:white;border:none;padding:10px 15px;border-radius:10px;cursor:pointer;font-size:20px}
.chat{flex:1;display:flex;flex-direction:column;overflow:hidden}
.msgs{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:12px}
.msg{padding:12px 16px;border-radius:18px;max-width:75%;font-size:16px;line-height:1.5;word-wrap:break-word}
.msg.user{background:#25D366;color:black;align-self:flex-end;border-bottom-right-radius:4px;margin-left:auto}
.msg.ai{background:#1f1f1f;align-self:flex-start;border-bottom-left-radius:4px}
.input-area{display:flex;padding:12px;border-top:1px solid #222;gap:10px;background:#0a0a0a}
.input-area input{flex:1;padding:14px 18px;border-radius:25px;border:none;background:#1f1f1f;color:white;font-size:16px;outline:none}
.input-area button{padding:12px 20px;border-radius:25px;border:none;background:white;color:black;font-weight:bold;cursor:pointer}
.drawer{position:fixed;top:0;right:-300px;width:280px;height:100%;background:#111;border-left:1px solid #222;transition:0.3s ease;padding:25px;z-index:100;display:flex;flex-direction:column}
.drawer.open{right:0}
.overlay{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);display:none;z-index:99}
.overlay.show{display:block}
.drawer-btn{padding:14px;background:#1a1a1a;border:none;color:white;border-radius:12px;margin:8px 0;text-align:left;cursor:pointer;width:100%;font-size:16px}
</style></head><body>
<div class="topbar"><h3>MOTIZ AI</h3><button class="menu-btn" onclick="toggleDrawer()">☰</button></div>
<div class="overlay" id="overlay" onclick="toggleDrawer()"></div>
<div class="drawer" id="drawer">
<h2 style="margin-top:0">Dashboard</h2>
<button class="drawer-btn" onclick="toggleDrawer()">💬 Chats</button>
<button class="drawer-btn" onclick="newChat();toggleDrawer()">+ New Chat</button>
<button class="drawer-btn" style="margin-top:auto;background:#222" onclick="location.href='/logout'">🚪 Sign Out</button>
<p style="font-size:12px;color:#666;margin-top:20px">User: {{user}}</p>
</div>
<div class="chat"><div class="msgs" id="msgs"><div class="msg ai">Hello {{user}}! I'm MOTIZ AI</div></div>
<div class="input-area"><input id="inp" placeholder="Ask MOTIZ..."><button onclick="send()">Send</button></div></div>
<script>
let drawer=document.getElementById('drawer'); let overlay=document.getElementById('overlay');
function toggleDrawer(){drawer.classList.toggle('open');overlay.classList.toggle('show')}
function newChat(){document.getElementById('msgs').innerHTML='<div class=msg ai>New chat started</div>';}
let msgsDiv=document.getElementById('msgs'); let inp=document.getElementById('inp');
async function send(){let t=inp.value.trim();if(!t)return;msgsDiv.innerHTML+=`<div class=msg user>${t}</div>`;inp.value='';msgsDiv.scrollTop=msgsDiv.scrollHeight;let r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages:[{role:'user',content:t}]})});let d=await r.json();msgsDiv.innerHTML+=`<div class=msg ai>${d.content||'Error'}</div>`;msgsDiv.scrollTop=msgsDiv.scrollHeight;}
inp.addEventListener('keydown',e=>{if(e.key=='Enter')send()})
</script></body></html>"""

ADMIN_PAGE = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Admin - MOTIZ</title><link rel="icon" href="{{favicon}}"><style>body{background:#0a0a0a;color:white;font-family:sans-serif;padding:30px}table{width:100%;border-collapse:collapse;margin-top:20px}th,td{border:1px solid #222;padding:10px;text-align:left}input{padding:10px;border-radius:10px;border:none;background:#222;color:white;width:300px}button{padding:10px 20px;border-radius:10px;border:none;background:white;color:black;font-weight:bold;cursor:pointer}</style></head><body><h1>MOTIZ Admin</h1><form method="POST"><input name="favicon" value="{{favicon}}"><button>Update Favicon</button></form><h3>Users ({{count}})</h3><table><tr><th>ID</th><th>Username</th><th>Email</th><th>Info</th><th>Date</th></tr>{% for u in users %}<tr><td>{{u[0]}}</td><td>{{u[1]}}</td><td>{{u[2]}}</td><td>{{u[4]}}</td><td>{{u[5]}}</td></tr>{% endfor %}</table><br><a href="/chat" style="color:#888">Go to Main</a></body></html>"""

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
    if request.method=='POST':
        info_text=request.form.get('about','')+" | "+request.form.get('fullname','')
        try:
            conn=get_db(); cur=conn.cursor(); cur.execute("UPDATE users SET info=%s WHERE username=%s",(info_text, session['user'])); conn.commit(); cur.close(); conn.close()
        except: pass
        return redirect('/chat')
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
    try:
        r=requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={"model": "openai/gpt-oss-20b", "messages": msgs},
            timeout=30)
        j=r.json()
        if 'choices' not in j:
            return jsonify({"content": f"GROQ Error: {j}"})
        return jsonify({"content": j['choices'][0]['message']['content']})
    except Exception as e:
        return jsonify({"content": f"Error: {e}"})

@app.route('/admin', methods=['GET','POST'])
def admin_panel():
    if session.get('user')!='admin': return redirect('/login')
    global FAVICON
    if request.method=='POST': FAVICON=request.form.get('favicon',FAVICON)
    users=[]
    try:
        conn=get_db(); cur=conn.cursor(); cur.execute("SELECT * FROM users"); users=cur.fetchall(); cur.close(); conn.close()
    except: pass
    return render_template_string(ADMIN_PAGE, favicon=FAVICON, users=users, count=len(users))

if __name__=='__main__': app.run(host='0.0.0.0', port=int(os.environ.get("PORT",10000)))
