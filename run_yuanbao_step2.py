"""
元宝引用链接提取器 - 步骤2：从分享链接提取引用（精简版）
"""

import sys
import io
import json
import time
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

# 设置控制台编码为 UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def extract_citations_from_page(page):
    """从页面直接获取 __NEXT_DATA__ 内容"""
    citations = []
    
    try:
        # 获取 __NEXT_DATA__ 脚本的内容
        script_content = page.evaluate('''
            () => {
                const script = document.getElementById('__NEXT_DATA__');
                return script ? script.textContent : null;
            }
        ''')
        
        if script_content:
            data = json.loads(script_content)
            
            # 遍历对话找到 docs
            convs = data.get('props', {}).get('pageProps', {}).get('fullChatShareData', {}).get('chat', {}).get('convs', [])
            print(f"[调试] 找到 {len(convs)} 个对话")
            
            for conv in convs:
                if conv.get('speaker') == 'ai':
                    speeches = conv.get('speechesV2', [])
                    for speech in speeches:
                        content = speech.get('content', [])
                        for item in content:
                            if item.get('type') == 'searchGuid':
                                docs = item.get('docs', [])
                                print(f"[调试] 找到 {len(docs)} 个引用文档")
                                for doc in docs:
                                    if doc.get('url'):
                                        citations.append({
                                            'seq': doc.get('index', len(citations) + 1),
                                            'title': doc.get('title', ''),
                                            'url': doc.get('url', ''),
                                            'source': doc.get('web_site_name', doc.get('webSiteSource', '')),
                                        })
            print(f"[调试] 从页面脚本提取到 {len(citations)} 条引用")
        else:
            print("[调试] 未找到 __NEXT_DATA__ 脚本")
    except Exception as e:
        print(f"[调试] 提取失败: {e}")
    
    return citations


def main():
    if len(sys.argv) < 2:
        print("用法: python run_yuanbao_step2.py <share_links_file>")
        return
    
    links_file = Path(sys.argv[1])
    if not links_file.exists():
        print(f"文件不存在: {links_file}")
        return
    
    # 读取分享链接
    items = []
    with open(links_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if '|' in line:
                parts = line.split('|', 1)
                q = parts[0]
                link = parts[1] if len(parts) > 1 else ''
                items.append({"question": q, "share_link": link})
    
    print(f"开始分析 {len(items)} 个分享链接...")
    
    # 启动浏览器
    playwright = sync_playwright().start()
    browser_data = Path.cwd() / "yuanbao_browser_data"
    browser_data.mkdir(exist_ok=True)
    
    context = playwright.chromium.launch_persistent_context(
        str(browser_data),
        headless=False,
        args=['--start-maximized'],
        no_viewport=True
    )
    
    page = context.pages[0] if context.pages else context.new_page()
    
    results = []
    
    try:
        for i, item in enumerate(items):
            question = item['question']
            share_link = item['share_link']
            
            print(f"\n处理第 {i+1} 个分享链接: {share_link if share_link else '(无链接)'}")
            
            if not share_link:
                print("跳过：无有效链接")
                results.append({
                    "question": question,
                    "citations": [],
                    "citation_count": 0,
                    "share_link": None,
                    "error": "无分享链接",
                    "timestamp": datetime.now().isoformat()
                })
                continue
            
            try:
                # 导航到分享页面
                page.goto(share_link, timeout=30000)
                print("分享页面加载成功")
                
                # 等待页面完全加载（网络空闲）
                page.wait_for_load_state('networkidle')
                print("网络空闲")
                
                # 额外等待 2 秒
                time.sleep(2)
                
                # 从页面直接提取引用
                citations = extract_citations_from_page(page)
                
                print(f"提取到 {len(citations)} 条引用")
                
                results.append({
                    "question": question,
                    "citations": citations,
                    "citation_count": len(citations),
                    "share_link": share_link,
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                print(f"处理失败: {e}")
                results.append({
                    "question": question,
                    "citations": [],
                    "citation_count": 0,
                    "share_link": share_link,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
        
        # 保存结果
        with open("temp_citations.json", 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        total_cites = sum(r['citation_count'] for r in results)
        print(f"\n完成！共 {len(results)} 个分享链接，提取 {total_cites} 条引用")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        context.close()
        playwright.stop()
        print("浏览器已关闭")


if __name__ == "__main__":
    from datetime import datetime
    main()