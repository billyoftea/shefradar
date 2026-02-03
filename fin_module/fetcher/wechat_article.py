"""
微信公众号文章数据获取器

通过 wechat-article-exporter 的 API 接口获取公众号文章数据
项目地址: https://github.com/wechat-article/wechat-article-exporter
"""

import asyncio
import aiohttp
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field


@dataclass
class WechatArticle:
    """微信公众号文章数据模型"""
    title: str                          # 文章标题
    author: str                         # 作者
    account_name: str                   # 公众号名称
    publish_time: datetime              # 发布时间
    url: str                            # 文章链接
    digest: str = ""                    # 摘要
    cover_url: str = ""                 # 封面图片
    read_count: int = 0                 # 阅读量
    like_count: int = 0                 # 点赞数
    comment_count: int = 0              # 评论数
    is_original: bool = False           # 是否原创
    content: str = ""                   # 文章内容（HTML）
    

@dataclass  
class WechatAccount:
    """微信公众号账号模型"""
    name: str                           # 公众号名称
    fakeid: str                         # 公众号 ID
    alias: str = ""                     # 微信号
    round_head_img: str = ""            # 头像
    service_type: int = 0               # 账号类型


class WechatArticleFetcher:
    """
    微信公众号文章获取器
    
    需要先部署 wechat-article-exporter 服务:
    cd fin_module/wechat-article && docker-compose up -d
    
    使用示例:
        fetcher = WechatArticleFetcher()
        
        # 搜索公众号
        accounts = await fetcher.search_accounts("华尔街见闻")
        
        # 获取文章列表
        articles = await fetcher.get_articles(accounts[0].fakeid)
        
        # 使用全局配置获取所有公众号文章
        all_articles = await fetcher.fetch_all_from_config()
    """
    
    def __init__(self, 
                 base_url: str = None,
                 timeout: int = None):
        """
        初始化获取器
        
        Args:
            base_url: wechat-article-exporter 服务地址，默认从配置文件读取
            timeout: 请求超时时间（秒），默认从配置文件读取
        """
        # 尝试从全局配置加载
        self._load_from_global_config()
        
        # 使用参数覆盖全局配置
        self.base_url = (base_url or self._global_service_url or "http://localhost:3001").rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=timeout or self._global_timeout or 30)
        self._session: Optional[aiohttp.ClientSession] = None
    
    def _load_from_global_config(self):
        """从全局配置文件加载微信公众号配置"""
        try:
            from .social_config import SocialSourceConfig
            global_config = SocialSourceConfig()
            
            self._global_enabled = global_config.wechat.enabled
            self._global_service_url = global_config.wechat.service_url
            self._global_timeout = global_config.wechat.timeout
            self._global_accounts = global_config.wechat.accounts
            self._global_max_articles = global_config.wechat.max_articles_per_account
            self._global_max_age_days = global_config.wechat.max_age_days
        except Exception as e:
            print(f"⚠️ 无法加载全局配置: {e}")
            self._global_enabled = True
            self._global_service_url = "http://localhost:3001"
            self._global_timeout = 30
            self._global_accounts = {}
            self._global_max_articles = 20
            self._global_max_age_days = 3
    
    def get_configured_accounts(self) -> Dict[str, List[str]]:
        """获取配置的公众号列表（按分类）"""
        return self._global_accounts
    
    def get_all_configured_accounts(self) -> List[str]:
        """获取所有配置的公众号名称"""
        all_accounts = []
        for category, accounts in self._global_accounts.items():
            all_accounts.extend(accounts)
        return all_accounts
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建 HTTP 会话"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self._session
        
    async def close(self):
        """关闭 HTTP 会话"""
        if self._session and not self._session.closed:
            await self._session.close()
            
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
    async def check_service(self) -> bool:
        """
        检查服务是否可用
        
        Returns:
            bool: 服务是否可用
        """
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/") as resp:
                return resp.status == 200
        except Exception:
            return False
            
    async def search_accounts(self, 
                              keyword: str,
                              limit: int = 10) -> List[WechatAccount]:
        """
        搜索公众号
        
        Args:
            keyword: 搜索关键词
            limit: 返回数量限制
            
        Returns:
            List[WechatAccount]: 公众号列表
        """
        session = await self._get_session()
        
        try:
            # API 端点参考项目文档
            url = f"{self.base_url}/api/search"
            params = {
                "keyword": keyword,
                "limit": limit
            }
            
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    print(f"搜索公众号失败: HTTP {resp.status}")
                    return []
                    
                data = await resp.json()
                
                accounts = []
                for item in data.get("list", []):
                    account = WechatAccount(
                        name=item.get("nickname", ""),
                        fakeid=item.get("fakeid", ""),
                        alias=item.get("alias", ""),
                        round_head_img=item.get("round_head_img", ""),
                        service_type=item.get("service_type", 0)
                    )
                    accounts.append(account)
                    
                return accounts
                
        except Exception as e:
            print(f"搜索公众号异常: {e}")
            return []
            
    async def get_articles(self,
                           fakeid: str,
                           offset: int = 0,
                           count: int = 20) -> List[WechatArticle]:
        """
        获取公众号文章列表
        
        Args:
            fakeid: 公众号 ID
            offset: 偏移量
            count: 获取数量
            
        Returns:
            List[WechatArticle]: 文章列表
        """
        session = await self._get_session()
        
        try:
            url = f"{self.base_url}/api/articles"
            params = {
                "fakeid": fakeid,
                "offset": offset,
                "count": count
            }
            
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    print(f"获取文章列表失败: HTTP {resp.status}")
                    return []
                    
                data = await resp.json()
                
                articles = []
                for item in data.get("list", []):
                    # 解析发布时间
                    create_time = item.get("create_time", 0)
                    if isinstance(create_time, int):
                        publish_time = datetime.fromtimestamp(create_time)
                    else:
                        publish_time = datetime.now()
                        
                    article = WechatArticle(
                        title=item.get("title", ""),
                        author=item.get("author", ""),
                        account_name=item.get("account_name", ""),
                        publish_time=publish_time,
                        url=item.get("link", ""),
                        digest=item.get("digest", ""),
                        cover_url=item.get("cover", ""),
                        is_original=item.get("is_original", False)
                    )
                    articles.append(article)
                    
                return articles
                
        except Exception as e:
            print(f"获取文章列表异常: {e}")
            return []
            
    async def get_article_stats(self,
                                article_url: str) -> Dict[str, int]:
        """
        获取文章统计数据（阅读量、点赞数等）
        
        注意：需要配置 credentials 才能获取统计数据
        参考: https://docs.mptext.top/advanced/wxdown-service.html
        
        Args:
            article_url: 文章链接
            
        Returns:
            Dict: 包含 read_count, like_count, comment_count
        """
        session = await self._get_session()
        
        try:
            url = f"{self.base_url}/api/article/stats"
            params = {"url": article_url}
            
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    return {"read_count": 0, "like_count": 0, "comment_count": 0}
                    
                data = await resp.json()
                return {
                    "read_count": data.get("read_num", 0),
                    "like_count": data.get("like_num", 0),
                    "comment_count": data.get("comment_count", 0)
                }
                
        except Exception:
            return {"read_count": 0, "like_count": 0, "comment_count": 0}


