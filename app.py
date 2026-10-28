import os,re,json,uuid
from pathlib import Path
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv
from groq import Groq
from supabase import create_client

BASE=Path(__file__).resolve().parent
load_dotenv(BASE/".env")
HISTORY=BASE/"saved_reviews.json"
MODEL=os.getenv("GROQ_MODEL","openai/gpt-oss-20b")
st.set_page_config(page_title="InternShield AI",page_icon="🛡️",layout="wide")
st.markdown("""<style>
.stApp{background:radial-gradient(ellipse at 80% -10%,#1d3558,transparent 45%),#0b0e15;color:#edf0fb}
header[data-testid="stHeader"]{background:transparent} footer{visibility:hidden}
.block-container{max-width:1150px;padding-top:1.5rem}
section[data-testid="stSidebar"]{background:#10141e;border-right:1px solid #293142}
.brand{color:#7dd3fc;letter-spacing:.17em;text-transform:uppercase;font-size:.76rem;font-weight:800}
div.stButton>button{border-radius:12px;border:1px solid #344258;background:#151d2b;color:#eaf3ff}
div[data-testid="stMetric"]{background:#121a27;border:1px solid #28364b;padding:12px;border-radius:14px}
</style>""",unsafe_allow_html=True)
SYSTEM="""You are InternShield AI, a student-focused recruitment opportunity review assistant. Summarize the role, extract skills, explain warning signs and unknowns, and give a practical independent verification checklist. Separate evidence from assumptions. Never claim you verified a company or URL online. A score is a heuristic signal, not proof of fraud. Never ask for passwords, OTPs, bank PINs, or sensitive identity documents. Answer general recruitment-safety questions too."""
RULES=[
("Upfront fee",r"\b(pay|payment|deposit|registration fee|processing fee|security fee|training fee)\b.{0,60}\b(job|internship|offer|selection|placement|certificate|training)\b|\b(job|internship|offer|selection|placement)\b.{0,60}\b(pay|payment|deposit|registration fee|processing fee|security fee|training fee)\b",25,"Requests money to apply, secure selection, or receive an offer."),
("Guaranteed selection",r"\b(guaranteed job|100% placement|guaranteed placement|assured selection|job guaranteed)\b",15,"Promises guaranteed selection or placement."),
("Urgent pressure",r"\b(act now|immediate payment|last chance|today only|urgent.{0,20}(pay|fee|register)|within \d+ hours)\b",10,"Uses pressure to rush a decision."),
("Sensitive credentials",r"\b(otp|password|bank pin|upi pin|cvv|card pin)\b",30,"Mentions sensitive authentication or banking information."),
("Informal-only contact",r"\b(telegram only|whatsapp only|dm to get selected|personal upi)\b",10,"Relies on informal contact or payment channels."),
("No interview / easy money",r"\b(no interview|no skills required|anyone can earn|no experience huge salary)\b",8,"Uses unusually easy-entry claims.")
]
def read_history():
 try:
  d=json.loads(HISTORY.read_text(encoding="utf-8")); return d if isinstance(d,list) else []
 except (OSError,json.JSONDecodeError): return []
def write_history(d): HISTORY.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")
def assess(text):
 flags=[]; score=0
 for name,pat,weight,why in RULES:
  if re.search(pat,text,re.I|re.S): flags.append({"name":name,"weight":weight,"why":why}); score+=weight
 missing=[]
 if len(text)<180: missing.append("The supplied message is short; context may be missing.")
 if not re.search(r"\b(company|organisation|organization|employer|startup|inc\.|ltd)\b",text,re.I): missing.append("No clear employer identity is stated.")
 if not re.search(r"\b(role|responsibilit|intern|developer|analyst|engineer|design|marketing|project)\b",text,re.I): missing.append("Role responsibilities are unclear.")
 label="High caution" if score>=35 else "Needs verification" if score>=15 else "No major rule-based flags found"
 return {"score":min(score,100),"label":label,"flags":flags,"missing":missing}
