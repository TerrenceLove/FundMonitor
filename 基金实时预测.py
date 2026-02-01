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

# --- 1. 页面基础配置 ---
st.set_page_config(page_title="Gemini 基金独立走势看板", layout="centered")

# --- 2. 初始化独立历史数据存储 (字典格式) ---
# 格式为: { "基金代码": DataFrame(time, rate) }
if 'fund_histories' not in st.session_state:
    st.session_state.fund_histories = {}

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
            "name": data['name'],       
            "est_rate": float(data['gszzl']), # 实时涨跌幅 (%)
            "est_nav": float(data['gsz']),   
            "update_time": data['gztime']    
        }
    except:
        return None

# --- 4. 主界面显示 ---
st.title("🛡️ Gemini 基金独立走势看板")
st.caption(f"数据更新于: {datetime.now().strftime('%H:%M:%S')}")

# 检查 Secrets 配置
if "funds" not in st.secrets:
    st.error("❌ 未在后台发现 [[funds]] 配置，请检查 Streamlit Secrets。")
    st.stop()

funds_list = st.secrets["funds"]

# 汇总变量
total_principal = 0.0
total_current_profit = 0.0
now_time = datetime.now().strftime('%H:%M:%S')

# --- 5. 循环处理每一个基金 ---
for fund in funds_list:
    f_code = fund["code"]
    f_p = float(fund["principal"])
    f_init_profit = float(fund["init_profit"])
    
    realtime = get_fund_realtime(f_code)
    
    if realtime:
        # --- 数据记录逻辑 ---
        # 如果是新基金，初始化其历史记录
        if f_code not in st.session_state.fund_histories:
            st.session_state.fund_histories[f_code] = pd.DataFrame(columns=['time', 'rate'])
        
        # 记录当前涨跌幅
        new_entry = pd.DataFrame({'time': [now_time], 'rate': [realtime['est_rate']]})
        hist_df = st.session_state.fund_histories[f_code]
        
        # 避免重复记录同一秒数据
        if hist_df.empty or hist_df.iloc[-1]['time'] != now_time:
            st.session_state.fund_histories[f_code] = pd.concat([hist_df, new_entry], ignore_index=True)
            hist_df = st.session_state.fund_histories[f_code] # 更新局部变量

        # 核心盈亏计算
        day_profit = (f_p + f_init_profit) * (realtime['est_rate'] / 100)
        total_profit = f_init_profit + day_profit
        
        # 汇总到总账
        total_principal += f_p
        total_current_profit += total_profit
        
        # --- UI 显示 ---
        with st.expander(f"📈 {realtime['name']} ({f_code}) - 当前: {realtime['est_rate']}%", expanded=True):
            # 顶部指标
            c1, c2, c3 = st.columns(3)
            c1.metric("今日涨跌", f"{realtime['est_rate']}%")
            c2.metric("今日损益", f"¥{day_profit:,.2f}")
            c3.metric("累计收益", f"¥{total_profit:,.2f}")
            
            # 每一个基金独有的折线图 (再次嵌套一个 expander 实现隐藏)
            with st.expander("📊 查看实时涨跌走势", expanded=False):
                if len(hist_df) > 1:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=hist_df['time'], 
                        y=hist_df['rate'],
                        mode='lines+markers',
                        name='涨跌幅 (%)',
                        line=dict(color='#1E88E5', width=2),
                        hovertemplate='时间: %{x}<br>涨跌: %{y}%'
                    ))
                    fig.update_layout(
                        margin=dict(l=0, r=0, t=10, b=0),
                        height=250,
                        xaxis_title="更新时间",
                        yaxis_title="涨跌幅 (%)",
                        template="plotly_white"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("数据点采集记录中，请稍后刷新...")
            
            st.caption(f"数据更新时间: {realtime['update_time']}")
    else:
        st.warning(f"⚠️ 基金 {f_code} 请求超时。")

# --- 6. 底部全账户资产汇总 ---
st.markdown("---")
st.subheader("💰 总资产全览")

m1, m2, m3 = st.columns(3)
m1.metric("总本金", f"¥{total_principal:,.2f}")
total_rate = (total_current_profit / total_principal * 100) if total_principal > 0 else 0
m2.metric("累计总收益", f"¥{total_current_profit:,.2f}", f"{total_rate:.2f}%")
m3.metric("总市值", f"¥{(total_principal + total_current_profit):,.2f}")

# --- 7. 操作按钮 ---
col_btn1, col_btn2 = st.columns(2)
if col_btn1.button("🔄 同步行情", use_container_width=True):
    st.rerun()
if col_btn2.button("🗑️ 重置所有图表", use_container_width=True):
    st.session_state.fund_histories = {}
    st.rerun()

st.caption("注：折线图记录你的实时刷新点，收盘后数据将清空。")
