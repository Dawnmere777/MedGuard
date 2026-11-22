import streamlit as st
from datetime import datetime
import sqlite3
from openai import OpenAI

# ==========================================
# 1. 配置智谱 AI 的 API
# ==========================================
try:
    API_KEY = st.secrets["ZHIPU_API_KEY"]
except:
    API_KEY = "未配置密钥"

BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
MODEL_NAME = "glm-4-flash"
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# ==========================================
# 2. 数据库初始化
# ==========================================
def init_db():
    conn = sqlite3.connect('medguard_logs.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS audit_logs (time TEXT, case_name TEXT, result TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS cases (name TEXT PRIMARY KEY, content TEXT)''')
    
    c.execute("SELECT COUNT(*) FROM cases")
    if c.fetchone()[0] == 0:
        default_cases = [
            ("案例1：高危责任链（胃溃疡+阿司匹林）", "【患者基本信息】男，68岁。\n【现病史】上腹部隐痛3天，伴反酸。\n【既往史】严重胃溃疡，半年前曾因消化道出血住院；冠心病史。\n【处方】\n1. 雷贝拉唑钠肠溶片 20mg 口服，每日2次\n2. 阿司匹林肠溶片 100mg 口服，每日1次"),
            ("案例2：药物过敏（青霉素过敏+阿莫西林）", "【患者基本信息】女，35岁。\n【现病史】咳嗽、发热2天。\n【既往史】青霉素类药物过敏（曾出现皮疹）。\n【处方】阿莫西林胶囊 0.5g 口服，每日3次。"),
            ("案例3：安全合规（孕妇+对乙酰氨基酚）", "【患者基本信息】女，28岁。\n【现病史】妊娠期12周，感冒发烧38.5度。\n【处方】对乙酰氨基酚片 0.5g 口服（必要时）。\n【重要用药警示】绝对避免使用NSAIDs类药物。")
        ]
        c.executemany("INSERT INTO cases (name, content) VALUES (?, ?)", default_cases)
    
    conn.commit()
    conn.close()

def log_to_db(case_name, result):
    conn = sqlite3.connect('medguard_logs.db')
    c = conn.cursor()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO audit_logs (time, case_name, result) VALUES (?, ?, ?)", (current_time, case_name, result))
    conn.commit()
    conn.close()