# 预定义的金融相关公众号列表
FINANCE_ACCOUNTS = [
    # 综合财经
    "华尔街见闻",
    "财联社",
    "金十数据",
    "Wind资讯",
    "第一财经",
    "界面新闻",
    "每日经济新闻",
    
    # 加密货币/区块链
    "PANews",
    "巴比特资讯", 
    "深潮TechFlow",
    "金色财经",
    "Odaily星球日报",
    "链捕手",
    
    # 投资理财
    "雪球",
    "同花顺",
    "东方财富",
    
    # 科技创投
    "36氪",
    "虎嗅APP",
    "钛媒体",
]


async def test_fetcher():
    """测试微信公众号文章获取器"""
    print("=" * 60)
    print("微信公众号文章获取器测试")
    print("=" * 60)
    
    async with WechatArticleFetcher() as fetcher:
        # 检查服务状态
        print("\n1. 检查服务状态...")
        is_available = await fetcher.check_service()
        
        if not is_available:
            print("❌ wechat-article-exporter 服务不可用")
            print("\n请先启动服务:")
            print("  cd fin_module/wechat-article")
            print("  docker-compose up -d")
            print("\n然后访问 http://localhost:3001 扫码登录")
            return
            
        print("✅ 服务可用")
        
        # 搜索公众号示例
        print("\n2. 搜索公众号: 华尔街见闻")
        accounts = await fetcher.search_accounts("华尔街见闻")
        
        if accounts:
            print(f"✅ 找到 {len(accounts)} 个公众号:")
            for acc in accounts[:3]:
                print(f"   - {acc.name} ({acc.alias})")
                
            # 获取文章列表
            print(f"\n3. 获取 {accounts[0].name} 的文章列表...")
            articles = await fetcher.get_articles(accounts[0].fakeid)
            
            if articles:
                print(f"✅ 获取到 {len(articles)} 篇文章:")
                for art in articles[:5]:
                    print(f"   - [{art.publish_time.strftime('%Y-%m-%d')}] {art.title[:40]}...")
            else:
                print("⚠️ 未获取到文章，可能需要先登录")
        else:
            print("⚠️ 未搜索到公众号，请确认已扫码登录")
            
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(test_fetcher())
