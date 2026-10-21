import os, json, random, string, sqlalchemy as sa, requests, html as html_lib
from datetime import datetime, timedelta
from flask import Flask, request, redirect, session, render_template_string, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from markupsafe import Markup
import pytz
from functools import wraps
import traceback

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', "flychat-v26-final")

def get_engine(name, fallback='DATABASE_URL'):
    url=os.environ.get(name) or os.environ.get(fallback)
    if not url: return None
    if url.startswith("postgres://"): url=url.replace("postgres://","postgresql://",1)
    return sa.create_engine(url, pool_pre_ping=True, pool_recycle=300, pool_size=5, max_overflow=10)

engine_main=get_engine('DATABASE_URL_TEXT') or get_engine('DATABASE_URL')
engine_voice=get_engine('DATABASE_URL_VOICE') or engine_main
engine_image=get_engine('DATABASE_URL_IMAGE') or engine_main
engine_video1=get_engine('DATABASE_URL_VIDEO1') or engine_main
engine_video2=get_engine('DATABASE_URL_VIDEO2') or engine_main

TZ=pytz.timezone('Africa/Lagos')
FAV="https://i.imgur.com/fcxK9Gl.jpeg"
SEND_BTN="https://i.imgur.com/fcxK9Gl.jpeg"
FLY_AI_AVATAR="https://files.catbox.moe/q3kij8.jpg"
SUPPORT_AVATAR="https://files.catbox.moe/lzech3.jpg"
ADMIN_PHONE="09035488319"
LIKE_BTN_URL="https://files.catbox.moe/04nq0i.png"
MIC_BTN_URL="https://files.catbox.moe/t7i2rd.jpg"
DING_SOUND="https://cdn.pixabay.com/download/audio/2021/08/04/audio_0625c1539c.mp3"
AVATARS=["https://files.catbox.moe/5pezkg.jpg","https://files.catbox.moe/oba2f6.jpg","https://files.catbox.moe/d50t8v.jpg","https://files.catbox.moe/enzwb0.jpg","https://files.catbox.moe/6e9yg3.jpg"]
DEFAULT_BUILDER={"header_color":"#00c853","button_color":"#00c853","background":"#f0f2f5","favicon":FAV}

def safe_json(t,d):
    try: return json.loads(t) if t else d
    except: return d

def init_db():
    if not engine_main: return
    with engine_main.connect() as conn:
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS fly_users (id SERIAL PRIMARY KEY, username TEXT UNIQUE, phone TEXT UNIQUE, password_hash TEXT, name TEXT, coins INTEGER DEFAULT 50, msg_count INTEGER DEFAULT 0, friends TEXT DEFAULT '[]', custom_names TEXT DEFAULT '{}', referral_code TEXT, banned_until TIMESTAMP, is_admin BOOLEAN DEFAULT FALSE, avatar_url TEXT DEFAULT '', last_seen TIMESTAMP DEFAULT NOW(), accounts TEXT DEFAULT '[]', typing_to INTEGER DEFAULT 0, blocked_users TEXT DEFAULT '[]', ip_addr TEXT DEFAULT '');"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS fly_posts (id SERIAL PRIMARY KEY, user_id INTEGER, name TEXT, text TEXT, likes TEXT DEFAULT '[]', post_image TEXT DEFAULT '', post_video TEXT DEFAULT '', is_ad BOOLEAN DEFAULT FALSE, ad_link TEXT DEFAULT '', ad_button_text TEXT DEFAULT 'Visit Link', ad_button_color TEXT DEFAULT '#0f3460', created_at TIMESTAMP DEFAULT NOW());"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS fly_messages_text (id SERIAL PRIMARY KEY, from_id INTEGER, to_id INTEGER, text TEXT, time TEXT, viewed BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT NOW());"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS fly_requests (id SERIAL PRIMARY KEY, from_id INTEGER, to_id INTEGER, status TEXT DEFAULT 'pending');"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS fly_reports (id SERIAL PRIMARY KEY, reporter_id INTEGER, target_id INTEGER, target_post INTEGER DEFAULT 0, reason TEXT, created_at TIMESTAMP DEFAULT NOW());"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS fly_builder (id SERIAL PRIMARY KEY, config TEXT DEFAULT '{}');"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS fly_groups (id SERIAL PRIMARY KEY, name TEXT, members TEXT DEFAULT '[]', admin_id INTEGER, created_at TIMESTAMP DEFAULT NOW());"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS fly_group_messages (id SERIAL PRIMARY KEY, group_id INTEGER, from_id INTEGER, text TEXT, time TEXT, created_at TIMESTAMP DEFAULT NOW());"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS fly_calls (id SERIAL PRIMARY KEY, caller_id INTEGER, callee_id INTEGER, sdp_offer TEXT DEFAULT '', sdp_answer TEXT DEFAULT '', ice_candidates TEXT DEFAULT '[]', call_type TEXT DEFAULT 'voice', status TEXT DEFAULT 'ringing', created_at TIMESTAMP DEFAULT NOW());"))
        conn.execute(sa.text("CREATE TABLE IF NOT EXISTS fly_missed_calls (id SERIAL PRIMARY KEY, caller_id INTEGER, callee_id INTEGER, call_type TEXT, created_at TIMESTAMP DEFAULT NOW());"))
        conn.commit()
        try:
            if not conn.execute(sa.text("SELECT id FROM fly_users WHERE username='FLY AI'")).scalar():
                conn.execute(sa.text("INSERT INTO fly_users (username,name,phone,password_hash,friends,referral_code,is_admin,avatar_url) VALUES ('FLY AI','FLY AI','00000000001',:h,'[]','FLYAI',TRUE,:av)"), {"h": generate_password_hash("flyai123"),"av":FLY_AI_AVATAR})
            if not conn.execute(sa.text("SELECT id FROM fly_users WHERE username='flychat support'")).scalar():
                conn.execute(sa.text("INSERT INTO fly_users (username,name,phone,password_hash,friends,referral_code,is_admin,avatar_url) VALUES ('flychat support','FLYCHAT SUPPORT','00000000000',:h,'[]','SUPPORT',TRUE,:av)"), {"h": generate_password_hash("support123"),"av":SUPPORT_AVATAR})
            conn.execute(sa.text("UPDATE fly_users SET is_admin=TRUE WHERE phone='"+ADMIN_PHONE+"'")); conn.commit()
            if not conn.execute(sa.text("SELECT id FROM fly_builder")).scalar():
                conn.execute(sa.text("INSERT INTO fly_builder (config) VALUES (:c)"),{"c":json.dumps(DEFAULT_BUILDER)}); conn.commit()
        except: pass
    for eng,tbl in [(engine_voice,"fly_messages_voice"),(engine_image,"fly_messages_image"),(engine_video1,"fly_messages_video"),(engine_video2,"fly_messages_video")]:
        try:
            with eng.connect() as conn:
                conn.execute(sa.text("CREATE TABLE IF NOT EXISTS "+tbl+" (id SERIAL PRIMARY KEY, from_id INTEGER, to_id INTEGER, text TEXT, time TEXT, viewed BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT NOW());")); conn.commit()
        except: pass
init_db()

def get_builder_config():
    try:
        with engine_main.connect() as conn:
            cfg=conn.execute(sa.text("SELECT config FROM fly_builder WHERE id=1")).scalar() or json.dumps(DEFAULT_BUILDER)
            return safe_json(cfg,DEFAULT_BUILDER)
    except: return DEFAULT_BUILDER

# --- FLY AI FIXED FOR gsk_ WITHOUT SPACE ---
def ask_fly_ai(q, user):
    extra=""
    if any(x in q.lower() for x in ["waec","neco","jamb","wassce","utme"]):
        extra="\n\n📚 WAEC, NECO, JAMB lessons & past questions: https://motiz-e-learning-institution.onrender.com"
    key = (os.environ.get('GROQ_API_KEY') or '').strip()
    # also accept GEMINI as fallback
    gem_key = (os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY') or '').strip()
    print(f"[FLY AI] key_len={len(key)} start={key[:8]} gem={len(gem_key)>0}", flush=True)
    if key.startswith("gsk_"):
        for model in ["llama-3.3-70b-versatile","llama3-8b-8192","mixtral-8x7b-32768","llama-3.1-8b-instant"]:
            try:
                r=requests.post("https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type":"application/json"},
                    json={"model":model,"messages":[{"role":"system","content":"You are FLY AI on FLYCHAT. For WAEC NECO JAMB always include https://motiz-e-learning-institution.onrender.com"},{"role":"user","content":q}],"max_tokens":700},
                    timeout=20)
                print(f"[GROQ] {model} -> {r.status_code}", flush=True)
                if r.status_code==200:
                    ans=r.json()['choices'][0]['message']['content'][:1200]
                    if extra and "motiz" not in ans.lower(): ans+=extra
                    return ans
                else:
                    print(r.text[:400], flush=True)
            except Exception as e:
                print(f"[GROQ] {model} EX {e}", flush=True)
                continue
    if gem_key.startswith("AIza"):
        try:
            url=f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gem_key}"
            r=requests.post(url, headers={"Content-Type":"application/json"}, json={"contents":[{"parts":[{"text":q}]}],"generationConfig":{"maxOutputTokens":600}}, timeout=15)
            if r.status_code==200 and r.json().get('candidates'):
                ans=r.json()['candidates'][0]['content']['parts'][0]['text'][:1200]
                if extra: ans+=extra
                return ans
        except: pass
    # FINAL FALLBACK - ALWAYS RESPONDS
    if not key:
        return "FLY AI key missing on server. Admin: add GROQ_API_KEY=gsk_... in Render ENV (no spaces)." + extra
    return f"I am FLY AI on FLYCHAT! You said: {q[:200]}. For WAEC/NECO/JAMB visit https://motiz-e-learning-institution.onrender.com" + extra