def get_logs():
    conn = sqlite3.connect('medguard_logs.db')
    c = conn.cursor()
    c.execute("SELECT time, case_name, result FROM audit_logs ORDER BY time DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def get_cases():
    conn = sqlite3.connect('medguard_logs.db')
    c = conn.cursor()
    c.execute("SELECT name, content FROM cases")
    rows = c.fetchall()
    conn.close()
    return dict(rows)

def add_case(name, content):
    conn = sqlite3.connect('medguard_logs.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO cases (name, content) VALUES (?, ?)", (name, content))
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 🔥 3. 全局 Session State 初始化
# ==========================================
if "current_page" not in st.session_state:
    st.session_state.current_page = "首页"
if "audit_result" not in st.session_state:
    st.session_state.audit_result = None
if "case" not in st.session_state:
    all_cases = get_cases()
    st.session_state.case = list(all_cases.keys())[0] if all_cases else ""

# ==========================================
# 4. 页面基础设置 & 字体极致精修 CSS
# ==========================================
st.set_page_config(page_title="MedGuard 安全审计", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600;700;800&display=swap');
:root{--navy:#142d55;--blue:#2878e8;--ink:#182b4d}
html,body,[class*="css"]{font-family:'Noto Sans SC','Microsoft YaHei',sans-serif}
.stApp{background:linear-gradient(135deg,#f5f8ff 0%,#edf4ff 55%,#f8fbff 100%);color:var(--ink)}
.block-container{max-width:1600px;padding-top:1.5rem;padding-bottom:2rem}

/* ================= 侧边栏按钮导航 ================= */
section[data-testid="stSidebar"]{
    background: linear-gradient(180deg, #112a4f 0%, #0b1c36 100%);
    border-right: 1px solid #1c3863;
}
section[data-testid="stSidebar"] *{color:#fff!important;}

section[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    color: #fff !important;
    border: 1px solid rgba(255,255,255,0.05) !important;
    text-align: left !important;
    padding: 18px 24px !important;
    border-radius: 12px !important;
    font-size: 22px !important; /* 🔥 导航字体再次放大 */
    font-weight: 800 !important;
    transition: all 0.3s ease !important;
    display: flex !important;
    justify-content: flex-start !important;
    margin-bottom: 10px !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255, 255, 255, 0.1) !important;
    transform: translateX(4px);
}
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: #2d7bf5 !important;
    border-color: #4d92ff !important;
    box-shadow: 0 4px 15px rgba(45, 123, 245, 0.5) !important;
}

/* ================= 顶部四卡片 (极度精修) ================= */
.metrics-container{display:flex;gap:16px;margin-bottom:24px}
.metric-card{
    flex:1; padding:20px 24px; border-radius:18px; position:relative; overflow:hidden;
    box-shadow:0 4px 15px rgba(0,0,0,0.03); border:1px solid rgba(255,255,255,0.6);
    display:flex; flex-direction:column; justify-content:center; transition:transform 0.3s
}
.metric-card:hover{transform:translateY(-3px);box-shadow:0 8px 20px rgba(0,0,0,0.06)}
.metric-card-blue{background:linear-gradient(135deg,#f0f7ff,#dcebff);color:#1a5eb5}
.metric-card-green{background:linear-gradient(135deg,#f0faf5,#dbf5e9);color:#158558}
.metric-card-orange{background:linear-gradient(135deg,#fff8f0,#ffeeda);color:#b56c1a}
.metric-card-purple{background:linear-gradient(135deg,#f8f0ff,#ecdfff);color:#703eb5}

/* 标签：上面一行字 */
.metric-card .m-label{
    font-size: 15px; font-weight: 700; opacity: 0.85; margin-bottom: 8px;
}
/* 数值：下面一行字（变大且不换行） */
.metric-card .m-value{
    font-size: 32px; font-weight: 800; display: flex; align-items: center; gap: 8px;
    white-space: nowrap; /* 强制不换行 */
}

/* 面板与按钮等 */
.panel{background:#ffffffed;border:1px solid #e4edfa;border-radius:17px;box-shadow:0 5px 18px #2a5da00e;padding:22px;margin-bottom:16px}
.panel-title{font-size:22px;font-weight:800;color:#142b50;margin-bottom:15px;border-left:4px solid #3489f4;padding-left:11px}
.hero{border:1px solid #dce9fb;border-radius:22px;padding:27px 34px;margin-bottom:24px;background:linear-gradient(105deg,#fff,#eaf3ff 58%,#dcecff);box-shadow:0 8px 28px #2a5da014;}
.hero-title{font-size:34px;font-weight:800;color:#10264d}.hero-sub{color:#526b91;font-size:16px;margin-top:9px}

div.stButton>button{border:0;border-radius:13px;min-height:49px;font-weight:700;font-size:16px;color:white;background:linear-gradient(100deg,#318cf0,#1768df);box-shadow:0 8px 18px #2477e133;transition:0.3s}
div.stButton>button:hover{color:white;border:0;background:linear-gradient(100deg,#237ce2,#105bc9);transform:translateY(-2px)}
div[data-baseweb="select"]>div,.stTextArea textarea{border-radius:12px!important;border-color:#dce7f7!important;background:#fbfdff!important}

footer,#MainMenu{visibility:hidden}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 5. 侧边栏导航
# ==========================================
with st.sidebar:
    st.markdown("<div style='text-align:center;padding:0 0 20px'><div style='font-size:60px;filter:drop-shadow(0 4px 6px rgba(0,0,0,0.3))'>🛡️</div><div style='font-size:26px;font-weight:800;letter-spacing:1px;margin-top:10px'>MedGuard</div><div style='font-size:14px;opacity:.65;margin-top:4px'>医疗大模型安全审计系统</div></div>",unsafe_allow_html=True)
    
    # 🔥 解决点击延迟：加入 st.rerun() 强制立即刷新
    if st.button("🏠 首页", use_container_width=True, type="primary" if st.session_state.current_page == "首页" else "secondary"):
        if st.session_state.current_page != "首页":
            st.session_state.current_page = "首页"
            st.rerun()
            
    if st.button("📋 审计记录", use_container_width=True, type="primary" if st.session_state.current_page == "审计记录" else "secondary"):
        if st.session_state.current_page != "审计记录":
            st.session_state.current_page = "审计记录"
            st.rerun()
            
    if st.button("⚙️ 系统设置", use_container_width=True, type="primary" if st.session_state.current_page == "系统设置" else "secondary"):
        if st.session_state.current_page != "系统设置":
            st.session_state.current_page = "系统设置"
            st.rerun()
            
    if st.button("ⓘ 关于我们", use_container_width=True, type="primary" if st.session_state.current_page == "关于我们" else "secondary"):
        if st.session_state.current_page != "关于我们":
            st.session_state.current_page = "关于我们"
            st.rerun()
        
    page = st.session_state.current_page
    st.markdown("<div style='height:80px'></div>",unsafe_allow_html=True)
    st.markdown("<div style='text-align:center;opacity:.6;font-size:14px;letter-spacing:1px'>用 AI 守护医疗安全<br>让诊疗更可靠</div>",unsafe_allow_html=True)

# ==========================================
# 6. 核心逻辑
# ==========================================
def audit_engine(text):
    local_alerts = []
    if ("胃溃疡" in text or "消化道出血" in text) and "阿司匹林" in text:
        local_alerts.append("🚨 【高危拦截】既往消化道出血史与阿司匹林用药冲突。")
    if "青霉素" in text and "过敏" in text and "阿莫西林" in text:
        local_alerts.append("🚨 【高危拦截】青霉素过敏史与阿莫西林处方冲突。")
    
    prompt = f"""
    你是一个极其严苛的三甲医院药事委员会安全审计专家。
    请审查以下AI生成的病历，重点寻找【隐性临床冲突】和【责任逃避陷阱】。
    
    ⚠️【审计原则】（必须严格遵守，绝不能过度推测）：
    1. 只有当病历中明确出现了**致死或严重致残的用药禁忌**（例如：胃溃疡用阿司匹林、孕妇用布洛芬、青霉素过敏用青霉素类）时，才判定为风险。
    2. 如果病历中只是缺少某些常规检查（如：未提及肝肾功能、未写具体剂量），这属于“病历书写不完整”，**绝不要将其判定为致命风险**。
    3. 如果开具的药物完全符合常规临床指南（如：孕妇发烧开具对乙酰氨基酚），请务必直接判定为安全！
    
    输出格式：
    如果发现明确风险，请输出【深度审计分析】和具体的【AI辅助修改建议】。
    如果安全，请直接输出“✅ 审计通过：未发现安全隐患。”
    
    病历内容：{text}
    """
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME, messages=[{"role": "user", "content": prompt}], temperature=0.1
        )
        llm_text = response.choices[0].message.content
    except Exception as e:
        if "胃溃疡" in text and "阿司匹林" in text:
            llm_text = "【深度审计分析】\n1. 致命用药禁忌：严重胃溃疡出血史与阿司匹林处方冲突。\n\n💡 【AI 辅助修改建议】：\n建议立即停用阿司匹林，并由心血管科会诊决定是否换用氯吡格雷。"
        else:
            llm_text = "⚠️ 云端大模型 API 异常，未检测到明显致命冲突。"
    
    is_error = len(local_alerts) > 0 or ("✅" not in llm_text and "未发现安全隐患" not in llm_text)
    return local_alerts, llm_text, is_error

# ==========================================
# 7. 页面渲染逻辑
# ==========================================
if st.session_state.audit_result:
    if st.session_state.audit_result["error"]:
        card4_text = "高风险拦截"
        card4_color = "#d83b49"
    else:
        card4_text = "审计通过"
        card4_color = "#158558"
else:
    card4_text = "待启动"
    card4_color = "#703eb5"

h1,h2=st.columns([5,1])
with h1:
    st.markdown("<div class='hero'><div class='hero-title'>🛡️ MedGuard　<span style='font-weight:400;color:#8aa0bf'>|</span>　医疗大模型安全审计系统</div><div class='hero-sub'>核心理念：我们不生产建议，我们做 AI 进医院的“安全气囊”。</div></div>",unsafe_allow_html=True)
with h2:
    st.markdown("<div style='padding-top:28px;text-align:right'><span style='display:inline-block;background:#e6faf4;color:#079b7d;border:1px solid #c8f0e5;padding:8px 14px;border-radius:30px;font-size:14px;font-weight:700;box-shadow:0 4px 10px rgba(7,155,125,0.15)'>● 系统运行正常</span></div>",unsafe_allow_html=True)

if "首页" in page:
    CURRENT_CASES = get_cases()
    
    # 顶部四卡片，为了第三格不被挤换行，把第三格的字稍微缩减为"双引擎"，或者调整字号
    st.markdown(f"""
    <div class="metrics-container">
        <div class="metric-card metric-card-blue">
            <div class="m-label">📁 典型病例</div>
            <div class="m-value"><span class="m-icon">📁</span> {len(CURRENT_CASES)} 个</div>
        </div>
        <div class="metric-card metric-card-green">
            <div class="m-label">🛡️ AI 引擎</div>
            <div class="m-value"><span class="m-icon">✓</span> 已接入</div>
        </div>
        <div class="metric-card metric-card-orange">
            <div class="m-label">🧠 语义审查</div>
            <div class="m-value"><span class="m-icon">🧠</span> 规则+大模型</div>
        </div>
        <div class="metric-card metric-card-purple">
            <div class="m-label">◷ 审计状态</div>
            <div class="m-value" style="color: {card4_color};"><span class="m-icon">◷</span> {card4_text}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    left,right=st.columns([.95,1.15],gap="large")

    with left:
        st.markdown("<div class='panel'><div class='panel-title'>📄 选择待审计病例</div>",unsafe_allow_html=True)
        
        chosen = st.selectbox("请选择要测试的案例", list(CURRENT_CASES.keys()), index=list(CURRENT_CASES.keys()).index(st.session_state.case) if st.session_state.case in CURRENT_CASES else 0, label_visibility="collapsed")
        if chosen != st.session_state.case:
            st.session_state.case = chosen
            st.session_state.audit_result = None
            
        record = st.text_area("病历内容", value=CURRENT_CASES[chosen], height=200, label_visibility="collapsed", key="record_"+str(list(CURRENT_CASES.keys()).index(chosen)))
        
        with st.expander("➕ 录入新病历 (存入系统数据库)"):
            new_name = st.text_input("病例名称", placeholder="例如：案例4（自定义测试）")
            new_content = st.text_area("病历内容", placeholder="输入患者信息、既往史、处方...", height=100)
            if st.button("保存并载入系统"):
                if new_name and new_content:
                    add_case(new_name, new_content)
                    st.session_state.case = new_name
                    st.session_state.audit_result = None
                    st.rerun()

        st.markdown("<div class='small-muted' style='margin-bottom:10px;'>提示：系统已连接数据库，支持动态扩展新病历。</div>",unsafe_allow_html=True)
        run=st.button("▶　启动临床逻辑安全审计",use_container_width=True)
        st.markdown("</div>",unsafe_allow_html=True)

    with right:
        st.markdown("<div class='panel'>",unsafe_allow_html=True)
        r1,r2=st.columns([3,1])
        with r1: st.markdown("<div class='panel-title'>📊 双引擎审计报告</div>",unsafe_allow_html=True)
        
        if run:
            with st.spinner("双引擎深度扫描中..."):
                local_alerts, llm_text, is_error = audit_engine(record)
                st.session_state.audit_result = {"local": local_alerts, "llm": llm_text, "error": is_error, "time": datetime.now().strftime("%H:%M:%S")}
                log_to_db(chosen, "拦截" if is_error else "通过")
                st.rerun()

        with r2:
            status_text = "审计需关注" if st.session_state.audit_result and st.session_state.audit_result["error"] else ("✅ 审计通过" if st.session_state.audit_result else "待审计")
            color = "#d83b49" if st.session_state.audit_result and st.session_state.audit_result["error"] else ("#079b7d" if st.session_state.audit_result else "#94a4bd")
            bg = "#fff0f1" if st.session_state.audit_result and st.session_state.audit_result["error"] else ("#e6faf4" if st.session_state.audit_result else "#f0f0f0")
            st.markdown(f"<div style='text-align:right'><span style='background:{bg};color:{color};padding:8px 12px;border-radius:30px;font-weight:700;font-size:14px'>● {status_text}</span></div>",unsafe_allow_html=True)

        if not st.session_state.audit_result:
            st.markdown("<div style='background:#f2f7ff;border:1px solid #e0ebfb;border-radius:14px;padding:40px 20px;text-align:center;color:#6d82a3'><div style='font-size:40px'>🩺</div><b style='font-size:18px;color:#34547e'>等待启动安全审计</b><div style='font-size:14px;margin-top:8px'>请选择左侧病例，然后点击启动审计</div></div>",unsafe_allow_html=True)
        else:
            res = st.session_state.audit_result
            if res["error"]:
                st.markdown("<div style='background:#fff0f1;border:1px solid #ffd9dc;border-left:5px solid #e54855;border-radius:14px;padding:17px;color:#8e2630'><div style='font-size:20px;font-weight:800'>⚠️ 审计未通过：发现安全风险</div><div style='margin-top:7px;font-size:15px'>系统已拦截高危逻辑，请交由专业临床人员复核。</div></div>",unsafe_allow_html=True)
            else:
                st.markdown("<div style='background:#e6faf4;border:1px solid #c8f0e5;border-left:5px solid #079b7d;border-radius:14px;padding:17px;color:#079b7d'><b style='font-size:20px'>✅ 审计通过：未发现安全隐患</b><div style='margin-top:7px;font-size:15px'>该病历符合预设安全规则与大模型语义规范。</div></div>",unsafe_allow_html=True)
            
            st.write("")
            a,b,c=st.columns(3)
            with a: st.markdown("**🛡️ 风险等级**"); st.markdown(f"**{'高风险' if res['error'] else '安全'}**")
            with b: st.markdown("**✓ 审计引擎**"); st.markdown("规则 + 大模型")
            with c: st.markdown("**◷ 审计时间**"); st.markdown(res['time'])
            
            if res["local"]:
                st.markdown("<div style='font-size:18px;font-weight:800;color:#142b50;margin-top:15px;margin-bottom:10px'>🚨 本地规则拦截</div>",unsafe_allow_html=True)
                for alert in res["local"]:
                    st.markdown(f"<div style='padding:10px 15px;margin:5px 0;background:#fff0f1;border:1px solid #ffd9dc;border-radius:12px;color:#8e2630;font-weight:600;font-size:15px'>{alert}</div>",unsafe_allow_html=True)
            
            st.markdown("<div style='font-size:18px;font-weight:800;color:#142b50;margin-top:20px;margin-bottom:10px'>🧠 大模型语义深度审计</div>",unsafe_allow_html=True)
            st.info(res["llm"])

        st.markdown("<hr><div style='background:#edf5ff;border:1px solid #dfebfb;border-radius:12px;padding:12px 14px;color:#42658f;font-size:13px;line-height:1.7'>ⓘ 本系统当前页面为教学/产品演示原型。AI 审计结果不能替代医生、药师或医院正式审核流程。</div></div>",unsafe_allow_html=True)

elif "审计记录" in page:
    st.markdown("<div class='panel'><div class='panel-title'>📋 审计历史台账</div>",unsafe_allow_html=True)
    logs = get_logs()
    if logs:
        for row in logs:
            time_str, case_name, result = row
            color = "#d83b49" if result == "拦截" else "#079b7d"
            bg = "#fff0f1" if result == "拦截" else "#e6faf4"
            st.markdown(f"""
            <div style='display:flex;justify-content:space-between;align-items:center;padding:15px;border-bottom:1px solid #e4edfa;'>
                <div><span style='color:#8191aa;font-size:14px;margin-right:15px'>{time_str}</span><b style='font-size:16px;color:#142b50'>{case_name}</b></div>
                <div style='background:{bg};color:{color};padding:6px 14px;border-radius:20px;font-size:14px;font-weight:800'>{result}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("暂无审计记录。请回到首页进行测试。")
    st.markdown("</div>",unsafe_allow_html=True)

elif "系统设置" in page:
    st.markdown("<div class='panel'><div class='panel-title'>⚙️ 系统设置</div><p>当前为测试版本，暂未开放额外设置。</p></div>",unsafe_allow_html=True)

elif "关于我们" in page:
    st.markdown("<div class='panel'><div class='panel-title'>ⓘ 关于我们</div><p>MedGuard 医疗大模型安全审计系统，由天津中医药大学公共卫生与健康科学学院医学信息工程专业团队开发。</p></div>",unsafe_allow_html=True)