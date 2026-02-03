"""
A股市场数据抓取器

基于 AkShare 开源库实现
GitHub: https://github.com/akfamily/akshare
文档: https://akshare.akfamily.xyz/

AkShare 功能概览:
- 股票指数数据: ak.stock_zh_index_daily()
- 北向资金: ak.stock_em_hsgt_north_net_flow_in()
- 板块数据: ak.stock_board_industry_name_em()
- 概念板块: ak.stock_board_concept_name_em()
- 涨跌统计: ak.stock_changes_em()

安装: pip install akshare>=1.12.0
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    ak = None

from . import BaseFetcher
from ..models.market_data import IndexData, SectorData, MarketOverview

logger = logging.getLogger(__name__)


class StockCNFetcher(BaseFetcher):
    """
    A股数据抓取器
    
    基于 AkShare 实现，支持获取:
    - 主要指数数据（上证、沪深300、创业板等）
    - 北向资金流向
    - 行业板块涨跌
    - 概念板块涨跌
    - 涨跌家数统计
    """
    
    # 主要指数代码映射
    INDEX_MAPPING = {
        "上证指数": {"code": "000001", "market": "sh"},
        "深证成指": {"code": "399001", "market": "sz"},
        "沪深300": {"code": "000300", "market": "sh"},
        "创业板指": {"code": "399006", "market": "sz"},
        "科创50": {"code": "000688", "market": "sh"},
        "中证500": {"code": "000905", "market": "sh"},
    }
    
    # 重点关注板块分类（默认配置）
    DEFAULT_FOCUS_SECTORS = {
        "tech": ["电子", "计算机", "通信"],
        "cyclical": ["有色金属", "钢铁", "煤炭", "化工"],
        "agriculture": ["农林牧渔"],
        "consumption": ["食品饮料", "家用电器", "汽车"],
        "finance": ["银行", "非银金融", "房地产"],
    }
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        
        if not AKSHARE_AVAILABLE:
            logger.warning("akshare not installed. Run: pip install akshare")
            self.enabled = False
        
        # 合并默认配置和用户配置
        self.focus_sectors = self.config.get("focus_sectors", self.DEFAULT_FOCUS_SECTORS)
    
    async def fetch(self) -> Dict[str, Any]:
        """
        抓取所有A股相关数据
        
        Returns:
            包含指数、板块、资金流向等数据的字典
        """
        # 使用线程池执行同步的 akshare 调用
        loop = asyncio.get_event_loop()
        
        # 并行获取各类数据
        indices_task = loop.run_in_executor(None, self._fetch_indices)
        north_flow_task = loop.run_in_executor(None, self._fetch_north_flow)
        sectors_task = loop.run_in_executor(None, self._fetch_sectors)
        market_stats_task = loop.run_in_executor(None, self._fetch_market_stats)
        
        indices, north_flow, sectors, market_stats = await asyncio.gather(
            indices_task, north_flow_task, sectors_task, market_stats_task,
            return_exceptions=True
        )
        
        return {
            "indices": indices if not isinstance(indices, Exception) else None,
            "north_flow": north_flow if not isinstance(north_flow, Exception) else None,
            "sectors": sectors if not isinstance(sectors, Exception) else None,
            "market_stats": market_stats if not isinstance(market_stats, Exception) else None,
            "timestamp": datetime.now()
        }
    
    def _fetch_indices(self) -> List[Dict]:
        """获取主要指数数据"""
        results = []
        
        for name, info in self.INDEX_MAPPING.items():
            try:
                symbol = f"{info['market']}{info['code']}"
                df = ak.stock_zh_index_daily(symbol=symbol)
                
                if df.empty:
                    continue
                
                latest = df.iloc[-1]
                prev = df.iloc[-2] if len(df) > 1 else latest
                
                change = float(latest["close"]) - float(prev["close"])
                change_pct = (change / float(prev["close"])) * 100 if prev["close"] != 0 else 0
                
                results.append({
                    "name": name,
                    "code": info["code"],
                    "price": float(latest["close"]),
                    "change": change,
                    "change_pct": round(change_pct, 2),
                    "volume": float(latest["volume"]) if "volume" in latest else 0,
                    "open": float(latest["open"]),
                    "high": float(latest["high"]),
                    "low": float(latest["low"]),
                })
            except Exception as e:
                logger.error(f"Error fetching index {name}: {e}")
                continue
        
        return results
    
    def _fetch_north_flow(self) -> Dict:
        """获取北向资金数据
        
        使用 stock_hsgt_fund_flow_summary_em 接口获取当日北向资金流向
        """
        try:
            df = ak.stock_hsgt_fund_flow_summary_em()
            if df is None or df.empty:
                return {}
            
            # 筛选北向资金（沪股通 + 深股通）
            north_data = df[df['资金方向'] == '北向']
            if north_data.empty:
                return {}
            
            # 计算北向资金总净流入（沪股通 + 深股通）
            total_net_flow = north_data['成交净买额'].sum()
            trade_date = north_data.iloc[0].get('交易日', '')
            
            # 获取详细数据
            hu_data = north_data[north_data['板块'] == '沪股通']
            shen_data = north_data[north_data['板块'] == '深股通']
            
            return {
                "net_flow": round(float(total_net_flow), 2),  # 单位: 亿元
                "date": str(trade_date),
                "hu_net_flow": round(float(hu_data['成交净买额'].iloc[0]), 2) if not hu_data.empty else 0,
                "shen_net_flow": round(float(shen_data['成交净买额'].iloc[0]), 2) if not shen_data.empty else 0,
            }
        except Exception as e:
            logger.error(f"Error fetching north flow: {e}")
            return {}
    
    def _fetch_sectors(self) -> List[Dict]:
        """获取行业板块数据"""
        try:
            df = ak.stock_board_industry_name_em()
            results = []
            
            for _, row in df.iterrows():
                sector_name = row.get("板块名称", "")
                
                # 判断板块分类
                category = "other"
                for cat, names in self.focus_sectors.items():
                    if sector_name in names:
                        category = cat
                        break
                
                results.append({
                    "name": sector_name,
                    "change_pct": float(row.get("涨跌幅", 0)),
                    "turnover": float(row.get("换手率", 0)) if "换手率" in row else 0,
                    "volume": float(row.get("总成交量", 0)) if "总成交量" in row else 0,
                    "amount": float(row.get("总成交额", 0)) if "总成交额" in row else 0,
                    "leading_stock": row.get("领涨股票", ""),
                    "category": category,
                })
            
            return results
        except Exception as e:
            logger.error(f"Error fetching sectors: {e}")
            return []
    
    def _fetch_market_stats(self) -> Dict:
        """获取市场涨跌统计
        
        使用 stock_zt_pool_em 和 stock_zt_pool_dtgc_em 接口
        获取涨停板和跌停板数量
        """
        from datetime import datetime
        today = datetime.now().strftime('%Y%m%d')
        
        result = {
            "limit_up_count": 0,
            "limit_down_count": 0,
        }
        
        try:
            # 获取涨停板数据
            df_up = ak.stock_zt_pool_em(date=today)
            result["limit_up_count"] = len(df_up) if df_up is not None and not df_up.empty else 0
        except Exception as e:
            logger.error(f"Error fetching limit up stocks: {e}")
        
        try:
            # 获取跌停板数据 (跌停观察池)
            df_down = ak.stock_zt_pool_dtgc_em(date=today)
            result["limit_down_count"] = len(df_down) if df_down is not None and not df_down.empty else 0
        except Exception as e:
            logger.error(f"Error fetching limit down stocks: {e}")
        
        return result
    
    def parse(self, raw_data: Dict[str, Any]) -> MarketOverview:
        """
        解析原始数据为标准格式
        
        Args:
            raw_data: fetch() 返回的原始数据
            
        Returns:
            MarketOverview 数据模型
        """
        indices = []
        if raw_data.get("indices"):
            for idx in raw_data["indices"]:
                indices.append(IndexData(
                    name=idx["name"],
                    code=idx["code"],
                    price=idx["price"],
                    change=idx["change"],
                    change_pct=idx["change_pct"],
                    volume=idx["volume"],
                    timestamp=raw_data.get("timestamp", datetime.now())
                ))
        
        sectors = []
        if raw_data.get("sectors"):
            for sec in raw_data["sectors"]:
                sectors.append(SectorData(
                    name=sec["name"],
                    change_pct=sec["change_pct"],
                    leading_stocks=[sec.get("leading_stock", "")] if sec.get("leading_stock") else [],
                    category=sec["category"]
                ))
        
        north_flow = raw_data.get("north_flow", {})
        market_stats = raw_data.get("market_stats", {})
        
        return MarketOverview(
            timestamp=raw_data.get("timestamp", datetime.now()),
            indices=indices,
            sectors=sectors,
            north_flow_net=north_flow.get("net_flow", 0),
            limit_up_count=market_stats.get("limit_up_count", 0),
            limit_down_count=market_stats.get("limit_down_count", 0),
        )
    
    # ==================== 便捷方法 ====================
    
    def get_top_sectors(self, n: int = 5, ascending: bool = False) -> List[SectorData]:
        """
        获取涨幅/跌幅前N的板块
        
        Args:
            n: 返回数量
            ascending: True 返回跌幅最大的，False 返回涨幅最大的
        """
        sectors = self._fetch_sectors()
        sorted_sectors = sorted(sectors, key=lambda x: x["change_pct"], reverse=not ascending)
        return sorted_sectors[:n]
    
    def get_focus_sectors_summary(self) -> Dict[str, List[Dict]]:
        """
        获取重点关注板块的汇总
        
        Returns:
            按分类组织的板块数据
        """
        sectors = self._fetch_sectors()
        result = {cat: [] for cat in self.focus_sectors.keys()}
        
        for sector in sectors:
            if sector["category"] != "other":
                result[sector["category"]].append(sector)
        
        return result
