"""
GitHub 趋势数据抓取器

可选实现方案：
1. PyGithub - GitHub 官方 Python SDK
   GitHub: https://github.com/PyGithub/PyGithub
   安装: pip install PyGithub

2. 直接使用 requests 调用 GitHub REST API
   API文档: https://docs.github.com/en/rest

3. 第三方 github-trending-api (非官方)
   GitHub: https://github.com/huchenme/github-trending-api

GitHub API 限制:
- 无认证: 60 requests/hour
- 有认证: 5000 requests/hour (使用 Personal Access Token)

支持获取:
- Trending 仓库（按 star 增长）
- 热门语言项目
- 最新创建的热门项目
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import logging

try:
    from github import Github
    PYGITHUB_AVAILABLE = True
except ImportError:
    PYGITHUB_AVAILABLE = False
    Github = None

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from . import BaseFetcher
from ..models.market_data import GitHubTrendingRepo

logger = logging.getLogger(__name__)


class GitHubFetcher(BaseFetcher):
    """
    GitHub 趋势数据抓取器
    
    支持获取:
    - 今日/本周热门仓库（按 star 排序）
    - 指定语言的热门项目
    - 最近创建的爆款项目
    - AI/ML 相关热门项目
    """
    
    GITHUB_API_BASE = "https://api.github.com"
    
    # 热门编程语言
    POPULAR_LANGUAGES = [
        "python", "javascript", "typescript", "rust", "go", 
        "java", "cpp", "c", "swift", "kotlin"
    ]
    
    # AI/ML 相关关键词
    AI_KEYWORDS = [
        "llm", "gpt", "ai", "machine-learning", "deep-learning",
        "transformer", "langchain", "chatgpt", "openai", "anthropic"
    ]
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        
        # GitHub Token（可选，用于提高 API 限额）
        self.token = self.config.get("token", "")
        
        # 初始化客户端
        if PYGITHUB_AVAILABLE and self.token:
            self.gh = Github(self.token)
        elif PYGITHUB_AVAILABLE:
            self.gh = Github()  # 无认证模式
        else:
            self.gh = None
            if not REQUESTS_AVAILABLE:
                logger.warning("Neither PyGithub nor requests available. Install one of them.")
                self.enabled = False
        
        # 配置
        self.languages = self.config.get("languages", ["python", "javascript", "rust"])
        self.fetch_count = self.config.get("fetch_count", 10)
    
    async def fetch(self) -> Dict[str, Any]:
        """
        抓取 GitHub 趋势数据
        
        Returns:
            包含热门仓库数据的字典
        """
        loop = asyncio.get_event_loop()
        
        # 并行获取不同类型的趋势数据
        trending_task = loop.run_in_executor(None, self._fetch_trending_repos)
        ai_task = loop.run_in_executor(None, self._fetch_ai_repos)
        
        trending, ai_repos = await asyncio.gather(
            trending_task, ai_task,
            return_exceptions=True
        )
        
        return {
            "trending": trending if not isinstance(trending, Exception) else [],
            "ai_trending": ai_repos if not isinstance(ai_repos, Exception) else [],
            "timestamp": datetime.now()
        }
    
    def _fetch_trending_repos(self) -> List[Dict]:
        """
        获取今日热门仓库
        
        通过搜索最近创建且 star 数增长快的仓库来模拟 trending
        """
        # 计算日期范围（最近7天创建的项目）
        date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        query = f"created:>{date_from} stars:>100"
        
        return self._search_repos(query, sort="stars", per_page=self.fetch_count)
    
    def _fetch_ai_repos(self) -> List[Dict]:
        """获取 AI/ML 相关热门仓库"""
        # 搜索 AI 相关仓库
        date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        # 使用多个关键词搜索
        keywords_query = " OR ".join(self.AI_KEYWORDS[:5])  # 限制关键词数量
        query = f"({keywords_query}) created:>{date_from} stars:>50"
        
        return self._search_repos(query, sort="stars", per_page=self.fetch_count)
    
    def _fetch_repos_by_language(self, language: str) -> List[Dict]:
        """获取指定语言的热门仓库"""
        date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        query = f"language:{language} created:>{date_from} stars:>50"
        
        return self._search_repos(query, sort="stars", per_page=5)
    
    def _search_repos(self, query: str, sort: str = "stars", per_page: int = 10) -> List[Dict]:
        """
        执行仓库搜索
        
        Args:
            query: GitHub 搜索查询语句
            sort: 排序方式 (stars, forks, updated)
            per_page: 返回数量
        """
        try:
            if self.gh and PYGITHUB_AVAILABLE:
                return self._search_with_pygithub(query, sort, per_page)
            else:
                return self._search_with_requests(query, sort, per_page)
        except Exception as e:
            logger.error(f"Error searching repos: {e}")
            return []
    
    def _search_with_pygithub(self, query: str, sort: str, per_page: int) -> List[Dict]:
        """使用 PyGithub 搜索"""
        repos = self.gh.search_repositories(query=query, sort=sort, order="desc")
        
        results = []
        for i, repo in enumerate(repos):
            if i >= per_page:
                break
            
            results.append({
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description or "",
                "url": repo.html_url,
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
                "language": repo.language or "Unknown",
                "topics": repo.topics if hasattr(repo, 'topics') else [],
                "created_at": repo.created_at.isoformat() if repo.created_at else "",
                "updated_at": repo.updated_at.isoformat() if repo.updated_at else "",
                "owner": repo.owner.login if repo.owner else "",
                "owner_avatar": repo.owner.avatar_url if repo.owner else "",
            })
        
        return results
    
    def _search_with_requests(self, query: str, sort: str, per_page: int) -> List[Dict]:
        """使用 requests 直接调用 API"""
        url = f"{self.GITHUB_API_BASE}/search/repositories"
        
        headers = {}
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        
        params = {
            "q": query,
            "sort": sort,
            "order": "desc",
            "per_page": per_page
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for repo in data.get("items", []):
            results.append({
                "name": repo.get("name", ""),
                "full_name": repo.get("full_name", ""),
                "description": repo.get("description", "") or "",
                "url": repo.get("html_url", ""),
                "stars": repo.get("stargazers_count", 0),
                "forks": repo.get("forks_count", 0),
                "language": repo.get("language", "Unknown") or "Unknown",
                "topics": repo.get("topics", []),
                "created_at": repo.get("created_at", ""),
                "updated_at": repo.get("updated_at", ""),
                "owner": repo.get("owner", {}).get("login", ""),
                "owner_avatar": repo.get("owner", {}).get("avatar_url", ""),
            })
        
        return results
    
    def parse(self, raw_data: Dict[str, Any]) -> Dict[str, List[GitHubTrendingRepo]]:
        """
        解析原始数据为标准格式
        
        Args:
            raw_data: fetch() 返回的原始数据
            
        Returns:
            按类别组织的 GitHubTrendingRepo 字典
        """
        timestamp = raw_data.get("timestamp", datetime.now())
        
        def convert_repos(repos: List[Dict]) -> List[GitHubTrendingRepo]:
            return [
                GitHubTrendingRepo(
                    name=repo.get("name", ""),
                    full_name=repo.get("full_name", ""),
                    description=repo.get("description", ""),
                    url=repo.get("url", ""),
                    stars=repo.get("stars", 0),
                    forks=repo.get("forks", 0),
                    language=repo.get("language", ""),
                    topics=repo.get("topics", []),
                    timestamp=timestamp
                )
                for repo in repos
            ]
        
        return {
            "trending": convert_repos(raw_data.get("trending", [])),
            "ai_trending": convert_repos(raw_data.get("ai_trending", [])),
        }
    
    # ==================== 便捷方法 ====================
    
    def get_daily_trending(self, limit: int = 10) -> List[Dict]:
        """获取今日热门仓库"""
        return self._fetch_trending_repos()[:limit]
    
    def get_language_trending(self, language: str, limit: int = 5) -> List[Dict]:
        """获取指定语言的热门仓库"""
        return self._fetch_repos_by_language(language)[:limit]
    
    def get_ai_ml_trending(self, limit: int = 10) -> List[Dict]:
        """获取 AI/ML 相关热门仓库"""
        return self._fetch_ai_repos()[:limit]
