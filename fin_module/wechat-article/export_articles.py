#!/usr/bin/env python3
"""
微信公众号文章批量导出脚本

使用方式：
1. 先在浏览器访问 http://localhost:3001 扫码登录
2. 运行此脚本获取文章
"""

import os
import json
import asyncio
import aiohttp
import urllib.parse
from datetime import datetime, date
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

# 配置
BASE_URL = "http://localhost:3001"
DATA_DIR = Path("/Users/angeloxu/Desktop/finradar/fin_module/wechat-article/data")
OUTPUT_DIR = Path("/Users/angeloxu/Desktop/finradar/fin_module/wechat-article/exports")


@dataclass
class Article:
    """文章数据"""
    aid: str
    title: str
    link: str
    digest: str
    author: str
    cover: str
    create_time: datetime
    
    def __str__(self):
        return f"[{self.create_time.strftime('%Y-%m-%d %H:%M')}] {self.title}"


def get_auth_key() -> Optional[str]:
    """从 KV 存储中获取 auth-key"""
    kv_dir = DATA_DIR / "kv" / "cookie"
    if not kv_dir.exists():
        return None
    
    # 获取第一个 auth-key 文件
    for f in kv_dir.iterdir():
        if f.is_file():
            return f.name
    return None


async def search_account(session: aiohttp.ClientSession, 
                         keyword: str, 
                         auth_key: str) -> List[Dict]:
    """搜索公众号"""
    url = f"{BASE_URL}/api/web/mp/searchbiz"
    params = {"keyword": keyword}
    headers = {"X-Auth-Key": auth_key}
    
    async with session.get(url, params=params, headers=headers) as resp:
        if resp.status != 200:
            print(f"❌ 搜索失败: HTTP {resp.status}")
            return []
        
        data = await resp.json()
        if data.get("base_resp", {}).get("ret") != 0:
            print(f"❌ 搜索失败: {data.get('base_resp', {}).get('err_msg')}")
            return []
        
        return data.get("list", [])


async def get_articles(session: aiohttp.ClientSession,
                       fakeid: str,
                       auth_key: str,
                       begin: int = 0,
                       size: int = 20) -> List[Article]:
    """获取公众号文章列表"""
    url = f"{BASE_URL}/api/web/mp/appmsgpublish"
    params = {
        "id": fakeid,
        "keyword": "",
        "begin": begin,
        "size": size
    }
    headers = {"X-Auth-Key": auth_key}
    
    async with session.get(url, params=params, headers=headers) as resp:
        if resp.status != 200:
            print(f"❌ 获取文章失败: HTTP {resp.status}")
            return []
        
        data = await resp.json()
        if data.get("base_resp", {}).get("ret") != 0:
            print(f"❌ 获取文章失败: {data.get('base_resp', {}).get('err_msg')}")
            return []
        
        articles = []
        
        # publish_page 是一个 JSON 字符串，需要再解析一次
        publish_page_str = data.get("publish_page", "{}")
        if isinstance(publish_page_str, str):
            publish_page = json.loads(publish_page_str)
        else:
            publish_page = publish_page_str
        
        publish_list = publish_page.get("publish_list", [])
        
        for item in publish_list:
            try:
                publish_info = json.loads(item.get("publish_info", "{}"))
                appmsgex_list = publish_info.get("appmsgex", [])
                
                for appmsg in appmsgex_list:
                    create_time = datetime.fromtimestamp(appmsg.get("create_time", 0))
                    
                    article = Article(
                        aid=appmsg.get("aid", ""),
                        title=appmsg.get("title", ""),
                        link=appmsg.get("link", "").replace("\\/", "/"),
                        digest=appmsg.get("digest", ""),
                        author=appmsg.get("author_name", ""),
                        cover=appmsg.get("cover", "").replace("\\/", "/"),
                        create_time=create_time
                    )
                    articles.append(article)
            except Exception as e:
                print(f"⚠️ 解析文章数据失败: {e}")
                continue
        
        return articles