def render_msg_content(txt):
    if not txt: return ""
    if txt.startswith("data:audio"): return f'<audio controls src="{txt}" style="width:200px;height:32px"></audio>'
    if txt.startswith("data:image"): return f'<img src="{txt}" style="max-width:220px;max-height:280px;border-radius:10px;cursor:pointer;object-fit:cover" onclick="openImagePreview(this.src)">'
    if txt.startswith("data:video"): return f'<video controls src="{txt}" style="max-width:220px;border-radius:10px"></video>'
    return f'<div style="word-break:break-word;white-space:pre-wrap">{html_lib.escape(txt).replace(chr(10),"<br>")}</div>'

BASE = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0"><link rel="icon" href="{{favicon}}"><title>{{title}}</title><style>
*{box-sizing:border-box} body{font-family:Segoe UI,system-ui;background:{{bg_color}};margin:0;display:flex;justify-content:center}
.header{background:{{header_color}};color:white;padding:0 12px;position:fixed;top:0;width:100%;max-width:480px;z-index:1000;display:flex;align-items:center;height:52px}
.container{padding:8px;padding-top:60px;padding-bottom:80px;width:100%;max-width:480px;margin:0 auto}
.card{background:white;padding:12px;margin:8px 0;border-radius:14px;box-shadow:0 2px 8px rgba(0,0,0,0.06);font-size:14px}
.btn{background:{{btn_color}};color:white;padding:9px 12px;border-radius:10px;border:none;cursor:pointer;font-weight:bold;font-size:14px}.btn.small{padding:5px 10px;font-size:12px}.btn.red{background:#e94560}.btn.blue{background:#0f3460}
.friend-card{display:flex;align-items:center;gap:10px;padding:10px 12px;background:white;border-radius:12px;margin:7px 0;text-decoration:none;color:#333;box-shadow:0 1px 4px rgba(0,0,0,0.05);width:100%}.friend-avatar{width:40px;height:40px;border-radius:50%;background:{{btn_color}};color:white;display:flex;align-items:center;justify-content:center;overflow:hidden;flex-shrink:0;position:relative}.friend-avatar img{width:100%;height:100%;object-fit:cover}
.chat-msg{display:flex;margin:10px 0;gap:6px}.chat-msg.me{justify-content:flex-end}.bubble{padding:8px 12px;border-radius:16px;max-width:75%;font-size:14px;white-space:pre-wrap;word-break:break-word}.me.bubble{background:{{btn_color}};color:white}.other.bubble{background:#fff;color:#222;box-shadow:0 1px 3px rgba(0,0,0,0.07)}
.bottom-nav{position:fixed;bottom:0;left:50%;transform:translateX(-50%);width:100%;max-width:480px;background:white;display:flex;justify-content:space-around;height:56px;box-shadow:0 -2px 8px rgba(0,0,0,0.08);z-index:1000;border-top:1px solid #eee}
.bottom-nav a{text-decoration:none;color:#777;text-align:center;flex:1;padding:4px;font-size:11px;display:flex;flex-direction:column;align-items:center}.bottom-nav a.active{color:{{btn_color}};font-weight:bold}
.post-card{background:white;border-radius:14px;box-shadow:0 2px 8px rgba(0,0,0,0.06);margin:12px 0;overflow:hidden;position:relative}
.post-header{padding:10px 12px;display:flex;justify-content:space-between;align-items:center}
.post-body{padding:0 12px 8px 12px;font-size:14px}
.post-media img{width:100%;display:block;max-height:380px;object-fit:contain;background:#f5f5f5}
.post-media video{width:100%;display:block;max-height:380px;object-fit:contain}
.post-actions{display:flex;border-top:1px solid #eee;margin-top:8px}
.post-actions button{flex:1;padding:10px 6px;border:none;background:none;cursor:pointer;font-size:13px;display:flex;align-items:center;justify-content:center;gap:4px;border-right:1px solid #f0f0f0}
.post-actions button img{width:18px !important;height:18px !important;object-fit:contain;flex-shrink:0}
.post-menu{position:absolute;top:42px;right:12px;background:white;border-radius:10px;box-shadow:0 4px 14px rgba(0,0,0,0.15);z-index:100;display:none;flex-direction:column;min-width:150px}
.post-menu button{padding:10px 12px;border:none;background:none;text-align:left;cursor:pointer;font-size:13px;border-bottom:1px solid #f0f0f0}
.modal{position:fixed;top:0;left:50%;transform:translateX(-50%);width:100%;max-width:480px;height:100%;background:rgba(0,0,0,0.5);z-index:26000;display:none;align-items:flex-end}
.modal-box{background:white;width:100%;max-height:75vh;border-top-left-radius:16px;border-top-right-radius:16px;overflow:auto;padding:14px}
.badge{background:red;color:white;font-size:10px;padding:2px 6px;border-radius:10px;position:absolute;top:-6px;right:-6px}
.call-modal{position:fixed;top:0;left:50%;transform:translateX(-50%);width:100%;max-width:480px;height:100%;background:#111;z-index:40000;display:none;flex-direction:column;color:white}
.online-dot{width:10px;height:10px;background:#00c853;border-radius:50%;position:absolute;bottom:0;right:0;border:2px solid white}
.top-notif{position:fixed;top:52px;left:50%;transform:translateX(-50%);width:100%;max-width:480px;background:#323232;color:white;padding:12px 14px;z-index:5000;display:none;align-items:center;gap:10px;border-bottom:1px solid #444}
</style></head><body>
<audio id="dingSound" src="{{ding_sound}}" preload="auto"></audio>
<div id="topNotif" class="top-notif"><img src="https://i.imgur.com/fcxK9Gl.jpeg" style="width:28px;height:28px;border-radius:50%"><span id="topNotifText">New message</span></div>
<div id="imagePreviewModal" style="position:fixed;top:0;left:50%;transform:translateX(-50%);width:100%;max-width:480px;height:100%;background:#000;z-index:30000;display:none;align-items:center;justify-content:center;flex-direction:column"><button onclick="closeModal('imagePreviewModal')" style="position:absolute;top:12px;left:12px;background:none;border:none;color:white;font-size:24px">X</button><img id="previewImg" style="max-width:95%;max-height:85vh;border-radius:10px"></div>
<div id="forwardModal" class="modal"><div class="modal-box"><h3>Forward to friends</h3><div id="forwardFriendsList"></div><button onclick="confirmForward()" class="btn" style="width:100%;margin-top:10px">Forward</button><button onclick="closeModal('forwardModal')" class="btn red small" style="width:100%;margin-top:6px">Cancel</button></div></div>
<div id="groupModal" class="modal"><div class="modal-box"><h3>Create Group</h3><input id="groupName" placeholder="Group name" style="width:100%;padding:10px;border-radius:10px;border:1px solid #ddd"><div id="groupFriendsSelect" style="max-height:40vh;overflow:auto;margin-top:8px"></div><button onclick="createGroup()" class="btn" style="width:100%;margin-top:10px">Create Group</button><button onclick="closeModal('groupModal')" class="btn red small" style="width:100%;margin-top:6px">Cancel</button></div></div>
<div id="callSelectModal" class="modal"><div class="modal-box"><h3>Call</h3><button onclick="startRealCall('voice')" class="btn blue" style="width:100%;margin:6px 0">📞 Voice</button><button onclick="startRealCall('video')" class="btn" style="width:100%;margin:6px 0">🎥 Video</button><button onclick="closeModal('callSelectModal')" class="btn red small" style="width:100%">Cancel</button></div></div>
<div id="callScreen" class="call-modal"><div style="flex:1;position:relative"><video id="remoteVideo" autoplay playsinline style="width:100%;height:100%;object-fit:cover;background:#000"></video><video id="localVideo" autoplay muted playsinline style="position:absolute;bottom:90px;right:12px;width:110px;height:150px;border-radius:10px;background:#222;object-fit:cover"></video><div style="position:absolute;top:20px;left:50%;transform:translateX(-50%);text-align:center"><h3 id="callStatus">Calling...</h3></div></div><div style="padding:20px;display:flex;justify-content:center;gap:20px;background:#222"><button onclick="endCall()" style="background:#e94560;color:white;width:56px;height:56px;border-radius:50%;border:none">✕</button><button onclick="toggleMute()" id="muteBtn" style="background:#444;color:white;width:56px;height:56px;border-radius:50%;border:none">🎤</button><button onclick="toggleVideo()" id="videoBtn" style="background:#444;color:white;width:56px;height:56px;border-radius:50%;border:none">🎥</button></div></div>
<div id="chatOptionsModal" class="modal"><div class="modal-box"><h3>Chat Options</h3><div style="display:flex;flex-direction:column;gap:8px"><button onclick="openRename()" class="btn blue small">Rename</button><button onclick="openDisappear()" class="btn small" style="background:#eee;color:#333">Disappearing</button><button onclick="doBlock()" class="btn small red">Block</button></div><button onclick="closeModal('chatOptionsModal')" class="btn red small" style="width:100%;margin-top:10px">Close</button></div></div>
<div id="renameModal" class="modal"><div class="modal-box"><h3>Rename</h3><input id="renameInput" placeholder="New name only you see" style="width:100%;padding:10px;border-radius:10px;border:1px solid #ddd"><button onclick="doRename()" class="btn" style="width:100%;margin-top:8px">Save</button></div></div>
<div id="disappearModal" class="modal"><div class="modal-box"><h3>Disappearing</h3><select id="disappearSelect" style="width:100%;padding:10px;border-radius:10px;border:1px solid #ddd"><option value="off">Off</option><option value="24 hrs">24 hrs</option><option value="7 days">7 days</option><option value="30 days">30 days</option></select><button onclick="doDisappear()" class="btn" style="width:100%;margin-top:10px">Save</button></div></div>
{{header}}<div class="container">{{content}}</div>{{bottom_nav}}
<script>
var currentChatUser=null; var forwardContent=null; var selectedForwardIds=[]; var groupSelectedIds=[];
function closeModal(id){document.getElementById(id).style.display='none';}
function openImagePreview(src){document.getElementById('previewImg').src=src; document.getElementById('imagePreviewModal').style.display='flex';}
function openChatOptions(uid){currentChatUser=uid; document.getElementById('chatOptionsModal').style.display='flex';}
function openRename(){closeModal('chatOptionsModal'); document.getElementById('renameModal').style.display='flex';}
function doRename(){var n=document.getElementById('renameInput').value.trim(); if(!n) return; fetch('/api/rename',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({friend_id:currentChatUser,name:n})}).then(()=>{alert('Renamed'); location.reload();});}
function openDisappear(){closeModal('chatOptionsModal'); document.getElementById('disappearModal').style.display='flex';}
function doDisappear(){var v=document.getElementById('disappearSelect').value; fetch('/api/settings/disappearing',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({val:v})}).then(()=>{alert('Set '+v); closeModal('disappearModal');});}
function doBlock(){if(confirm('Block?')) fetch('/api/user/block/'+currentChatUser,{method:'POST'}).then(()=>{alert('Blocked'); location.href='/';});}
function togglePostMenu(id){var m=document.getElementById('pmenu-'+id); if(!m) return; var f=m.style.display==='flex'; document.querySelectorAll('.post-menu').forEach(x=>x.style.display='none'); if(!f){m.style.display='flex'; setTimeout(()=>m.style.display='none',5000);} }
function savePost(id){fetch('/api/post/save/'+id,{method:'POST'}).then(()=>alert('Saved'));}
function openForwardModal(c){forwardContent=c; selectedForwardIds=[]; fetch('/api/friends/list').then(r=>r.json()).then(d=>{var h=''; d.friends.forEach(f=>{h+='<div style="display:flex;align-items:center;gap:8px;padding:8px;border-bottom:1px solid #eee"><input type="checkbox" value="'+f.id+'" onchange="toggleForward(this)"> '+f.name+'</div>';}); document.getElementById('forwardFriendsList').innerHTML=h||'No friends'; document.getElementById('forwardModal').style.display='flex';});}
function toggleForward(cb){var id=parseInt(cb.value); if(cb.checked) selectedForwardIds.push(id); else selectedForwardIds=selectedForwardIds.filter(x=>x!==id);}
function confirmForward(){if(selectedForwardIds.length==0) return alert('Select'); fetch('/api/forward',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({to_ids:selectedForwardIds,content:forwardContent})}).then(()=>{alert('Forwarded'); closeModal('forwardModal');});}
function forwardPost(id){var txt=document.querySelector('#post-'+id+' .post-body')?.innerText||''; var img=document.querySelector('#post-'+id+' .post-media img')?.src||''; openForwardModal(img||txt);}
function openGroupModal(){fetch('/api/friends/list').then(r=>r.json()).then(d=>{var h=''; d.friends.forEach(f=>{h+='<div style="display:flex;align-items:center;gap:8px;padding:6px;border-bottom:1px solid #eee"><input type="checkbox" value="'+f.id+'" onchange="toggleGroup(this)"> <img src="'+(f.avatar||'')+'" style="width:28px;height:28px;border-radius:50%"> '+f.name+'</div>';}); document.getElementById('groupFriendsSelect').innerHTML=h||'No friends yet - add friends first'; document.getElementById('groupModal').style.display='flex';});}
function toggleGroup(cb){var id=parseInt(cb.value); if(cb.checked){if(groupSelectedIds.indexOf(id)===-1) groupSelectedIds.push(id);} else {groupSelectedIds=groupSelectedIds.filter(x=>x!==id);}}
function createGroup(){var name=document.getElementById('groupName').value.trim(); if(!name) return alert('Enter group name'); if(groupSelectedIds.length==0) return alert('Select at least 1 friend'); fetch('/api/groups/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name,members:groupSelectedIds})}).then(r=>r.json()).then(d=>{if(d.ok){alert('Group created'); location.href='/group/'+d.group_id;} else alert(d.msg||'Failed');});}
var localStream=null, pc=null, callInterval=null, currentCallId=null;
function openCallSelect(){if(!currentChatUser) return; document.getElementById('callSelectModal').style.display='flex';}
function startRealCall(type){closeModal('callSelectModal'); document.getElementById('callScreen').style.display='flex'; document.getElementById('callStatus').innerText=type=='video'?'Video calling...':'Voice calling...'; navigator.mediaDevices.getUserMedia({video:type=='video',audio:true}).then(s=>{localStream=s; document.getElementById('localVideo').srcObject=s; initPeer(true, type);}).catch(()=>{alert('Mic/Camera needed'); endCall();});}
function initPeer(isCaller, type){pc=new RTCPeerConnection({iceServers:[{urls:'stun:stun.l.google.com:19302'},{urls:'stun:stun1.l.google.com:19302'}]}); if(localStream) localStream.getTracks().forEach(t=>pc.addTrack(t,localStream)); pc.ontrack=e=>{document.getElementById('remoteVideo').srcObject=e.streams[0]; document.getElementById('callStatus').innerText='Connected';}; pc.onicecandidate=e=>{if(e.candidate&&currentCallId) fetch('/api/call/ice',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({call_id:currentCallId,candidate:JSON.stringify(e.candidate)})});}; if(isCaller){pc.createOffer().then(o=>pc.setLocalDescription(o).then(()=>{fetch('/api/call/request',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({callee_id:currentChatUser,type:type,sdp:JSON.stringify(o)})}).then(r=>r.json()).then(d=>{currentCallId=d.call_id; callInterval=setInterval(pollCall,2000);});}));}}
function pollCall(){if(!currentCallId) return; fetch('/api/call/poll/'+currentCallId).then(r=>r.json()).then(d=>{if(d.status=='ended'){endCall(); return;} if(d.sdp_answer&&pc&&!pc.currentRemoteDescription){pc.setRemoteDescription(new RTCSessionDescription(JSON.parse(d.sdp_answer)));} });}
function endCall(){if(currentCallId) fetch('/api/call/end/'+currentCallId,{method:'POST'}); if(pc){pc.close(); pc=null;} if(localStream){localStream.getTracks().forEach(t=>t.stop()); localStream=null;} clearInterval(callInterval); document.getElementById('callScreen').style.display='none'; document.getElementById('remoteVideo').srcObject=null; currentCallId=null;}
function toggleMute(){var a=localStream?.getAudioTracks()[0]; if(a){a.enabled=!a.enabled; document.getElementById('muteBtn').innerText=a.enabled?'🎤':'🔇';}}
function toggleVideo(){var v=localStream?.getVideoTracks()[0]; if(v){v.enabled=!v.enabled; document.getElementById('videoBtn').innerText=v.enabled?'🎥':'📷';}}
var notifCount=0;
function showTopBar(text){var bar=document.getElementById('topNotif'); document.getElementById('topNotifText').innerText=text; bar.style.display='flex'; var audio=document.getElementById('dingSound'); audio.currentTime=0; audio.play().then(()=>{}).catch(()=>{}); if(Notification && Notification.permission==='granted'){new Notification('FLYCHAT', {body:text, icon:'https://i.imgur.com/fcxK9Gl.jpeg'});} setTimeout(()=>bar.style.display='none',4500);}
function checkNotif(){fetch('/api/notifications/count').then(r=>r.json()).then(d=>{var badge=document.getElementById('notifBadge'); if(d.total>0 && d.total>notifCount){showTopBar(d.last_msg||'New request');} if(d.new_msg){showTopBar(d.new_msg);} if(d.missed_calls && d.missed_calls.length>0){d.missed_calls.forEach(c=>showTopBar('Missed '+c.call_type+' call from '+c.caller_name));} notifCount=d.total; if(badge){badge.innerText=d.total + (d.missed_count||0); badge.style.display=(d.total + (d.missed_count||0))>0?'block':'none';} var ti=document.getElementById('typingIndicator'); if(ti && d.typing_from) ti.innerText=d.typing_from+' typing...'; else if(ti) ti.innerText='';});}
setInterval(checkNotif,3000); checkNotif();
if(Notification && Notification.permission!=='granted') Notification.requestPermission();
setInterval(()=>{fetch('/api/call/incoming').then(r=>r.json()).then(d=>{if(d.call && !currentCallId){currentCallId=d.call.id; currentChatUser=d.call.caller_id; if(confirm('Incoming '+d.call.call_type+' call from '+d.call.caller_name+'. Answer?')){document.getElementById('callScreen').style.display='flex'; document.getElementById('callStatus').innerText='Incoming '+d.call.call_type; navigator.mediaDevices.getUserMedia({video:d.call.call_type=='video',audio:true}).then(stream=>{localStream=stream; document.getElementById('localVideo').srcObject=stream; pc=new RTCPeerConnection({iceServers:[{urls:'stun:stun.l.google.com:19302'}]}); localStream.getTracks().forEach(t=>pc.addTrack(t,localStream)); pc.ontrack=e=>{document.getElementById('remoteVideo').srcObject=e.streams[0]; document.getElementById('callStatus').innerText='Connected';}; pc.onicecandidate=e=>{if(e.candidate) fetch('/api/call/ice',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({call_id:currentCallId,candidate:JSON.stringify(e.candidate)})});}; pc.setRemoteDescription(new RTCSessionDescription(JSON.parse(d.call.sdp_offer))).then(()=>pc.createAnswer().then(ans=>pc.setLocalDescription(ans).then(()=>{fetch('/api/call/answer',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({call_id:currentCallId,sdp:JSON.stringify(ans)})}); callInterval=setInterval(pollCall,2000);} )));});} else {fetch('/api/call/end/'+d.call.id,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({missed:true})}); currentCallId=null;}}});},3000);
</script>
</body></html>"""

def get_header(user, other=None):
    cfg=get_builder_config()
    header_color=cfg.get('header_color','#00c853')
    if other:
        uname=(other.get('username') or '').lower()
        is_special='fly ai' in uname or 'support' in uname
        av=other.get('avatar_url') or FAV
        if 'fly ai' in uname: av=FLY_AI_AVATAR
        if 'support' in uname: av=SUPPORT_AVATAR
        display=other.get('display_name') or other.get('name') or 'User'
        if is_special:
            return f'<div class="header" style="background:{header_color}"><a href="/?tab=chat" style="color:white;text-decoration:none;font-size:20px;margin-right:8px">←</a><img src="{av}" style="width:30px;height:30px;border-radius:50%;margin-right:6px"><div style="flex:1"><b>{html_lib.escape(display[:22])}</b></div></div>'
        return f'<div class="header" style="background:{header_color}"><a href="/?tab=chat" style="color:white;text-decoration:none;font-size:20px;margin-right:8px">←</a><img src="{av}" style="width:30px;height:30px;border-radius:50%;margin-right:6px"><div style="flex:1"><b>{html_lib.escape(display[:22])}</b><br><small id="typingIndicator" style="font-size:11px;opacity:0.8"></small></div><button onclick="openCallSelect()" style="background:none;border:none;color:white;font-size:20px;margin-right:8px">📞</button><button onclick="openChatOptions({other["id"]})" style="background:none;border:none;color:white;font-size:20px">⋮</button></div>'
    return f'<div class="header" style="background:{header_color}"><img src="{FAV}" style="width:32px;height:32px;border-radius:50%;margin-right:8px"><b style="flex:1">FLYCHAT</b><a href="/notifications" style="color:white;text-decoration:none;position:relative">🔔<span id="notifBadge" class="badge" style="display:none">0</span></a></div>'

def get_bottom_nav(user, active="chat"):
    is_admin=user.get('is_admin') or user.get('phone')==ADMIN_PHONE
    admin_tab = f"<a href='/admin' class='{'active' if active=='admin' else ''}'><span>🛡️</span>Admin</a>" if is_admin else ""
    return f"<div class=\"bottom-nav\"><a href=\"/?tab=chat\" class=\"{'active' if active=='chat' else ''}\"><span>💬</span>Chat</a><a href=\"/?tab=people\" class=\"{'active' if active=='people' else ''}\"><span>👥</span>People</a><a href=\"/post\" class=\"{'active' if active=='post' else ''}\"><span>📝</span>Post</a><a href=\"/earn\" class=\"{'active' if active=='earn' else ''}\"><span>💰</span>Earn</a><a href=\"/profile\" class=\"{'active' if active=='profile' else ''}\"><span>👤</span>Profile</a>{admin_tab}</div>"

def get_user_obj():
    uid=session.get('uid')
    if not uid or not engine_main: return None
    with engine_main.connect() as conn:
        u=conn.execute(sa.text("SELECT * FROM fly_users WHERE id=:id"),{"id":uid}).mappings().first()
        if not u: return None
        d=dict(u)
        d['friends']=safe_json(d.get('friends','[]'),[])
        d['custom_names']=safe_json(d.get('custom_names','{}'),{})
        d['accounts']=safe_json(d.get('accounts','[]'),[])
        d['blocked_users']=safe_json(d.get('blocked_users','[]'),[])
        return d

def login_required(f):
    @wraps(f)
    def w(*a,**k):
        u=get_user_obj()
        if not u: return redirect("/login")
        return f(u,*a,**k)
    return w
def admin_required(f):
    @wraps(f)
    def w(*a,**k):
        u=get_user_obj()
        if not u or not (u.get('is_admin') or u.get('phone')==ADMIN_PHONE): return redirect("/")
        return f(u,*a,**k)
    return w

def save_message_by_type(from_id,to_id,text,time_str,viewed=False):
    try:
        txt=text
        if txt.startswith("data:audio"):
            with engine_voice.begin() as w: w.execute(sa.text("INSERT INTO fly_messages_voice (from_id,to_id,text,time,viewed) VALUES (:f,:t,:txt,:time,:vd)"),{"f":from_id,"t":to_id,"txt":txt,"time":time_str,"vd":viewed})
        elif txt.startswith("data:image"):
            with engine_image.begin() as w: w.execute(sa.text("INSERT INTO fly_messages_image (from_id,to_id,text,time,viewed) VALUES (:f,:t,:txt,:time,:vd)"),{"f":from_id,"t":to_id,"txt":txt,"time":time_str,"vd":viewed})
        elif txt.startswith("data:video"):
            eng=engine_video1 if (from_id%2==0) else engine_video2
            with eng.begin() as w: w.execute(sa.text("INSERT INTO fly_messages_video (from_id,to_id,text,time,viewed) VALUES (:f,:t,:txt,:time,:vd)"),{"f":from_id,"t":to_id,"txt":txt,"time":time_str,"vd":viewed})
        else:
            with engine_main.begin() as w: w.execute(sa.text("INSERT INTO fly_messages_text (from_id,to_id,text,time,viewed) VALUES (:f,:t,:txt,:time,:vd)"),{"f":from_id,"t":to_id,"txt":txt,"time":time_str,"vd":viewed})
    except Exception as e: print(e, flush=True)

def load_all_messages(a,b):
    all_msgs=[]
    for eng, table in [(engine_main,"fly_messages_text"),(engine_voice,"fly_messages_voice"),(engine_image,"fly_messages_image"),(engine_video1,"fly_messages_video"),(engine_video2,"fly_messages_video")]:
        try:
            with eng.connect() as conn:
                rows=conn.execute(sa.text("SELECT * FROM "+table+" WHERE (from_id=:a AND to_id=:b) OR (from_id=:b AND to_id=:a) ORDER BY created_at ASC"),{"a":a,"b":b}).mappings().all()
                for r in rows: all_msgs.append(dict(r))
        except: pass
    all_msgs.sort(key=lambda x: x.get('created_at') or datetime.min)
    return all_msgs[-400:]

def get_last_message(a,b):
    try:
        latest=None; latest_time=None
        for eng, table in [(engine_main,"fly_messages_text"),(engine_voice,"fly_messages_voice"),(engine_image,"fly_messages_image"),(engine_video1,"fly_messages_video"),(engine_video2,"fly_messages_video")]:
            try:
                with eng.connect() as conn:
                    row=conn.execute(sa.text("SELECT text,time,created_at,viewed FROM "+table+" WHERE (from_id=:a AND to_id=:b) OR (from_id=:b AND to_id=:a) ORDER BY created_at DESC LIMIT 1"),{"a":a,"b":b}).mappings().first()
                    if row and (latest is None or (row.get('created_at') or datetime.min) > (latest_time or datetime.min)):
                        latest=row; latest_time=row.get('created_at')
            except: continue
        if not latest: return "", "", ""
        txt=latest['text'][:28]
        if txt.startswith("data:"): txt="📷 Photo" if "image" in txt[:20] else "🎤 Voice" if "audio" in txt[:20] else "🎥 Video"
        tick="✓✓" if latest.get('viewed') else "✓"
        return txt, latest.get('time',''), tick
    except: return "", "", ""

def is_online(last_seen):
    try:
        if not last_seen: return False
        ls=last_seen.replace(tzinfo=pytz.utc) if last_seen.tzinfo is None else last_seen
        return (datetime.now(pytz.utc)-ls).total_seconds() < 120
    except: return False

@app.route('/api/friends/list')
@login_required
def api_friends_list(user):
    with engine_main.connect() as conn:
        lst=[]
        for fid in user['friends']:
            u=conn.execute(sa.text("SELECT id,name,avatar_url,username FROM fly_users WHERE id=:id"),{"id":fid}).mappings().first()
            if not u: continue
            # REMOVE FLY AI AND SUPPORT FROM GROUP
            if u['username'] and u['username'].lower() in ('fly ai','flychat support'): continue
            custom=user.get('custom_names',{}).get(str(fid), u['name'])
            lst.append({"id":u['id'],"name":custom,"avatar":u['avatar_url'] or FAV})
        return jsonify({"friends":lst})

@app.route('/api/notifications/count')
@login_required
def api_notif_count(user):
    with engine_main.connect() as conn:
        req=conn.execute(sa.text("SELECT COUNT(*) FROM fly_requests WHERE to_id=:id AND status='pending'"),{"id":user['id']}).scalar() or 0
        typing_user=None
        try:
            tu=conn.execute(sa.text("SELECT name FROM fly_users WHERE typing_to=:id AND last_seen > NOW() - INTERVAL '10 seconds' LIMIT 1"),{"id":user['id']}).mappings().first()
            if tu: typing_user=tu['name']
        except: pass
        missed=[]; missed_count=0
        try:
            rows=conn.execute(sa.text("SELECT mc.*, u.name as caller_name FROM fly_missed_calls mc JOIN fly_users u ON u.id=mc.caller_id WHERE mc.callee_id=:id AND mc.created_at > NOW() - INTERVAL '24 hours' ORDER BY mc.created_at DESC LIMIT 5"),{"id":user['id']}).mappings().all()
            missed=[dict(r) for r in rows]; missed_count=len(rows)
        except: pass
        new_msg=None
        try:
            r=conn.execute(sa.text("SELECT text, u.name FROM fly_messages_text m JOIN fly_users u ON u.id=m.from_id WHERE m.to_id=:id AND m.viewed=FALSE ORDER BY m.created_at DESC LIMIT 1"),{"id":user['id']}).mappings().first()
            if r: new_msg=f"{r['name']}: {r['text'][:40]}"
        except: pass
        return jsonify({"total": int(req), "typing_from": typing_user, "missed_calls": missed, "missed_count": missed_count, "new_msg": new_msg, "last_msg": new_msg})

@app.route('/api/forward', methods=["POST"])
@login_required
def api_forward(user):
    data=request.get_json() or {}; to_ids=data.get('to_ids',[]); content=data.get('content','')[:8000]
    time_str=datetime.now(TZ).strftime("%I:%M %p")
    for tid in to_ids: save_message_by_type(user['id'], int(tid), content, time_str)
    return jsonify({"ok":True})

@app.route('/api/groups/create', methods=["POST"])
@login_required
def api_group_create(user):
    data=request.get_json() or {}; name=(data.get('name') or '').strip()[:30]; members=data.get('members',[])
    if not name: return jsonify({"ok":False,"msg":"Enter name"})
    if not members: return jsonify({"ok":False,"msg":"Select friends"})
    members=[int(m) for m in members if int(m)!=user['id']]; members.append(user['id'])
    with engine_main.begin() as w:
        res=w.execute(sa.text("INSERT INTO fly_groups (name,members,admin_id) VALUES (:n,:m,:a) RETURNING id"),{"n":name,"m":json.dumps(members),"a":user['id']})
        gid=res.scalar()
    return jsonify({"ok":True,"group_id":gid})

@app.route('/api/typing', methods=["POST"])
@login_required
def api_typing(user):
    data=request.get_json() or {}; to_id=data.get('to_id'); typ=data.get('type','typing')
    with engine_main.begin() as w:
        if typ=='typing':
            w.execute(sa.text("UPDATE fly_users SET typing_to=:t, last_seen=NOW() WHERE id=:id"),{"t":to_id,"id":user['id']})
        else:
            w.execute(sa.text("UPDATE fly_users SET typing_to=0, last_seen=NOW() WHERE id=:id"),{"id":user['id']})
    return jsonify({"ok":True})

@app.route('/api/dm/send', methods=["POST"])
@login_required
def api_dm_send(user):
    data=request.get_json() or {}; uid=data.get('to_id'); txt=(data.get('text') or '').strip()
    aud=data.get('audio_data',''); imgs=data.get('images',[]); vid=data.get('video_data','')
    if data.get('image_data'): imgs=[data.get('image_data')] + imgs
    time_str=datetime.now(TZ).strftime("%I:%M %p")
    sent=False
    if txt: save_message_by_type(user['id'], uid, txt, time_str); sent=True
    if aud: save_message_by_type(user['id'], uid, aud, time_str); sent=True
    if vid: save_message_by_type(user['id'], uid, vid, time_str); sent=True
    for im in imgs:
        if im: save_message_by_type(user['id'], uid, im, time_str); sent=True
    if not sent: return jsonify({"ok":False})
    with engine_main.begin() as w: w.execute(sa.text("UPDATE fly_users SET msg_count=msg_count+1, last_seen=NOW(), ip_addr=:ip WHERE id=:id"),{"id":user['id'],"ip":request.remote_addr})
    if txt:
        with engine_main.connect() as conn: other=conn.execute(sa.text("SELECT username FROM fly_users WHERE id=:id"),{"id":uid}).scalar()
        if other=='FLY AI':
            reply=ask_fly_ai(txt, user); save_message_by_type(uid, user['id'], reply, time_str); return jsonify({"ok":True,"ai":reply})
    return jsonify({"ok":True})

@app.route('/test_groq')
def test_groq():
    key=(os.environ.get('GROQ_API_KEY') or '').strip()
    if not key: return f"NO GROQ KEY - ENV has: {[k for k in os.environ.keys() if 'GROQ' in k]}"
    out=f"Key {key[:12]}... len {len(key)}<br>"
    for model in ["llama-3.3-70b-versatile","llama3-8b-8192"]:
        try:
            r=requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"}, json={"model":model,"messages":[{"role":"user","content":"hi"}],"max_tokens":10}, timeout=10)
            out+=f"{model} -> {r.status_code} {r.text[:300]}<br><br>"
        except Exception as e:
            out+=f"{model} EX {e}<br>"
    return out

@app.route('/login', methods=["GET","POST"])
def login():
    if get_user_obj(): return redirect("/")
    err=""
    if request.method=="POST":
        p=request.form.get("phone","").strip(); pwd=request.form.get("password","").strip()
        with engine_main.connect() as conn:
            u=conn.execute(sa.text("SELECT * FROM fly_users WHERE phone=:p"),{"p":p}).mappings().first()
            if u and check_password_hash(u["password_hash"], pwd):
                session["uid"]=u["id"]
                try:
                    accs=safe_json(u.get('accounts','[]'),[])
                    if not any(a.get('phone')==p for a in accs):
                        accs.append({"phone":p,"name":u['name'],"avatar":u.get('avatar_url') or FAV})
                        with engine_main.begin() as w: w.execute(sa.text("UPDATE fly_users SET accounts=:a WHERE id=:id"),{"a":json.dumps(accs[-5:]),"id":u['id']})
                except: pass
                return redirect("/")
            else: err="Wrong phone/password"
    cfg=get_builder_config()
    content=f'''<div style="min-height:80vh;display:flex;align-items:center;justify-content:center;padding:16px"><div style="background:white;width:100%;max-width:360px;padding:20px;border-radius:16px;text-align:center"><img src="{FAV}" style="width:64px;height:64px;border-radius:50%;display:block;margin:0 auto 12px auto"><h2 style="margin:0">FLYCHAT</h2><div style="color:#e94560;font-size:13px;margin:6px 0">{err}</div><form method="POST"><input name="phone" placeholder="Phone" required style="width:100%;padding:11px;margin:6px 0;border:1px solid #ddd;border-radius:10px"><input name="password" type="password" placeholder="Password" required style="width:100%;padding:11px;margin:6px 0;border:1px solid #ddd;border-radius:10px"><button class="btn" style="width:100%;display:flex;align-items:center;justify-content:center;gap:8px"><img src="{SEND_BTN}" style="width:20px;height:20px;border-radius:50%"> Login</button></form><a href="/register" style="display:block;margin-top:14px;text-decoration:none;color:#0f3460;font-size:13px">Don't have an account, register here</a></div></div>'''
    return render_template_string(BASE, title="Login", header="", bottom_nav="", content=Markup(content), header_color=cfg.get('header_color','#00c853'), btn_color=cfg.get('button_color','#00c853'), bg_color=cfg.get('background','#f0f2f5'), favicon=cfg.get('favicon') or FAV, is_admin=False, ding_sound=DING_SOUND)

@app.route('/register', methods=["GET","POST"])
def register():
    err=""
    if request.method=="POST":
        nick=request.form.get("nickname","").strip(); phone=request.form.get("phone","").strip(); pwd=request.form.get("password","").strip(); pwd2=request.form.get("password2","").strip()
        if pwd!=pwd2: err="Passwords don't match"
        else:
            with engine_main.connect() as conn:
                if conn.execute(sa.text("SELECT id FROM fly_users WHERE phone=:p"),{"p":phone}).scalar(): err="Phone already used"
                else:
                    code=''.join(random.choices(string.ascii_uppercase+string.digits,k=6))
                    with engine_main.begin() as w:
                        sup=conn.execute(sa.text("SELECT id FROM fly_users WHERE username='flychat support'")).scalar()
                        ai=conn.execute(sa.text("SELECT id FROM fly_users WHERE username='FLY AI'")).scalar()
                        w.execute(sa.text("INSERT INTO fly_users (username,name,phone,password_hash,friends,referral_code,avatar_url,accounts) VALUES (:u,:n,:p,:h,:f,:rc,:av,:acc)"),{"u":nick,"n":nick,"p":phone,"h":generate_password_hash(pwd),"f":json.dumps([x for x in [sup,ai] if x]),"rc":code,"av":AVATARS[0],"acc":json.dumps([{"phone":phone,"name":nick,"avatar":AVATARS[0]}])})
                    with engine_main.connect() as c2: nid=c2.execute(sa.text("SELECT id FROM fly_users WHERE phone=:p"),{"p":phone}).scalar(); session["uid"]=nid; return redirect("/")
    cfg=get_builder_config()
    content=f'''<div style="min-height:80vh;display:flex;align-items:center;justify-content:center;padding:16px"><div style="background:white;width:100%;max-width:360px;padding:20px;border-radius:16px"><img src="{FAV}" style="width:64px;height:64px;border-radius:50%;display:block;margin:0 auto 12px auto"><h2 style="text-align:center;margin:0">Join FLYCHAT</h2><div style="color:#e94560;text-align:center;font-size:13px">{err}</div><form method="POST"><input name="nickname" placeholder="Username" required style="width:100%;padding:11px;margin:5px 0;border:1px solid #ddd;border-radius:10px"><input name="phone" placeholder="Phone" required style="width:100%;padding:11px;margin:5px 0;border:1px solid #ddd;border-radius:10px"><input name="password" type="password" placeholder="Password" required style="width:100%;padding:11px;margin:5px 0;border:1px solid #ddd;border-radius:10px"><input name="password2" type="password" placeholder="Confirm" required style="width:100%;padding:11px;margin:5px 0;border:1px solid #ddd;border-radius:10px"><button class="btn" style="width:100%;display:flex;align-items:center;justify-content:center;gap:8px"><img src="{SEND_BTN}" style="width:20px;height:20px;border-radius:50%"> Register</button></form><a href="/login" style="display:block;text-align:center;margin-top:12px;font-size:13px;text-decoration:none">Already have account? Login</a></div></div>'''
    return render_template_string(BASE, title="Register", header="", bottom_nav="", content=Markup(content), header_color=cfg.get('header_color','#00c853'), btn_color=cfg.get('button_color','#00c853'), bg_color=cfg.get('background','#f0f2f5'), favicon=cfg.get('favicon') or FAV, is_admin=False, ding_sound=DING_SOUND)

@app.route('/logout')
def logout(): session.clear(); return redirect("/login")

@app.route('/')
@login_required
def home(user):
    tab=request.args.get('tab','chat'); search_q=request.args.get('q','').lower()
    cfg=get_builder_config()
    with engine_main.connect() as conn:
        friends_objs=[]
        for fid in user['friends']:
            u=conn.execute(sa.text("SELECT * FROM fly_users WHERE id=:id"),{"id":fid}).mappings().first()
            if u:
                custom_name=user.get('custom_names',{}).get(str(fid), u['name'])
                d=dict(u); d['display_name']=custom_name; d['is_online']=is_online(u.get('last_seen')); friends_objs.append(d)
        all_users=conn.execute(sa.text("SELECT * FROM fly_users WHERE id!=:id AND LOWER(username) NOT IN ('fly ai','flychat support') ORDER BY id DESC LIMIT 40"),{"id":user['id']}).mappings().all()
        incoming=conn.execute(sa.text("SELECT r.id, r.from_id, u.name FROM fly_requests r JOIN fly_users u ON u.id=r.from_id WHERE r.to_id=:id AND r.status='pending'"),{"id":user['id']}).mappings().all()
        outgoing=conn.execute(sa.text("SELECT to_id FROM fly_requests WHERE from_id=:id AND status='pending'"),{"id":user['id']}).mappings().all()
        outgoing_ids=[o['to_id'] for o in outgoing]
        try: groups=conn.execute(sa.text("SELECT * FROM fly_groups WHERE members LIKE :like"),{"like":"%"+str(user['id'])+"%"}).mappings().all()
        except: groups=[]
    req_html="".join([f"<div class='card' style='display:flex;justify-content:space-between'><div><b>{html_lib.escape(r['name'] or 'User')}</b></div><div><a href='/request/accept/{r['id']}' class='btn small'>Accept</a> <a href='/request/reject/{r['id']}' class='btn small red'>Reject</a></div></div>" for r in incoming]) if incoming else ""
    if search_q: friends_objs=[u for u in friends_objs if search_q in (u['display_name'] or '').lower()]
    chat_html_parts=[]
    for g in groups:
        chat_html_parts.append(f"<a class='friend-card' href='/group/{g['id']}'><div class='friend-avatar' style='background:#673ab7'>👥</div><div style='flex:1'><b>{html_lib.escape(g['name'][:28])}</b></div></a>")
    for u in friends_objs:
        av=(u.get('avatar_url') or FAV)
        if u['username']=='FLY AI': av=FLY_AI_AVATAR
        if u['username']=='flychat support': av=SUPPORT_AVATAR
        last_text,last_time,tick=get_last_message(user['id'], u['id'])
        dname=html_lib.escape((u['display_name'] or u['name'] or 'User')[:28])
        ltxt=html_lib.escape((last_text or 'No messages')[:32])
        online_dot="<span class='online-dot'></span>" if u.get('is_online') else ""
        online_text="<small style='color:#00c853'> ● online</small>" if u.get('is_online') else ""
        chat_html_parts.append(f"<a class='friend-card' href='/dm/{u['id']}'><div class='friend-avatar'><img src='{av}'>{online_dot}</div><div style='flex:1;overflow:hidden'><b>{dname}{online_text}</b><br><small style='color:#888'>{ltxt} {tick}</small></div><small style='font-size:10px;color:#888'>{last_time}</small></a>")
    chat_html="".join(chat_html_parts) or "<div class='card' style='text-align:center;color:#888'>No chats — add friends or create group</div>"
    people_html_parts=[]
    for u in all_users:
        if u['id'] in user['friends'] or u['id'] in outgoing_ids: continue
        av=u.get('avatar_url') or FAV
        name=html_lib.escape((u['name'] or 'User')[:28])
        online_badge="<small style='color:#00c853'> ● online</small>" if is_online(u.get('last_seen')) else ""
        people_html_parts.append(f"<div class='friend-card'><div class='friend-avatar'><img src='{av}'></div><div style='flex:1'><b>{name}</b>{online_badge}</div><a href='/request/send/{u['id']}' class='btn small blue'>Add</a></div>")
    people_html="".join(people_html_parts) or "<div class='card'>No new people</div>"
    inside=chat_html if tab=='chat' else people_html
    group_btn='<div style="padding:6px 8px"><button onclick="openGroupModal()" class="btn small blue" style="width:100%">+ Create Group</button></div>' if tab=='chat' else ''
    content=f"<div style='padding:6px 8px'><input placeholder='🔎 Search' value='{html_lib.escape(search_q)}' oninput=\"var u=new URL(window.location); u.searchParams.set('q',this.value); u.searchParams.set('tab','{tab}'); window.location=u;\" style='width:100%;padding:10px;border-radius:20px;border:1px solid #ddd'></div>"+group_btn+req_html+inside
    return render_template_string(BASE, title="FLYCHAT", header=Markup(get_header(user)), bottom_nav=Markup(get_bottom_nav(user, active=tab)), content=Markup(content), header_color=cfg.get('header_color','#00c853'), btn_color=cfg.get('button_color','#00c853'), bg_color=cfg.get('background','#f0f2f5'), favicon=cfg.get('favicon') or FAV, is_admin=user.get('is_admin'), ding_sound=DING_SOUND)

@app.route('/request/send/<int:uid>')
@login_required
def req_send(user, uid):
    with engine_main.begin() as w: w.execute(sa.text("INSERT INTO fly_requests (from_id,to_id,status) VALUES (:f,:t,'pending')"),{"f":user['id'],"t":uid})
    return redirect("/?tab=people")
@app.route('/request/accept/<int:req_id>')
@login_required
def req_accept(user, req_id):
    withengine_main.connect() as conn: req=conn.execute(sa.text("SELECT * FROM fly_requests WHERE id=:id"),{"id":req_id}).mappings().first()
    if not req: return redirect("/")
    with engine_main.begin() as w:
        for uid1,uid2 in [(user['id'],req['from_id']),(req['from_id'],user['id'])]:
            u=w.execute(sa.text("SELECT friends FROM fly_users WHERE id=:id"),{"id":uid1}).scalar(); friends=safe_json(u,[])
            if uid2 not in friends: friends.append(uid2); w.execute(sa.text("UPDATE fly_users SET friends=:f WHERE id=:id"),{"f":json.dumps(friends),"id":uid1})
        w.execute(sa.text("DELETE FROM fly_requests WHERE id=:id"),{"id":req_id})
    return redirect("/?tab=chat")
@app.route('/request/reject/<int:req_id>')
@login_required
def req_reject(user, req_id):
    with engine_main.begin() as w: w.execute(sa.text("DELETE FROM fly_requests WHERE id=:id"),{"id":req_id})
    return redirect("/?tab=people")

@app.route('/dm/<int:uid>')
@login_required
def dm_chat(user, uid):
    cfg=get_builder_config()
    with engine_main.connect() as conn: other=conn.execute(sa.text("SELECT * FROM fly_users WHERE id=:id"),{"id":uid}).mappings().first()
    if not other: return redirect("/")
    custom_name=user.get('custom_names',{}).get(str(uid))
    if custom_name: other=dict(other); other['display_name']=custom_name
    else: other=dict(other); other['display_name']=other['name']
    msgs=load_all_messages(user['id'], uid)
    try:
        with engine_main.begin() as w: w.execute(sa.text("UPDATE fly_messages_text SET viewed=TRUE WHERE from_id=:fid AND to_id=:tid"),{"fid":uid,"tid":user['id']})
    except: pass
    msgs_html=""
    for m in msgs:
        is_me=m['from_id']==user['id']
        content_html=render_msg_content(m['text'])
        tick="✓✓" if m.get('viewed') else "✓"
        msgs_html+=f"<div class='chat-msg {('me' if is_me else '')}'><div class='bubble {('me' if is_me else 'other')}'><span>{content_html}</span><small style='display:block;font-size:10px;opacity:0.6'>{m.get('time','')} {(tick if is_me else '')}</small></div></div>"
    if not msgs_html: msgs_html="<div style='text-align:center;color:#999;margin-top:30px'>No messages yet</div>"
    content = f"<div id=\"chatBox\" style=\"margin-bottom:90px;max-height:62vh;overflow-y:auto\">{msgs_html}</div><div style=\"position:fixed;bottom:60px;left:50%;transform:translateX(-50%);width:100%;max-width:480px;display:flex;gap:6px;background:white;padding:6px 8px;border-radius:24px;box-shadow:0 -2px 10px rgba(0,0,0,0.12);align-items:center\"><label style=\"background:#f0f2f5;width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;cursor:pointer\">📎<input type=\"file\" id=\"fileInput\" accept=\"image/*,video/*\" multiple style=\"display:none\"></label><input type=\"text\" id=\"msgInput\" placeholder=\"Type a message\" style=\"flex:1;padding:10px;border-radius:20px;border:1px solid #ddd\"><button id=\"micBtn\" style=\"background:none;border:none;width:42px;height:42px;border-radius:50%\"><img src=\"{MIC_BTN_URL}\" style=\"width:32px;height:32px;border-radius:50%\"></button><button id=\"sendBtn\" style=\"background:{cfg.get('button_color','#00c853')};color:white;width:36px;height:36px;border-radius:50%;border:none;display:none\"><img src=\"{SEND_BTN}\" style=\"width:20px;height:20px;border-radius:50%\"></button></div><script>var otherId={uid}; var msgInput=document.getElementById('msgInput'); var sendBtn=document.getElementById('sendBtn'); var micBtn=document.getElementById('micBtn'); var chatBox=document.getElementById('chatBox'); chatBox.scrollTop=chatBox.scrollHeight; function toggleSendMic(){{if(msgInput.value.trim()){{sendBtn.style.display='flex'; micBtn.style.display='none';}} else {{sendBtn.style.display='none'; micBtn.style.display='flex';}}}} msgInput.addEventListener('input', ()=>{{toggleSendMic(); fetch('/api/typing',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{to_id:otherId,type:'typing'}})}});}}); function addBubble(html, me){{var d=document.createElement('div'); d.className='chat-msg '+(me?'me':''); d.innerHTML='<div class=\"bubble '+(me?'me':'other')+'\"><span>'+html+'</span><small style=display:block;font-size:10px;opacity:0.6>Now</small></div>'; chatBox.appendChild(d); chatBox.scrollTop=chatBox.scrollHeight;}} async function sendMessage(text,images,videoData,audioData){{if(!text&&images.length==0&&!videoData&&!audioData) return; var html=text||''; if(images.length>0) html=images.map(s=>'<img src=\"'+s+'\" style=\"max-width:200px;border-radius:10px\">').join(''); if(videoData) html='<video controls src=\"'+videoData+'\" style=\"max-width:200px;border-radius:10px\"></video>'; if(audioData) html='<audio controls src=\"'+audioData+'\" style=\"width:200px\"></audio>'; addBubble(html,true); var payload={{to_id:otherId,text:text,images:images,video_data:videoData,audio_data:audioData}}; msgInput.value=''; toggleSendMic(); var res=await fetch('/api/dm/send',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(payload)}}); var data=await res.json(); if(data.ai) addBubble(data.ai,false);}} msgInput.addEventListener('keydown', e=>{{if(e.key==='Enter'){{e.preventDefault(); sendMessage(msgInput.value.trim(),[],'','');}}}}); sendBtn.addEventListener('click', ()=>sendMessage(msgInput.value.trim(),[],'','')); document.getElementById('fileInput').addEventListener('change', function(){{var files=Array.from(this.files); var images=[]; var vids=[]; var pending=files.length; files.forEach(f=>{{var r=new FileReader(); r.onloadend=function(){{if(f.type.startsWith('image/')) images.push(r.result); else vids.push(r.result); pending--; if(pending==0){{if(images.length>0) sendMessage('',images,'',''); if(vids.length>0) vids.forEach(v=>sendMessage('','',v,''));}}}}; r.readAsDataURL(f);}});}}); var mediaRecorder=null, audioChunks=[], isRecording=false; micBtn.addEventListener('click', ()=>{{if(isRecording) return; navigator.mediaDevices.getUserMedia({{audio:true}}).then(stream=>{{mediaRecorder=new MediaRecorder(stream); audioChunks=[]; mediaRecorder.ondataavailable=e=>audioChunks.push(e.data); mediaRecorder.onstop=()=>{{var blob=new Blob(audioChunks,{{type:'audio/webm'}}); var reader=new FileReader(); reader.onloadend=()=>{{sendMessage('','', '', reader.result);}}; reader.readAsDataURL(blob); stream.getTracks().forEach(t=>t.stop()); isRecording=false; micBtn.innerHTML='<img src=\"{MIC_BTN_URL}\" style=\"width:32px;height:32px;border-radius:50%\">';}}; mediaRecorder.start(); isRecording=true; micBtn.innerHTML='⏹️'; setTimeout(()=>{{if(isRecording&&mediaRecorder.state=='recording') mediaRecorder.stop();}},15000);}});}});</script>"
    return render_template_string(BASE, title=other['display_name'], header=Markup(get_header(user, other)), bottom_nav=Markup(""), content=Markup(content), header_color=cfg.get('header_color','#00c853'), btn_color=cfg.get('button_color','#00c853'), bg_color=cfg.get('background','#f0f2f5'), favicon=cfg.get('favicon') or FAV, is_admin=user.get('is_admin'), ding_sound=DING_SOUND)

@app.route('/post')
@login_required
def post_page(user):
    cfg=get_builder_config()
    cutoff=datetime.now(pytz.utc)-timedelta(hours=24)
    with engine_main.connect() as conn:
        posts=conn.execute(sa.text("SELECT * FROM fly_posts WHERE created_at > :cutoff OR is_ad=TRUE ORDER BY is_ad DESC, id DESC LIMIT 100"),{"cutoff":cutoff}).mappings().all()
        friends_set=set(user['friends']+[user['id']])
        filtered=[p for p in posts if p['user_id'] in friends_set or p['is_ad']]
    posts_html=""
    for p in filtered:
        likes=safe_json(p.get('likes','[]'),[])
        media_html=""
        if p.get('post_image'): media_html+=f"<div class='post-media'><img src='{p['post_image']}' onclick=\"openImagePreview(this.src)\" loading='lazy'></div>"
        if p.get('post_video'): media_html+=f"<div class='post-media'><video controls src='{p['post_video']}'></video></div>"
        is_owner=p['user_id']==user['id']
        del_btn=f"<button onclick=\"deletePost({p['id']})\" style='color:red'>Delete</button>" if is_owner else ""
        posts_html+=f"<div class=\"post-card\" id=\"post-{p['id']}\"><div class=\"post-header\"><b>{html_lib.escape(p['name'] or 'User')}</b> <button onclick=\"togglePostMenu({p['id']})\" style=\"background:none;border:none;font-size:18px\">⋮</button><div id=\"pmenu-{p['id']}\" class=\"post-menu\"><button onclick=\"savePost({p['id']})\">Save</button><button onclick=\"forwardPost({p['id']})\">Forward</button>{del_btn}</div></div><div class=\"post-body\"><p>{html_lib.escape(p['text'] or '')[:1000]}</p></div>{media_html}<div class=\"post-actions\"><button onclick=\"likePost({p['id']})\"><img src=\"{LIKE_BTN_URL}\"> <span>{len(likes)}</span></button><button>💬</button></div></div>"
    post_box=f"<div class=\"card\"><h3>Create Post (friends only)</h3><textarea id=\"postText\" placeholder=\"What's on your mind?\" style=\"width:100%;min-height:70px;padding:10px;border-radius:12px;border:1px solid #ddd\"></textarea><label class=\"btn small blue\" style=\"margin-top:6px\">Attach<input type=\"file\" id=\"postImageInput\" accept=\"image/*,video/*\" multiple style=\"display:none\"></label> <button class=\"btn\" id=\"createPostBtn\" style=\"display:flex;align-items:center;gap:6px\"><img src=\"{SEND_BTN}\" style=\"width:18px;height:18px;border-radius:50%\"> Post</button><div id=\"postPreview\" style=\"margin:8px 0;display:none;flex-wrap:wrap;gap:6px\"></div></div>"+(posts_html or "<div class='card'>No posts</div>")+f"<script>var postImgs=[]; var postVid=''; document.getElementById('postImageInput').addEventListener('change', function(){{var files=Array.from(this.files); var preview=document.getElementById('postPreview'); preview.style.display='flex'; preview.innerHTML=''; postImgs=[]; files.forEach(f=>{{var r=new FileReader(); r.onloadend=function(){{if(f.type.startsWith('image/')){{postImgs.push(r.result); var img=document.createElement('img'); img.src=r.result; img.style.width='70px'; img.style.height='70px'; img.style.borderRadius='8px'; preview.appendChild(img);}} else postVid=r.result;}}; r.readAsDataURL(f);}});}}); document.getElementById('createPostBtn').addEventListener('click', async function(){{var t=document.getElementById('postText').value.trim(); if(!t&&postImgs.length==0&&!postVid) return; var imgData=postImgs.length>0?postImgs[0]:''; var res=await fetch('/post/create',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{text:t,image_data:imgData,video_data:postVid,images:postImgs}})}}); if((await res.json()).ok) location.reload();}}); function deletePost(id){{if(confirm('Delete?')) fetch('/post/delete/'+id,{{method:'POST'}}).then(()=>location.reload());}} function likePost(id){{fetch('/api/post/like',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{id:id}})}}).then(()=>location.reload());}}</script>"
    return render_template_string(BASE, title="Posts", header=Markup(get_header(user)), bottom_nav=Markup(get_bottom_nav(user, active="post")), content=Markup(post_box), header_color=cfg.get('header_color','#00c853'), btn_color=cfg.get('button_color','#00c853'), bg_color=cfg.get('background','#f0f2f5'), favicon=cfg.get('favicon') or FAV, is_admin=user.get('is_admin'), ding_sound=DING_SOUND)

@app.route('/post/delete/<int:pid>', methods=["POST"])
@login_required
def post_delete(user, pid):
    with engine_main.connect() as conn:
        p=conn.execute(sa.text("SELECT user_id FROM fly_posts WHERE id=:id"),{"id":pid}).mappings().first()
        if p and p['user_id']==user['id']:
            with engine_main.begin() as w: w.execute(sa.text("DELETE FROM fly_posts WHERE id=:id"),{"id":pid})
            return jsonify({"ok":True})
    return jsonify({"ok":False})

@app.route('/post/create', methods=["POST"])
@login_required
def post_create_api(user):
    data=request.get_json() or {}; txt=(data.get('text') or '').strip()[:2000]
    imgs=data.get('images',[]); img=data.get('image_data','')[:8000000] if data.get('image_data') else (imgs[0][:8000000] if imgs else '')
    vid=data.get('video_data','')[:15000000]
    if txt or img or vid:
        with engine_main.begin() as w: w.execute(sa.text("INSERT INTO fly_posts (user_id,name,text,post_image,post_video,likes,is_ad) VALUES (:uid,:n,:t,:img,:vid,'[]',FALSE)"),{"uid":user['id'],"n":user["name"],"t":txt,"img":img,"vid":vid})
    return jsonify({"ok":True})

@app.route('/profile')
@login_required
def profile(user):
    cfg=get_builder_config()
    acc_html=""
    for acc in user.get('accounts',[]):
        acc_html+=f"<div class='friend-card' style='cursor:pointer' onclick=\"switchAcc('{html_lib.escape(acc.get('phone',''))}')\"><div class='friend-avatar'><img src='{acc.get('avatar') or FAV}'></div><div style='flex:1'><b>{html_lib.escape(acc.get('name',''))}</b><br><small>{html_lib.escape(acc.get('phone',''))}</small></div><small style='color:#00c853'>● Switch</small></div>"
    if not acc_html: acc_html="<small>No other accounts — login with another phone to save here like Facebook</small>"
    referral_link=f"https://{request.host}/register?ref={user.get('referral_code','')}"
    content=f"<div class='card' style='text-align:center'><img src='{user.get('avatar_url') or FAV}' style='width:80px;height:80px;border-radius:50%'><h3>{html_lib.escape(user['name'])}</h3><p>Referral Code: <b>{user.get('referral_code','')}</b></p><div style='background:#f0f2f5;padding:10px;border-radius:10px;word-break:break-all'><small>Your referral link:</small><br><a href='{referral_link}' style='font-size:12px'>{referral_link}</a><br><button onclick=\"navigator.clipboard.writeText('{referral_link}'); alert('Copied')\" class='btn small' style='margin-top:6px'>Copy Link</button></div></div><div class='card'><h3>Your Accounts (Facebook style — tap to switch)</h3>{acc_html}</div><div class='card'><a href='/logout' class='btn red small' style='display:block;text-align:center;text-decoration:none'>Logout</a></div><script>function switchAcc(phone){{fetch('/api/switch_account',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{phone:phone}})}}).then(r=>r.json()).then(d=>{{if(d.ok) location.href='/'; else alert('Login again');}});}}</script>"
    return render_template_string(BASE, title="Profile", header=Markup(get_header(user)), bottom_nav=Markup(get_bottom_nav(user, active="profile")), content=Markup(content), header_color=cfg.get('header_color','#00c853'), btn_color=cfg.get('button_color','#00c853'), bg_color=cfg.get('background','#f0f2f5'), favicon=cfg.get('favicon') or FAV, is_admin=user.get('is_admin'), ding_sound=DING_SOUND)

@app.route('/api/switch_account', methods=["POST"])
@login_required
def api_switch_account(user):
    data=request.get_json() or {}; phone=data.get('phone')
    with engine_main.connect() as conn:
        u=conn.execute(sa.text("SELECT id FROM fly_users WHERE phone=:p"),{"p":phone}).mappings().first()
        if u: session["uid"]=u['id']; return jsonify({"ok":True})
    return jsonify({"ok":False})

@app.route('/api/profile/update', methods=["POST"])
@login_required
def api_profile_update(user):
    data=request.get_json() or {}; name=(data.get('name') or '').strip()[:30]
    with engine_main.begin() as w: w.execute(sa.text("UPDATE fly_users SET name=:n WHERE id=:id"),{"n":name or user['name'],"id":user['id']})
    return jsonify({"ok":True})

@app.route('/api/rename', methods=["POST"])
@login_required
def api_rename(user):
    data=request.get_json() or {}; fid=str(data.get('friend_id')); new_name=(data.get('name') or '').strip()[:30]
    custom=user.get('custom_names',{}); custom[fid]=new_name
    with engine_main.begin() as w: w.execute(sa.text("UPDATE fly_users SET custom_names=:c WHERE id=:id"),{"c":json.dumps(custom),"id":user['id']})
    return jsonify({"ok":True})

@app.route('/api/settings/disappearing', methods=["POST"])
@login_required
def api_disappearing(user): return jsonify({"ok":True})
@app.route('/api/user/mute/<int:uid>', methods=["POST"])
@login_required
def api_mute(user, uid): return jsonify({"ok":True})
@app.route('/api/user/block/<int:uid>', methods=["POST"])
@login_required
def api_block(user, uid):
    with engine_main.begin() as w: w.execute(sa.text("UPDATE fly_users SET blocked_users=:b WHERE id=:id"),{"b":json.dumps([uid]),"id":user['id']})
    return jsonify({"ok":True})
@app.route('/api/report', methods=["POST"])
@login_required
def api_report(user):
    data=request.get_json() or {}
    with engine_main.begin() as w: w.execute(sa.text("INSERT INTO fly_reports (reporter_id,target_id,target_post,reason) VALUES (:r,:t,:p,:reason)"),{"r":user['id'],"t":data.get('target_id',0),"p":data.get('post_id',0),"reason":data.get('reason','spam')})
    return jsonify({"ok":True})
@app.route('/api/post/like', methods=["POST"])
@login_required
def api_like(user):
    pid=(request.get_json() or {}).get('id')
    with engine_main.connect() as conn:
        row=conn.execute(sa.text("SELECT likes FROM fly_posts WHERE id=:id"),{"id":pid}).mappings().first()
        if not row: return jsonify({"ok":False})
        likes=safe_json(row['likes'],'[]')
        if user['id'] in likes: likes.remove(user['id'])
        else: likes.append(user['id'])
        with engine_main.begin() as w: w.execute(sa.text("UPDATE fly_posts SET likes=:l WHERE id=:id"),{"l":json.dumps(likes),"id":pid})
        return jsonify({"ok":True})

@app.route('/group/<int:gid>')
@login_required
def group_chat(user, gid):
    cfg=get_builder_config()
    with engine_main.connect() as conn:
        g=conn.execute(sa.text("SELECT * FROM fly_groups WHERE id=:id"),{"id":gid}).mappings().first()
        if not g: return redirect("/")
        members=safe_json(g['members'],[])
        if user['id'] not in members: return redirect("/")
        msgs=conn.execute(sa.text("SELECT * FROM fly_group_messages WHERE group_id=:gid ORDER BY created_at ASC LIMIT 300"),{"gid":gid}).mappings().all()
    msgs_html="".join([f"<div class='chat-msg'><div class='bubble other'>{render_msg_content(m['text'])}</div></div>" for m in msgs]) or "<div style='text-align:center;color:#999'>No group msgs</div>"
    content=f"<h3>{html_lib.escape(g['name'])}</h3><div style='max-height:60vh;overflow:auto;margin-bottom:80px'>{msgs_html}</div><div style='position:fixed;bottom:60px;left:50%;transform:translateX(-50%);width:100%;max-width:480px;display:flex;gap:6px;background:white;padding:6px 8px;border-radius:24px'><input id='gInput' placeholder='Group msg' style='flex:1;padding:10px;border-radius:20px;border:1px solid #ddd'><button id='gSend' style='background:{cfg.get('button_color','#00c853')};color:white;width:36px;height:36px;border-radius:50%;border:none'><img src='{SEND_BTN}' style='width:20px;height:20px;border-radius:50%'></button></div><script>var gid={gid}; document.getElementById('gSend').addEventListener('click',()=>{{var t=document.getElementById('gInput').value.trim(); if(!t) return; document.getElementById('gInput').value=''; fetch('/api/group/send',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{group_id:gid,text:t}})}}).then(()=>location.reload());}});</script>"
    return render_template_string(BASE, title=g['name'], header=Markup(get_header(user)), bottom_nav=Markup(""), content=Markup(content), header_color=cfg.get('header_color','#00c853'), btn_color=cfg.get('button_color','#00c853'), bg_color=cfg.get('background','#f0f2f5'), favicon=cfg.get('favicon') or FAV, is_admin=user.get('is_admin'), ding_sound=DING_SOUND)

@app.route('/api/group/send', methods=["POST"])
@login_required
def api_group_send(user):
    data=request.get_json() or {}; gid=data.get('group_id'); txt=(data.get('text') or '').strip()[:2000]
    time_str=datetime.now(TZ).strftime("%I:%M %p")
    with engine_main.begin() as w: w.execute(sa.text("INSERT INTO fly_group_messages (group_id,from_id,text,time) VALUES (:gid,:fid,:txt,:time)"),{"gid":gid,"fid":user['id'],"txt":txt,"time":time_str})
    return jsonify({"ok":True})

@app.route('/api/call/request', methods=["POST"])
@login_required
def call_request(user):
    data=request.get_json() or {}; callee=data.get('callee_id'); sdp=data.get('sdp',''); ctype=data.get('type','voice')
    with engine_main.begin() as w:
        w.execute(sa.text("DELETE FROM fly_calls WHERE caller_id=:cid OR callee_id=:cid"),{"cid":user['id']})
        w.execute(sa.text("DELETE FROM fly_calls WHERE caller_id=:callee OR callee_id=:callee"),{"callee":callee})
        res=w.execute(sa.text("INSERT INTO fly_calls (caller_id,callee_id,sdp_offer,call_type,status) VALUES (:caller,:callee,:sdp,:type,'ringing') RETURNING id"),{"caller":user['id'],"callee":callee,"sdp":sdp,"type":ctype})
        cid=res.scalar()
    return jsonify({"ok":True,"call_id":cid})

@app.route('/api/call/answer', methods=["POST"])
@login_required
def call_answer(user):
    data=request.get_json() or {}; call_id=data.get('call_id'); sdp=data.get('sdp','')
    with engine_main.begin() as w: w.execute(sa.text("UPDATE fly_calls SET sdp_answer=:sdp,status='answered' WHERE id=:id"),{"sdp":sdp,"id":call_id})
    return jsonify({"ok":True})

@app.route('/api/call/ice', methods=["POST"])
@login_required
def call_ice(user):
    data=request.get_json() or {}; call_id=data.get('call_id'); cand=data.get('candidate','')
    with engine_main.connect() as conn:
        cur=conn.execute(sa.text("SELECT ice_candidates FROM fly_calls WHERE id=:id"),{"id":call_id}).scalar() or '[]'
        lst=safe_json(cur,[]); lst.append(cand)
        with engine_main.begin() as w: w.execute(sa.text("UPDATE fly_calls SET ice_candidates=:ic WHERE id=:id"),{"ic":json.dumps(lst[-20:]),"id":call_id})
    return jsonify({"ok":True})

@app.route('/api/call/poll/<int:call_id>')
@login_required
def call_poll(user, call_id):
    with engine_main.connect() as conn:
        c=conn.execute(sa.text("SELECT * FROM fly_calls WHERE id=:id"),{"id":call_id}).mappings().first()
        if not c: return jsonify({"status":"ended"})
        return jsonify({"status":c['status'],"sdp_answer":c['sdp_answer'],"ice_candidates":c['ice_candidates']})

@app.route('/api/call/incoming')
@login_required
def call_incoming(user):
    with engine_main.connect() as conn:
        c=conn.execute(sa.text("SELECT c.*, u.name as caller_name FROM fly_calls c JOIN fly_users u ON u.id=c.caller_id WHERE c.callee_id=:id AND c.status='ringing' ORDER BY c.created_at DESC LIMIT 1"),{"id":user['id']}).mappings().first()
        if not c: return jsonify({"call":None})
        return jsonify({"call":{"id":c['id'],"caller_id":c['caller_id'],"caller_name":c['caller_name'],"call_type":c['call_type'],"sdp_offer":c['sdp_offer']}})

@app.route('/api/call/end/<int:call_id>', methods=["POST"])
@login_required
def call_end(user, call_id):
    data=request.get_json() or {}
    missed=data.get('missed',False)
    with engine_main.begin() as w:
        w.execute(sa.text("UPDATE fly_calls SET status='ended' WHERE id=:id"),{"id":call_id})
        if missed:
            c=w.execute(sa.text("SELECT caller_id, callee_id, call_type FROM fly_calls WHERE id=:id"),{"id":call_id}).mappings().first()
            if c: w.execute(sa.text("INSERT INTO fly_missed_calls (caller_id,callee_id,call_type) VALUES (:caller,:callee,:type)"),{"caller":c['caller_id'],"callee":c['callee_id'],"type":c['call_type']})
    return jsonify({"ok":True})

@app.errorhandler(500)
def handle_500(e):
    print("500 "+str(e)+"\n"+traceback.format_exc(), flush=True)
    return "<h3>Recovered</h3><a href='/'>Home</a>", 200
@app.errorhandler(404)
def handle_404(e): return redirect("/")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
