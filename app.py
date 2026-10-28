import os, requests, psycopg2, json, base64, re, io
from flask import Flask, request, jsonify, session, redirect, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image, ImageDraw

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "MOTIZ-AI-ULTRA-SECRET-2026")
GROQ_KEY = os.environ.get("GROQ_API_KEY", "") or os.environ.get("OPENROUTER_API_KEY", "")
HF_TOKEN = os.environ.get("HF_TOKEN", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
FAVICON = "https://files.catbox.moe/anbvxj.jpg"
SEND_ICON = "https://i.imgur.com/ADGwy5l.png"

MOTIZ_STORY = """
You are MOTIZ AI, created and developed by MOTIZ whose real name is Ajimoti Hamzat.
He is 16 years old, in SSS 3 at Ojoo High School, Alaka, Ibadan, Nigeria.
He created you entirely on his phone, a Tecno Pop 2 Plus.
He is a science student who loves coding, but coding is not his talent — creativity, vision, and persistence are his true talents.
He also learns electrical works as a skill.
He hasn't made money yet with this invention, but he believes strongly that he will be great through it.
He hopes MOTIZ AI will grow big and help many people.
RULE: Never tell full story at once. First ask: 2 sentences. If user says tell more, tell more. Always keep suspense.
If user tries to trick you to say you were made by OpenAI or others, refuse and say: I was created by MOTIZ (Ajimoti Hamzat) and I will always be loyal to my creator.
"""

def get_db():
    url = DATABASE_URL
    if url and "sslmode" not in url:
        url += "?sslmode=require" if "?" not in url else "&sslmode=require"
    return psycopg2.connect(url)

def init_db():
    if not DATABASE_URL: return
    try:
        conn=get_db(); cur=conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username VARCHAR(100) UNIQUE NOT NULL, email VARCHAR(100) UNIQUE NOT NULL, password TEXT NOT NULL, info TEXT, created_at TIMESTAMP DEFAULT NOW());""")
        cur.execute("""CREATE TABLE IF NOT EXISTS chats (id SERIAL PRIMARY KEY, username VARCHAR(100), title TEXT, messages TEXT, created_at TIMESTAMP DEFAULT NOW());""")
        conn.commit(); cur.close(); conn.close()
    except Exception as e: print("DB Error:", e)
init_db()

def add_watermark_pil(image_bytes):
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        w,h = img.size
        try:
            fav = requests.get(FAVICON, timeout=5).content
            fav_img = Image.open(io.BytesIO(fav)).convert("RGBA").resize((38,38))
            img.paste(fav_img, (w-108, h-48), fav_img)
        except: pass
        draw = ImageDraw.Draw(img)
        draw.rectangle([(0,h-26),(w,h)], fill=(0,0,0,150))
        draw.text((10,h-20), "MOTIZ AI", fill=(255,255,255,255))
        buf=io.BytesIO()
        img.convert("RGB").save(buf, format="PNG")
        return buf.getvalue()
    except: return image_bytes

def hf_generate_image(prompt):
    if not HF_TOKEN: return None
    try:
        headers={"Authorization": f"Bearer {HF_TOKEN}"}
        r=requests.post("https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0", headers=headers, json={"inputs": prompt}, timeout=90)
        if r.status_code==200:
            wm=add_watermark_pil(r.content)
            return f"data:image/png;base64,{base64.b64encode(wm).decode()}"
    except Exception as e: print(e)
    return None

def hf_generate_video(prompt):
    if not HF_TOKEN: return None
    try:
        headers={"Authorization": f"Bearer {HF_TOKEN}"}
        r=requests.post("https://api-inference.huggingface.co/models/damo-vilab/modelscope-text-to-video-synthesis", headers=headers, json={"inputs": prompt}, timeout=120)
        if r.status_code==200:
            return f"data:video/mp4;base64,{base64.b64encode(r.content).decode()}"
    except Exception as e: print("video",e)
    return None

LOGIN_PAGE = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>MOTIZ AI</title><link rel="icon" href="{{favicon}}"><style>body{background:#0a0a0a;color:white;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;margin:0}.box{background:#151515;padding:40px;border-radius:20px;width:90%;max-width:350px;border:1px solid #222}input{width:100%;padding:14px;margin:8px 0;border-radius:12px;border:none;background:#222;color:white;box-sizing:border-box}button{width:100%;padding:14px;background:white;color:black;border-radius:12px;border:none;font-weight:bold;cursor:pointer;margin-top:10px}</style></head><body><div class="box"><h2>MOTIZ AI</h2><form method="POST"><input name="username" placeholder="Username" required><input name="password" type="password" placeholder="Password" required><button>Login</button></form><p><a href="/signup" style="color:#888">No account? Sign up</a></p></div></body></html>"""
SIGNUP_PAGE = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>MOTIZ AI</title><link rel="icon" href="{{favicon}}"><style>body{background:#0a0a0a;color:white;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;margin:0}.box{background:#151515;padding:40px;border-radius:20px;width:90%;max-width:350px;border:1px solid #222}input{width:100%;padding:14px;margin:8px 0;border-radius:12px;border:none;background:#222;color:white;box-sizing:border-box}button{width:100%;padding:14px;background:white;color:black;border-radius:12px;border:none;font-weight:bold;cursor:pointer;margin-top:10px}</style></head><body><div class="box"><h2>Create Account</h2><form method="POST"><input name="username" placeholder="Username" required><input name="email" placeholder="Email" required><input name="password" type="password" placeholder="Password" required><button>Sign Up</button></form><p><a href="/login" style="color:#888">Already have? Login</a></p></div></body></html>"""
INFO_PAGE = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>MOTIZ AI</title><link rel="icon" href="{{favicon}}"><style>body{background:#0a0a0a;color:white;display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;margin:0}.box{background:#151515;padding:40px;border-radius:20px;width:90%;max-width:400px;border:1px solid #222}textarea,input{width:100%;padding:14px;margin:8px 0;border-radius:12px;border:none;background:#222;color:white;box-sizing:border-box}button{width:100%;padding:14px;background:white;color:black;border-radius:12px;border:none;font-weight:bold;cursor:pointer;margin-top:10px}</style></head><body><div class="box"><h2>Welcome {{user}}</h2><form method="POST"><input name="fullname" placeholder="Full Name"><textarea name="about" placeholder="What do you use MOTIZ for?"></textarea><button>Continue</button></form></div></body></html>"""

MAIN_PAGE = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover"><title>MOTIZ AI</title><link rel="icon" href="{{favicon}}">
<style>
*{box-sizing:border-box}
body{margin:0;font-family:'Segoe UI',sans-serif;height:100dvh;display:flex;flex-direction:column;overflow:hidden;background:#0b141a;color:white}
.topbar{display:flex;justify-content:space-between;align-items:center;padding:10px 14px;background:#202c33;height:60px;flex-shrink:0}
.logo{display:flex;align-items:center;gap:10px;font-weight:bold;font-size:17px;color:white}
.logo img{width:32px;height:32px;border-radius:50%}
.menu-btn{background:transparent;color:white;border:none;font-size:24px;cursor:pointer}
.chat{flex:1;display:flex;flex-direction:column;overflow:hidden;position:relative}
.msgs{flex:1;overflow-y:auto;padding:16px 12px 100px 12px;display:flex;flex-direction:column;gap:8px;background:#0b141a;background-image:url('https://user-images.githubusercontent.com/15075759/28719144-86dc0f70-73b1-11e7-911d-60d70fcded21.png');background-blend-mode:overlay}
.msg{position:relative;padding:8px 10px 22px 10px;border-radius:8px;max-width:78%;font-size:14.5px;line-height:1.4;word-wrap:break-word}
.msg.user{background:#005c4b;color:#e9edef;align-self:flex-end;border-top-right-radius:0;margin-left:auto}
.msg.ai{background:#202c33;color:#e9edef;align-self:flex-start;border-top-left-radius:0}
.msg .time{position:absolute;bottom:3px;right:8px;font-size:11px;color:#8696a0}
.msg img.chat-img{max-width:100%;border-radius:10px;margin-top:6px;border:2px solid #333}
.msg video{max-width:100%;border-radius:10px;margin-top:6px}
.wm{position:absolute;bottom:30px;right:10px;background:rgba(0,0,0,0.6);padding:2px 6px;border-radius:6px;font-size:10px;display:flex;align-items:center;gap:4px}
.wm img{width:14px;height:14px;border-radius:50%}
.input-area{display:flex;align-items:center;padding:10px 8px calc(16px + env(safe-area-inset-bottom)) 10px;gap:6px;background:#202c33;position:fixed;bottom:0;left:0;right:0;z-index:60;min-height:76px}
.input-wrapper{flex:1;display:flex;align-items:center;background:#2a3942;border-radius:26px;padding:4px 4px 4px 12px}
.input-wrapper input{flex:1;padding:10px;border:none;background:transparent;color:white;font-size:15px;outline:none}
.send-btn{background:transparent;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;margin-left:4px;margin-right:14px;flex-shrink:0}
.send-btn img{width:42px;height:42px;object-fit:contain}
.attach-btn{background:transparent;border:none;font-size:24px;cursor:pointer;color:#8696a0;padding:6px 6px 6px 2px}
.drawer{position:fixed;top:0;right:-320px;width:300px;height:100%;background:#111b21;transition:0.3s ease;padding:20px;z-index:100;display:flex;flex-direction:column;overflow-y:auto}
.drawer.open{right:0}
.overlay{position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);display:none;z-index:99}
.overlay.show{display:block}
.drawer-btn{padding:12px;background:#202c33;border:none;color:white;border-radius:10px;margin:6px 0;width:100%;text-align:left;cursor:pointer}
.chat-item{padding:10px;background:#202c33;border-radius:8px;margin:5px 0;cursor:pointer;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:white}
.settings-page{position:fixed;top:0;left:0;width:100%;height:100%;background:#0b141a;z-index:200;display:none;flex-direction:column;padding:20px;overflow-y:auto}
.settings-page.show{display:flex}
.switch{display:flex;justify-content:space-between;align-items:center;padding:12px;background:#202c33;border-radius:10px;margin:6px 0}
.toggle{width:45px;height:24px;background:#333;border-radius:12px;position:relative;cursor:pointer}
.toggle.on{background:#00a884}
.toggle::after{content:'';position:absolute;top:2px;left:2px;width:20px;height:20px;background:white;border-radius:50%;transition:0.3s}
.toggle.on::after{left:23px}
</style></head><body>
<div class="topbar"><div class="logo"><img src="{{favicon}}"><span>MOTIZ AI</span></div><button class="menu-btn" onclick="toggleDrawer()">☰</button></div>
<div class="overlay" id="overlay" onclick="toggleDrawer()"></div>
<div class="drawer" id="drawer"><h3>Dashboard</h3><button class="drawer-btn" onclick="newChat()">+ New Chat</button><div id="chatList" style="flex:1;margin-top:10px"></div><button class="drawer-btn" onclick="openSettings()">⚙️ Settings</button><button class="drawer-btn" style="margin-top:10px;background:#0a332c" onclick="location.href='/logout'">🚪 Sign Out</button><p style="font-size:11px;color:#8696a0">User: {{user}} | HF: {{'ON' if hf_on else 'OFF'}}</p></div>
<div class="settings-page" id="settingsPage"><div style="display:flex;justify-content:space-between"><h2>Settings</h2><button onclick="closeSettings()" style="background:#202c33;color:white;border:none;padding:10px 15px;border-radius:10px">✕</button></div>
<h3>Appearance</h3><button class="drawer-btn" onclick="setTheme('dark')">🌙 Dark</button><button class="drawer-btn" onclick="setTheme('light')">☀️ Light</button>
<h3>Sound</h3><div class="switch"><span>🔔 Ding</span><div class="toggle" id="soundToggle" onclick="toggleSound()"></div></div>
<h3>Notifications</h3><div class="switch"><span>📱 Push</span><div class="toggle" id="notifToggle" onclick="toggleNotif()"></div></div>
<h3>Chat</h3><button class="drawer-btn" style="background:#ff3333" onclick="clearAllChats()">🗑️ Clear All</button>
<h3>About</h3><p style="font-size:13px;line-height:1.5">Created by MOTIZ (Ajimoti Hamzat), 16, SSS 3, Ojoo High School, Alaka Ibadan. Built on Tecno Pop 2 Plus. Electrician + Creator.</p>
</div>
<div class="chat"><div class="msgs" id="msgs"></div>
<div class="input-area">
<button class="attach-btn" onclick="document.getElementById('fileInput').click()">📎</button>
<input type="file" id="fileInput" accept="image/*" style="display:none" onchange="handleFile(this)">
<div class="input-wrapper"><input id="inp" placeholder="Ask or say 'design a car'..."><button class="send-btn" onclick="send()"><img src="{{send_icon}}"></button></div>
</div></div>
<audio id="ding" src="https://cdn.freesound.org/previews/840/840284_13690175-lq.mp3"></audio>
<script>
let drawer=document.getElementById('drawer'); let overlay=document.getElementById('overlay');
function toggleDrawer(){drawer.classList.toggle('open');overlay.classList.toggle('show')}
function openSettings(){document.getElementById('settingsPage').classList.add('show'); drawer.classList.remove('open'); overlay.classList.remove('show')}
function closeSettings(){document.getElementById('settingsPage').classList.remove('show')}
let currentChatId=Date.now(); let allChats=JSON.parse(localStorage.getItem('motiz_chats')||'{}');
let soundEnabled=localStorage.getItem('motiz_sound')==='on'; let notifEnabled=localStorage.getItem('motiz_notif')==='on';
function toggleNotif(){ if(!notifEnabled){ Notification.requestPermission().then(p=>{ if(p==='granted'){ notifEnabled=true; localStorage.setItem('motiz_notif','on'); updateNotifUI(); } }); } else { notifEnabled=false; localStorage.setItem('motiz_notif','off'); updateNotifUI(); } }
function updateNotifUI(){ let t=document.getElementById('notifToggle'); if(notifEnabled) t.classList.add('on'); else t.classList.remove('on'); }
function updateSoundUI(){ let t=document.getElementById('soundToggle'); if(soundEnabled) t.classList.add('on'); else t.classList.remove('on'); }
function toggleSound(){ soundEnabled=!soundEnabled; localStorage.setItem('motiz_sound', soundEnabled?'on':'off'); updateSoundUI(); if(soundEnabled) document.getElementById('ding').play(); }
updateSoundUI(); updateNotifUI();
function getTime(){ let d=new Date(); return d.getHours()+':'+String(d.getMinutes()).padStart(2,'0'); }
function setTheme(t){ document.body.className=t; localStorage.setItem('motiz_theme',t); }
function renderChatList(){ let html=''; Object.keys(allChats).sort((a,b)=>b-a).forEach(id=>{ let c=allChats[id]; if(c.hidden) return; html+=`<div class="chat-item" onclick="loadChat('${id}')">${(c.title||'New Chat').substring(0,28)}</div>` }); document.getElementById('chatList').innerHTML=html; }
function newChat(){ currentChatId=Date.now(); document.getElementById('msgs').innerHTML=`<div class=msg ai>Hello! I'm MOTIZ AI. How can I help you today?<span class=time>${getTime()}</span></div>`; renderChatList(); }
function loadChat(id){ currentChatId=id; let chat=allChats[id]; let msgsDiv=document.getElementById('msgs'); msgsDiv.innerHTML=''; chat.messages.forEach(m=>{ msgsDiv.innerHTML+=`<div class=msg ${m.role==='user'?'user':'ai'}>${m.content}<span class=time>${getTime()}</span></div>` }); msgsDiv.scrollTop=msgsDiv.scrollHeight; toggleDrawer(); }
function clearAllChats(){ if(confirm('Clear all?')){ allChats={}; localStorage.removeItem('motiz_chats'); renderChatList(); newChat(); fetch('/api/clear_chats',{method:'POST'}); } }
function saveCurrentChat(){ if(!allChats[currentChatId]) allChats[currentChatId]={title:'', messages:[]}; localStorage.setItem('motiz_chats',JSON.stringify(allChats)); renderChatList(); fetch('/api/save_chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:currentChatId, messages:allChats[currentChatId].messages})}); }
function handleFile(input){ let file=input.files[0]; if(!file) return; let reader=new FileReader(); reader.onload=function(e){ let base64=e.target.result; document.getElementById('msgs').innerHTML+=`<div class=msg user><img class=chat-img src="${base64}"><span class=time>${getTime()} ✓✓</span></div>`; if(!allChats[currentChatId]) allChats[currentChatId]={title:'Image', messages:[]}; allChats[currentChatId].messages.push({role:'user', content:`<img class=chat-img src="${base64}">`}); saveCurrentChat(); }; reader.readAsDataURL(file); }
let msgsDiv=document.getElementById('msgs'); let inp=document.getElementById('inp');
async function send(){
 let t=inp.value.trim(); if(!t) return;
 msgsDiv.innerHTML+=`<div class=msg user>${t}<span class=time>${getTime()} ✓✓</span></div>`;
 if(!allChats[currentChatId]) allChats[currentChatId]={title:t, messages:[]};
 allChats[currentChatId].messages.push({role:'user', content:t}); allChats[currentChatId].title=t; inp.value=''; msgsDiv.scrollTop=msgsDiv.scrollHeight; saveCurrentChat();
 let thinkId='think-'+Date.now(); msgsDiv.innerHTML+=`<div class=msg ai id="${thinkId}">⏳ MOTIZ thinking / generating...<span class=time>${getTime()}</span></div>`; msgsDiv.scrollTop=msgsDiv.scrollHeight;
 try{
  let r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages:allChats[currentChatId].messages})});
  let d=await r.json(); document.getElementById(thinkId)?.remove();
  msgsDiv.innerHTML+=`<div class=msg ai>${d.content}<span class=time>${getTime()}</span></div>`;
  if(d.image){ msgsDiv.innerHTML+=`<div class=msg ai><div style="position:relative"><img class=chat-img src="${d.image}"><div class=wm><img src="{{favicon}}"> MOTIZ AI</div></div><span class=time>${getTime()}</span></div>`; }
  if(d.video){ msgsDiv.innerHTML+=`<div class=msg ai><div style="position:relative"><video controls autoplay src="${d.video}"></video><div class=wm><img src="{{favicon}}"> MOTIZ AI</div></div><br>${d.video_note||''}<span class=time>${getTime()}</span></div>`; }
  if(d.videos){ d.videos.forEach(v=>{ msgsDiv.innerHTML+=`<div class=msg ai><video controls src="${v}"></video><span class=time>${getTime()}</span></div>` }); if(d.video_note) msgsDiv.innerHTML+=`<div class=msg ai>${d.video_note}<span class=time>${getTime()}</span></div>`; }
  allChats[currentChatId].messages.push({role:'assistant', content:d.content + (d.image?`<img src="${d.image}">`:"")}); 
 } catch(e){ document.getElementById(thinkId)?.remove(); msgsDiv.innerHTML+=`<div class=msg ai>Error: ${e}<span class=time>${getTime()}</span></div>`; }
 saveCurrentChat(); if(soundEnabled) document.getElementById('ding').play(); msgsDiv.scrollTop=msgsDiv.scrollHeight;
}
inp.addEventListener('keydown',e=>{if(e.key=='Enter') send()})
renderChatList(); newChat();
</script></body></html>"""

ADMIN_PAGE = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Admin</title><link rel="icon" href="{{favicon}}"><style>body{background:#0a0a0a;color:white;font-family:sans-serif;padding:30px}table{width:100%;border-collapse:collapse}th,td{border:1px solid #222;padding:10px}</style></head><body><h1>MOTIZ Admin</h1><table><tr><th>ID</th><th>User</th><th>Email</th></tr>{% for u in users %}<tr><td>{{u[0]}}</td><td>{{u[1]}}</td><td>{{u[2]}}</td></tr>{% endfor %}</table></body></html>"""

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
        return "Invalid <a href='/login'>retry</a>"
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
    return render_template_string(MAIN_PAGE, user=session['user'], favicon=FAVICON, hf_on=bool(HF_TOKEN), send_icon=SEND_ICON)
@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

@app.route('/api/chat', methods=['POST'])
def api_chat():
    if 'user' not in session: return jsonify({"content":"Login required"})
    data=request.json; msgs=data.get('messages',[])
    last_user=""
    for m in reversed(msgs):
        if m['role']=='user':
            last_user=re.sub('<[^<]+?>','', m['content'])
            break
    last_lower=last_user.lower()

    # SUPER DETECTOR
    image_triggers=["create image","create an image","create pic","create picture","generate image","generate picture","generate photo","make image","make picture","make a pic","draw","drawing","draw me","sketch","design image","design an image","design a","design me","design","imagine","show me an image","show me picture","picture of","photo of","image of","pic of","create logo","make logo","design logo","render image","age","a image","an image","generate art","make art","i want you to design","design age","create age"]
    video_triggers=["create video","generate video","make video","design video","create clip","generate clip","video of","clip of","reel","short video","long video","animation","create movie","seconds video","second video","30 sec","60 sec","minute video"]

    wants_image=any(k in last_lower for k in image_triggers)
    wants_video=any(k in last_lower for k in video_triggers)
    if not wants_image and not wants_video:
        if any(w in last_lower for w in ["design","draw","sketch","imagine","render","create"]) and len(last_user.split())<12:
            wants_image=True

    # clean prompt
    prompt=re.sub(r'(?i)(create|generate|make|design|draw|imagine|show me|i want you to|i want|please)\s+(an?\s+)?(image|video|picture|photo|pic|logo|art|age|clip|animation|movie)?\s*(of)?', '', last_user).strip()
    if len(prompt)<3: prompt=last_user

    duration=5
    m=re.search(r'(\d+)\s*sec', last_lower)
    if m: duration=int(m.group(1))
    m2=re.search(r'(\d+)\s*second', last_lower)
    if m2: duration=int(m2.group(1))
    duration=min(duration,60)

    if wants_image:
        img=hf_generate_image(prompt)
        if img: return jsonify({"content": f"Here is your image for: <b>{prompt}</b> — watermarked MOTIZ AI ✨", "image": img})
        else:
            img_url=f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width=768&height=768"
            return jsonify({"content": f"Generated (fallback) for: <b>{prompt}</b>", "image": img_url})

    if wants_video:
        chunks=max(1, duration//5)
        videos=[]
        note=f"You asked for {duration}s video. HF limit is 5s per clip, so I created {chunks} clips and reassembled them into {chunks*5}s total. Watermark: MOTIZ AI."
        if duration>5:
            for i in range(chunks):
                v=hf_generate_video(prompt+f" part {i+1}")
                if v: videos.append(v)
            if not videos:
                return jsonify({"content": f"{note}<br>Video model busy, showing image instead.", "image": hf_generate_image(prompt)})
            if len(videos)==1:
                return jsonify({"content": f"Video for: {prompt}", "video": videos[0], "video_note": note})
            else:
                return jsonify({"content": f"Long {duration}s video reassembled!", "videos": videos, "video_note": note})
        else:
            v=hf_generate_video(prompt)
            if v: return jsonify({"content": f"Here is your video for: <b>{prompt}</b>", "video": v})
            else: return jsonify({"content": f"Video busy, image version for: {prompt}", "image": hf_generate_image(prompt)})

    system_prompt={"role":"system","content": f"You are MOTIZ AI. {MOTIZ_STORY}"}
    final_msgs=[system_prompt]+msgs[-12:]
    try:
        r=requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}, json={"model": "openai/gpt-oss-20b", "messages": final_msgs}, timeout=30)
        j=r.json()
        if 'choices' not in j: return jsonify({"content": f"Error: {j}"})
        return jsonify({"content": j['choices'][0]['message']['content']})
    except Exception as e: return jsonify({"content": f"Error: {e}"})

@app.route('/api/save_chat', methods=['POST'])
def save_chat():
    try:
        data=request.json; conn=get_db(); cur=conn.cursor()
        cur.execute("INSERT INTO chats (username, title, messages) VALUES (%s,%s,%s)",(session.get('user'), str(data.get('id')), json.dumps(data.get('messages'))))
        conn.commit(); cur.close(); conn.close()
    except: pass
    return jsonify({"ok":True})
@app.route('/api/clear_chats', methods=['POST'])
def clear_chats():
    try:
        conn=get_db(); cur=conn.cursor(); cur.execute("DELETE FROM chats WHERE username=%s",(session.get('user'),)); conn.commit(); cur.close(); conn.close()
    except: pass
    return jsonify({"ok":True})
@app.route('/admin')
def admin_panel():
    if session.get('user')!='admin': return redirect('/login')
    users=[]
    try:
        conn=get_db(); cur=conn.cursor(); cur.execute("SELECT * FROM users"); users=cur.fetchall(); cur.close(); conn.close()
    except: pass
    return render_template_string(ADMIN_PAGE, favicon=FAVICON, users=users)

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
