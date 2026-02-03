"""
数据抓取器基类和通用接口
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class BaseFetcher(ABC):
    """
    数据抓取器基类
    
    所有数据源抓取器都应继承此基类，实现 fetch() 和 parse() 方法
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化抓取器
        
        Args:
            config: 配置字典，包含该数据源的特定配置
        """
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self._cache = {}
    
    @abstractmethod
    async def fetch(self) -> Any:
        """
        抓取原始数据
        
        Returns:
            原始数据（格式因数据源而异）
        """
        pass
    
    @abstractmethod
    def parse(self, raw_data: Any) -> Any:
        """
        解析原始数据为标准格式
        
        Args:
            raw_data: fetch() 返回的原始数据
            
        Returns:
            标准化后的数据
        """
        pass
    
    async def get_data(self) -> Optional[Any]:
        """
        获取并解析数据的便捷方法
        
        Returns:
            解析后的数据，如果抓取器被禁用则返回 None
        """
        if not self.enabled:
            logger.info(f"{self.__class__.__name__} is disabled, skipping...")
            return None
        
        try:
            raw = await self.fetch()
            return self.parse(raw)
        except Exception as e:
            logger.error(f"Error fetching data from {self.__class__.__name__}: {e}")
            return None
    
    def clear_cache(self):
        """清除缓存"""
        self._cache = {}


# ==================== 导出各个抓取器 ====================

# 市场数据抓取器
from .stock_cn import StockCNFetcher
from .precious_metal import PreciousMetalFetcher
from .crypto import CryptoFetcher
from .futures import FuturesFetcher

# 社交媒体抓取器
from .twitter import TwitterFetcher
from .nitter_rss import NitterRSSFetcher

# 内容抓取器
from .github import GitHubFetcher
from .wechat_article import WechatArticleFetcher

# 配置管理
from .social_config import SocialSourceConfig, TwitterConfig, WechatConfig

# 导出列表
__all__ = [
    # 基类
    "BaseFetcher",
    
    # 市场数据
    "StockCNFetcher",
    "PreciousMetalFetcher", 
    "CryptoFetcher",
    "FuturesFetcher",
    
    # 社交媒体
    "TwitterFetcher",
    "NitterRSSFetcher",
    
    # 内容
    "GitHubFetcher",
    "WechatArticleFetcher",
    
    # 配置管理
    "SocialSourceConfig",
    "TwitterConfig",
    "WechatConfig",
]
