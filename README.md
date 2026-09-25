\# K-POP COMEBACK INSIGHT



> DATA · OPINION · STRATEGY  

> 回归数据 · 舆情分析 · 营销策略 · 生命周期诊断



K-POP COMEBACK INSIGHT 是一个面向 K-POP 艺人回归场景的数据分析与智能体系统。



项目以 Bilibili 平台公开数据为主要数据来源，通过 Django 后端完成数据采集、数据存储与 API 服务，并结合 GLM-4-Flash 大语言模型，对艺人回归期间的数据和舆情进行分析。



系统根据不同分析任务设置了五种 Agent 角色：



\- 🔥 回归热度分析

\- 👤 大众画像与舆论分析

\- 📢 营销策略建议

\- 📊 数据概览

\- 📈 回归生命周期诊断



前端采用 Vue.js 和 ECharts，实现数据展示、生命周期曲线以及 AI 分析结果的可视化。



\## 技术栈



\- Frontend：Vue.js、ECharts

\- Backend：Django

\- Database：SQLite

\- Data Source：Bilibili

\- LLM：GLM-4-Flash

\- Data Collection：Bilibili API + HTML 解析

\- Development：Python、JavaScript



\## 系统流程



```text

Bilibili 数据采集

&#x20;      ↓

数据清洗与 SQLite 存储

&#x20;      ↓

Django API

&#x20;      ↓

数据库数据上下文注入

&#x20;      ↓

GLM-4-Flash

&#x20;      ↓

五类 Agent 分析

&#x20;      ↓

Vue + ECharts 可视化展示

