"""
Twitter/X 热点数据抓取器

实现方案：
1. tweepy - Twitter API v2 官方 Python 封装 (推荐)
   GitHub: https://github.com/tweepy/tweepy
   安装: pip install tweepy>=4.14.0

2. snscrape - 无需 API 的爬虫方案 (备选)
   GitHub: https://github.com/JustAnotherArchivist/snscrape
   注意: 可能不稳定

3. Nitter RSS - 第三方前端 (备选)
   无需 API，但稳定性较差

Twitter API v2 限制:
- Basic 免费版: 
  - 每月 10,000 读取
  - 每月 1,500 发布
- 需要申请开发者账号

支持获取:
- 指定用户的最新推文
- 热门话题/标签
- 金融/加密相关 KOL 动态
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import logging

try:
    import tweepy
    TWEEPY_AVAILABLE = True
except ImportError:
    TWEEPY_AVAILABLE = False
    tweepy = None

from . import BaseFetcher
from ..models.market_data import TwitterHotTopic

logger = logging.getLogger(__name__)


class TwitterFetcher(BaseFetcher):
    """
    Twitter/X 热点数据抓取器
    
    基于 tweepy (Twitter API v2) 实现，支持:
    - 获取指定用户最新推文
    - 搜索热门话题
    - 获取金融/加密 KOL 动态
    
    注意: 需要配置 Twitter API Bearer Token
    """
    
    # 推荐关注的账号分类
    RECOMMENDED_ACCOUNTS = {
        # 加密货币/Web3 KOL
        "crypto": [
            "VitalikButerin",   # 以太坊创始人
            "caborez",          # 知名加密投资者
            "WatcherGuru",      # 加密新闻
            "whale_alert",      # 大额转账监控
            "DefiLlama",        # DeFi 数据
        ],
        # 科技/AI
        "tech": [
            "elonmusk",         # Elon Musk
            "sama",             # Sam Altman (OpenAI)
            "ylecun",           # Yann LeCun (Meta AI)
            "kaborai",          # Karpathy
        ],
        # 宏观经济/金融
        "finance": [
            "zaborohead",       # 金融分析
            "MacroAlf",         # 宏观分析
            "unusual_whales",   # 期权异动
        ],
    }
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        
        if not TWEEPY_AVAILABLE:
            logger.warning("tweepy not installed. Run: pip install tweepy")
            self.enabled = False
            return
        
        # Bearer Token (必需)
        self.bearer_token = self.config.get("bearer_token", "")
        
        if not self.bearer_token:
            logger.warning("Twitter Bearer Token not configured. Twitter fetcher disabled.")
            self.enabled = False
            return
        
        # 初始化客户端
        try:
            self.client = tweepy.Client(bearer_token=self.bearer_token)
        except Exception as e:
            logger.error(f"Failed to initialize Twitter client: {e}")
            self.enabled = False
            return
        
        # 配置要关注的账号
        self.accounts_to_follow = self.config.get("accounts_to_follow", [])
        if not self.accounts_to_follow:
            # 使用默认的 crypto 和 tech 账号
            self.accounts_to_follow = (
                self.RECOMMENDED_ACCOUNTS.get("crypto", [])[:3] +
                self.RECOMMENDED_ACCOUNTS.get("tech", [])[:2]
            )
        
        self.max_tweets_per_user = self.config.get("max_tweets_per_user", 5)
    
    async def fetch(self) -> Dict[str, Any]:
        """
        抓取 Twitter 热点数据
        
        Returns:
            包含推文和话题的字典
        """
        if not self.enabled:
            return {"tweets": [], "timestamp": datetime.now()}
        
        loop = asyncio.get_event_loop()
        
        # 获取关注用户的最新推文
        tweets_task = loop.run_in_executor(None, self._fetch_user_tweets)
        
        tweets = await tweets_task
        if isinstance(tweets, Exception):
            logger.error(f"Error fetching tweets: {tweets}")
            tweets = []
        
        return {
            "tweets": tweets,
            "timestamp": datetime.now()
        }
    
    def _fetch_user_tweets(self) -> List[Dict]:
        """获取关注用户的最新推文"""
        all_tweets = []
        
        for username in self.accounts_to_follow:
            try:
                tweets = self._get_user_recent_tweets(username)
                all_tweets.extend(tweets)
            except Exception as e:
                logger.error(f"Error fetching tweets for @{username}: {e}")
                continue
        
        # 按时间排序
        all_tweets.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return all_tweets
    
    def _get_user_recent_tweets(self, username: str) -> List[Dict]:
        """
        获取指定用户的最新推文
        
        Args:
            username: Twitter 用户名（不含@）
        """
        try:
            # 首先获取用户 ID
            user = self.client.get_user(username=username)
            if not user.data:
                logger.warning(f"User @{username} not found")
                return []
            
            user_id = user.data.id
            user_name = user.data.name
            
            # 获取最新推文
            tweets = self.client.get_users_tweets(
                id=user_id,
                max_results=self.max_tweets_per_user,
                tweet_fields=["created_at", "public_metrics", "text"],
                exclude=["retweets", "replies"]  # 排除转推和回复
            )
            
            if not tweets.data:
                return []
            
            results = []
            for tweet in tweets.data:
                metrics = tweet.public_metrics or {}
                results.append({
                    "id": str(tweet.id),
                    "text": tweet.text,
                    "username": username,
                    "user_name": user_name,
                    "created_at": tweet.created_at.isoformat() if tweet.created_at else "",
                    "likes": metrics.get("like_count", 0),
                    "retweets": metrics.get("retweet_count", 0),
                    "replies": metrics.get("reply_count", 0),
                    "url": f"https://twitter.com/{username}/status/{tweet.id}",
                })
            
            return results
            
        except tweepy.errors.TooManyRequests:
            logger.warning("Twitter API rate limit exceeded")
            return []
        except Exception as e:
            logger.error(f"Error getting tweets for @{username}: {e}")
            return []
    
    def _search_tweets(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        搜索推文
        
        Args:
            query: 搜索关键词
            max_results: 返回数量
        """
        try:
            tweets = self.client.search_recent_tweets(
                query=query,
                max_results=max_results,
                tweet_fields=["created_at", "public_metrics", "author_id"],
            )
            
            if not tweets.data:
                return []
            
            results = []
            for tweet in tweets.data:
                metrics = tweet.public_metrics or {}
                results.append({
                    "id": str(tweet.id),
                    "text": tweet.text,
                    "author_id": str(tweet.author_id),
                    "created_at": tweet.created_at.isoformat() if tweet.created_at else "",
                    "likes": metrics.get("like_count", 0),
                    "retweets": metrics.get("retweet_count", 0),
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching tweets: {e}")
            return []
    
    def parse(self, raw_data: Dict[str, Any]) -> List[TwitterHotTopic]:
        """
        解析原始数据为标准格式
        
        Args:
            raw_data: fetch() 返回的原始数据
            
        Returns:
            TwitterHotTopic 列表
        """
        results = []
        tweets = raw_data.get("tweets", [])
        timestamp = raw_data.get("timestamp", datetime.now())
        
        for tweet in tweets:
            results.append(TwitterHotTopic(
                tweet_id=tweet.get("id", ""),
                text=tweet.get("text", ""),
                username=tweet.get("username", ""),
                user_name=tweet.get("user_name", ""),
                created_at=tweet.get("created_at", ""),
                likes=tweet.get("likes", 0),
                retweets=tweet.get("retweets", 0),
                url=tweet.get("url", ""),
                timestamp=timestamp
            ))
        
        return results
    
    # ==================== 便捷方法 ====================
    
    def get_crypto_kol_tweets(self) -> List[Dict]:
        """获取加密货币 KOL 的最新推文"""
        original_accounts = self.accounts_to_follow
        self.accounts_to_follow = self.RECOMMENDED_ACCOUNTS.get("crypto", [])
        
        tweets = self._fetch_user_tweets()
        
        self.accounts_to_follow = original_accounts
        return tweets
    
    def search_crypto_news(self, keyword: str = "bitcoin") -> List[Dict]:
        """搜索加密货币相关推文"""
        query = f"{keyword} -is:retweet lang:en"
        return self._search_tweets(query, max_results=10)