async def download_article_html(session: aiohttp.ClientSession,
                                 article: Article,
                                 output_dir: Path) -> bool:
    """下载文章 HTML 内容"""
    try:
        # 直接访问微信文章链接
        async with session.get(article.link, timeout=30) as resp:
            if resp.status != 200:
                print(f"❌ 下载失败 [{article.title[:20]}...]: HTTP {resp.status}")
                return False
            
            html_content = await resp.text()
            
            # 保存文件
            safe_title = "".join(c for c in article.title if c.isalnum() or c in ' _-')[:50]
            filename = f"{article.create_time.strftime('%Y%m%d_%H%M')}_{safe_title}.html"
            filepath = output_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"✅ 已保存: {filename}")
            return True
            
    except Exception as e:
        print(f"❌ 下载异常 [{article.title[:20]}...]: {e}")
        return False


async def export_articles_to_json(articles: List[Article], 
                                   account_name: str,
                                   output_dir: Path) -> str:
    """导出文章列表为 JSON"""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    data = {
        "account": account_name,
        "export_time": datetime.now().isoformat(),
        "count": len(articles),
        "articles": [
            {
                "aid": a.aid,
                "title": a.title,
                "link": a.link,
                "digest": a.digest,
                "author": a.author,
                "cover": a.cover,
                "create_time": a.create_time.isoformat()
            }
            for a in articles
        ]
    }
    
    filename = f"{account_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = output_dir / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return str(filepath)


async def main():
    """主函数"""
    print("=" * 60)
    print("📱 微信公众号文章批量导出")
    print("=" * 60)
    
    # 获取 auth-key
    auth_key = get_auth_key()
    if not auth_key:
        print("❌ 未找到登录凭证！请先在浏览器访问 http://localhost:3001 扫码登录")
        return
    
    print(f"✅ 已获取登录凭证: {auth_key[:8]}...")
    
    # 要搜索的公众号
    target_account = "新智元"
    
    async with aiohttp.ClientSession() as session:
        # 1. 搜索公众号
        print(f"\n🔍 搜索公众号: {target_account}")
        accounts = await search_account(session, target_account, auth_key)
        
        if not accounts:
            print("❌ 未找到公众号")
            return
        
        # 显示搜索结果
        print(f"📋 找到 {len(accounts)} 个公众号:")
        for i, acc in enumerate(accounts[:5]):
            print(f"   [{i+1}] {acc.get('nickname')} (@{acc.get('alias', 'N/A')})")
        
        # 选择第一个（通常是最匹配的）
        selected = accounts[0]
        fakeid = selected.get("fakeid")
        account_name = selected.get("nickname")
        
        print(f"\n📌 选择: {account_name}")
        
        # 2. 获取文章列表
        print(f"\n📰 获取文章列表...")
        articles = await get_articles(session, fakeid, auth_key, begin=0, size=20)
        
        if not articles:
            print("❌ 未获取到文章")
            return
        
        print(f"📊 共获取 {len(articles)} 篇文章")
        
        # 3. 筛选今天的文章
        today = date.today()
        today_articles = [a for a in articles if a.create_time.date() == today]
        
        print(f"\n📅 今日 ({today}) 文章: {len(today_articles)} 篇")
        
        if today_articles:
            for i, article in enumerate(today_articles, 1):
                print(f"   [{i}] {article}")
            
            # 4. 导出为 JSON
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            json_path = await export_articles_to_json(today_articles, account_name, OUTPUT_DIR)
            print(f"\n💾 已导出 JSON: {json_path}")
            
            # 显示文章链接
            print(f"\n🔗 文章链接:")
            for article in today_articles:
                print(f"   • {article.title}")
                print(f"     {article.link}")
                print()
        else:
            print("ℹ️ 今天暂无新文章")
            print("\n📋 最近文章:")
            for article in articles[:5]:
                print(f"   • [{article.create_time.strftime('%Y-%m-%d')}] {article.title}")
    
    print("\n" + "=" * 60)
    print("✅ 导出完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
