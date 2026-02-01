import streamlit as st
import pandas as pd
import requests
import json
import time
import re
import plotly.graph_objects as go
from datetime import datetime


# --- 1. 从后台配置 (Secrets) 加载初始化数据 ---
# 如果后台没配置，则使用默认值
def get_default_config():
    if "portfolio" in st.secrets:
        return st.secrets["portfolio"]
    else:
        # 如果后台完全没配置，返回一个空的初始模版
        return {"code": "025209", "principal": 0.0, "init_profit": 0.0}

# 页面配置
st.set_page_config(page_title="Gemini 智能决策系统-云端版")

# 初始化数据
default_data = get_default_config()

# --- 2. 侧边栏：显示当前的后台配置 ---
with st.sidebar:
    st.header("⚙️ 云端配置预览")
    st.write(f"**当前监听代码：** `{default_data['code']}`")
    st.write(f"**预设本金：** `{default_data['principal']}` 元")
    st.write(f"**预设收益：** `{default_data['init_profit']}` 元")
    st.info("💡 如需修改上述数据，请前往 Streamlit Cloud 后台的 Secrets 模块。")

# --- 3. 主界面逻辑 (直接引用配置好的数据) ---
st.title("🛡️ Gemini 智能决策系统 (云端持久版)")

p_code = default_data['code']
p_principal = float(default_data['principal'])
p_profit = float(default_data['init_profit'])

if st.button(f"🚀 立即对 {p_code} 执行深度分析"):
    with st.spinner("从官方接口拉取最新数据..."):
        try:
            # 这里的分析逻辑保持和你之前的一致
            hist = ak.fund_open_fund_info_em(fund=p_code, indicator="单位净值走势")
            # ... 你的量化分析逻辑 ...
            st.success(f"分析完成！当前本金 {p_principal} 元，总收益 {p_profit} 元。")
        except:
            st.error("分析失败，请检查代码或后台配置。")













# 页面配置
st.set_page_config(page_title="Gemini 基金高精度看板 Pro", layout="wide")

# --- 初始化历史数据存储 (用于折线图) ---
if 'history_profit' not in st.session_state:
    st.session_state.history_profit = pd.DataFrame(columns=['time', 'profit', 'rate'])


def get_official_nav(code):
    """抓取该基金官方最新发布的单位净值 (高精度基准)"""
    url = f"http://fund.eastmoney.com/pingzhongdata/{code}.js"
    try:
        res = requests.get(url, timeout=5)
        pattern = r"Data_netWorthTrend = \[(.*?)\];"
        match = re.search(pattern, res.text)
        if match:
            data_str = match.group(1)
            latest_data = data_str.split('},')[-1]
            nav_val = re.search(r'"y":(\d+\.\d+)', latest_data).group(1)
            return float(nav_val)
    except:
        return None


def get_valuation_data(code):
    """抓取日内实时估值预测"""
    url = f"http://fundgz.1234567.com.cn/js/{code}.js?rt={int(time.time())}"
    try:
        res = requests.get(url, timeout=3)
        return json.loads(res.text[res.text.find('{'):res.text.rfind('}') + 1])
    except:
        return None


# --- 侧边栏：资产精准录入 ---
with st.sidebar:
    st.header("🎯 资产精准录入")
    with st.form("input_form"):
        f_code = st.text_input("基金代码", "025209")
        f_principal = st.number_input("持有本金 (元)", min_value=0.0, value=10000.0)
        f_profit = st.number_input("当前总持有收益 (元)", value=500.0)
        st.info("💡 提示：系统将以官方最新净值为起点，叠加日内波动计算实时损益。")
        submit = st.form_submit_button("同步数据并重置图表")

    if submit:
        off_nav = get_official_nav(f_code)
        st.session_state['portfolio'] = {
            "code": f_code,
            "principal": f_principal,
            "init_profit": f_profit,
            "base_nav": off_nav
        }
        # 重置折线图历史
        st.session_state.history_profit = pd.DataFrame(columns=['time', 'profit', 'rate'])
        st.success(f"同步成功！官方基准净值：{off_nav}")

    if st.button("🗑️ 清空图表历史"):
        st.session_state.history_profit = pd.DataFrame(columns=['time', 'profit', 'rate'])
        st.rerun()

