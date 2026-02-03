#!/usr/bin/env python3
"""
Twitter Guest Account Token 获取工具

此脚本用于从 Twitter 账号获取 session tokens，
这些 tokens 是运行自建 Nitter 实例所必需的。

使用方法:
    python get_twitter_tokens.py

警告:
    - 使用此脚本可能违反 Twitter 服务条款
    - 建议使用专门的小号
    - tokens 会过期，需要定期更新

参考:
    https://github.com/zedeus/nitter/wiki/Guest-Account-Branch-Deployment
"""

import asyncio
import json
import os
import sys
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("❌ 需要安装 playwright:")
    print("   pip install playwright")
    print("   playwright install chromium")
    sys.exit(1)


async def get_twitter_tokens(username: str, password: str) -> dict:
    """
    通过模拟登录获取 Twitter session tokens
    
    Args:
        username: Twitter 用户名
        password: Twitter 密码
    
    Returns:
        包含 oauth_token 和 oauth_token_secret 的字典
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 设为 False 方便调试
        context = await browser.new_context()
        page = await context.new_page()
        
        print(f"🔄 正在登录 @{username}...")
        
        try:
            # 访问 Twitter 登录页面
            await page.goto("https://twitter.com/i/flow/login")
            await page.wait_for_timeout(3000)
            
            # 输入用户名
            print("📝 输入用户名...")
            await page.fill('input[autocomplete="username"]', username)
            await page.click('text=Next')
            await page.wait_for_timeout(2000)
            
            # 检查是否需要验证（有时 Twitter 会要求邮箱/手机验证）
            try:
                # 如果出现额外验证步骤
                verify_input = await page.query_selector('input[data-testid="ocfEnterTextTextInput"]')
                if verify_input:
                    print("⚠️  Twitter 要求额外验证，请在浏览器中手动完成")
                    await page.wait_for_timeout(30000)  # 等待30秒手动处理
            except:
                pass
            
            # 输入密码
            print("🔑 输入密码...")
            await page.fill('input[name="password"]', password)
            await page.click('text=Log in')
            await page.wait_for_timeout(5000)
            
            # 检查是否登录成功
            if "home" in page.url or "twitter.com" in page.url:
                print("✅ 登录成功!")
            else:
                print(f"⚠️  当前页面: {page.url}")
            
            # 获取 cookies
            cookies = await context.cookies()
            
            # 查找关键的 auth_token 和 ct0
            token_data = {}
            for cookie in cookies:
                if cookie['name'] == 'auth_token':
                    token_data['oauth_token'] = cookie['value']
                elif cookie['name'] == 'ct0':
                    token_data['oauth_token_secret'] = cookie['value']
            
            if 'oauth_token' in token_data and 'oauth_token_secret' in token_data:
                print(f"✅ 成功获取 tokens!")
                return token_data
            else:
                print("❌ 未能获取完整的 tokens")
                print(f"   获取到的 cookies: {[c['name'] for c in cookies]}")
                return {}
        
        except Exception as e:
            print(f"❌ 错误: {e}")
            return {}
        
        finally:
            await browser.close()


async def get_guest_token() -> dict:
    """
    获取 Guest Token (不需要登录)
    
    注意: Guest token 功能已被 Twitter 限制，可能无法使用
    """
    import aiohttp
    
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs=1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        async with session.post(
            "https://api.twitter.com/1.1/guest/activate.json",
            headers=headers
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return {"guest_token": data.get("guest_token")}
            else:
                print(f"❌ 获取 guest token 失败: {resp.status}")
                return {}


def save_tokens(tokens: list, output_file: str = "guest_accounts.json"):
    """保存 tokens 到文件"""
    output_path = Path(__file__).parent / output_file
    
    with open(output_path, 'w') as f:
        json.dump(tokens, f, indent=2)
    
    print(f"✅ Tokens 已保存到: {output_path}")


async def main():
    print("=" * 50)
    print("Twitter Session Token 获取工具")
    print("=" * 50)
    print()
    print("⚠️  警告: 此工具用于获取运行 Nitter 所需的 tokens")
    print("   建议使用专门的小号，避免主账号被限制")
    print()
    
    # 获取账号信息
    accounts = []
    
    while True:
        print("-" * 30)
        username = input("请输入 Twitter 用户名 (输入 q 结束): ").strip()
        
        if username.lower() == 'q':
            break
        
        password = input("请输入密码: ").strip()
        
        if username and password:
            tokens = await get_twitter_tokens(username, password)
            if tokens:
                accounts.append(tokens)
                print(f"✅ 已获取 @{username} 的 tokens")
            else:
                print(f"❌ 获取 @{username} 的 tokens 失败")
        
        another = input("是否继续添加账号? (y/n): ").strip().lower()
        if another != 'y':
            break
    
    if accounts:
        save_tokens(accounts)
        print()
        print("=" * 50)
        print("完成! 接下来请:")
        print("1. 确保 guest_accounts.json 已生成")
        print("2. 运行: docker-compose up -d")
        print("3. 访问: http://localhost:8080")
        print("=" * 50)
    else:
        print("未获取到任何 tokens")


if __name__ == "__main__":
    asyncio.run(main())
