"""
Nitter RSS 推文抓取器

Nitter 是一个开源的 Twitter 前端替代品，提供 RSS 订阅功能

推荐使用方式:
    1. 自建 Nitter 实例 (最稳定，需要 Twitter 账号 tokens)
    2. 公共 Nitter 实例 (可能不可用)

自建实例部署:
    参考 fin_module/nitter/README.md

使用方法:
    # 方式1: 使用自建实例 (推荐)
    from fin_module.fetcher.nitter_rss import NitterRSSFetcher
    
    fetcher = NitterRSSFetcher(config={
        "nitter_instance": "http://localhost:8080",  # 自建实例地址
        "accounts": ["VitalikButerin", "elonmusk"]
    })
    data = await fetcher.fetch()
    
    # 方式2: 使用环境变量配置
    # export NITTER_INSTANCE="http://localhost:8080"
    fetcher = NitterRSSFetcher(config={
        "accounts": ["VitalikButerin"]
    })
"""

import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging
import re
import html
import os
from email.utils import parsedate_to_datetime

from . import BaseFetcher

logger = logging.getLogger(__name__)


class NitterRSSFetcher(BaseFetcher):
    """
    Nitter RSS 推文抓取器
    
    通过 Nitter 实例的 RSS 订阅源获取推文
    完全免费，无需 Twitter API
    """
    
    # 自建实例地址 (优先使用，最稳定)
    # 可通过环境变量 NITTER_INSTANCE 或 config 参数配置
    LOCAL_INSTANCE = os.environ.get("NITTER_INSTANCE", "")
    
    # 公共 Nitter 实例备用列表 (2024年后大部分已失效)
    # 注意: 公共实例可能随时下线，强烈建议自建实例
    # 自建部署文档: fin_module/nitter/README.md
    NITTER_INSTANCES = [
        # 这些公共实例可能已经失效，仅作为后备
        "https://nitter.privacydev.net",
        "https://nitter.poast.org",
        "https://nitter.lucabased.xyz",
        "https://nitter.perennialte.ch",
        "https://nitter.net",
    ]
    
    # 推荐关注的账号
    RECOMMENDED_ACCOUNTS = {
        "crypto": [
            "VitalikButerin",   # 以太坊创始人
            "cz_binance",       # Binance CEO
            "WatcherGuru",      # 加密新闻
            "whale_alert",      # 大额转账监控
            "DefiLlama",        # DeFi 数据
            "coinaborek",       # Coinbase
        ],
        "tech": [
            "elonmusk",         # Elon Musk
            "sama",             # Sam Altman
            "ylecun",           # Yann LeCun
            "OpenAI",           # OpenAI 官方
        ],
        "finance": [
            "MacroAlf",         # 宏观分析
            "unusual_whales",   # 期权异动
            "zerohedge",        # 金融新闻
        ],
    }
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        
        # 配置要关注的账号
        self.accounts = self.config.get("accounts", [])
        if not self.accounts:
            # 默认使用 crypto 账号
            self.accounts = self.RECOMMENDED_ACCOUNTS.get("crypto", [])[:5]
        
        # 每个账号获取的推文数量
        self.max_tweets_per_user = self.config.get("max_tweets_per_user", 10)
        
        # 确定 Nitter 实例 (优先级: config > 环境变量 > 默认公共实例)
        self.current_instance = self._determine_instance()
        
        # 是否使用自建实例
        self.using_local_instance = self._is_local_instance(self.current_instance)
        
        # 请求超时时间
        self.timeout = self.config.get("timeout", 15)
        
        # 是否启用
        self.enabled = True
        
        instance_type = "自建" if self.using_local_instance else "公共"
        logger.info(f"NitterRSSFetcher initialized with {len(self.accounts)} accounts, using {instance_type} instance: {self.current_instance}")
    
    def _determine_instance(self) -> str:
        """
        确定要使用的 Nitter 实例
        优先级: config 参数 > 环境变量 > 默认公共实例
        """
        # 1. 首先检查 config 参数
        config_instance = self.config.get("nitter_instance", "")
        if config_instance:
            return config_instance.rstrip("/")
        
        # 2. 检查环境变量
        env_instance = os.environ.get("NITTER_INSTANCE", "")
        if env_instance:
            return env_instance.rstrip("/")
        
        # 3. 使用默认公共实例
        return self.NITTER_INSTANCES[0] if self.NITTER_INSTANCES else ""
    
    def _is_local_instance(self, url: str) -> bool:
        """检查是否为本地/自建实例"""
        local_patterns = ["localhost", "127.0.0.1", "0.0.0.0", "192.168.", "10."]
        return any(pattern in url for pattern in local_patterns)
    
    async def fetch(self) -> Dict[str, Any]:
        """
        抓取所有关注账号的推文
        
        Returns:
            包含推文列表的字典
        """
        all_tweets = []
        errors = []
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={"User-Agent": "Mozilla/5.0 (compatible; FinRadar/1.0)"}
        ) as session:
            # 并发获取所有账号的推文
            tasks = [
                self._fetch_user_rss(session, username)
                for username in self.accounts
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for username, result in zip(self.accounts, results):
                if isinstance(result, Exception):
                    errors.append(f"@{username}: {str(result)}")
                    logger.warning(f"Failed to fetch @{username}: {result}")
                elif result:
                    all_tweets.extend(result)
        
        # 按时间排序（最新在前）
        all_tweets.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return {
            "tweets": all_tweets,
            "errors": errors,
            "instance_used": self.current_instance,
            "timestamp": datetime.now()
        }
    
    async def _fetch_user_rss(self, session: aiohttp.ClientSession, username: str) -> List[Dict]:
        """
        获取单个用户的 RSS 订阅
        
        Args:
            session: aiohttp 会话
            username: Twitter 用户名
        
        Returns:
            推文列表
        """
        # 构建实例列表: 自建实例优先，公共实例作为后备
        instances_to_try = [self.current_instance]
        
        # 如果使用自建实例，不添加公共实例作为后备
        # 如果使用公共实例，添加其他公共实例作为后备
        if not self.using_local_instance:
            for inst in self.NITTER_INSTANCES:
                if inst != self.current_instance and inst not in instances_to_try:
                    instances_to_try.append(inst)
        
        last_error = None
        for instance in instances_to_try:
            rss_url = f"{instance}/{username}/rss"
            
            try:
                async with session.get(rss_url) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # 检查是否是有效的 RSS 内容
                        if not content.strip().startswith("<"):
                            logger.warning(f"Invalid RSS response from {instance}: not XML")
                            continue
                        
                        tweets = self._parse_rss(content, username)
                        
                        # 更新当前可用实例
                        if instance != self.current_instance:
                            logger.info(f"Switched to working instance: {instance}")
                            self.current_instance = instance
                        
                        return tweets[:self.max_tweets_per_user]
                    
                    elif response.status == 404:
                        logger.warning(f"User @{username} not found on {instance}")
                        return []
                    
                    elif response.status == 403:
                        logger.warning(f"Access denied (403) from {instance}, may need authentication tokens")
                        last_error = f"403 Forbidden - instance may require tokens"
                        continue
                    
                    else:
                        logger.warning(f"HTTP {response.status} from {instance}")
                        last_error = f"HTTP {response.status}"
                        continue
                    
            except asyncio.TimeoutError:
                logger.warning(f"Timeout fetching {rss_url}")
                last_error = "Timeout"
                continue
            except Exception as e:
                logger.warning(f"Error fetching {rss_url}: {e}")
                last_error = str(e)
                continue
        
        error_msg = f"All Nitter instances failed for @{username}"
        if last_error:
            error_msg += f" (last error: {last_error})"
        if self.using_local_instance:
            error_msg += ". Make sure your local Nitter instance is running with valid tokens."
        raise Exception(error_msg)
    
    def _parse_rss(self, rss_content: str, username: str) -> List[Dict]:
        """
        解析 RSS XML 内容
        
        Args:
            rss_content: RSS XML 字符串
            username: 用户名
        
        Returns:
            推文列表
        """
        tweets = []
        
        try:
            root = ET.fromstring(rss_content)
            channel = root.find("channel")
            
            if channel is None:
                return []
            
            # 获取用户显示名称
            user_name = username
            title_elem = channel.find("title")
            if title_elem is not None and title_elem.text:
                # 格式: "User Name / @username"
                user_name = title_elem.text.split(" /")[0].strip()
            
            # 解析每条推文
            for item in channel.findall("item"):
                tweet = self._parse_item(item, username, user_name)
                if tweet:
                    tweets.append(tweet)
        
        except ET.ParseError as e:
            logger.error(f"RSS parse error: {e}")
        
        return tweets
    
    def _parse_item(self, item: ET.Element, username: str, user_name: str) -> Optional[Dict]:
        """
        解析单条 RSS item
        
        Args:
            item: XML item 元素
            username: 用户名
            user_name: 显示名称
        
        Returns:
            推文字典或 None
        """
        try:
            # 获取推文链接
            link_elem = item.find("link")
            link = link_elem.text if link_elem is not None else ""
            
            # 从链接提取推文 ID
            tweet_id = ""
            if link:
                # 格式: https://nitter.xxx/user/status/123456
                match = re.search(r"/status/(\d+)", link)
                if match:
                    tweet_id = match.group(1)
            
            # 获取发布时间
            pub_date_elem = item.find("pubDate")
            created_at = ""
            if pub_date_elem is not None and pub_date_elem.text:
                try:
                    dt = parsedate_to_datetime(pub_date_elem.text)
                    created_at = dt.isoformat()
                except:
                    created_at = pub_date_elem.text
            
            # 获取推文内容
            description_elem = item.find("description")
            raw_text = description_elem.text if description_elem is not None else ""
            
            # 清理 HTML 标签
            text = self._clean_html(raw_text)
            
            # 构造 Twitter 原始链接
            twitter_url = f"https://twitter.com/{username}/status/{tweet_id}" if tweet_id else ""
            
            return {
                "id": tweet_id,
                "text": text,
                "username": username,
                "user_name": user_name,
                "created_at": created_at,
                "url": twitter_url,
                "nitter_url": link,
                # RSS 不提供互动数据
                "likes": 0,
                "retweets": 0,
                "replies": 0,
                "source": "nitter_rss"
            }
        
        except Exception as e:
            logger.error(f"Error parsing RSS item: {e}")
            return None
    
    def _clean_html(self, html_text: str) -> str:
        """
        清理 HTML 标签，保留纯文本
        
        Args:
            html_text: 包含 HTML 的文本
        
        Returns:
            清理后的纯文本
        """
        if not html_text:
            return ""
        
        # 解码 HTML 实体
        text = html.unescape(html_text)
        
        # 将 <br> 转换为换行
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        
        # 将链接转换为 URL
        text = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>.*?</a>', r'\1', text)
        
        # 移除所有其他 HTML 标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 清理多余空白
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = text.strip()
        
        return text
    
    def parse(self, raw_data: Dict[str, Any]) -> List[Dict]:
        """
        解析原始数据（已经是标准格式，直接返回）
        """
        return raw_data.get("tweets", [])
    
    # ==================== 便捷方法 ====================
    
    async def get_single_user(self, username: str, max_tweets: int = 10) -> List[Dict]:
        """
        获取单个用户的推文
        
        Args:
            username: Twitter 用户名
            max_tweets: 最大推文数
        
        Returns:
            推文列表
        """
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={"User-Agent": "Mozilla/5.0 (compatible; FinRadar/1.0)"}
        ) as session:
            try:
                tweets = await self._fetch_user_rss(session, username)
                return tweets[:max_tweets]
            except Exception as e:
                logger.error(f"Error fetching @{username}: {e}")
                return []
    
    def get_all_recommended_accounts(self) -> Dict[str, List[str]]:
        """获取所有推荐账号"""
        return self.RECOMMENDED_ACCOUNTS
    
    async def check_instance_health(self) -> Dict[str, Any]:
        """
        检查所有 Nitter 实例的健康状态
        
        Returns:
            包含各实例状态的字典
        """
        results = {
            "local_instance": None,
            "public_instances": {}
        }
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=5)
        ) as session:
            # 检查自建实例
            if self.using_local_instance:
                try:
                    async with session.get(f"{self.current_instance}/VitalikButerin/rss") as response:
                        results["local_instance"] = {
                            "url": self.current_instance,
                            "status": response.status,
                            "healthy": response.status == 200
                        }
                except Exception as e:
                    results["local_instance"] = {
                        "url": self.current_instance,
                        "status": "error",
                        "healthy": False,
                        "error": str(e)
                    }
            
            # 检查公共实例
            for instance in self.NITTER_INSTANCES:
                try:
                    async with session.get(f"{instance}/VitalikButerin/rss") as response:
                        results["public_instances"][instance] = {
                            "status": response.status,
                            "healthy": response.status == 200
                        }
                except Exception as e:
                    results["public_instances"][instance] = {
                        "status": "error",
                        "healthy": False,
                        "error": str(e)
                    }
        
        return results
    
    def get_instance_info(self) -> Dict[str, Any]:
        """
        获取当前实例配置信息
        
        Returns:
            当前实例的配置信息
        """
        return {
            "current_instance": self.current_instance,
            "is_local": self.using_local_instance,
            "accounts": self.accounts,
            "max_tweets_per_user": self.max_tweets_per_user,
            "timeout": self.timeout,
            "env_instance": os.environ.get("NITTER_INSTANCE", "(not set)"),
            "setup_guide": "See fin_module/nitter/README.md for self-hosted setup"
        }


# ==================== 便捷函数 ====================

async def quick_fetch_tweets(usernames: List[str]) -> List[Dict]:
    """
    快速获取指定用户的推文
    
    Args:
        usernames: 用户名列表
    
    Returns:
        推文列表
    
    示例:
        tweets = await quick_fetch_tweets(["VitalikButerin", "elonmusk"])
    """
    fetcher = NitterRSSFetcher(config={"accounts": usernames})
    result = await fetcher.fetch()
    return result.get("tweets", [])
