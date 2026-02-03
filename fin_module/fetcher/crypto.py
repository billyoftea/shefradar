"""
加密货币数据抓取器

可选实现方案：
1. pycoingecko - CoinGecko 官方 Python 封装
   GitHub: https://github.com/man-c/pycoingecko
   安装: pip install pycoingecko

2. 直接使用 requests 调用 CoinGecko API
   API文档: https://www.coingecko.com/en/api/documentation

CoinGecko API 限制:
- 免费版: 10-30 calls/minute
- 无需 API Key

支持获取:
- 主流币: BTC, ETH, SOL 等
- Meme币: DOGE, SHIB, PEPE 等
- 市值、价格变化、交易量等
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

try:
    from pycoingecko import CoinGeckoAPI
    PYCOINGECKO_AVAILABLE = True
except ImportError:
    PYCOINGECKO_AVAILABLE = False
    CoinGeckoAPI = None

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from . import BaseFetcher
from ..models.market_data import CryptoData

logger = logging.getLogger(__name__)


class CryptoFetcher(BaseFetcher):
    """
    加密货币数据抓取器
    
    基于 CoinGecko API 实现，支持:
    - 主流币数据 (BTC, ETH, SOL, BNB 等)
    - Meme币数据 (DOGE, SHIB, PEPE, FLOKI 等)
    - 24h/7d 价格变化
    - 市值排名
    - 交易量数据
    """
    
    # 默认关注的币种 (CoinGecko ID)
    DEFAULT_COINS = {
        "mainstream": [
            "bitcoin", "ethereum", "solana", "binancecoin", 
            "ripple", "cardano", "avalanche-2", "polkadot"
        ],
        "meme": [
            "dogecoin", "shiba-inu", "pepe", "floki", 
            "bonk", "dogwifcoin", "brett"
        ],
        "defi": [
            "uniswap", "aave", "chainlink", "maker"
        ],
    }
    
    # Meme币列表（用于标记）
    MEME_COINS = [
        "dogecoin", "shiba-inu", "pepe", "floki", "bonk", 
        "dogwifcoin", "brett", "book-of-meme", "cat-in-a-dogs-world"
    ]
    
    COINGECKO_API_BASE = "https://api.coingecko.com/api/v3"
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        
        # 优先使用 pycoingecko，否则使用 requests
        self.use_pycoingecko = PYCOINGECKO_AVAILABLE and self.config.get("use_pycoingecko", True)
        
        if self.use_pycoingecko:
            self.cg = CoinGeckoAPI()
        elif not REQUESTS_AVAILABLE:
            logger.warning("Neither pycoingecko nor requests available. Install one of them.")
            self.enabled = False
        
        # 合并默认币种和用户配置的币种
        self.coins_to_fetch = self.config.get("coins", [])
        if not self.coins_to_fetch:
            # 使用默认列表
            for category_coins in self.DEFAULT_COINS.values():
                self.coins_to_fetch.extend(category_coins)
            # 去重
            self.coins_to_fetch = list(set(self.coins_to_fetch))
        
        self.vs_currency = self.config.get("vs_currency", "usd")
    
    async def fetch(self) -> Dict[str, Any]:
        """
        抓取加密货币数据
        
        Returns:
            包含加密货币市场数据的字典
        """
        loop = asyncio.get_event_loop()
        
        # 使用线程池执行同步API调用
        result = await loop.run_in_executor(None, self._fetch_market_data)
        
        return {
            "coins": result,
            "timestamp": datetime.now()
        }
    
    def _fetch_market_data(self) -> List[Dict]:
        """
        获取市场数据
        
        使用 /coins/markets 端点一次性获取多个币种数据
        """
        try:
            if self.use_pycoingecko:
                return self._fetch_with_pycoingecko()
            else:
                return self._fetch_with_requests()
        except Exception as e:
            logger.error(f"Error fetching crypto data: {e}")
            return []
    
    def _fetch_with_pycoingecko(self) -> List[Dict]:
        """使用 pycoingecko 库获取数据"""
        coins_str = ",".join(self.coins_to_fetch)
        
        data = self.cg.get_coins_markets(
            vs_currency=self.vs_currency,
            ids=coins_str,
            order="market_cap_desc",
            per_page=len(self.coins_to_fetch),
            page=1,
            sparkline=False,
            price_change_percentage="24h,7d"
        )
        
        return self._process_market_data(data)
    
    def _fetch_with_requests(self) -> List[Dict]:
        """使用 requests 直接调用 API"""
        url = f"{self.COINGECKO_API_BASE}/coins/markets"
        params = {
            "vs_currency": self.vs_currency,
            "ids": ",".join(self.coins_to_fetch),
            "order": "market_cap_desc",
            "per_page": len(self.coins_to_fetch),
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "24h,7d"
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        return self._process_market_data(data)
    
    def _process_market_data(self, data: List[Dict]) -> List[Dict]:
        """处理API返回的市场数据"""
        results = []
        
        for coin in data:
            coin_id = coin.get("id", "")
            is_meme = coin_id in self.MEME_COINS
            
            # 判断分类
            category = "other"
            for cat, coins in self.DEFAULT_COINS.items():
                if coin_id in coins:
                    category = cat
                    break
            
            results.append({
                "id": coin_id,
                "symbol": coin.get("symbol", "").upper(),
                "name": coin.get("name", ""),
                "price": coin.get("current_price", 0),
                "market_cap": coin.get("market_cap", 0),
                "market_cap_rank": coin.get("market_cap_rank", 0),
                "volume_24h": coin.get("total_volume", 0),
                "change_24h": coin.get("price_change_percentage_24h", 0),
                "change_7d": coin.get("price_change_percentage_7d_in_currency", 0),
                "high_24h": coin.get("high_24h", 0),
                "low_24h": coin.get("low_24h", 0),
                "ath": coin.get("ath", 0),  # All Time High
                "ath_change_pct": coin.get("ath_change_percentage", 0),
                "is_meme": is_meme,
                "category": category,
                "image": coin.get("image", ""),
            })
        
        return results
    
    def parse(self, raw_data: Dict[str, Any]) -> List[CryptoData]:
        """
        解析原始数据为标准格式
        
        Args:
            raw_data: fetch() 返回的原始数据
            
        Returns:
            CryptoData 列表
        """
        results = []
        coins_data = raw_data.get("coins", [])
        timestamp = raw_data.get("timestamp", datetime.now())
        
        for coin in coins_data:
            results.append(CryptoData(
                symbol=coin.get("symbol", ""),
                name=coin.get("name", ""),
                price_usd=coin.get("price", 0),
                change_24h=coin.get("change_24h", 0),
                change_7d=coin.get("change_7d", 0),
                market_cap=coin.get("market_cap", 0),
                volume_24h=coin.get("volume_24h", 0),
                is_meme=coin.get("is_meme", False),
                category=coin.get("category", "other"),
                timestamp=timestamp
            ))
        
        return results
    
    # ==================== 便捷方法 ====================
    
    def get_mainstream_coins(self) -> List[Dict]:
        """获取主流币数据"""
        all_data = self._fetch_market_data()
        return [c for c in all_data if c.get("category") == "mainstream"]
    
    def get_meme_coins(self) -> List[Dict]:
        """获取 Meme 币数据"""
        all_data = self._fetch_market_data()
        return [c for c in all_data if c.get("is_meme", False)]
    
    def get_top_gainers(self, n: int = 5, timeframe: str = "24h") -> List[Dict]:
        """
        获取涨幅最大的币种
        
        Args:
            n: 返回数量
            timeframe: "24h" 或 "7d"
        """
        all_data = self._fetch_market_data()
        key = "change_24h" if timeframe == "24h" else "change_7d"
        sorted_data = sorted(all_data, key=lambda x: x.get(key, 0) or 0, reverse=True)
        return sorted_data[:n]
    
    def get_top_losers(self, n: int = 5, timeframe: str = "24h") -> List[Dict]:
        """
        获取跌幅最大的币种
        
        Args:
            n: 返回数量
            timeframe: "24h" 或 "7d"
        """
        all_data = self._fetch_market_data()
        key = "change_24h" if timeframe == "24h" else "change_7d"
        sorted_data = sorted(all_data, key=lambda x: x.get(key, 0) or 0)
        return sorted_data[:n]
    
    def get_btc_dominance(self) -> Optional[float]:
        """
        获取 BTC 市场占有率（需要额外 API 调用）
        """
        try:
            if self.use_pycoingecko:
                global_data = self.cg.get_global()
            else:
                url = f"{self.COINGECKO_API_BASE}/global"
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                global_data = response.json().get("data", {})
            
            return global_data.get("market_cap_percentage", {}).get("btc", 0)
        except Exception as e:
            logger.error(f"Error fetching BTC dominance: {e}")
            return None
