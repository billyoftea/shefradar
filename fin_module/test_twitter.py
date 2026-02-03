"""
Twitter Fetcher 测试脚本

测试 Twitter/X API 数据获取功能
需要配置 Bearer Token
"""

import asyncio
import sys
sys.path.insert(0, '/Users/angeloxu/Desktop/finradar')

from datetime import datetime


# 配置你的 Twitter Bearer Token
TWITTER_BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAAA9c7QEAAAAAhJ8YJSv%2FRNDiGvHzvA0iTcj37rA%3DngE5Qv4qc6ZMTYe6tnnEt0Qsqjf6ENf4pRNSFyxzZPPFw6hNO0"


def test_separator(title: str):
    """打印分隔线"""
    print("\n" + "=" * 70)
    print(f"🐦 {title}")
    print("=" * 70)


def test_twitter_fetcher():
    """测试 Twitter 数据抓取"""
    test_separator("Twitter Fetcher 测试 (需要 Bearer Token)")
    
    try:
        from fin_module.fetcher.twitter import TwitterFetcher, TWEEPY_AVAILABLE
        
        print(f"\n📦 依赖检查:")
        print(f"   - tweepy: {'✅ 已安装' if TWEEPY_AVAILABLE else '❌ 未安装'}")
        
        if not TWEEPY_AVAILABLE:
            print("\n⚠️ tweepy 未安装，请运行:")
            print("   pip install tweepy>=4.14.0")
            return False
        
        # 初始化 fetcher，配置 Bearer Token
        fetcher = TwitterFetcher(config={
            "bearer_token": TWITTER_BEARER_TOKEN,
            "accounts_to_follow": [
                "VitalikButerin",   # 以太坊创始人
                "elonmusk",         # Elon Musk
                "WatcherGuru",      # 加密新闻
            ]
        })
        
        print(f"\n✅ Fetcher 初始化状态:")
        print(f"   - 启用状态: {fetcher.enabled}")
        
        if not fetcher.enabled:
            print("\n❌ Twitter Fetcher 未启用")
            print("   可能原因:")
            print("   1. Bearer Token 无效")
            print("   2. API 权限不足")
            return False
        
        print(f"   - 关注账号数: {len(fetcher.accounts_to_follow)}")
        print(f"   - 关注列表: {', '.join(['@' + a for a in fetcher.accounts_to_follow])}")
        
        # 测试1: 获取单个用户推文
        print("\n📊 测试1: 获取 Vitalik Buterin 最新推文")
        print("-" * 50)
        
        try:
            tweets = fetcher._get_user_recent_tweets("VitalikButerin", max_results=3)
            if tweets:
                print(f"✅ 成功获取 {len(tweets)} 条推文\n")
                for i, tweet in enumerate(tweets, 1):
                    print(f"  [{i}] @{tweet.get('author', 'Unknown')}")
                    print(f"      {tweet.get('text', '')[:100]}...")
                    print(f"      ❤️ {tweet.get('like_count', 0)} | 🔁 {tweet.get('retweet_count', 0)} | 💬 {tweet.get('reply_count', 0)}")
                    print(f"      🔗 {tweet.get('url', '')}")
                    print()
            else:
                print("  ⚠️ 未获取到推文（账号可能无最新发言）")
        except Exception as e:
            print(f"  ❌ 获取失败: {e}")
        
        # 测试2: 获取 Elon Musk 推文
        print("\n📊 测试2: 获取 Elon Musk 最新推文")
        print("-" * 50)
        
        try:
            tweets = fetcher._get_user_recent_tweets("elonmusk", max_results=3)
            if tweets:
                print(f"✅ 成功获取 {len(tweets)} 条推文\n")
                for i, tweet in enumerate(tweets, 1):
                    print(f"  [{i}] @{tweet.get('author', 'Unknown')}")
                    text = tweet.get('text', '')[:80]
                    print(f"      {text}{'...' if len(tweet.get('text', '')) > 80 else ''}")
                    print(f"      ❤️ {tweet.get('like_count', 0):,} | 🔁 {tweet.get('retweet_count', 0):,}")
                    print()
            else:
                print("  ⚠️ 未获取到推文")
        except Exception as e:
            print(f"  ❌ 获取失败: {e}")
        
        # 测试3: 异步获取所有关注用户推文
        print("\n📊 测试3: 异步获取所有关注用户推文")
        print("-" * 50)
        
        async def async_test():
            return await fetcher.fetch()
        
        try:
            result = asyncio.run(async_test())
            tweets = result.get("tweets", [])
            
            if tweets:
                print(f"✅ 成功获取 {len(tweets)} 条推文\n")
                
                # 按点赞数排序显示 Top 5
                sorted_tweets = sorted(tweets, key=lambda x: x.get('like_count', 0), reverse=True)[:5]
                
                print("  🔥 热门推文 Top 5 (按点赞数):")
                for i, tweet in enumerate(sorted_tweets, 1):
                    print(f"\n  [{i}] @{tweet.get('author', 'Unknown')} - ❤️ {tweet.get('like_count', 0):,}")
                    text = tweet.get('text', '')[:60]
                    print(f"      {text}{'...' if len(tweet.get('text', '')) > 60 else ''}")
            else:
                print("  ⚠️ 未获取到推文")
        except Exception as e:
            print(f"  ❌ 异步获取失败: {e}")
        
        # 测试4: 获取加密货币 KOL 推荐账号
        print("\n📊 测试4: 推荐关注的 KOL 账号")
        print("-" * 50)
        
        print("\n  💰 加密货币/Web3:")
        for acc in fetcher.RECOMMENDED_ACCOUNTS.get("crypto", []):
            print(f"     • @{acc}")
        
        print("\n  🤖 科技/AI:")
        for acc in fetcher.RECOMMENDED_ACCOUNTS.get("tech", []):
            print(f"     • @{acc}")
        
        print("\n  📈 宏观经济/金融:")
        for acc in fetcher.RECOMMENDED_ACCOUNTS.get("finance", []):
            print(f"     • @{acc}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "🐦" * 35)
    print("     FinRadar Twitter Fetcher 测试")
    print("🐦" * 35)
    print(f"\n⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if not TWITTER_BEARER_TOKEN or TWITTER_BEARER_TOKEN == "your_bearer_token_here":
        print("\n❌ 请先配置 TWITTER_BEARER_TOKEN")
        print("   在脚本顶部设置你的 Bearer Token")
        return
    
    print(f"\n🔑 Bearer Token: {TWITTER_BEARER_TOKEN[:20]}...{TWITTER_BEARER_TOKEN[-10:]}")
    
    success = test_twitter_fetcher()
    
    # 结果汇总
    print("\n" + "=" * 70)
    print("📋 测试结果")
    print("=" * 70)
    
    if success:
        print("\n✅ Twitter Fetcher 测试通过！")
        print("\n💡 使用提示:")
        print("   - 免费 API 每月有请求限制 (约 10,000 次读取)")
        print("   - 建议添加缓存机制减少 API 调用")
        print("   - 可以修改 accounts_to_follow 关注更多 KOL")
    else:
        print("\n❌ Twitter Fetcher 测试失败")
        print("\n🔧 排查步骤:")
        print("   1. 确认 Bearer Token 正确")
        print("   2. 确认已安装 tweepy: pip install tweepy>=4.14.0")
        print("   3. 检查网络连接（可能需要代理）")


if __name__ == "__main__":
    main()
