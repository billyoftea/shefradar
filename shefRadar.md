我现在想基于FinRadar项目，写一个每日追踪最新大盘和板块的agent，计划包括以下几个板块：
1.大盘情况：
    上证指数的涨跌，沪深300的涨跌
    成交量、国家队情况、北上资金、主力流向
    上涨的股票/下跌股票的比例

2.分版块情况，按照统一的板块标准的涨跌情况。此外，我特别关注科技股、周期股、农业股，需要重点说明这三个大类的情况

3.黄金、白银的涨跌

4.比特币、以太坊的涨跌，以及一些最近比较火的meme币

5.期货市场

6.twitter比较火的项目解析

7.github上热门项目解析


在除了目前的newsnow外，还要增加一些其他的信息源：

信息源：
新闻：财联社
金融数据：ths，金价、银价，yahoo finance
twitter：补充国外政要和web3的最新动态

• 大盘/板块：ifind。。。、东方财富API（北上/主力流）、AkShare库。​
• 黄金/白银：Yahoo Finance API或Investing.com。
• 比特币/meme币：CoinGecko免费API（ETH、SOL、DOGE等日涨跌）。
• 期货：Wind API或CFFEX官网。
Twitter火项目：Twitter API v2（trends endpoint）或LunarCrush（crypto社交热度）。
