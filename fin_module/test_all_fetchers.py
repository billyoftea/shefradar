"""
Fetcher 综合测试脚本 - 无需 API Key 版本

测试以下数据源：
1. CryptoFetcher - 加密货币 (CoinGecko)
2. PreciousMetalFetcher - 贵金属 (Yahoo Finance)  
3. FuturesFetcher - 期货 (AkShare + yfinance)
4. StockCNFetcher - A股市场 (AkShare)

Twitter 需要 API Key，不在此测试范围内
"""

import asyncio
import sys
import time
sys.path.insert(0, '/Users/angeloxu/Desktop/finradar')

from datetime import datetime


def test_separator(title: str):
    """打印分隔线"""
    print("\n" + "=" * 70)
    print(f"🧪 {title}")
    print("=" * 70)


def test_crypto_fetcher():
    """测试加密货币数据抓取"""
    test_separator("加密货币 Fetcher 测试 (CoinGecko - 无需 API Key)")
    
    try:
        from fin_module.fetcher.crypto import CryptoFetcher
        
        fetcher = CryptoFetcher(config={
            "coins": ["bitcoin", "ethereum", "solana", "dogecoin", "pepe"],
            "vs_currency": "usd"
        })
        
        print(f"\n✅ Fetcher 初始化成功")
        print(f"   - 启用状态: {fetcher.enabled}")
        print(f"   - 使用 pycoingecko: {fetcher.use_pycoingecko}")
        
        # 测试1: 获取市场数据 (只调用一次API，缓存结果)
        print("\n📊 测试1: 获取加密货币市场数据")
        print("-" * 50)
        
        coins_data = fetcher._fetch_market_data()
        print(f"✅ 获取成功，共 {len(coins_data)} 个币种\n")
        
        for coin in coins_data:
            icon = "🐶" if coin.get("is_meme") else "💰"
            change = coin.get('change_24h', 0) or 0
            change_icon = "📈" if change >= 0 else "📉"
            print(f"  {icon} {coin['symbol']}: ${coin['price']:,.2f}  {change_icon} {change:+.2f}%")
            print(f"     市值: ${coin['market_cap']:,.0f} | 排名: #{coin['market_cap_rank']}")
        
        # 测试2: 涨跌幅排行 - 使用已获取的数据，避免重复API调用
        print("\n📊 测试2: 24h 涨幅榜 Top 3 (使用缓存数据)")
        print("-" * 50)
        
        # 直接对已有数据排序，而不是再次调用API
        sorted_data = sorted(coins_data, key=lambda x: x.get('change_24h', 0) or 0, reverse=True)
        gainers = sorted_data[:3]
        for i, coin in enumerate(gainers, 1):
            print(f"  {i}. {coin['symbol']}: {coin.get('change_24h', 0):+.2f}%")
        
        # 测试3: Meme 币专项 - 使用已获取的数据
        print("\n🐕 测试3: Meme 币数据 (使用缓存数据)")
        print("-" * 50)
        
        # 直接从已有数据筛选
        meme_coins = [c for c in coins_data if c.get("is_meme", False)]
        if meme_coins:
            for coin in meme_coins:
                print(f"  🎭 {coin['name']} ({coin['symbol']}): ${coin['price']:.6f}")
        else:
            print("  暂无 Meme 币数据")
        
        # 测试4: BTC 市场占有率 - 这个需要单独API调用
        print("\n📊 测试4: BTC 市场占有率")
        print("-" * 50)
        
        btc_dominance = fetcher.get_btc_dominance()
        if btc_dominance:
            print(f"  ₿ BTC Dominance: {btc_dominance:.2f}%")
        else:
            print("  获取失败（可能触发速率限制）")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_precious_metal_fetcher():
    """测试贵金属数据抓取"""
    test_separator("贵金属 Fetcher 测试 (Yahoo Finance - 无需 API Key)")
    
    try:
        from fin_module.fetcher.precious_metal import PreciousMetalFetcher
        
        fetcher = PreciousMetalFetcher(config={
            "metals": ["gold", "silver", "platinum", "palladium"]
        })
        
        print(f"\n✅ Fetcher 初始化成功")
        print(f"   - 启用状态: {fetcher.enabled}")
        
        # 测试1: 获取黄金价格
        print("\n🥇 测试1: 获取黄金价格")
        print("-" * 50)
        
        gold = fetcher.get_gold_price()
        if gold:
            change = gold.get('change_pct', 0)
            change_icon = "📈" if change >= 0 else "📉"
            print(f"  💰 {gold['name']}: ${gold['price']:.2f} {gold['unit']}")
            print(f"     {change_icon} 涨跌: {gold['change']:+.2f} ({change:+.2f}%)")
            print(f"     📊 开盘: ${gold['open']:.2f} | 最高: ${gold['high']:.2f} | 最低: ${gold['low']:.2f}")
        else:
            print("  ❌ 获取失败")
        
        # 测试2: 获取白银价格
        print("\n🥈 测试2: 获取白银价格")
        print("-" * 50)
        
        silver = fetcher.get_silver_price()
        if silver:
            change = silver.get('change_pct', 0)
            change_icon = "📈" if change >= 0 else "📉"
            print(f"  💰 {silver['name']}: ${silver['price']:.2f} {silver['unit']}")
            print(f"     {change_icon} 涨跌: {silver['change']:+.2f} ({change:+.2f}%)")
        else:
            print("  ❌ 获取失败")
        
        # 测试3: 金银比
        print("\n⚖️ 测试3: 金银比计算")
        print("-" * 50)
        
        ratio = fetcher.get_gold_silver_ratio()
        if ratio:
            status = "白银相对便宜 💡" if ratio > 80 else ("黄金相对便宜 💡" if ratio < 50 else "正常区间")
            print(f"  📊 金银比: {ratio:.2f}")
            print(f"     历史均值: ~60 | 当前状态: {status}")
        else:
            print("  ❌ 计算失败")
        
        # 测试4: 异步获取所有贵金属
        print("\n🔄 测试4: 异步获取所有贵金属")
        print("-" * 50)
        
        async def async_test():
            raw_data = await fetcher.fetch()
            return raw_data
        
        raw_data = asyncio.run(async_test())
        metals = raw_data.get("metals", {})
        
        for metal_key, data in metals.items():
            if data:
                print(f"  ✅ {data['name']}: ${data['price']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_futures_fetcher():
    """测试期货数据抓取"""
    test_separator("期货 Fetcher 测试 (AkShare + yfinance - 无需 API Key)")
    
    try:
        from fin_module.fetcher.futures import FuturesFetcher, AKSHARE_AVAILABLE, YFINANCE_AVAILABLE
        
        print(f"\n📦 依赖检查:")
        print(f"   - akshare: {'✅ 已安装' if AKSHARE_AVAILABLE else '❌ 未安装'}")
        print(f"   - yfinance: {'✅ 已安装' if YFINANCE_AVAILABLE else '❌ 未安装'}")
        
        fetcher = FuturesFetcher(config={
            "fetch_commodity": AKSHARE_AVAILABLE,
            "fetch_index_futures": False,  # 股指期货接口可能不稳定，暂时跳过
            "fetch_international": YFINANCE_AVAILABLE,
            "commodity_codes": ["AU", "AG", "CU"]  # 只测试几个
        })
        
        print(f"\n✅ Fetcher 初始化成功")
        
        # 测试1: 国际期货 (WTI原油等)
        if YFINANCE_AVAILABLE:
            print("\n🛢️ 测试1: 国际期货 (yfinance)")
            print("-" * 50)
            
            intl_futures = fetcher._fetch_international_futures()
            if intl_futures:
                for f in intl_futures:
                    change = f.get('change_pct', 0)
                    change_icon = "📈" if change >= 0 else "📉"
                    print(f"  🌍 {f['name']}: ${f['price']:.2f} {f.get('unit', '')}")
                    print(f"     {change_icon} 涨跌: {change:+.2f}%")
            else:
                print("  暂无数据")
        
        # 测试2: 原油价格快捷方法
        if YFINANCE_AVAILABLE:
            print("\n🛢️ 测试2: 原油价格快捷获取")
            print("-" * 50)
            
            oil = fetcher.get_oil_price()
            if oil:
                print(f"  ⛽ {oil['name']}: ${oil['price']:.2f}/桶")
            else:
                print("  ❌ 获取失败")
        
        # 测试3: 国内商品期货 (需要 akshare)
        if AKSHARE_AVAILABLE:
            print("\n📊 测试3: 国内商品期货 (akshare)")
            print("-" * 50)
            print("  ⏳ 正在获取数据（akshare 可能较慢）...")
            
            try:
                commodity = fetcher._fetch_commodity_futures()
                if commodity:
                    for f in commodity:
                        basis_rate = f.get('basis_rate', 0)
                        basis_icon = "⬆️" if basis_rate >= 0 else "⬇️"
                        print(f"  🏭 {f['name']} ({f['code']})")
                        print(f"     主力合约 ({f.get('dominant_contract', 'N/A')}): ¥{f['price']:.2f}")
                        print(f"     现货价格: ¥{f.get('spot_price', 0):.2f} | {basis_icon} 基差率: {basis_rate:+.2f}%")
                else:
                    print("  ⚠️ 获取数据为空（可能是非交易时段）")
            except Exception as e:
                print(f"  ⚠️ 获取失败（可能是非交易时段）: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_stock_cn_fetcher():
    """测试 A 股数据抓取"""
    test_separator("A股 Fetcher 测试 (AkShare - 无需 API Key)")
    
    try:
        from fin_module.fetcher.stock_cn import StockCNFetcher, AKSHARE_AVAILABLE
        
        print(f"\n📦 依赖检查:")
        print(f"   - akshare: {'✅ 已安装' if AKSHARE_AVAILABLE else '❌ 未安装'}")
        
        if not AKSHARE_AVAILABLE:
            print("\n⚠️ akshare 未安装，跳过测试")
            print("   安装命令: pip install akshare")
            return False
        
        fetcher = StockCNFetcher()
        
        print(f"\n✅ Fetcher 初始化成功")
        print(f"   - 启用状态: {fetcher.enabled}")
        
        # 测试1: 获取主要指数
        print("\n📊 测试1: 获取主要指数")
        print("-" * 50)
        print("  ⏳ 正在获取数据...")
        
        try:
            indices = fetcher._fetch_indices()
            if indices:
                for idx in indices:
                    change = idx.get('change_pct', 0)
                    change_icon = "📈" if change >= 0 else "📉"
                    print(f"  📌 {idx['name']}: {idx['price']:.2f}")
                    print(f"     {change_icon} 涨跌: {change:+.2f}%")
            else:
                print("  ⚠️ 获取数据为空（可能是非交易时段）")
        except Exception as e:
            print(f"  ⚠️ 获取失败: {e}")
        
        # 测试2: 获取北向资金
        print("\n💰 测试2: 获取北向资金")
        print("-" * 50)
        
        try:
            north_flow = fetcher._fetch_north_flow()
            if north_flow:
                flow = north_flow.get('net_flow', 0)
                flow_icon = "📈" if flow >= 0 else "📉"
                print(f"  {flow_icon} 北向资金净流入: {flow:.2f} 亿元")
                print(f"     日期: {north_flow.get('date', 'N/A')}")
            else:
                print("  ⚠️ 获取数据为空")
        except Exception as e:
            print(f"  ⚠️ 获取失败: {e}")
        
        # 测试3: 获取行业板块 Top 5
        print("\n📊 测试3: 行业板块涨幅 Top 5")
        print("-" * 50)
        
        try:
            top_sectors = fetcher.get_top_sectors(n=5, ascending=False)
            if top_sectors:
                for i, sector in enumerate(top_sectors, 1):
                    change = sector.get('change_pct', 0)
                    print(f"  {i}. {sector['name']}: {change:+.2f}%")
                    if sector.get('leading_stock'):
                        print(f"     领涨股: {sector['leading_stock']}")
            else:
                print("  ⚠️ 获取数据为空")
        except Exception as e:
            print(f"  ⚠️ 获取失败: {e}")
        
        # 测试4: 涨跌停统计
        print("\n📊 测试4: 涨跌停统计")
        print("-" * 50)
        
        try:
            stats = fetcher._fetch_market_stats()
            if stats:
                print(f"  🔴 涨停家数: {stats.get('limit_up_count', 0)}")
                print(f"  🟢 跌停家数: {stats.get('limit_down_count', 0)}")
            else:
                print("  ⚠️ 获取数据为空")
        except Exception as e:
            print(f"  ⚠️ 获取失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "🚀" * 35)
    print("     FinRadar Fetcher 综合测试 - 无需 API Key 版本")
    print("🚀" * 35)
    print(f"\n⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # 测试1: 加密货币
    print("\n" + "▶" * 35)
    results["crypto"] = test_crypto_fetcher()
    time.sleep(1)  # 避免 API 限制
    
    # 测试2: 贵金属
    print("\n" + "▶" * 35)
    results["precious_metal"] = test_precious_metal_fetcher()
    time.sleep(1)
    
    # 测试3: 期货
    print("\n" + "▶" * 35)
    results["futures"] = test_futures_fetcher()
    time.sleep(1)
    
    # 测试4: A股
    print("\n" + "▶" * 35)
    results["stock_cn"] = test_stock_cn_fetcher()
    
    # 汇总结果
    print("\n" + "=" * 70)
    print("📋 测试结果汇总")
    print("=" * 70)
    
    for name, success in results.items():
        icon = "✅" if success else "❌"
        status = "成功" if success else "失败"
        print(f"  {icon} {name.replace('_', ' ').title()}: {status}")
    
    total = len(results)
    passed = sum(1 for s in results.values() if s)
    
    print(f"\n📊 总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有无需 API Key 的 Fetcher 测试通过！")
    else:
        print("\n⚠️ 部分测试未通过，请检查依赖安装或网络连接")
        print("   建议安装: pip install pycoingecko yfinance akshare")


if __name__ == "__main__":
    main()