# --- 主界面 ---
st.title("🛡️ 基金实时盈亏清算看板 Pro")
st.caption(f"当前时间：{datetime.now().strftime('%H:%M:%S')} | 基准源：官方历史净值接口")

if 'portfolio' in st.session_state:
    p = st.session_state['portfolio']
    val_data = get_valuation_data(p['code'])

    if val_data:
        # 1. 核心计算逻辑
        off_nav = get_official_nav(p['code'])
        est_nav = float(val_data['gsz'])

        # 计算日内涨跌幅 (相对于官方最新公布值的偏离度)
        current_day_pct = (est_nav - off_nav) / off_nav

        # 收益计算
        day_earn = (p['principal'] + p['init_profit']) * current_day_pct
        total_earn = p['init_profit'] + day_earn
        total_rate = (total_earn / p['principal']) * 100 if p['principal'] > 0 else 0

        # 2. 记录历史数据 (用于绘图)
        now_time = datetime.now().strftime('%H:%M:%S')
        new_record = pd.DataFrame({
            'time': [now_time],
            'profit': [round(total_earn, 2)],
            'rate': [round(total_rate, 2)]
        })
        # 避免重复记录同一秒的数据
        if st.session_state.history_profit.empty or st.session_state.history_profit.iloc[-1]['time'] != now_time:
            st.session_state.history_profit = pd.concat([st.session_state.history_profit, new_record],
                                                        ignore_index=True)

        # 3. 顶部指标卡片
        c1, c2, c3 = st.columns(3)
        c1.metric("今日预估损益", f"¥{day_earn:,.2f}", f"{current_day_pct * 100:.2f}%")
        c2.metric("累计总持有收益", f"¥{total_earn:,.2f}", f"{total_rate:.2f}%")
        c3.metric("预估当前总资产", f"¥{(p['principal'] + total_earn):,.2f}")

        # --- 📈 实时收益折线图 (可隐藏式) ---
        st.markdown("---")
        with st.expander("📊 查看实时收益波动曲线 (点击展开/隐藏)", expanded=True):
            if len(st.session_state.history_profit) > 1:
                fig = go.Figure()
                # 绘制收益金额曲线
                fig.add_trace(go.Scatter(
                    x=st.session_state.history_profit['time'],
                    y=st.session_state.history_profit['profit'],
                    mode='lines+markers',
                    name='累计收益 (元)',
                    line=dict(color='#ff4b4b', width=3),
                    hovertemplate='时间: %{x}<br>收益: ¥%{y}'
                ))
                fig.update_layout(
                    hovermode="x unified",
                    height=400,
                    margin=dict(l=0, r=0, t=20, b=0),
                    xaxis_title="监控时间",
                    yaxis_title="收益金额 (元)",
                    template="plotly_white"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("正在采集实时波动数据，请保持页面开启或点击刷新按钮...")

        # 4. 数据对账单
        st.subheader("📋 数据对账清单")
        comparison = pd.DataFrame([{
            "基金名称": val_data['name'],
            "代码": p['code'],
            "官方最新净值": f"{off_nav:.4f}",
            "日内预估净值": f"{est_nav:.4f}",
            "基准偏离度": f"{current_day_pct * 100:.2f}%",
            "估值更新时间": val_data['gztime']
        }])
        st.table(comparison)
        st.info("💡 提示：折线图会记录你每次刷新时的收益数值。建议在交易时段保持页面开启并定时刷新。")

    if st.button("🔄 立即手动刷新"):
        st.rerun()
else:
    st.warning("⬅️ 请在左侧侧边栏录入本金和当前收益，系统将自动对齐官方数据。")

# 底部说明
st.markdown("---")
st.caption("注：折线图数据存储在浏览器会话中，刷新页面或重置侧边栏将重新开始记录。")

###使用方法： streamlit run 基金实时预测.py

