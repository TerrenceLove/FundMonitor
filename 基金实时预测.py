import streamlit as st
import requests
import json
import time
import pandas as pd
from datetime import datetime

# --- 1. 页面基础配置 (移动端适配) ---
st.set_page_config(page_title="Gemini 多基金智能对账单", layout="centered")

# --- 2. 核心数据抓取函数 ---
def get_fund_realtime(code):
    """从接口抓取实时估值、名称和涨跌幅"""
    url = f"http://fundgz.1234567.com.cn/js/{code}.js?rt={int(time.time())}"
    try:
        res = requests.get(url, timeout=5)
        # 提取并解析 JSON
        content = res.text
        json_str = content[content.find('{'):content.rfind('}')+1]
        data = json.loads(json_str)
        return {
            "name": data['name'],       # 基金名称
            "jz_date": data['jzrq'],    # 上次净值日期
            "last_nav": float(data['dwjz']), # 上次单位净值
            "est_nav": float(data['gsz']),   # 实时估值净值
            "est_rate": float(data['gszzl']), # 实时涨跌幅 (%)
            "update_time": data['gztime']    # 估值更新时间
        }
    except:
        return None

# --- 3. 主界面显示 ---
st.title("🛡️ Gemini 多基金智能看板")
st.caption(f"数据实时同步中 | 当前时间: {datetime.now().strftime('%H:%M:%S')}")

# 检查 Secrets 配置
if "funds" not in st.secrets:
    st.error("❌ 未在后台发现 [[funds]] 配置，请检查 Streamlit Secrets 填写是否正确。")
    st.stop()

funds_list = st.secrets["funds"]

# 汇总变量
total_principal = 0.0
total_current_profit = 0.0
summary_data = []

# --- 4. 循环处理每一个基金 ---
for fund in funds_list:
    f_code = fund["code"]
    f_p = float(fund["principal"])
    f_init_profit = float(fund["init_profit"])
    
    # 获取实时行情
    realtime = get_fund_realtime(f_code)
    
    if realtime:
        # 计算逻辑
        # 今日盈亏 = (本金 + 历史收益) * 今日涨跌幅%
        day_profit = (f_p + f_init_profit) * (realtime['est_rate'] / 100)
        # 累计总收益 = 历史收益 + 今日预估盈亏
        total_profit = f_init_profit + day_profit
        # 实时总市值
        total_value = f_p + total_profit
        
        # 累加汇总
        total_principal += f_p
        total_current_profit += total_profit
        
        # UI 显示：使用折叠框节省手机屏幕空间
        with st.expander(f"📈 {realtime['name']} ({f_code})", expanded=True):
            # 第一行：实时涨跌指标
            c1, c2, c3 = st.columns(3)
            c1.metric("实时估值", f"{realtime['est_nav']:.4f}")
            c2.metric("估值涨跌", f"{realtime['est_rate']}%", f"{realtime['est_rate']}%")
            c3.metric("今日损益", f"¥{day_profit:,.2f}")
            
            # 第二行：资产详情
            col1, col2 = st.columns(2)
            col1.write(f"**持有本金:** ¥{f_p:,.2f}")
            col1.write(f"**累计收益:** ¥{total_profit:,.2f}")
            col2.write(f"**预估当前市值:** ¥{total_value:,.2f}")
            col2.caption(f"更新时间: {realtime['update_time']}")
    else:
        st.warning(f"⚠️ 基金 {f_code} 数据请求超时，请检查代码或稍后重试。")

# --- 5. 底部全账户资产汇总 ---
st.markdown("---")
st.subheader("💰 总资产全览")

m1, m2, m3 = st.columns(3)
m1.metric("总投入本金", f"¥{total_principal:,.2f}")
total_rate = (total_current_profit / total_principal * 100) if total_principal > 0 else 0
m2.metric("累计总收益", f"¥{total_current_profit:,.2f}", f"{total_rate:.2f}%")
m3.metric("实时总市值", f"¥{(total_principal + total_current_profit):,.2f}")

# 刷新按钮
if st.button("🔄 立即同步最新行情", use_container_width=True):
    st.rerun()

st.info("💡 提示：系统已自动通过 6 位代码匹配基金名称，无需手动输入。")
