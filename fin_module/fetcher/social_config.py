#!/usr/bin/env python3
"""
FinRadar 社交源配置管理器

支持从 config/config.yaml 读取 Twitter 和微信公众号配置
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class TwitterConfig:
    """Twitter/Nitter RSS 配置"""
    enabled: bool = True
    nitter_instance: str = "http://localhost:8080"
    accounts: Dict[str, List[str]] = field(default_factory=dict)
    max_tweets_per_user: int = 10
    timeout: int = 15
    
    def get_all_accounts(self) -> List[str]:
        """获取所有账号列表"""
        all_accounts = []
        for category, accounts in self.accounts.items():
            all_accounts.extend(accounts)
        return all_accounts
    
    def get_accounts_by_category(self, category: str) -> List[str]:
        """按分类获取账号"""
        return self.accounts.get(category, [])


@dataclass
class WechatConfig:
    """微信公众号配置"""
    enabled: bool = True
    service_url: str = "http://localhost:3001"
    timeout: int = 30
    accounts: Dict[str, List[str]] = field(default_factory=dict)
    max_articles_per_account: int = 20
    max_age_days: int = 3
    
    def get_all_accounts(self) -> List[str]:
        """获取所有公众号列表"""
        all_accounts = []
        for category, accounts in self.accounts.items():
            all_accounts.extend(accounts)
        return all_accounts
    
    def get_accounts_by_category(self, category: str) -> List[str]:
        """按分类获取公众号"""
        return self.accounts.get(category, [])


class SocialSourceConfig:
    """
    社交源配置管理器
    
    从 config/config.yaml 读取 Twitter 和微信公众号配置
    
    使用示例:
        config = SocialSourceConfig()
        
        # 获取 Twitter 配置
        twitter_accounts = config.twitter.get_all_accounts()
        
        # 获取微信公众号配置
        wechat_accounts = config.wechat.get_all_accounts()
    """
    
    # 配置文件默认路径
    DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，默认为 config/config.yaml
        """
        self.config_path = Path(config_path) if config_path else self.DEFAULT_CONFIG_PATH
        self._raw_config: Dict = {}
        self._twitter: Optional[TwitterConfig] = None
        self._wechat: Optional[WechatConfig] = None
        
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        if not self.config_path.exists():
            print(f"⚠️ 配置文件不存在: {self.config_path}")
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._raw_config = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"❌ 读取配置文件失败: {e}")
    
    @property
    def twitter(self) -> TwitterConfig:
        """获取 Twitter/Nitter RSS 配置"""
        if self._twitter is None:
            twitter_config = self._raw_config.get("twitter", {})
            self._twitter = TwitterConfig(
                enabled=twitter_config.get("enabled", True),
                nitter_instance=twitter_config.get("nitter_instance", "http://localhost:8080"),
                accounts=twitter_config.get("accounts", {}),
                max_tweets_per_user=twitter_config.get("max_tweets_per_user", 10),
                timeout=twitter_config.get("timeout", 15)
            )
        return self._twitter
    
    @property
    def wechat(self) -> WechatConfig:
        """获取微信公众号配置"""
        if self._wechat is None:
            wechat_config = self._raw_config.get("wechat", {})
            self._wechat = WechatConfig(
                enabled=wechat_config.get("enabled", True),
                service_url=wechat_config.get("service_url", "http://localhost:3001"),
                timeout=wechat_config.get("timeout", 30),
                accounts=wechat_config.get("accounts", {}),
                max_articles_per_account=wechat_config.get("max_articles_per_account", 20),
                max_age_days=wechat_config.get("max_age_days", 3)
            )
        return self._wechat
    
    def reload(self):
        """重新加载配置"""
        self._twitter = None
        self._wechat = None
        self._load_config()
    
    def get_raw_config(self) -> Dict:
        """获取原始配置字典"""
        return self._raw_config


# ==================== 便捷函数 ====================

def get_twitter_accounts() -> List[str]:
    """
    获取所有 Twitter 账号
    
    Returns:
        Twitter 账号用户名列表
    """
    config = SocialSourceConfig()
    return config.twitter.get_all_accounts()


def get_wechat_accounts() -> List[str]:
    """
    获取所有微信公众号
    
    Returns:
        微信公众号名称列表
    """
    config = SocialSourceConfig()
    return config.wechat.get_all_accounts()


def print_config_summary():
    """打印配置摘要"""
    config = SocialSourceConfig()
    
    print("=" * 60)
    print("📋 FinRadar 社交源配置摘要")
    print("=" * 60)
    
    # Twitter 配置
    print("\n🐦 Twitter/Nitter RSS 配置:")
    print(f"   启用状态: {'✅ 已启用' if config.twitter.enabled else '❌ 已禁用'}")
    print(f"   Nitter 实例: {config.twitter.nitter_instance}")
    print(f"   超时时间: {config.twitter.timeout}s")
    print(f"   每用户推文数: {config.twitter.max_tweets_per_user}")
    
    print("\n   📌 关注账号:")
    for category, accounts in config.twitter.accounts.items():
        print(f"      [{category}] ({len(accounts)}人): {', '.join(accounts[:3])}{'...' if len(accounts) > 3 else ''}")
    
    total_twitter = len(config.twitter.get_all_accounts())
    print(f"   合计: {total_twitter} 个账号")
    
    # 微信公众号配置
    print("\n📱 微信公众号配置:")
    print(f"   启用状态: {'✅ 已启用' if config.wechat.enabled else '❌ 已禁用'}")
    print(f"   服务地址: {config.wechat.service_url}")
    print(f"   超时时间: {config.wechat.timeout}s")
    print(f"   每账号文章数: {config.wechat.max_articles_per_account}")
    print(f"   最大文章天数: {config.wechat.max_age_days} 天")
    
    print("\n   📌 关注公众号:")
    for category, accounts in config.wechat.accounts.items():
        print(f"      [{category}] ({len(accounts)}个): {', '.join(accounts[:3])}{'...' if len(accounts) > 3 else ''}")
    
    total_wechat = len(config.wechat.get_all_accounts())
    print(f"   合计: {total_wechat} 个公众号")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    print_config_summary()
