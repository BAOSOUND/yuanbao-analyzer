"""
元宝引用链接提取器 - 核心模块（优化版）
"""

import time
import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import sys
import io

# 设置控制台编码为 UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def log(msg):
    """实时输出日志"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


from playwright.sync_api import sync_playwright


class YuanbaoAnalyzer:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright = None
        self.context = None
        self.page = None
        self.question_count = 0
        
    def start(self):
        """启动浏览器"""
        log("启动浏览器...")
        self.playwright = sync_playwright().start()
        
        browser_data = Path.cwd() / "yuanbao_browser_data"
        browser_data.mkdir(exist_ok=True)
        
        self.context = self.playwright.chromium.launch_persistent_context(
            str(browser_data),
            headless=self.headless,
            args=['--start-maximized'],
            no_viewport=True
        )
        
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        log("浏览器启动成功")
        return self
    
    def wait_for_login(self):
        """等待用户手动登录"""
        log("打开元宝首页...")
        self.page.goto('https://yuanbao.tencent.com/')
        
        # 检查是否已登录
        try:
            self.page.wait_for_selector('div[contenteditable="true"]', timeout=5000)
            log("检测到已登录状态")
            return True
        except:
            pass
        
        log("\n" + "="*60)
        log("浏览器已打开，请手动完成登录")
        log("登录步骤：")
        log("1. 点击「登录」按钮")
        log("2. 使用微信或手机号登录")
        log("3. 完成登录后回到此页面")
        log("\n登录成功后按回车键继续...")
        log("="*60)
        
        input()
        log("继续执行...")
        return True
    
    def select_model(self):
        """选择 Hunyuan 模型"""
        log("检查当前模型...")
        
        time.sleep(2)
        
        try:
            model_btn = self.page.locator('.ybc-model-select-button').first
            if model_btn.count() > 0 and model_btn.is_visible():
                current_text = model_btn.text_content() or ''
                if 'Hunyuan' in current_text or '混元' in current_text:
                    log("已经是 Hunyuan 模型")
                    return True
                
                model_btn.click()
                log("点击模型选择按钮")
                time.sleep(1)
                
                hunyuan_option = self.page.locator('text=Hunyuan').first
                if hunyuan_option.count() > 0 and hunyuan_option.is_visible():
                    hunyuan_option.click()
                    log("已切换到 Hunyuan 模型")
                    time.sleep(1)
                    return True
        except Exception as e:
            log(f"模型切换失败: {e}")
        
        log("使用当前模型")
        return True
    
    def new_conversation(self):
        """开启新对话 - 使用 JavaScript 快速点击"""
        log("开启新对话...")
        
        # 直接使用 JavaScript 点击新建对话图标
        clicked = self.page.evaluate('''
            () => {
                // 优先使用新建对话图标
                const icon = document.querySelector('.icon-yb-ic_newchat_20');
                if (icon) {
                    icon.click();
                    return true;
                }
                // 备用：通过按钮文字
                const btns = document.querySelectorAll('button');
                for (let btn of btns) {
                    if (btn.textContent && btn.textContent.includes('新对话')) {
                        btn.click();
                        return true;
                    }
                }
                return false;
            }
        ''')
        
        if clicked:
            log("✅ 新对话已开启")
            time.sleep(1)  # 减少等待时间
        else:
            log("❌ 开启新对话失败")
    
    def wait_for_answer_complete(self):
        """等待回答完成 - 不设超时，等停止按钮消失"""
        log("等待回答生成...")
        
        # 等待停止生成按钮出现（开始生成）
        try:
            self.page.wait_for_selector('button:has-text("停止生成")', timeout=10000)
            log("检测到开始生成")
        except:
            log("可能已经开始生成")
        
        # 无限等待停止生成按钮消失（不设超时，一直等到生成完成）
        log("等待回答完成...")
        self.page.wait_for_selector('button:has-text("停止生成")', state='hidden', timeout=0)
        log("回答完成")
        time.sleep(2)
    
    def click_share_and_get_link(self):
        """点击分享按钮并获取分享链接"""
        log("="*40)
        log("开始获取分享链接...")
        
        captured_share_id = None
        
        # 监听响应
        def handle_response(response):
            nonlocal captured_share_id
            url = response.url
            if '/api/conversations/v2/share' in url:
                log(f"捕获到分享API: {url}")
                try:
                    data = response.json()
                    log(f"API响应: {data}")
                    if data.get('shareId'):
                        captured_share_id = data.get('shareId')
                        log(f"获取到 shareId: {captured_share_id}")
                except Exception as e:
                    log(f"解析失败: {e}")
        
        self.page.on('response', handle_response)
        
        # 1. 等待分享按钮出现
        log("等待分享按钮出现...")
        try:
            self.page.wait_for_selector('.icon-yb-ic_share_2504', timeout=15000)
            log("✅ 找到分享按钮")
        except:
            log("❌ 等待超时，未找到分享按钮")
            self.page.remove_listener('response', handle_response)
            return None
        
        # 2. 使用 JavaScript 强制点击分享按钮（绕过遮挡）
        log("点击分享按钮...")
        share_clicked = self.page.evaluate('''
            () => {
                const btn = document.querySelector('.icon-yb-ic_share_2504');
                if (btn) {
                    btn.click();
                    return true;
                }
                return false;
            }
        ''')
        
        if not share_clicked:
            log("❌ 点击分享按钮失败")
            self.page.remove_listener('response', handle_response)
            return None
        
        log("✅ 分享按钮已点击")
        time.sleep(2)
        
        # 3. 等待复制链接按钮出现
        log("等待复制链接按钮出现...")
        try:
            self.page.wait_for_selector('.agent-chat__share-bar__item__logo', timeout=10000)
            log("✅ 找到复制链接按钮")
        except:
            log("❌ 等待超时，未找到复制链接按钮")
            self.page.keyboard.press('Escape')
            self.page.remove_listener('response', handle_response)
            return None
        
        # 4. 使用 JavaScript 强制点击复制链接按钮
        log("点击复制链接按钮...")
        copy_clicked = self.page.evaluate('''
            () => {
                const iconDiv = document.querySelector('.agent-chat__share-bar__item__logo');
                if (iconDiv) {
                    iconDiv.click();
                    return true;
                }
                return false;
            }
        ''')
        
        if not copy_clicked:
            log("❌ 点击复制链接按钮失败")
            self.page.keyboard.press('Escape')
            self.page.remove_listener('response', handle_response)
            return None
        
        log("✅ 复制链接按钮已点击")
        time.sleep(2)
        
        # 5. 检查提示
        toast_text = self.page.evaluate('''
            () => {
                const toast = document.querySelector('[class*="toast"], [class*="message"]');
                return toast ? toast.innerText : null;
            }
        ''')
        if toast_text:
            log(f"提示: {toast_text}")
        
        # 6. 等待 API 响应
        log("等待分享 API 响应...")
        for i in range(15):
            if captured_share_id:
                break
            time.sleep(1)
        
        self.page.remove_listener('response', handle_response)
        self.page.keyboard.press('Escape')
        
        if captured_share_id:
            share_link = f"https://yb.tencent.com/s/{captured_share_id}"
            log(f"✅ 分享链接: {share_link}")
            return share_link
        
        log("❌ 获取分享链接失败")
        return None
    
    def extract_citations_from_share_page(self, share_url: str):
        """从分享页面提取引用"""
        log(f"访问分享页面: {share_url}")
        
        current_url = self.page.url
        
        try:
            self.page.goto(share_url, timeout=30000)
            log("分享页面加载成功")
            time.sleep(3)
            
            citations = self.page.evaluate('''
                () => {
                    const results = [];
                    const html = document.documentElement.outerHTML;
                    
                    // 查找 docs 数据
                    const docsMatch = html.match(/"docs"\\s*:\\s*\\[([\\s\\S]*?)\\]/);
                    if (docsMatch) {
                        try {
                            const docMatches = docsMatch[1].matchAll(/\\{([^}]+)\\}/g);
                            for (const match of docMatches) {
                                const docStr = '{' + match[1] + '}';
                                try {
                                    const doc = JSON.parse(docStr);
                                    if (doc.url) {
                                        results.push({
                                            seq: doc.index || results.length + 1,
                                            title: doc.title || '',
                                            url: doc.url || '',
                                            source: doc.web_site_name || doc.webSiteSource || '',
                                        });
                                    }
                                } catch(e) {}
                            }
                        } catch(e) {}
                    }
                    
                    // 备用：从 DOM 提取链接
                    if (results.length === 0) {
                        const links = document.querySelectorAll('a[href*="http"]');
                        const seen = new Set();
                        for (let link of links) {
                            let href = link.href;
                            if (!href) continue;
                            if (href.includes('yuanbao') || href.includes('tencent')) continue;
                            if (!seen.has(href)) {
                                seen.add(href);
                                let source = '';
                                try {
                                    source = new URL(href).hostname.replace('www.', '');
                                } catch(e) {}
                                results.push({
                                    seq: results.length + 1,
                                    title: link.innerText?.trim() || source,
                                    url: href,
                                    source: source,
                                });
                            }
                        }
                    }
                    return results;
                }
            ''')
            
            log(f"提取到 {len(citations)} 条引用")
            
            # 返回原页面
            self.page.goto(current_url, timeout=30000)
            time.sleep(2)
            return citations
            
        except Exception as e:
            log(f"提取失败: {e}")
            try:
                self.page.goto(current_url, timeout=30000)
            except:
                pass
            return []
    
    def analyze_question(self, question: str) -> Dict:
        """分析单个问题"""
        log(f"\n{'='*50}")
        log(f"第 {self.question_count+1} 个问题: {question[:50]}...")
        
        try:
            # 1. 开启新对话
            self.new_conversation()
            
            # 2. 选择模型
            self.select_model()
            
            # 3. 发送问题
            input_box = self.page.locator('div[contenteditable="true"]').first
            if input_box.count() == 0:
                log("找不到输入框")
                return {
                    "question": question,
                    "citations": [],
                    "citation_count": 0,
                    "error": "找不到输入框",
                    "timestamp": datetime.now().isoformat()
                }
            
            input_box.click()
            input_box.fill(question)
            time.sleep(0.3)
            input_box.press('Enter')
            log("问题已发送")
            
            # 4. 等待回答
            self.wait_for_answer_complete()
            time.sleep(2)
            
            # 5. 获取分享链接
            share_link = self.click_share_and_get_link()
            
            # 6. 提取引用
            if share_link:
                citations = self.extract_citations_from_share_page(share_link)
            else:
                citations = []
            
            self.question_count += 1
            log(f"完成！引用数: {len(citations)}")
            
            return {
                "question": question,
                "citations": citations,
                "citation_count": len(citations),
                "share_link": share_link,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            log(f"处理失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "question": question,
                "citations": [],
                "citation_count": 0,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def batch_analyze(self, questions: List[str]) -> List[Dict]:
        """批量分析"""
        results = []
        
        if not self.wait_for_login():
            log("登录失败")
            return results
        
        log(f"\n开始分析 {len(questions)} 个问题...")
        log("请勿关闭浏览器窗口\n")
        
        for i, q in enumerate(questions):
            log(f"\n{'#'*50}")
            log(f"进度: {i+1}/{len(questions)}")
            
            result = self.analyze_question(q)
            results.append(result)
            
            if i < len(questions) - 1:
                log("等待 2 秒...")
                time.sleep(2)
        
        total_cites = sum(r['citation_count'] for r in results)
        log(f"\n{'='*50}")
        log(f"全部完成！共 {len(questions)} 个问题，{total_cites} 条引用")
        log("浏览器保持打开，请手动关闭")
        
        return results
    
    def close(self):
        """关闭浏览器"""
        log("关闭浏览器...")
        if self.context:
            self.context.close()
        if self.playwright:
            self.playwright.stop()
        log("浏览器已关闭")