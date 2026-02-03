"""
贵金属数据抓取器

基于 yfinance 开源库实现
GitHub: https://github.com/ranaroussi/yfinance
文档: https://pypi.org/project/yfinance/

yfinance 功能概览:
- 黄金期货: GC=F (COMEX Gold)
- 白银期货: SI=F (COMEX Silver)
- 现货黄金: XAUUSD (通过其他方式)
- 铂金: PL=F
- 钯金: PA=F

安装: pip install yfinance>=0.2.36
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    yf = None

from . import BaseFetcher
from ..models.market_data import PreciousMetalData

logger = logging.getLogger(__name__)


class PreciousMetalFetcher(BaseFetcher):
    """
    贵金属数据抓取器
    
    基于 yfinance 实现，支持获取:
    - 黄金期货 (GC=F)
    - 白银期货 (SI=F)
    - 铂金期货 (PL=F)
    - 钯金期货 (PA=F)
    - 上海黄金 (可扩展使用 akshare)
    """
    
    # 贵金属代码映射 (Yahoo Finance 格式)
    METAL_MAPPING = {
        "gold": {
            "symbol": "GC=F",
            "name": "黄金",
            "name_en": "Gold",
            "unit": "美元/盎司"
        },
        "silver": {
            "symbol": "SI=F", 
            "name": "白银",
            "name_en": "Silver",
            "unit": "美元/盎司"
        },
        "platinum": {
            "symbol": "PL=F",
            "name": "铂金",
            "name_en": "Platinum",
            "unit": "美元/盎司"
        },
        "palladium": {
            "symbol": "PA=F",
            "name": "钯金",
            "name_en": "Palladium",
            "unit": "美元/盎司"
        },
    }
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        
        if not YFINANCE_AVAILABLE:
            logger.warning("yfinance not installed. Run: pip install yfinance")
            self.enabled = False
        
        # 默认获取的金属类型
        self.metals_to_fetch = self.config.get("metals", ["gold", "silver"])
    
    async def fetch(self) -> Dict[str, Any]:
        """
        抓取贵金属数据
        
        Returns:
            包含各贵金属价格数据的字典
        """
        loop = asyncio.get_event_loop()
        
        # 并行获取各金属数据
        tasks = []
        for metal_key in self.metals_to_fetch:
            if metal_key in self.METAL_MAPPING:
                task = loop.run_in_executor(
                    None, 
                    self._fetch_single_metal, 
                    metal_key
                )
                tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 组装结果
        data = {}
        for i, metal_key in enumerate(self.metals_to_fetch):
            if metal_key in self.METAL_MAPPING:
                result = results[i] if i < len(results) else None
                if not isinstance(result, Exception):
                    data[metal_key] = result
                else:
                    logger.error(f"Error fetching {metal_key}: {result}")
                    data[metal_key] = None
        
        return {
            "metals": data,
            "timestamp": datetime.now()
        }
    
    def _fetch_single_metal(self, metal_key: str) -> Dict:
        """
        获取单个贵金属数据
        
        Args:
            metal_key: 金属键名 (gold, silver, platinum, palladium)
        """
        metal_info = self.METAL_MAPPING.get(metal_key)
        if not metal_info:
            return {}
        
        try:
            ticker = yf.Ticker(metal_info["symbol"])
            
            # 获取历史数据（最近2天用于计算涨跌）
            hist = ticker.history(period="5d")
            
            if hist.empty:
                logger.warning(f"No data for {metal_key}")
                return {}
            
            latest = hist.iloc[-1]
            prev = hist.iloc[-2] if len(hist) > 1 else latest
            
            price = float(latest["Close"])
            prev_close = float(prev["Close"])
            change = price - prev_close
            change_pct = (change / prev_close * 100) if prev_close != 0 else 0
            
            return {
                "symbol": metal_info["symbol"],
                "name": metal_info["name"],
                "name_en": metal_info["name_en"],
                "price": round(price, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "open": round(float(latest["Open"]), 2),
                "high": round(float(latest["High"]), 2),
                "low": round(float(latest["Low"]), 2),
                "volume": int(latest["Volume"]) if "Volume" in latest else 0,
                "unit": metal_info["unit"],
                "prev_close": round(prev_close, 2),
            }
        except Exception as e:
            logger.error(f"Error fetching {metal_key}: {e}")
            return {}
    
    def parse(self, raw_data: Dict[str, Any]) -> List[PreciousMetalData]:
        """
        解析原始数据为标准格式
        
        Args:
            raw_data: fetch() 返回的原始数据
            
        Returns:
            PreciousMetalData 列表
        """
        results = []
        metals_data = raw_data.get("metals", {})
        timestamp = raw_data.get("timestamp", datetime.now())
        
        for metal_key, data in metals_data.items():
            if data:
                results.append(PreciousMetalData(
                    symbol=data.get("symbol", ""),
                    name=data.get("name", ""),
                    name_en=data.get("name_en", ""),
                    price=data.get("price", 0),
                    change=data.get("change", 0),
                    change_pct=data.get("change_pct", 0),
                    unit=data.get("unit", ""),
                    timestamp=timestamp
                ))
        
        return results
    
    # ==================== 便捷方法 ====================
    
    def get_gold_price(self) -> Optional[Dict]:
        """快速获取黄金价格"""
        return self._fetch_single_metal("gold")
    
    def get_silver_price(self) -> Optional[Dict]:
        """快速获取白银价格"""
        return self._fetch_single_metal("silver")
    
    def get_gold_silver_ratio(self) -> Optional[float]:
        """
        计算金银比（黄金价格/白银价格）
        
        金银比是重要的市场指标：
        - 历史均值约 60:1
        - 高于 80 通常表示白银相对便宜
        - 低于 50 通常表示黄金相对便宜
        """
        gold = self._fetch_single_metal("gold")
        silver = self._fetch_single_metal("silver")
        
        if gold and silver and silver.get("price", 0) > 0:
            return round(gold["price"] / silver["price"], 2)
        return None
