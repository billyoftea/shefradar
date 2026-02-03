"""
Nitter RSS Fetcher 测试脚本

测试通过 Nitter RSS 获取 Twitter 推文

支持两种模式:
1. 自建 Nitter 实例 (推荐，最稳定)
2. 公共 Nitter 实例 (可能不可用)

自建实例配置方式:
- 环境变量: export NITTER_INSTANCE="http://localhost:8080"
- 或在代码中指定: config={"nitter_instance": "http://localhost:8080"}

部署文档: fin_module/nitter/README.md
"""

import asyncio
import sys
import os
sys.path.insert(0, '/Users/angeloxu/Desktop/finradar')

from datetime import datetime


def test_separator(title: str):
    """打印分隔线"""
    print("\n" + "=" * 70)
    print(f"🐦 {title}")
    print("=" * 70)


async def test_nitter_rss():
    """测试 Nitter RSS 数据抓取"""
    
    from fin_module.fetcher.nitter_rss import NitterRSSFetcher, quick_fetch_tweets
    
    # 显示当前配置
    test_separator("当前配置信息")
    
    env_instance = os.environ.get("NITTER_INSTANCE", "")
    if env_instance:
        print(f"\n✅ 检测到环境变量 NITTER_INSTANCE: {env_instance}")
        print("   将使用自建 Nitter 实例")
    else:
        print("\n⚠️  未设置 NITTER_INSTANCE 环境变量")
        print("   将尝试使用公共 Nitter 实例 (可能不可用)")
        print("\n💡 如果您已部署自建实例，请设置环境变量:")
        print("   export NITTER_INSTANCE=\"http://localhost:8080\"")
    
    # 创建 fetcher 实例
    # 如果要测试自建实例，可以取消注释下面的配置
    # fetcher = NitterRSSFetcher(config={
    #     "nitter_instance": "http://localhost:8080"
    # })
    fetcher = NitterRSSFetcher()
    
    # 显示实例信息
    info = fetcher.get_instance_info()
    print(f"\n📊 实例信息:")
    print(f"   当前实例: {info['current_instance']}")
    print(f"   是否本地: {'是 ✅' if info['is_local'] else '否 (公共实例)'}")
    print(f"   关注账号: {', '.join(info['accounts'][:3])}...")
    
    # 测试1: 检查实例健康状态
    test_separator("测试1: 检查 Nitter 实例健康状态")
    
    print("\n正在检查实例健康状态...")
    health = await fetcher.check_instance_health()
    
    # 检查自建实例
    if health.get("local_instance"):
        local = health["local_instance"]
        status = "✅ 可用" if local["healthy"] else "❌ 不可用"
        print(f"\n  🏠 自建实例: {status}")
        print(f"     URL: {local['url']}")
        if not local["healthy"] and "error" in local:
            print(f"     错误: {local['error']}")
    
    # 检查公共实例
    print(f"\n  🌐 公共实例状态:")
    available_count = 0
    for instance, status in health.get("public_instances", {}).items():
        is_healthy = status.get("healthy", False)
        status_text = "✅ 可用" if is_healthy else "❌ 不可用"
        print(f"     {status_text} - {instance}")
        if is_healthy:
            available_count += 1
    
    total_public = len(health.get("public_instances", {}))
    print(f"\n📊 公共实例可用: {available_count}/{total_public}")
    
    # 判断是否可以继续测试
    local_available = health.get("local_instance", {}).get("healthy", False)
    if not local_available and available_count == 0:
        print("\n❌ 没有可用的 Nitter 实例！")
        print("\n🔧 解决方案:")
        print("   1. 部署自建 Nitter 实例 (推荐)")
        print("      参考: fin_module/nitter/README.md")
        print("   2. 检查网络连接")
        print("   3. 等待公共实例恢复")
        return False
    
    # 测试2: 获取单个用户推文
    test_separator("测试2: 获取 Vitalik Buterin 的推文")
    
    try:
        tweets = await fetcher.get_single_user("VitalikButerin", max_tweets=5)
        
        if tweets:
            print(f"\n✅ 成功获取 {len(tweets)} 条推文\n")
            for i, tweet in enumerate(tweets, 1):
                print(f"  [{i}] @{tweet['username']} ({tweet['user_name']})")
                text = tweet['text'][:80]
                print(f"      {text}{'...' if len(tweet['text']) > 80 else ''}")
                print(f"      🕐 {tweet['created_at'][:19] if tweet['created_at'] else 'N/A'}")
                print(f"      🔗 {tweet['url']}")
                print()
        else:
            print("  ⚠️ 未获取到推文")
    except Exception as e:
        print(f"  ❌ 获取失败: {e}")
    
    # 测试3: 获取 Elon Musk 推文
    test_separator("测试3: 获取 Elon Musk 的推文")
    
    try:
        tweets = await fetcher.get_single_user("elonmusk", max_tweets=3)
        
        if tweets:
            print(f"\n✅ 成功获取 {len(tweets)} 条推文\n")
            for i, tweet in enumerate(tweets, 1):
                text = tweet['text'][:60]
                print(f"  [{i}] {text}{'...' if len(tweet['text']) > 60 else ''}")
                print(f"      🔗 {tweet['url']}")
                print()
        else:
            print("  ⚠️ 未获取到推文")
    except Exception as e:
        print(f"  ❌ 获取失败: {e}")
    
    # 测试4: 批量获取多个用户
    test_separator("测试4: 批量获取多个加密 KOL 推文")
    
    try:
        # 配置多个账号
        multi_fetcher = NitterRSSFetcher(config={
            "accounts": ["VitalikButerin", "WatcherGuru", "whale_alert"],
            "max_tweets_per_user": 3
        })
        
        result = await multi_fetcher.fetch()
        tweets = result.get("tweets", [])
        errors = result.get("errors", [])
        
        print(f"\n📊 使用实例: {result.get('instance_used', 'Unknown')}")
        print(f"📊 获取推文: {len(tweets)} 条")
        
        if errors:
            print(f"⚠️ 错误: {len(errors)} 个")
            for err in errors:
                print(f"   - {err}")
        
        if tweets:
            print(f"\n✅ 最新推文:\n")
            for i, tweet in enumerate(tweets[:8], 1):
                print(f"  [{i}] @{tweet['username']}")
                text = tweet['text'][:60]
                print(f"      {text}{'...' if len(tweet['text']) > 60 else ''}")
                print()
        
    except Exception as e:
        print(f"  ❌ 批量获取失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试5: 使用快捷函数
    test_separator("测试5: 使用 quick_fetch_tweets 快捷函数")
    
    try:
        tweets = await quick_fetch_tweets(["VitalikButerin"])
        print(f"\n✅ quick_fetch_tweets 成功获取 {len(tweets)} 条推文")
    except Exception as e:
        print(f"  ❌ 失败: {e}")
    
    # 测试6: 推荐账号列表
    test_separator("测试6: 推荐关注的 KOL 账号")
    
    accounts = fetcher.get_all_recommended_accounts()
    
    print("\n  💰 加密货币/Web3:")
    for acc in accounts.get("crypto", []):
        print(f"     • @{acc}")
    
    print("\n  🤖 科技/AI:")
    for acc in accounts.get("tech", []):
        print(f"     • @{acc}")
    
    print("\n  📈 宏观经济/金融:")
    for acc in accounts.get("finance", []):
        print(f"     • @{acc}")
    
    return True


def main():
    """主测试函数"""
    print("\n" + "🐦" * 35)
    print("     FinRadar Nitter RSS Fetcher 测试")
    print("     支持自建实例 + 公共实例")
    print("🐦" * 35)
    print(f"\n⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = asyncio.run(test_nitter_rss())
    
    # 结果汇总
    print("\n" + "=" * 70)
    print("📋 测试结果")
    print("=" * 70)
    
    if success:
        print("\n✅ Nitter RSS Fetcher 测试通过！")
        print("\n💡 使用优势:")
        print("   ✓ 完全免费，无需 API Key")
        print("   ✓ 无调用次数限制")
        print("   ✓ 无需 Twitter 开发者账号")
        print("\n📦 自建实例部署 (推荐):")
        print("   参考文档: fin_module/nitter/README.md")
        print("   1. 获取 Twitter tokens: python nitter/get_twitter_tokens.py")
        print("   2. 启动服务: cd nitter && docker-compose up -d")
        print("   3. 配置环境变量: export NITTER_INSTANCE=\"http://localhost:8080\"")
    else:
        print("\n❌ Nitter RSS Fetcher 测试失败")
        print("\n🔧 推荐解决方案:")
        print("\n   【方案一】部署自建 Nitter 实例 (最稳定)")
        print("   ------------------------------------------")
        print("   参考文档: fin_module/nitter/README.md")
        print("   ")
        print("   步骤1: 获取 Twitter session tokens")
        print("   $ cd fin_module/nitter")
        print("   $ pip install playwright && playwright install chromium")
        print("   $ python get_twitter_tokens.py")
        print("   ")
        print("   步骤2: 启动 Nitter Docker 服务")
        print("   $ docker-compose up -d")
        print("   ")
        print("   步骤3: 配置环境变量")
        print("   $ export NITTER_INSTANCE=\"http://localhost:8080\"")
        print("\n   【方案二】等待公共实例恢复")
        print("   ------------------------------------------")
        print("   公共 Nitter 实例可能因为 Twitter 限制而暂时不可用")


if __name__ == "__main__":
    main()
