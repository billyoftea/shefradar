"""
期货市场数据抓取器

基于 AkShare 开源库实现
GitHub: https://github.com/akfamily/akshare

支持获取:
- 国内商品期货 (新浪/东方财富)
- 股指期货 (IF/IC/IH)
- 国际原油 (通过 yfinance)
- 主要商品持仓数据

安装: pip install akshare>=1.12.0
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    ak = None

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    yf = None

from . import BaseFetcher
from ..models.market_data import FuturesData

logger = logging.getLogger(__name__)


class FuturesFetcher(BaseFetcher):
    """
    期货市场数据抓取器
    
    基于 AkShare + yfinance 实现，支持:
    - 国内商品期货主力合约
    - 股指期货 (IF/IC/IH/IM)
    - 国际原油 (WTI/Brent)
    - 主要农产品期货
    """
    
    # 国内主要商品期货代码 (主力合约)
    COMMODITY_FUTURES = {
        # 贵金属
        "AU": {"name": "沪金", "exchange": "SHFE"},
        "AG": {"name": "沪银", "exchange": "SHFE"},
        # 有色金属
        "CU": {"name": "沪铜", "exchange": "SHFE"},
        "AL": {"name": "沪铝", "exchange": "SHFE"},
        # 黑色系
        "RB": {"name": "螺纹钢", "exchange": "SHFE"},
        "I": {"name": "铁矿石", "exchange": "DCE"},
        "J": {"name": "焦炭", "exchange": "DCE"},
        # 能源化工
        "SC": {"name": "原油", "exchange": "INE"},
        "FU": {"name": "燃油", "exchange": "SHFE"},
        # 农产品
        "A": {"name": "豆一", "exchange": "DCE"},
        "M": {"name": "豆粕", "exchange": "DCE"},
        "OI": {"name": "菜油", "exchange": "CZCE"},
    }
    
    # 股指期货
    INDEX_FUTURES = {
        "IF": {"name": "沪深300期货", "underlying": "沪深300"},
        "IC": {"name": "中证500期货", "underlying": "中证500"},
        "IH": {"name": "上证50期货", "underlying": "上证50"},
        "IM": {"name": "中证1000期货", "underlying": "中证1000"},
    }
    
    # 国际期货 (Yahoo Finance)
    INTERNATIONAL_FUTURES = {
        "CL=F": {"name": "WTI原油", "unit": "美元/桶"},
        "BZ=F": {"name": "布伦特原油", "unit": "美元/桶"},
        "NG=F": {"name": "天然气", "unit": "美元/MMBtu"},
        "HG=F": {"name": "COMEX铜", "unit": "美元/磅"},
    }
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        
        if not AKSHARE_AVAILABLE:
            logger.warning("akshare not installed. Run: pip install akshare")
        
        if not YFINANCE_AVAILABLE:
            logger.warning("yfinance not installed. International futures disabled.")
        
        # 配置要获取的期货类型
        self.fetch_commodity = self.config.get("fetch_commodity", True)
        self.fetch_index_futures = self.config.get("fetch_index_futures", True)
        self.fetch_international = self.config.get("fetch_international", True)
        
        # 指定要获取的商品期货代码
        self.commodity_codes = self.config.get(
            "commodity_codes", 
            ["AU", "AG", "CU", "RB", "I", "SC"]
        )
    
    async def fetch(self) -> Dict[str, Any]:
        """
        抓取期货市场数据
        
        Returns:
            包含各类期货数据的字典
        """
        loop = asyncio.get_event_loop()
        tasks = []
        
        if self.fetch_commodity and AKSHARE_AVAILABLE:
            tasks.append(("commodity", loop.run_in_executor(None, self._fetch_commodity_futures)))
        
        if self.fetch_index_futures and AKSHARE_AVAILABLE:
            tasks.append(("index", loop.run_in_executor(None, self._fetch_index_futures)))
        
        if self.fetch_international and YFINANCE_AVAILABLE:
            tasks.append(("international", loop.run_in_executor(None, self._fetch_international_futures)))
        
        # 执行所有任务
        results = {}
        for name, task in tasks:
            try:
                result = await task
                results[name] = result if not isinstance(result, Exception) else []
            except Exception as e:
                logger.error(f"Error fetching {name} futures: {e}")
                results[name] = []
        
        return {
            "commodity": results.get("commodity", []),
            "index_futures": results.get("index", []),
            "international": results.get("international", []),
            "timestamp": datetime.now()
        }
    
    def _fetch_commodity_futures(self) -> List[Dict]:
        """获取国内商品期货主力合约数据
        
        使用 futures_spot_price 接口获取最新现货价和主力合约价格
        """
        from datetime import datetime, timedelta
        
        results = []
        
        # 尝试获取最近交易日的数据（可能周末需要回溯）
        for days_back in range(5):
            try:
                check_date = datetime.now() - timedelta(days=days_back)
                date_str = check_date.strftime('%Y-%m-%d')
                
                df = ak.futures_spot_price(date=date_str)
                if df is not None and not df.empty:
                    break
            except:
                continue
        else:
            logger.warning("无法获取期货数据，可能是节假日")
            return results
        
        for code in self.commodity_codes:
            if code not in self.COMMODITY_FUTURES:
                continue
            
            info = self.COMMODITY_FUTURES[code]
            
            try:
                # 筛选对应品种的数据
                code_data = df[df['symbol'].str.upper() == code.upper()]
                
                if code_data.empty:
                    continue
                
                row = code_data.iloc[0]
                
                # 获取主力合约价格
                price = float(row.get('dominant_contract_price', 0))
                spot_price = float(row.get('spot_price', 0))
                
                # 基差率作为参考
                basis_rate = float(row.get('dom_basis_rate', 0)) * 100  # 转为百分比
                
                results.append({
                    "code": code,
                    "name": info["name"],
                    "exchange": info["exchange"],
                    "price": round(price, 2),
                    "spot_price": round(spot_price, 2),
                    "dominant_contract": row.get('dominant_contract', ''),
                    "basis_rate": round(basis_rate, 2),  # 基差率 (%)
                    "change": 0,  # 无法直接获取涨跌
                    "change_pct": 0,
                    "type": "commodity",
                })
            except Exception as e:
                logger.error(f"Error processing futures {code}: {e}")
                continue
        
        return results
    
    def _fetch_index_futures(self) -> List[Dict]:
        """获取股指期货数据
        
        使用 get_cffex_daily 获取中金所股指期货数据
        """
        from datetime import datetime, timedelta
        
        results = []
        
        try:
            # 尝试获取最近交易日的数据
            for days_back in range(5):
                check_date = datetime.now() - timedelta(days=days_back)
                date_str = check_date.strftime('%Y%m%d')
                
                try:
                    df = ak.get_cffex_daily(date=date_str)
                    if df is not None and not df.empty:
                        break
                except:
                    continue
            else:
                return results
            
            # 筛选股指期货品种
            for prefix, info in self.INDEX_FUTURES.items():
                # 筛选以该前缀开头的合约，选取成交量最大的主力合约
                prefix_data = df[df['variety'].str.upper().str.startswith(prefix)]
                
                if prefix_data.empty:
                    continue
                
                # 按成交量排序，取主力合约
                if 'volume' in prefix_data.columns:
                    main_contract = prefix_data.sort_values('volume', ascending=False).iloc[0]
                else:
                    main_contract = prefix_data.iloc[0]
                
                price = float(main_contract.get('close', 0))
                prev_close = float(main_contract.get('pre_settle', 0))
                
                change = price - prev_close if prev_close > 0 else 0
                change_pct = (change / prev_close * 100) if prev_close > 0 else 0
                
                results.append({
                    "code": main_contract.get('variety', prefix),
                    "name": info["name"],
                    "underlying": info["underlying"],
                    "price": round(price, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                    "type": "index",
                })
        except Exception as e:
            logger.error(f"Error fetching index futures: {e}")
        
        return results
    
    def _fetch_international_futures(self) -> List[Dict]:
        """获取国际期货数据 (通过 yfinance)"""
        results = []
        
        for symbol, info in self.INTERNATIONAL_FUTURES.items():
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="5d")
                
                if hist.empty:
                    continue
                
                latest = hist.iloc[-1]
                prev = hist.iloc[-2] if len(hist) > 1 else latest
                
                price = float(latest["Close"])
                prev_close = float(prev["Close"])
                change = price - prev_close
                change_pct = (change / prev_close * 100) if prev_close != 0 else 0
                
                results.append({
                    "code": symbol,
                    "name": info["name"],
                    "price": round(price, 2),
                    "change": round(change, 2),
                    "change_pct": round(change_pct, 2),
                    "unit": info["unit"],
                    "type": "international",
                })
            except Exception as e:
                logger.error(f"Error fetching {symbol}: {e}")
                continue
        
        return results
    
    def parse(self, raw_data: Dict[str, Any]) -> Dict[str, List[FuturesData]]:
        """
        解析原始数据为标准格式
        
        Args:
            raw_data: fetch() 返回的原始数据
            
        Returns:
            按类别组织的 FuturesData 字典
        """
        timestamp = raw_data.get("timestamp", datetime.now())
        
        def convert_futures(futures_list: List[Dict]) -> List[FuturesData]:
            return [
                FuturesData(
                    code=f.get("code", ""),
                    name=f.get("name", ""),
                    price=f.get("price", 0),
                    change=f.get("change", 0),
                    change_pct=f.get("change_pct", 0),
                    futures_type=f.get("type", ""),
                    timestamp=timestamp
                )
                for f in futures_list
            ]
        
        return {
            "commodity": convert_futures(raw_data.get("commodity", [])),
            "index_futures": convert_futures(raw_data.get("index_futures", [])),
            "international": convert_futures(raw_data.get("international", [])),
        }
    
    # ==================== 便捷方法 ====================
    
    def get_precious_metal_futures(self) -> List[Dict]:
        """获取贵金属期货（沪金、沪银）"""
        original_codes = self.commodity_codes
        self.commodity_codes = ["AU", "AG"]
        
        result = self._fetch_commodity_futures()
        
        self.commodity_codes = original_codes
        return result
    
    def get_energy_futures(self) -> List[Dict]:
        """获取能源期货"""
        return self._fetch_international_futures()
    
    def get_oil_price(self) -> Optional[Dict]:
        """快速获取原油价格"""
        for symbol in ["CL=F", "BZ=F"]:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="2d")
                if not hist.empty:
                    return {
                        "symbol": symbol,
                        "name": self.INTERNATIONAL_FUTURES[symbol]["name"],
                        "price": round(float(hist.iloc[-1]["Close"]), 2)
                    }
            except:
                continue
        return None
