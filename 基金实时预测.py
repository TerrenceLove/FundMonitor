import streamlit as st
import requests
import json
import time
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import warnings

# 忽略警告
warnings.filterwarnings('ignore')

# --- 1. 页面基础配置 (移动端适配) ---
st.set_page_config(page_title="Gemini 多基金智能对账单 Pro", layout="centered")

# --- 2. 初始化实时折线图数据存储 ---
# 只要浏览器不刷新（Session 存在），数据就会一直累积
if 'history_data' not in st.session_state:
    st.session_state.history_data = pd.DataFrame(columns=['time', 'total_profit'])

# --- 3. 核心数据抓取函数 ---
def get_fund_realtime(code):
    """从接口抓取实时估值、名称和涨跌幅"""
    url = f"http://fundgz.1234567.com.cn/js/{code}.js?rt={int(time.time())}"
    try:
        res = requests.get(url, timeout=5)
        content = res.text
        json_str = content[content.find('{'):content.rfind('}')+1]
        data = json.loads(json_str)
        return {
            "name": data['name'],       # 基金名称
            "est_rate": float(data['gszzl']), # 实时涨跌幅 (%)
            "est_nav": float(data['gsz']),   # 实时估值净值
            "update_time": data['gztime']    # 估值更新时间
        }
    except:
        return None

# --- 4. 主界面显示 ---
st.title("🛡️ Gemini 多基金智能看板 Pro")
st.caption(f"数据实时同步中 | 当前时间: {datetime.now().strftime('%H:%M:%S')}")

# 检查 Secrets 配置
if "funds" not in st.secrets:
    st.error("❌ 未在后台发现 [[funds]] 配置，请检查 Streamlit Secrets。")
    st.stop()

funds_list = st.secrets["funds"]

# 汇总变量
total_principal = 0.0
total_current_profit = 0.0

# --- 5. 循环处理每一个基金 ---
for fund in funds_list:
    f_code = fund["code"]
    f_p = float(fund["principal"])
    f_init_profit = float(fund["init_profit"])
    
    realtime = get_fund_realtime(f_code)
    
    if realtime:
        # 核心盈亏计算
        day_profit = (f_p + f_init_profit) * (realtime['est_rate'] / 100)
        total_profit = f_init_profit + day_profit
        total_value = f_p + total_profit
        
        # 累加到总账户
        total_principal += f_p
        total_current_profit += total_profit
        
        with st.expander(f"📈 {realtime['name']} ({f_code})", expanded=True):
            c1, c2, c3 = st.columns(3)
            c1.metric("实时估值", f"{realtime['est_nav']:.4f}")
            c2.metric("估值涨跌", f"{realtime['est_rate']}%")
            c3.metric("今日损益", f"¥{day_profit:,.2f}")
            
            col1, col2 = st.columns(2)
            col1.write(f"**累计收益:** ¥{total_profit:,.2f}")
            col2.write(f"**更新时间:** {realtime['update_time']}")
    else:
        st.warning(f"⚠️ 基金 {f_code} 请求超时。")

# --- 6. 记录历史数据 (用于折线图) ---
now_time = datetime.now().strftime('%H:%M:%S')
new_record = pd.DataFrame({
    'time': [now_time], 
    'total_profit': [round(total_current_profit, 2)]
})
# 避免重复记录同一秒的数据
if st.session_state.history_data.empty or st.session_state.history_data.iloc[-1]['time'] != now_time:
    st.session_state.history_data = pd.concat([st.session_state.history_data, new_record], ignore_index=True)

# --- 7. 底部全账户资产汇总 ---
st.markdown("---")
st.subheader("💰 总资产概览")

m1, m2, m3 = st.columns(3)
m1.metric("总投入本金", f"¥{total_principal:,.2f}")
total_rate = (total_current_profit / total_principal * 100) if total_principal > 0 else 0
m2.metric("累计总盈亏", f"¥{total_current_profit:,.2f}", f"{total_rate:.2f}%")
m3.metric("实时总市值", f"¥{(total_principal + total_current_profit):,.2f}")

# --- 8. 实时收益折线图 (重点功能) ---
st.markdown("---")
with st.expander("📈 全账户实时收益趋势 (点击展开/收起)", expanded=True):
    if len(st.session_state.history_data) > 1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=st.session_state.history_data['time'], 
            y=st.session_state.history_data['total_profit'],
            mode='lines+markers',
            name='总收益 (元)',
            line=dict(color='#FF4B4B', width=3),
            marker=dict(size=6)
        ))
        fig.update_layout(
            margin=dict(l=0, r=0, t=10, b=0),
            height=300,
            xaxis_title="监控时间",
            yaxis_title="总收益 (元)",
            hovermode="x unified",
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("💡 正在记录首个数据点，请点击下方刷新按钮或保持页面开启。")

# --- 9. 操作按钮 ---
col_btn1, col_btn2 = st.columns(2)
if col_btn1.button("🔄 同步行情", use_container_width=True):
    st.rerun()
if col_btn2.button("🗑️ 重置图表", use_container_width=True):
    st.session_state.history_data = pd.DataFrame(columns=['time', 'total_profit'])
    st.rerun()

st.caption("注：折线图数据仅在当前浏览器会话中有效。")
