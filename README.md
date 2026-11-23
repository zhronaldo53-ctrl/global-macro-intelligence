# 全球宏观与股市观察台

## 运行

在电脑或支持 Python 的云端环境中：

```bash
pip install -r requirements.txt
streamlit run app.py
```

浏览器将打开交互式仪表盘。点击侧栏“重新抓取最新数据”可刷新。首次运行需要能访问 Yahoo Finance 和 FRED 的网络环境。

## 在 Codex Cloud 中

把文件放入 GitHub 仓库并在 Codex 中连接该仓库。请 Codex 检查依赖并运行 `streamlit run app.py`。注意：Codex 的任务运行环境不一定会自动对外发布网页；若需要在 iPad 随时访问，可进一步部署到 Streamlit Community Cloud 或其他托管平台。

## 统计口径

- 股指：上证综指 `^SSEC`，纳斯达克综合指数 `^IXIC`，历史日收盘价。
- 宏观：FRED 官方 CSV 接口。CPI、失业率、联邦基金有效利率、10 年期国债收益率、实际 GDP，以及可用时的中国 CPI。
- 将价格转换为月收益；将宏观值转换为月变化，滞后一期后计算 Pearson 相关系数。
- 这是教学/探索工具，不是经过发布日期校正的事件研究、因果模型或投资建议。
