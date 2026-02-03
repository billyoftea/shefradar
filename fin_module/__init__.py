"""
FinRadar 市场追踪模块
=====================

基于开源项目和Python包的金融数据采集与分析模块

模块结构:
- fetcher/: 数据抓取器 (基于 akshare, yfinance, pycoingecko, tweepy 等)
- analyzer/: 数据分析器
- models/: 数据模型定义
- report/: 报告生成器
- utils/: 工具函数

依赖的开源库:
- akshare: A股、期货数据
- yfinance: 贵金属、国际市场数据  
- pycoingecko/requests: 加密货币数据
- tweepy: Twitter API
- PyGithub: GitHub API
"""

__version__ = "0.1.0"
__author__ = "FinRadar"
