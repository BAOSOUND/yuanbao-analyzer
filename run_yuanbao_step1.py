"""
元宝引用链接提取器 - 步骤1：获取分享链接（完成后自动关闭浏览器）
"""

import sys
import json
import time
from pathlib import Path
from yuanbao_core import YuanbaoAnalyzer


def main():
    if len(sys.argv) < 2:
        print("用法: python run_yuanbao_step1.py <questions_file>")
        return
    
    question_file = Path(sys.argv[1])
    if not question_file.exists():
        print(f"文件不存在: {question_file}")
        return
    
    with open(question_file, 'r', encoding='utf-8') as f:
        questions = [line.strip() for line in f if line.strip()]
    
    print(f"开始获取 {len(questions)} 个问题的分享链接...")
    
    analyzer = YuanbaoAnalyzer(headless=False)
    results = []
    
    try:
        analyzer.start()
        
        if analyzer.wait_for_login():
            for i, q in enumerate(questions):
                print(f"\n处理第 {i+1} 个问题: {q[:50]}...")
                
                # 开启新对话
                analyzer.new_conversation()
                analyzer.select_model()
                
                # 发送问题
                input_box = analyzer.page.locator('div[contenteditable="true"]').first
                input_box.click()
                input_box.fill(q)
                time.sleep(0.5)
                input_box.press('Enter')
                print("问题已发送")
                
                # 等待回答完成
                analyzer.wait_for_answer_complete()
                time.sleep(3)
                
                # 获取分享链接
                share_link = analyzer.click_share_and_get_link()
                
                results.append({
                    "question": q,
                    "share_link": share_link,
                    "timestamp": time.time()
                })
                
                if share_link:
                    print(f"✅ 获取到分享链接: {share_link}")
                else:
                    print("❌ 未能获取分享链接")
                
                # 等待一下
                if i < len(questions) - 1:
                    print("等待 3 秒后继续...")
                    time.sleep(3)
            
            # 保存结果
            with open("temp_share_links.json", 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            print(f"\n完成！共获取 {len(results)} 个分享链接")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 关闭浏览器，让子进程结束
        analyzer.close()
        print("浏览器已关闭")


if __name__ == "__main__":
    main()