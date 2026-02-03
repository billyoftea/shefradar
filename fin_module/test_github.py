"""
GitHub Fetcher 测试脚本 - 无需 API Key 版本

测试使用 requests 直接调用 GitHub REST API
"""

import asyncio
import sys
sys.path.insert(0, '/Users/angeloxu/Desktop/finradar')

from fin_module.fetcher.github import GitHubFetcher


def test_github_fetcher():
    """测试 GitHub 数据抓取"""
    
    print("=" * 60)
    print("🧪 GitHub Fetcher 测试 (无需 API Key)")
    print("=" * 60)
    
    # 初始化 fetcher（不传入 token，使用无认证模式）
    fetcher = GitHubFetcher(config={
        "fetch_count": 5,  # 只获取5个，避免超出限额
        "languages": ["python", "rust"]
    })
    
    print(f"\n✅ Fetcher 初始化成功")
    print(f"   - 启用状态: {fetcher.enabled}")
    print(f"   - 使用 PyGithub: {fetcher.gh is not None}")
    
    # 测试1: 获取今日热门仓库
    print("\n" + "-" * 40)
    print("📊 测试1: 获取今日热门仓库 (最近7天创建, stars>100)")
    print("-" * 40)
    
    try:
        trending = fetcher.get_daily_trending(limit=5)
        print(f"✅ 获取成功，共 {len(trending)} 个仓库\n")
        
        for i, repo in enumerate(trending, 1):
            print(f"  {i}. ⭐ {repo['stars']:,} | {repo['full_name']}")
            print(f"     📝 {repo['description'][:60]}..." if len(repo.get('description', '')) > 60 else f"     📝 {repo.get('description', 'No description')}")
            print(f"     🔗 {repo['url']}")
            print(f"     💻 语言: {repo['language']} | 🍴 Forks: {repo['forks']}")
            print()
    except Exception as e:
        print(f"❌ 获取失败: {e}")
    
    # 测试2: 获取 AI/ML 相关热门仓库
    print("\n" + "-" * 40)
    print("🤖 测试2: 获取 AI/ML 相关热门仓库")
    print("-" * 40)
    
    try:
        ai_repos = fetcher.get_ai_ml_trending(limit=5)
        print(f"✅ 获取成功，共 {len(ai_repos)} 个仓库\n")
        
        for i, repo in enumerate(ai_repos, 1):
            print(f"  {i}. ⭐ {repo['stars']:,} | {repo['full_name']}")
            desc = repo.get('description', 'No description') or 'No description'
            print(f"     📝 {desc[:60]}..." if len(desc) > 60 else f"     📝 {desc}")
            print(f"     🏷️  Topics: {', '.join(repo.get('topics', [])[:5])}")
            print()
    except Exception as e:
        print(f"❌ 获取失败: {e}")
    
    # 测试3: 获取指定语言热门仓库
    print("\n" + "-" * 40)
    print("🐍 测试3: 获取 Python 语言热门仓库")
    print("-" * 40)
    
    try:
        python_repos = fetcher.get_language_trending("python", limit=3)
        print(f"✅ 获取成功，共 {len(python_repos)} 个仓库\n")
        
        for i, repo in enumerate(python_repos, 1):
            print(f"  {i}. ⭐ {repo['stars']:,} | {repo['full_name']}")
            print(f"     🔗 {repo['url']}")
            print()
    except Exception as e:
        print(f"❌ 获取失败: {e}")
    
    # 测试4: 异步获取完整数据
    print("\n" + "-" * 40)
    print("🔄 测试4: 异步获取完整数据")
    print("-" * 40)
    
    async def async_test():
        try:
            raw_data = await fetcher.fetch()
            print(f"✅ 异步获取成功")
            print(f"   - trending: {len(raw_data.get('trending', []))} 个")
            print(f"   - ai_trending: {len(raw_data.get('ai_trending', []))} 个")
            print(f"   - timestamp: {raw_data.get('timestamp')}")
            
            # 测试 parse 方法
            parsed = fetcher.parse(raw_data)
            print(f"\n✅ 数据解析成功")
            print(f"   - parsed trending: {len(parsed.get('trending', []))} 个 GitHubTrendingRepo")
            print(f"   - parsed ai_trending: {len(parsed.get('ai_trending', []))} 个 GitHubTrendingRepo")
            
            return raw_data
        except Exception as e:
            print(f"❌ 异步获取失败: {e}")
            return None
    
    result = asyncio.run(async_test())
    
    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)
    
    return result


if __name__ == "__main__":
    test_github_fetcher()
