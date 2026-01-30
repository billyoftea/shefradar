# 📊 每日市场追踪 Agent - 实施规划文档

> 基于 FinRadar 项目，构建一个全方位的每日市场追踪系统

---

## 📋 目录

1. [项目概述](#1-项目概述)
2. [系统架构设计](#2-系统架构设计)
3. [功能模块详解](#3-功能模块详解)
4. [数据源接入方案](#4-数据源接入方案)
5. [技术实现路线](#5-技术实现路线)
6. [推送格式设计](#6-推送格式设计)
7. [开发计划与优先级](#7-开发计划与优先级)
8. [风险评估与备选方案](#8-风险评估与备选方案)

---

## 1. 项目概述

### 1.1 项目目标

构建一个**每日自动运行的市场追踪 Agent**，整合多维度金融数据和社交热点，生成结构化的市场日报，帮助用户快速了解：

- 🇨🇳 A股大盘与板块动态
- 🥇 贵金属（黄金/白银）走势
- ₿ 加密货币市场行情
- 📈 期货市场变化
- 🐦 Twitter/社交热点
- 💻 GitHub 技术趋势

### 1.2 与现有 FinRadar 的关系

```
┌─────────────────────────────────────────────────────────────┐
│                    FinRadar (现有)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ newsnow API │  │ RSS 订阅    │  │ AI 分析     │         │
│  │ 热榜抓取    │  │ 新闻聚合    │  │ 内容总结    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼ 复用
┌─────────────────────────────────────────────────────────────┐
│              市场追踪 Agent (新增模块)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ 金融数据源  │  │ 加密货币API │  │ 社交媒体    │         │
│  │ (AkShare等) │  │ (CoinGecko) │  │ (Twitter)   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

**关键决策**: 新功能作为 **独立模块** 接入现有框架，复用：
- ✅ 现有的推送通知系统（飞书/钉钉/Telegram等）
- ✅ AI 分析引擎（LiteLLM 配置）
- ✅ 存储框架（SQLite + 远程存储）
- ✅ 定时任务机制（GitHub Actions / Docker）

---

## 2. 系统架构设计

### 2.1 整体架构

```
┌──────────────────────────────────────────────────────────────────┐
│                         数据采集层                                │
├──────────────┬──────────────┬──────────────┬────────────────────┤
│  A股数据源   │  贵金属数据   │  加密货币    │  社交/代码热点     │
│  - AkShare   │  - Yahoo Fin │  - CoinGecko │  - Twitter API     │
│  - 东方财富  │  - Investing │  - CoinCap   │  - GitHub API      │
│  - 同花顺    │              │              │  - LunarCrush      │
└──────┬───────┴──────┬───────┴──────┬───────┴──────────┬─────────┘
       │              │              │                   │
       ▼              ▼              ▼                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                         数据处理层                                │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    数据标准化 & 清洗                        │ │
│  │  - 统一数据格式 (JSON Schema)                              │ │
│  │  - 异常值处理 & 缺失值填充                                 │ │
│  │  - 涨跌幅计算 & 排名生成                                   │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                         分析聚合层                                │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────────┐ │
│  │ 规则分析    │  │ AI 深度分析 │  │ 关联分析                 │ │
│  │ - 涨跌统计  │  │ - 趋势解读  │  │ - 板块联动               │ │
│  │ - 排名计算  │  │ - 热点归因  │  │ - 跨市场相关性           │ │
│  └─────────────┘  └─────────────┘  └──────────────────────────┘ │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                         输出推送层                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ 飞书/钉钉   │  │ Telegram    │  │ 邮件        │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 模块划分

建议在 `trendradar/` 目录下新增以下模块：

```
trendradar/
├── market/                      # 🆕 市场追踪模块（新增）
│   ├── __init__.py
│   ├── fetcher/                 # 数据抓取器
│   │   ├── __init__.py
│   │   ├── stock_cn.py          # A股数据（AkShare）
│   │   ├── precious_metal.py    # 贵金属数据
│   │   ├── crypto.py            # 加密货币数据
│   │   ├── futures.py           # 期货数据
│   │   ├── twitter.py           # Twitter 热点
│   │   └── github.py            # GitHub 趋势
│   ├── analyzer/                # 数据分析器
│   │   ├── __init__.py
│   │   ├── market_analyzer.py   # 市场综合分析
│   │   └── ai_market.py         # AI 市场解读
│   ├── models/                  # 数据模型
│   │   ├── __init__.py
│   │   └── market_data.py       # 市场数据结构定义
│   └── report/                  # 报告生成
│       ├── __init__.py
│       └── market_report.py     # 市场日报生成器
```

---

## 3. 功能模块详解

### 3.1 模块一：大盘情况

| 指标 | 数据来源 | 获取方式 | 更新频率 |
|-----|---------|---------|---------|
| 上证指数 | AkShare | `ak.stock_zh_index_daily()` | 日频 |
| 沪深300 | AkShare | `ak.stock_zh_index_daily()` | 日频 |
| 成交量 | AkShare | 同上 | 日频 |
| 北向资金 | 东方财富 | `ak.stock_em_hsgt_north_net_flow_in()` | 日频 |
| 主力资金流向 | 东方财富 | `ak.stock_individual_fund_flow()` | 日频 |
| 涨跌家数 | AkShare | `ak.stock_changes_em()` | 日频 |

**输出示例**:
```
📊 【大盘概况】2025-01-29
━━━━━━━━━━━━━━━━━━━
🔹 上证指数: 3,250.35 (+0.85%)
🔹 沪深300: 4,120.18 (+1.02%)
🔹 成交量: 1.2万亿 (较昨日+15%)
🔹 北向资金: 净流入 82.5亿
🔹 涨跌比: 3,542涨 / 1,285跌 / 168平
```

### 3.2 模块二：板块情况

#### 核心需求

1. **统一板块标准**: 使用申万行业分类（一级31个行业）
2. **重点关注板块**:
   - 🖥️ 科技股: 电子、计算机、通信
   - 🔄 周期股: 有色金属、钢铁、煤炭、化工
   - 🌾 农业股: 农林牧渔

| 指标 | 数据来源 | API |
|-----|---------|-----|
| 申万行业涨跌 | AkShare | `ak.stock_board_industry_name_em()` |
| 概念板块 | 东方财富 | `ak.stock_board_concept_name_em()` |

**输出示例**:
```
📈 【板块涨跌榜】
━━━━━━━━━━━━━━━━━━━
🔥 涨幅前5:
  1. 电子 +3.25%
  2. 有色金属 +2.88%
  3. 计算机 +2.15%
  ...

💧 跌幅前5:
  1. 房地产 -1.85%
  ...

━━━━━━━━━━━━━━━━━━━
🎯 重点关注板块:
  🖥️ 科技股: 电子+3.25% | 计算机+2.15% | 通信+0.85%
  🔄 周期股: 有色+2.88% | 钢铁+1.22% | 煤炭-0.35%
  🌾 农业股: 农林牧渔 +0.55%
```

### 3.3 模块三：黄金/白银

| 品种 | 数据来源 | API | 备注 |
|-----|---------|-----|-----|
| 现货黄金(XAUUSD) | Yahoo Finance | `yfinance.Ticker("GC=F")` | 免费 |
| 现货白银(XAGUSD) | Yahoo Finance | `yfinance.Ticker("SI=F")` | 免费 |
| 上海金 | AkShare | `ak.futures_main_sina()` | 国内金价 |

**代码示例**:
```python
import yfinance as yf

def get_precious_metals():
    gold = yf.Ticker("GC=F")  # 黄金期货
    silver = yf.Ticker("SI=F")  # 白银期货
    
    gold_price = gold.history(period="1d")
    silver_price = silver.history(period="1d")
    
    return {
        "gold": {
            "price": gold_price["Close"].iloc[-1],
            "change_pct": (gold_price["Close"].iloc[-1] - gold_price["Open"].iloc[0]) / gold_price["Open"].iloc[0] * 100
        },
        "silver": {...}
    }
```

### 3.4 模块四：加密货币

| 品种 | 数据来源 | API | 限制 |
|-----|---------|-----|-----|
| BTC/ETH等主流币 | CoinGecko | 免费API | 10-30 calls/min |
| Meme币(DOGE/SHIB/PEPE等) | CoinGecko | 同上 | 同上 |
| 社交热度 | LunarCrush | 免费基础版 | 有限额 |

**CoinGecko API 示例**:
```python
import requests

def get_crypto_data():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": "bitcoin,ethereum,solana,dogecoin,shiba-inu,pepe",
        "order": "market_cap_desc",
        "per_page": 10,
        "page": 1,
        "sparkline": False,
        "price_change_percentage": "24h,7d"
    }
    response = requests.get(url, params=params)
    return response.json()
```

**输出示例**:
```
₿ 【加密货币行情】
━━━━━━━━━━━━━━━━━━━
主流币:
  BTC: $98,250 (+2.35% 24h)
  ETH: $3,150 (+1.88% 24h)
  SOL: $185.50 (+5.22% 24h)

Meme币:
  DOGE: $0.125 (+8.55% 24h) 🔥
  SHIB: $0.0000185 (+3.22% 24h)
  PEPE: $0.0000125 (+15.88% 24h) 🚀
```

### 3.5 模块五：期货市场

| 品种 | 数据来源 | API |
|-----|---------|-----|
| 国内商品期货 | AkShare | `ak.futures_main_sina()` |
| 股指期货 | AkShare | `ak.futures_zh_spot()` |
| 国际原油 | Yahoo Finance | `yf.Ticker("CL=F")` |

### 3.6 模块六：Twitter 热点

**数据获取方案**:

| 方案 | 优点 | 缺点 | 成本 |
|-----|-----|-----|-----|
| Twitter API v2 | 官方数据、稳定 | 需申请、有配额 | 免费基础版 |
| Nitter RSS | 免费、无需申请 | 不稳定、可能被封 | 免费 |
| 第三方聚合 | 开箱即用 | 数据可能延迟 | 部分收费 |

**推荐**: 使用 Twitter API v2 Basic 版（免费，每月 10,000 reads）

**关注对象建议**:
- 政要: @POTUS, @elikiachina
- Web3: @VitalikButerin, @caborez, @pumpdotfun
- 财经: @zaborohead, @WatcherGuru

### 3.7 模块七：GitHub 趋势

| API | 描述 | 限制 |
|-----|-----|-----|
| GitHub REST API | 搜索热门仓库 | 60 req/h (无认证) |
| GitHub GraphQL | 更灵活的查询 | 需 Token |

**代码示例**:
```python
import requests

def get_github_trending():
    # 获取今日 Star 增长最多的项目
    url = "https://api.github.com/search/repositories"
    params = {
        "q": "created:>2025-01-28",
        "sort": "stars",
        "order": "desc",
        "per_page": 10
    }
    response = requests.get(url, params=params)
    return response.json()["items"]
```

---

## 4. 数据源接入方案

### 4.1 数据源优先级与成本分析

| 模块 | 首选数据源 | 备选数据源 | 成本 | 稳定性 |
|-----|-----------|-----------|-----|--------|
| A股大盘 | **AkShare** | 东方财富爬虫 | 🆓免费 | ⭐⭐⭐⭐⭐ |
| 板块数据 | **AkShare** | 同花顺爬虫 | 🆓免费 | ⭐⭐⭐⭐⭐ |
| 贵金属 | **Yahoo Finance** | Investing爬虫 | 🆓免费 | ⭐⭐⭐⭐ |
| 加密货币 | **CoinGecko** | CoinCap | 🆓免费 | ⭐⭐⭐⭐ |
| 期货 | **AkShare** | Wind(收费) | 🆓免费 | ⭐⭐⭐⭐ |
| Twitter | **Twitter API v2** | Nitter RSS | 🆓基础免费 | ⭐⭐⭐ |
| GitHub | **GitHub API** | 网页爬虫 | 🆓免费 | ⭐⭐⭐⭐⭐ |

### 4.2 依赖安装

在 `requirements.txt` 中新增：

```txt
# 市场数据
akshare>=1.12.0          # A股/期货数据
yfinance>=0.2.36         # Yahoo Finance
pycoingecko>=3.1.0       # CoinGecko API (可选，也可直接 requests)

# Twitter (可选)
tweepy>=4.14.0           # Twitter API v2 封装

# 数据处理
pandas>=2.0.0
numpy>=1.24.0
```

### 4.3 环境变量配置

在 `config/config.yaml` 中新增配置段：

```yaml
# ===============================================================
# 12. 市场追踪配置（新增）
# ===============================================================
market_tracker:
  enabled: true
  
  # A股市场
  stock_cn:
    enabled: true
    focus_sectors:
      tech: ["电子", "计算机", "通信"]
      cyclical: ["有色金属", "钢铁", "煤炭", "化工"]
      agriculture: ["农林牧渔"]
  
  # 贵金属
  precious_metal:
    enabled: true
    symbols: ["GC=F", "SI=F"]  # Yahoo Finance 代码
  
  # 加密货币
  crypto:
    enabled: true
    coins: ["bitcoin", "ethereum", "solana", "dogecoin", "shiba-inu", "pepe"]
    use_coingecko: true
  
  # 期货
  futures:
    enabled: true
  
  # Twitter
  twitter:
    enabled: false              # 需要 API Key
    bearer_token: ""            # 在 GitHub Secrets 配置
    accounts_to_follow:
      - "elonmusk"
      - "VitalikButerin"
  
  # GitHub
  github:
    enabled: true
    token: ""                   # 可选，增加 API 限额
    languages: ["python", "javascript", "rust"]
```

---

## 5. 技术实现路线

### 5.1 阶段规划

```
Phase 1 (1-2周) - 基础框架
├── 搭建模块目录结构
├── 实现 AkShare 数据抓取 (大盘 + 板块)
├── 接入 Yahoo Finance (贵金属)
└── 基础报告格式输出

Phase 2 (1周) - 加密货币 + 期货
├── CoinGecko API 接入
├── 期货数据抓取
└── 数据存储到 SQLite

Phase 3 (1周) - 社交热点
├── GitHub API 接入
├── Twitter API 接入 (可选)
└── 热点解析逻辑

Phase 4 (1周) - AI 分析 + 集成
├── 编写市场分析 Prompt
├── 与现有 AI 引擎集成
├── 完整日报推送测试
└── 定时任务配置
```

### 5.2 核心代码结构

#### 5.2.1 数据模型定义

```python
# trendradar/market/models/market_data.py

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class IndexData:
    """指数数据"""
    name: str           # 指数名称
    code: str           # 指数代码
    price: float        # 最新价
    change: float       # 涨跌额
    change_pct: float   # 涨跌幅
    volume: float       # 成交量
    timestamp: datetime

@dataclass
class SectorData:
    """板块数据"""
    name: str
    change_pct: float
    leading_stocks: List[str]
    category: str       # tech/cyclical/agriculture/other

@dataclass
class CryptoData:
    """加密货币数据"""
    symbol: str
    name: str
    price_usd: float
    change_24h: float
    change_7d: float
    market_cap: float
    is_meme: bool

@dataclass
class MarketSnapshot:
    """市场快照（聚合所有数据）"""
    timestamp: datetime
    indices: List[IndexData]
    sectors: List[SectorData]
    precious_metals: dict
    crypto: List[CryptoData]
    futures: dict
    github_trending: List[dict]
    twitter_hot: List[dict]
```

#### 5.2.2 数据抓取器基类

```python
# trendradar/market/fetcher/__init__.py

from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseFetcher(ABC):
    """数据抓取器基类"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.enabled = config.get("enabled", True)
    
    @abstractmethod
    async def fetch(self) -> Any:
        """抓取数据"""
        pass
    
    @abstractmethod
    def parse(self, raw_data: Any) -> Any:
        """解析数据"""
        pass
    
    async def get_data(self) -> Any:
        """获取并解析数据"""
        if not self.enabled:
            return None
        raw = await self.fetch()
        return self.parse(raw)
```

#### 5.2.3 A股数据抓取示例

```python
# trendradar/market/fetcher/stock_cn.py

import akshare as ak
import pandas as pd
from datetime import datetime
from typing import List, Dict
from .base import BaseFetcher
from ..models.market_data import IndexData, SectorData

class StockCNFetcher(BaseFetcher):
    """A股数据抓取器"""
    
    INDEX_CODES = {
        "上证指数": "000001",
        "沪深300": "000300",
        "创业板指": "399006",
        "科创50": "000688"
    }
    
    async def fetch_indices(self) -> List[IndexData]:
        """获取指数数据"""
        results = []
        for name, code in self.INDEX_CODES.items():
            df = ak.stock_zh_index_daily(symbol=f"sh{code}")
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            change = latest["close"] - prev["close"]
            change_pct = change / prev["close"] * 100
            
            results.append(IndexData(
                name=name,
                code=code,
                price=latest["close"],
                change=change,
                change_pct=change_pct,
                volume=latest["volume"],
                timestamp=datetime.now()
            ))
        return results
    
    async def fetch_north_flow(self) -> Dict:
        """获取北向资金"""
        df = ak.stock_em_hsgt_north_net_flow_in()
        today = df.iloc[-1]
        return {
            "net_flow": today["value"],  # 单位: 亿
            "date": today["date"]
        }
    
    async def fetch_sectors(self) -> List[SectorData]:
        """获取板块数据"""
        df = ak.stock_board_industry_name_em()
        results = []
        
        focus_map = self.config.get("focus_sectors", {})
        
        for _, row in df.iterrows():
            category = "other"
            for cat, names in focus_map.items():
                if row["板块名称"] in names:
                    category = cat
                    break
            
            results.append(SectorData(
                name=row["板块名称"],
                change_pct=row["涨跌幅"],
                leading_stocks=[],  # 可进一步获取龙头股
                category=category
            ))
        
        return results
```

---

## 6. 推送格式设计

### 6.1 完整日报模板

```markdown
📊 【每日市场追踪】2025-01-29
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🇨🇳 A股大盘
━━━━━━━━━━━━━━━━━━━
📈 上证指数: 3,250.35 (+0.85%)
📈 沪深300: 4,120.18 (+1.02%)
📊 成交量: 1.2万亿 (+15%)
💰 北向资金: +82.5亿
📊 涨跌比: 3542涨 / 1285跌

## 📈 板块涨跌
━━━━━━━━━━━━━━━━━━━
🔥 涨幅TOP5: 电子(+3.25%) | 有色(+2.88%) | ...
💧 跌幅TOP5: 房地产(-1.85%) | ...

🎯 重点关注:
  🖥️ 科技: 电子+3.25% | 计算机+2.15% | 通信+0.85%
  🔄 周期: 有色+2.88% | 钢铁+1.22% | 煤炭-0.35%
  🌾 农业: 农林牧渔 +0.55%

## 🥇 贵金属
━━━━━━━━━━━━━━━━━━━
🟡 黄金: $2,035.50/oz (+0.65%)
⚪ 白银: $23.15/oz (+1.22%)

## ₿ 加密货币
━━━━━━━━━━━━━━━━━━━
主流币:
  BTC $98,250 (+2.35%) | ETH $3,150 (+1.88%)

Meme币热度:
  🐕 DOGE +8.55% | 🐶 SHIB +3.22% | 🐸 PEPE +15.88%

## 📊 期货市场
━━━━━━━━━━━━━━━━━━━
原油: $78.50 (+1.2%)
铜: ¥72,500 (+0.8%)

## 🔥 社交热点
━━━━━━━━━━━━━━━━━━━
🐦 Twitter: [热点话题摘要]
💻 GitHub: [trending 项目介绍]

## 🤖 AI 分析
━━━━━━━━━━━━━━━━━━━
[AI 生成的市场解读与投资建议]
```

### 6.2 AI 分析 Prompt 设计

新建 `config/ai_market_prompt.txt`:

```
你是一位专业的金融市场分析师，请基于以下市场数据生成简洁、专业的每日市场分析报告。

## 分析要求：
1. 总结今日市场整体表现（多/空氛围）
2. 分析主要指数走势及成交量变化的含义
3. 解读板块轮动特征，特别是科技/周期/农业板块
4. 分析北向资金动向及其可能的影响
5. 贵金属与加密货币的联动关系
6. 给出未来1-3天的市场展望

## 输出格式要求：
- 使用中文
- 简洁明了，每个要点不超过2句话
- 总字数控制在500字以内
- 使用emoji增加可读性

## 今日市场数据：
{market_data}
```

---

## 7. 开发计划与优先级

### 7.1 MVP（最小可行产品）

**优先级 P0** - 先跑起来

| 功能 | 预估工时 | 依赖 |
|-----|---------|-----|
| A股指数数据 | 2h | AkShare |
| 板块涨跌数据 | 2h | AkShare |
| 北向资金 | 1h | AkShare |
| 贵金属价格 | 1h | yfinance |
| 基础报告生成 | 3h | - |
| 接入现有推送 | 2h | - |

**预计 2-3 天完成 MVP**

### 7.2 完整版本

**优先级 P1** - 核心功能

| 功能 | 预估工时 | 依赖 |
|-----|---------|-----|
| 加密货币数据 | 2h | CoinGecko |
| 期货数据 | 2h | AkShare |
| AI 市场分析 | 3h | LiteLLM |
| 数据持久化 | 2h | SQLite |

**优先级 P2** - 增强功能

| 功能 | 预估工时 | 依赖 |
|-----|---------|-----|
| GitHub Trending | 2h | GitHub API |
| Twitter 热点 | 4h | Twitter API |
| HTML 可视化报告 | 4h | - |

### 7.3 任务清单 (Checklist)

```
## Phase 1: 基础框架
- [ ] 创建 `trendradar/market/` 目录结构
- [ ] 定义数据模型 (`models/market_data.py`)
- [ ] 实现 AkShare A股数据抓取
- [ ] 实现 yfinance 贵金属数据抓取
- [ ] 基础 Markdown 报告生成

## Phase 2: 数据扩展
- [ ] CoinGecko 加密货币接入
- [ ] AkShare 期货数据接入
- [ ] 数据存储到 SQLite

## Phase 3: AI 分析
- [ ] 编写市场分析 Prompt
- [ ] 与现有 ai 模块集成
- [ ] 测试生成质量

## Phase 4: 社交热点
- [ ] GitHub API 接入
- [ ] Twitter API 接入 (可选)

## Phase 5: 集成测试
- [ ] 接入现有推送系统
- [ ] 定时任务配置
- [ ] 完整流程测试
```

---

## 8. 风险评估与备选方案

### 8.1 风险点

| 风险 | 概率 | 影响 | 缓解措施 |
|-----|-----|-----|---------|
| AkShare API 变更 | 中 | 高 | 版本锁定 + 备选东方财富爬虫 |
| CoinGecko 限流 | 中 | 中 | 加缓存 + 降低频率 |
| Twitter API 配额 | 高 | 低 | 使用 Nitter RSS 备选 |
| 数据源宕机 | 低 | 高 | 多数据源冗余 |

### 8.2 备选数据源

| 主数据源 | 备选方案1 | 备选方案2 |
|---------|----------|----------|
| AkShare | Tushare (需注册) | 东方财富爬虫 |
| Yahoo Finance | Investing.com爬虫 | 新浪财经 |
| CoinGecko | CoinCap API | Binance API |
| Twitter API | Nitter RSS | 直接爬虫 |

### 8.3 成本预估

| 项目 | 费用 | 备注 |
|-----|-----|-----|
| 数据源 | 🆓 | 全部使用免费 API |
| AI 分析 | ~0.1-0.2元/天 | DeepSeek 计费，同现有 |
| 服务器 | 🆓 | GitHub Actions 免费 |
| **总计** | **< 0.3元/天** | |

---

## 📝 下一步行动

1. **确认需求**: 请确认以上规划是否符合预期
2. **环境准备**: 安装必要依赖 (`pip install akshare yfinance`)
3. **开始开发**: 从 MVP（A股 + 贵金属）开始实现

---

> 📅 文档创建时间: 2025-01-29
> 📝 作者: FinRadar Agent
