# 自建 Nitter 实例部署指南

本目录包含自建 Nitter 实例所需的所有配置文件。

## 为什么需要自建 Nitter？

由于 Twitter/X 在 2023 年后大幅限制了 API 访问和第三方客户端，公共 Nitter 实例基本都已失效。
自建 Nitter 实例需要使用真实的 Twitter 账号 session tokens 才能正常工作。

## 文件说明

```
nitter/
├── docker-compose.yml          # Docker 部署配置
├── nitter.conf                 # Nitter 服务配置
├── guest_accounts.json.example # Token 配置模板
├── get_twitter_tokens.py       # Token 获取脚本
└── README.md                   # 本文档
```

## 部署步骤

### 1. 准备 Twitter 账号

建议准备 1-2 个 Twitter 账号（推荐使用小号）。

### 2. 获取 Session Tokens

**方法一：使用脚本自动获取**

```bash
# 安装依赖
pip install playwright
playwright install chromium

# 运行脚本
python get_twitter_tokens.py
```

**方法二：手动从浏览器获取**

1. 登录 Twitter (https://twitter.com)
2. 打开浏览器开发者工具 (F12)
3. 切换到 Application/Storage -> Cookies
4. 找到以下两个 cookie:
   - `auth_token` -> 对应 `oauth_token`
   - `ct0` -> 对应 `oauth_token_secret`
5. 复制值到 `guest_accounts.json`

### 3. 配置 Token 文件

```bash
# 复制模板文件
cp guest_accounts.json.example guest_accounts.json

# 编辑 guest_accounts.json，填入真实的 token
```

`guest_accounts.json` 格式:
```json
[
  {
    "oauth_token": "从 auth_token cookie 获取的值",
    "oauth_token_secret": "从 ct0 cookie 获取的值"
  }
]
```

### 4. 启动 Nitter

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 5. 验证服务

访问以下地址确认服务正常:

- 主页: http://localhost:8080
- RSS 测试: http://localhost:8080/VitalikButerin/rss
- 健康检查: http://localhost:8080/about

## 在 FinRadar 中使用

配置 `NitterRSSFetcher` 使用本地实例:

```python
from fin_module.fetcher.nitter_rss import NitterRSSFetcher

fetcher = NitterRSSFetcher(config={
    "nitter_instance": "http://localhost:8080",
    "accounts": ["VitalikButerin", "cz_binance"]
})

result = await fetcher.fetch()
```

或者设置环境变量:

```bash
export NITTER_INSTANCE="http://localhost:8080"
```

## 配置说明

### nitter.conf 重要参数

| 参数 | 说明 | 推荐值 |
|------|------|--------|
| `enableRSS` | 是否启用 RSS | `true` |
| `rssMinutes` | RSS 缓存时间 (分钟) | `10` |
| `tokenCount` | 每个账号的请求数 | `10` |
| `hmacKey` | 安全密钥 | 随机字符串 |

### 性能优化

- 增加 `tokenCount` 可提高并发能力
- 降低 `rssMinutes` 可获取更实时的数据
- 多个 Twitter 账号可分担请求压力

## 常见问题

### Q: Token 多久会过期？
A: 通常 1-3 个月，如果服务出现 403 错误需要更新 token。

### Q: 需要几个账号？
A: 个人使用 1-2 个即可，高频率访问建议 3-5 个。

### Q: 是否会导致账号被封？
A: 有风险，建议使用小号，避免使用主账号。

### Q: 国内网络能否使用？
A: 需要能够访问 Twitter，如果无法直接访问需要配置代理。

## 配置代理 (可选)

如果需要代理访问 Twitter，编辑 `nitter.conf`:

```ini
[Config]
proxy = "http://your-proxy:port"
proxyAuth = "username:password"  # 如果需要认证
```

## 监控和维护

### 检查服务状态
```bash
docker-compose ps
docker-compose logs nitter
```

### 更新 Nitter
```bash
docker-compose pull
docker-compose up -d
```

### 清理缓存
```bash
docker-compose exec nitter-redis redis-cli FLUSHALL
```

## 参考链接

- [Nitter GitHub](https://github.com/zedeus/nitter)
- [Nitter Wiki](https://github.com/zedeus/nitter/wiki)
- [Guest Account 部署文档](https://github.com/zedeus/nitter/wiki/Guest-Account-Branch-Deployment)