def groq(system,prompt,history=None):
 key=config_value("GROQ_API_KEY")
 if not key: return None,"API key missing. Create `.env` beside app.py with GROQ_API_KEY=your_key_here."
 try:
  client=Groq(api_key=key); msgs=[{"role":"system","content":system}]
  for m in (history or [])[-6:]:
   if m.get("role") in ("user","assistant"): msgs.append({"role":m["role"],"content":str(m.get("content",""))[:7000]})
  msgs.append({"role":"user","content":prompt})
  res=client.chat.completions.create(model=config_value("GROQ_MODEL",MODEL),messages=msgs,temperature=.25,max_tokens=1300)
  return res.choices[0].message.content,None
 except Exception as e:
  s=str(e)
  if "model_not_found" in s.lower() or "does not exist" in s.lower(): return None,f"Model {config_value('GROQ_MODEL',MODEL)} unavailable. Set GROQ_MODEL in .env to a model enabled for your account."
  if "401" in s or "authentication" in s.lower(): return None,"Groq rejected the API key. Check .env."
  if "429" in s or "rate limit" in s.lower(): return None,"Groq rate limit reached. Wait briefly and retry."
  return None,f"Groq request failed. Check internet/configuration. ({s[:150]})"
def analyze(text):
 a=assess(text)
 p=f"""Review this opportunity as preliminary screening, not a verified verdict.
Summarize the role and skills if available. Explain the signals and missing information below, then give a safe verification checklist: independently find official careers site, verify recruiter using contact details found independently, read written terms, never pay to secure selection, never share OTP/password/bank PIN.
Rule-based signals: {json.dumps(a)}
Message: {text[:9000]}"""
 answer,error=groq(SYSTEM,p)
 return a,answer,error


def config_value(name, default=""):
    """Read configuration from environment/.env or Streamlit Cloud secrets."""
    value = os.getenv(name, default)
    try:
        if not value and name in st.secrets:
            value = st.secrets[name]
    except Exception:
        pass
    return str(value).strip()

