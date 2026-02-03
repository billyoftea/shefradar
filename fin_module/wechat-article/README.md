# 微信公众号文章导出工具 - wechat-article-exporter

## 项目介绍

这是 [wechat-article-exporter](https://github.com/wechat-article/wechat-article-exporter) 的 Docker 部署配置。

一款在线的**微信公众号文章批量下载**工具：
- 支持导出阅读量与评论数据
- 无需搭建复杂环境
- 支持 Docker 私有化部署
- 支持下载多种文件格式（HTML 格式可100%还原文章排版与样式）

## 快速开始

### 1. 启动服务

```bash
cd /Users/angeloxu/Desktop/finradar/fin_module/wechat-article
docker-compose up -d
```

### 2. 访问界面

打开浏览器访问: http://localhost:3001

### 3. 使用流程

1. **登录**: 扫描二维码登录微信公众号后台（需要有公众号）
2. **搜索**: 输入目标公众号名称进行搜索
3. **选择**: 选择要下载的文章
4. **导出**: 选择导出格式（html/json/excel/txt/md/docx）并下载

## 功能特性

- [x] 搜索公众号，支持关键字搜索
- [x] 支持导出 html/json/excel/txt/md/docx 格式
- [x] HTML 格式可100%还原文章样式（打包图片和样式文件）
- [x] 缓存文章列表数据，减少接口请求次数
- [x] 支持文章过滤（作者、标题、发布时间、原创标识、所属合集）
- [x] 支持合集下载
- [x] 支持图片分享消息
- [x] 支持视频分享消息
- [x] 支持导出评论、评论回复、阅读量、转发量等数据

## 工作原理

利用微信公众号后台写文章时的"搜索其他公众号文章"功能来实现抓取指定公众号所有文章的目的。

## 相关金融公众号推荐

可以关注以下财经/加密货币相关公众号：

| 公众号名称 | 类型 | 说明 |
|-----------|------|------|
| 华尔街见闻 | 综合财经 | 全球金融资讯 |
| 财联社 | 综合财经 | 实时财经新闻 |
| Wind资讯 | 金融数据 | 专业金融数据 |
| 金十数据 | 实时数据 | 外汇、期货数据 |
| 吴晓波频道 | 财经观点 | 财经评论 |
| 36氪 | 科技创投 | 科技公司新闻 |
| PANews | 加密货币 | 区块链资讯 |
| 比推 BitPush | 加密货币 | 加密市场新闻 |
| 巴比特资讯 | 加密货币 | 区块链深度报道 |
| 深潮 TechFlow | 加密货币 | Web3 资讯 |

## Docker 命令

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看状态
docker-compose ps
```

## 数据存储

导出的文章数据存储在 `./data` 目录下。

## 注意事项

1. **账号安全**: 本程序不会利用您扫码登录的公众号进行任何私有爬虫
2. **版权声明**: 通过本程序获取的公众号文章内容，版权归文章原作者所有
3. **合理使用**: 请合理使用，避免频繁请求导致账号受限

## 参考链接

- 项目仓库: https://github.com/wechat-article/wechat-article-exporter
- 在线使用: https://down.mptext.top
- 使用文档: https://docs.mptext.top
