import io
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import requests
import streamlit as st
import yfinance as yf
import plotly.express as px

st.set_page_config(page_title='全球宏观与股市观察台', layout='wide')
st.title('📈 全球宏观与股市观察台')
st.caption('数据在每次刷新时在线获取；展示的是各市场最近可获得的交易日/数据发布日期，并非保证当日实时成交价。')

MARKETS = {'上证综指 (^SSEC)': '^SSEC', '纳斯达克综合指数 (^IXIC)': '^IXIC'}
MACROS = {'美国CPI指数': 'CPIAUCSL', '美国失业率 (%)': 'UNRATE', '美国联邦基金有效利率 (%)': 'DFF', '美国10年期国债收益率 (%)': 'DGS10', '美国实际GDP (十亿美元)': 'GDPC1', '中国CPI同比 (%)': 'CHNCPIALLMINMEI'}

@st.cache_data(ttl=1800, show_spinner=False)
def get_market(ticker, start, end):
    df = yf.download(ticker, start=start, end=end + timedelta(days=1), auto_adjust=True, progress=False, threads=False)
    if df.empty: raise ValueError(f'{ticker} 无行情返回')
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    s = df['Close'].dropna().astype(float)
    s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
    return s

@st.cache_data(ttl=3600, show_spinner=False)
def get_fred(series, start):
    url = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}'
    r = requests.get(url, timeout=20, headers={'User-Agent': 'Mozilla/5.0'})
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    if 'DATE' not in df.columns: raise ValueError('FRED 响应格式异常')
    df['DATE'] = pd.to_datetime(df['DATE'])
    df[series] = pd.to_numeric(df[series], errors='coerce')
    return df.set_index('DATE')[series].loc[start:].dropna()

with st.sidebar:
    st.header('分析设置')
    years = st.slider('历史区间（年）', 2, 10, 5)
    selected = st.selectbox('目标指数', list(MARKETS))
    st.button('🔄 重新抓取最新数据', on_click=st.cache_data.clear)
    st.caption('行情：Yahoo Finance（yfinance）；宏观：FRED。免费数据可能延迟、修订或暂时不可用。')

end = datetime.now().date()
start = end - timedelta(days=round(years * 365.25))
prices = {}
errors = []
with st.spinner('正在获取市场与宏观数据…'):
    for label, ticker in MARKETS.items():
        try: prices[label] = get_market(ticker, start, end)
        except Exception as e: errors.append(f'{label}: {e}')
    macros = {}
    for label, series in MACROS.items():
        try: macros[label] = get_fred(series, start)
        except Exception as e: errors.append(f'{label}: {e}')
for err in errors: st.warning(f'数据源暂不可用 — {err}')
if not prices:
    st.error('两大股指均未获取成功。请检查网络是否允许访问 Yahoo Finance，然后刷新。')
    st.stop()

st.subheader('一、最新可得市场快照')
cols = st.columns(2)
for col, (label, s) in zip(cols, prices.items()):
    pct = (s.iloc[-1] / s.iloc[-2] - 1) * 100 if len(s) > 1 else np.nan
    col.metric(label, f'{s.iloc[-1]:,.2f}', f'{pct:+.2f}%（相对上一交易日）' if pd.notna(pct) else None)
    col.caption(f'最新交易日：{s.index[-1].date()}')

if macros:
    st.subheader('二、宏观指标最新发布值')
    rows = [{'指标': label, '最新值': round(float(s.iloc[-1]), 3), '观测日期': str(s.index[-1].date()), 'FRED代码': MACROS[label]} for label, s in macros.items()]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.subheader('三、股市历史走势（各自基期归一化为100）')
normalized = pd.concat({label: s / s.iloc[0] * 100 for label, s in prices.items()}, axis=1)
fig = px.line(normalized.reset_index().rename(columns={'index':'日期'}), x='日期', y=list(normalized.columns), labels={'value':'归一化指数', 'variable':'市场'})
st.plotly_chart(fig, use_container_width=True)

st.subheader('四、宏观指标与股市月收益的统计关系')
st.info('采用月末股价计算月收益；宏观变量按月末观测值计算月度变化，并滞后一个月与股市收益配对。此处为探索性相关性，不是因果识别或可直接交易的预测。FRED 历史序列可能经过修订，且本例未按首次公布日构建真实历史信息集。')
chosen = prices[selected]
monthly_returns = chosen.resample('ME').last().pct_change(fill_method=None) * 100
records = []
scatter_data = {}
for label, macro in macros.items():
    monthly_macro = macro.resample('ME').last().ffill()
    # CPI, GDP: use percent change; rates/unemployment: percentage point change.
    if label in ('美国CPI指数', '美国实际GDP (十亿美元)'):
        change = monthly_macro.pct_change(fill_method=None) * 100
        change_unit = '环比变化 (%)'
    else:
        change = monthly_macro.diff()
        change_unit = '月度变化（百分点/指数单位）'
    paired = pd.concat([change.shift(1).rename('宏观变化'), monthly_returns.rename('指数月收益')], axis=1).dropna()
    if len(paired) >= 12 and paired['宏观变化'].std() > 0 and paired['指数月收益'].std() > 0:
        corr = paired.corr().iloc[0,1]
        records.append({'宏观指标':label, 'Pearson相关系数':round(float(corr), 3), '有效月份':len(paired), '宏观单位':change_unit})
        scatter_data[label] = paired
if records:
    st.dataframe(pd.DataFrame(records).sort_values('Pearson相关系数'), use_container_width=True, hide_index=True)
    choice = st.selectbox('查看散点关系', list(scatter_data))
    paired = scatter_data[choice].reset_index()
    fig2 = px.scatter(paired, x='宏观变化', y='指数月收益', trendline='ols', hover_data=[paired.columns[0]], title=f'{choice}（滞后1个月） vs {selected}月收益')
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.warning('有效配对月份不足（至少12个月）或宏观数据暂不可用，无法计算相关系数。')

st.subheader('五、方法与风险')
st.markdown('''- **时间差**：中国股市、美国股市交易时区不同；当天未收盘时通常只显示上一交易日数据。\n- **公布滞后**：CPI、失业率、GDP 的“观测日期”不是数据正式公布日期。简单滞后一个月并不能完全避免未来信息泄露。\n- **频率与可比性**：GDP 为季度数据，月度前向填充仅用于探索；不同国家指标口径也不同。\n- **相关不等于因果**：相关系数受样本期、共同趋势、市场预期及政策反应影响，不能单独作为买卖依据。\n- **中国 CPI**：所用 OECD/FRED 系列是否仍持续更新取决于数据源；缺失时不会虚构数值。''')