SUPABASE_URL = config_value("SUPABASE_URL")
SUPABASE_ANON_KEY = config_value("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    st.title("🛡️ InternShield AI")
    st.error("Authentication setup is incomplete.")
    st.markdown(
        "Add `SUPABASE_URL` and `SUPABASE_ANON_KEY` to your local `.env` file "
        "or Streamlit Cloud secrets. Do not put secret keys or passwords in your source code."
    )
    st.stop()

try:
    sb = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
except Exception:
    st.error("Could not initialize Supabase. Check SUPABASE_URL and SUPABASE_ANON_KEY.")
    st.stop()

if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None

if not st.session_state.user_id:
    st.markdown('<div class="brand">STUDENT OPPORTUNITY SAFETY AGENT</div>', unsafe_allow_html=True)
    st.title("🛡️ InternShield AI")
    st.write("Sign in to review recruitment offers and keep your review history private.")
    login_tab, signup_tab = st.tabs(["Log in", "Create account"])

    with login_tab:
        with st.form("login_form"):
            login_email = st.text_input("Email address", key="login_email")
            login_password = st.text_input("Password", type="password", key="login_password")
            login_submit = st.form_submit_button("Log in", type="primary", use_container_width=True)
        if login_submit:
            try:
                result = sb.auth.sign_in_with_password({
                    "email": login_email.strip(),
                    "password": login_password
                })
                if result.user:
                    st.session_state.user_id = result.user.id
                    st.session_state.user_email = result.user.email
                    st.rerun()
                else:
                    st.error("Login failed. Check your details and try again.")
            except Exception:
                st.error("Login failed. Check your email and password. If you just registered, confirm your email first.")

    with signup_tab:
        with st.form("signup_form"):
            signup_email = st.text_input("Email address", key="signup_email")
            signup_password = st.text_input("Password (at least 8 characters)", type="password", key="signup_password")
            signup_confirm = st.text_input("Confirm password", type="password", key="signup_confirm")
            signup_submit = st.form_submit_button("Create account", type="primary", use_container_width=True)
        if signup_submit:
            if not signup_email.strip() or "@" not in signup_email:
                st.error("Enter a valid email address.")
            elif len(signup_password) < 8:
                st.error("Use a password with at least 8 characters.")
            elif signup_password != signup_confirm:
                st.error("The passwords do not match.")
            else:
                try:
                    result = sb.auth.sign_up({
                        "email": signup_email.strip(),
                        "password": signup_password
                    })
                    if result.session and result.user:
                        st.session_state.user_id = result.user.id
                        st.session_state.user_email = result.user.email
                        st.success("Account created.")
                        st.rerun()
                    else:
                        st.success("Account created. Check your email for a confirmation link, then log in.")
                except Exception:
                    st.error("Registration failed. The email may already be registered, or Supabase settings need checking.")
    st.caption("Use a unique password. InternShield AI will not store your password in its own database.")
    st.stop()

USER_ID = st.session_state.user_id

def read_history():
    """Fetch only the signed-in user's reviews from Supabase."""
    try:
        response = sb.table("saved_reviews").select("data").eq("user_id", USER_ID).order("created_at", desc=True).execute()
        return [row["data"] for row in (response.data or []) if isinstance(row.get("data"), dict)]
    except Exception:
        # Keep the dashboard clean if saved-review storage is not configured yet.
        return []

def write_history(reviews):
    """Replace the signed-in user's review history only."""
    try:
        sb.table("saved_reviews").delete().eq("user_id", USER_ID).execute()
        if reviews:
            rows = [{"user_id": USER_ID, "data": review} for review in reviews]
            sb.table("saved_reviews").insert(rows).execute()
    except Exception:
        st.error("Could not save review history. Check the Supabase table and row-level security policy.")


st.sidebar.markdown('<div class="brand">INTERN SHIELD</div>',unsafe_allow_html=True)
st.sidebar.markdown("### Saved reviews")
st.sidebar.caption("Signed in as: " + str(st.session_state.get("user_email", "")))
if st.sidebar.button("Log out", use_container_width=True):
    try:
        sb.auth.sign_out()
    except Exception:
        pass
    st.session_state.user_id = None
    st.session_state.user_email = None
    st.session_state.active = None
    st.session_state.latest = None
    st.session_state.chat = []
    st.rerun()
if st.sidebar.button("＋ New review",use_container_width=True,type="primary"): st.session_state.active=None; st.rerun()
reviews=read_history()
for r in sorted(reviews,key=lambda x:x.get("date",""),reverse=True)[:20]:
 if st.sidebar.button("🛡️ "+r["title"][:32],key=r["id"],use_container_width=True): st.session_state.active=r["id"]; st.rerun()
st.sidebar.caption("Your reviews are stored in your account. No live company verification is performed.")
if st.sidebar.button("Delete all reviews"):
 write_history([]); st.session_state.active=None; st.rerun()

st.markdown('<div class="brand">STUDENT OPPORTUNITY SAFETY AGENT</div><h1>🛡️ InternShield AI</h1><p style="color:#aeb9ce">Check the warning signs. Understand the offer. Know what to verify next.</p>',unsafe_allow_html=True)
st.info("This tool screens text for warning signs; it does not browse the web or prove an offer is genuine or fraudulent. Verify independently.")
active=st.session_state.get("active")
selected=next((r for r in reviews if r["id"]==active),None)
if selected:
 st.header(selected["title"])
 x,y,z=st.columns(3); x.metric("Rule-based score",f'{selected["assessment"]["score"]}/100'); y.metric("Screening signal",selected["assessment"]["label"]); z.metric("Signals",len(selected["assessment"]["flags"]))
 st.markdown(selected["review"])
 with st.expander("Detected signals / missing details"):
  for f in selected["assessment"]["flags"]: st.write(f'• **{f["name"]} (+{f["weight"]})** — {f["why"]}')
  for m in selected["assessment"]["missing"]: st.write("• "+m)
 if st.button("Back to new review"): st.session_state.active=None; st.rerun()
else:
 tab1,tab2=st.tabs(["🔎 Review an opportunity","💬 Ask InternShield"])
 with tab1:
  if "offer_text" not in st.session_state:
   st.session_state.offer_text = ""
  offer_examples = [
   "Congratulations! You are selected for a data science internship. Pay a refundable registration and training fee of ₹2,999 today to confirm your seat. Guaranteed placement, no interview required. Message us on WhatsApp only.",
   "BrightPath Analytics is inviting applications for a 3-month remote Data Analyst internship. Work includes Excel, SQL, and Python dashboards with a mentor. Apply through the official careers portal; shortlisted candidates complete a technical interview. Stipend: ₹12,000 per month. Verify the company and supervisor independently.",
   "URGENT: You are selected for a work-from-home AI internship paying ₹45,000 per month. No interview or experience needed. Pay ₹1,499 for a refundable onboarding kit within 2 hours or lose your seat. Send money to a personal UPI ID and share the screenshot on Telegram.",
   "Northstar Digital Labs is hiring a Software Engineering Intern for 12 weeks. Responsibilities include fixing bugs, writing unit tests, and participating in code reviews. Submit your resume and GitHub profile through the company careers page. Selection includes a coding task and interview.",
   "FINAL REMINDER: Guaranteed placement at a top MNC after our 5-day internship course. Pay a ₹5,000 certificate and processing fee today. No interview, no assessment, 100% job guarantee. Contact only this WhatsApp number. Limited seats; payment is non-refundable after 30 minutes.",
   "Greenfield Media is inviting applications for a Marketing Intern for 10 weeks. Work includes social media research, campaign reporting, and content planning. A video interview is required. Check the official website for the role description, supervisor contact, stipend, and company registration details. No payment is required to apply."
  ]
  if st.button("Load a random example offer"):
   import random
   choices = [sample for sample in offer_examples if sample != st.session_state.offer_text]
   st.session_state.offer_text = random.choice(choices or offer_examples)
  text=st.text_area("Paste an internship/job offer or recruitment message. Remove personal details first.",key="offer_text",height=200,placeholder="Paste the message here…")
  if st.button("Analyze opportunity",type="primary",use_container_width=True):
   if len(text.strip())<25: st.warning("Paste a little more text to analyze.")
   else:
    with st.spinner("Analyzing warning signs and preparing verification steps…"): a,review,error=analyze(text.strip())
    if error: st.error(error)
    else: st.session_state.latest={"text":text.strip(),"assessment":a,"review":review}; st.rerun()
  latest=st.session_state.get("latest")
  if latest:
   st.divider(); st.subheader("Screening result")
   a=latest["assessment"]; x,y,z=st.columns(3); x.metric("Rule-based score",f'{a["score"]}/100'); y.metric("Screening signal",a["label"]); z.metric("Warning signs",len(a["flags"]))
   st.caption("This score is based on visible text patterns; it is not a probability of fraud.")
   if a["flags"]:
    st.markdown("#### Detected signals")
    for f in a["flags"]: st.markdown(f'- **{f["name"]} (+{f["weight"]})** — {f["why"]}')
   else: st.success("No major warning patterns matched. This does not prove legitimacy.")
   for m in a["missing"]: st.markdown("- ℹ️ "+m)
   st.markdown("#### AI review & next steps"); st.markdown(latest["review"])
   if st.button("Save review to history",use_container_width=True):
    allr=read_history(); allr.append({"id":str(uuid.uuid4()),"title":re.sub(r"\s+"," ",latest["text"])[:38],"date":datetime.now().isoformat(timespec="seconds"),"assessment":a,"review":latest["review"],"text":latest["text"]}); write_history(allr); st.session_state.latest=None; st.success("Saved. Open it from the sidebar."); st.rerun()
 with tab2:
  st.caption("Ask what to verify before accepting an offer or how to spot suspicious recruitment practices.")
  if "chat" not in st.session_state: st.session_state.chat=[]
  for m in st.session_state.chat:
   with st.chat_message(m["role"]): st.markdown(m["content"])
  q=st.chat_input("Ask a recruitment-safety question…")
  if q:
   prior=st.session_state.chat.copy(); st.session_state.chat.append({"role":"user","content":q})
   with st.chat_message("user"): st.markdown(q)
   with st.chat_message("assistant"):
    with st.spinner("Thinking…"): ans,err=groq(SYSTEM,q,prior)
    if err: st.error(err); ans=err
    else: st.markdown(ans)
   st.session_state.chat.append({"role":"assistant","content":ans}); st.rerun()
st.divider()
st.caption("Privacy: review history is stored under your account. Do not paste passwords, OTPs, bank credentials, or sensitive identity documents.")
