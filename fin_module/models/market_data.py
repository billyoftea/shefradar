"""
数据模型定义

定义所有市场数据的标准化数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


# ==================== A股/指数相关 ====================

@dataclass
class IndexData:
    """指数数据"""
    name: str           # 指数名称
    code: str           # 指数代码
    price: float        # 最新价
    change: float       # 涨跌额
    change_pct: float   # 涨跌幅 (%)
    volume: float       # 成交量
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SectorData:
    """板块数据"""
    name: str                           # 板块名称
    change_pct: float                   # 涨跌幅 (%)
    leading_stocks: List[str] = field(default_factory=list)  # 领涨股票
    category: str = "other"             # 分类: tech/cyclical/agriculture/consumption/finance/other


@dataclass
class MarketOverview:
    """A股市场概览"""
    timestamp: datetime
    indices: List[IndexData] = field(default_factory=list)
    sectors: List[SectorData] = field(default_factory=list)
    north_flow_net: float = 0           # 北向资金净流入 (亿元)
    limit_up_count: int = 0             # 涨停数量
    limit_down_count: int = 0           # 跌停数量
    up_count: int = 0                   # 上涨家数
    down_count: int = 0                 # 下跌家数


# ==================== 贵金属相关 ====================

@dataclass
class PreciousMetalData:
    """贵金属数据"""
    symbol: str         # 代码 (GC=F, SI=F 等)
    name: str           # 中文名称
    name_en: str        # 英文名称
    price: float        # 最新价
    change: float       # 涨跌额
    change_pct: float   # 涨跌幅 (%)
    unit: str           # 单位 (美元/盎司)
    timestamp: datetime = field(default_factory=datetime.now)


# ==================== 加密货币相关 ====================

@dataclass
class CryptoData:
    """加密货币数据"""
    symbol: str         # 代码 (BTC, ETH 等)
    name: str           # 名称
    price_usd: float    # USD 价格
    change_24h: float   # 24h 涨跌幅 (%)
    change_7d: float    # 7d 涨跌幅 (%)
    market_cap: float   # 市值
    volume_24h: float = 0   # 24h 交易量
    is_meme: bool = False   # 是否为 Meme 币
    category: str = "other" # 分类: mainstream/meme/defi/other
    timestamp: datetime = field(default_factory=datetime.now)


# ==================== 期货相关 ====================

@dataclass
class FuturesData:
    """期货数据"""
    code: str           # 合约代码
    name: str           # 名称
    price: float        # 最新价
    change: float       # 涨跌额
    change_pct: float   # 涨跌幅 (%)
    futures_type: str   # 类型: commodity/index/international
    timestamp: datetime = field(default_factory=datetime.now)


# ==================== 社交媒体相关 ====================

@dataclass
class TwitterHotTopic:
    """Twitter 热门推文"""
    tweet_id: str
    text: str
    username: str       # 用户名 (@xxx)
    user_name: str      # 显示名称
    created_at: str     # 创建时间
    likes: int          # 点赞数
    retweets: int       # 转发数
    url: str            # 推文链接
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class GitHubTrendingRepo:
    """GitHub 热门仓库"""
    name: str           # 仓库名称
    full_name: str      # 完整名称 (owner/repo)
    description: str    # 描述
    url: str            # 仓库链接
    stars: int          # Star 数量
    forks: int          # Fork 数量
    language: str       # 主要语言
    topics: List[str] = field(default_factory=list)  # 话题标签
    timestamp: datetime = field(default_factory=datetime.now)


# ==================== 聚合数据结构 ====================

@dataclass
class MarketSnapshot:
    """
    市场快照 - 聚合所有市场数据
    
    用于生成完整的市场日报
    """
    timestamp: datetime
    
    # A股市场
    market_overview: Optional[MarketOverview] = None
    
    # 贵金属
    precious_metals: List[PreciousMetalData] = field(default_factory=list)
    
    # 加密货币
    crypto: List[CryptoData] = field(default_factory=list)
    
    # 期货
    futures_commodity: List[FuturesData] = field(default_factory=list)
    futures_index: List[FuturesData] = field(default_factory=list)
    futures_international: List[FuturesData] = field(default_factory=list)
    
    # 社交热点
    twitter_hot: List[TwitterHotTopic] = field(default_factory=list)
    github_trending: List[GitHubTrendingRepo] = field(default_factory=list)
    
    # AI 分析结果
    ai_analysis: str = ""
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "market_overview": {
                "indices": [vars(idx) for idx in self.market_overview.indices] if self.market_overview else [],
                "sectors": [vars(sec) for sec in self.market_overview.sectors] if self.market_overview else [],
                "north_flow_net": self.market_overview.north_flow_net if self.market_overview else 0,
            },
            "precious_metals": [vars(pm) for pm in self.precious_metals],
            "crypto": [vars(c) for c in self.crypto],
            "futures": {
                "commodity": [vars(f) for f in self.futures_commodity],
                "index": [vars(f) for f in self.futures_index],
                "international": [vars(f) for f in self.futures_international],
            },
            "social": {
                "twitter": [vars(t) for t in self.twitter_hot],
                "github": [vars(g) for g in self.github_trending],
            },
            "ai_analysis": self.ai_analysis,
        }
