"""
元宝引用链接提取器 - Streamlit 界面（两步流程版）
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os
import re
import base64
from pathlib import Path
import subprocess
import json

st.set_page_config(
    page_title="元宝引用链接提取器",
    page_icon="🔗",
    layout="wide"
)

# ==================== 自定义CSS ====================
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 600;
        background: linear-gradient(135deg, #00aaff 0%, #0066cc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    .log-container {
        height: 300px;
        overflow-y: auto;
        background-color: #1e1e1e;
        border-radius: 8px;
        padding: 8px;
        font-family: monospace;
        font-size: 12px;
        color: #d4d4d4;
    }
    .citation-card {
        background-color: white;
        border-radius: 8px;
        padding: 12px;
        margin: 8px 0;
        border: 1px solid #e9ecef;
        border-left: 3px solid #00aaff;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 初始化 ====================
if 'share_links' not in st.session_state:
    st.session_state.share_links = []
if 'citations_results' not in st.session_state:
    st.session_state.citations_results = []
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'is_running' not in st.session_state:
    st.session_state.is_running = False


def add_log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.logs.append(f"[{timestamp}] {message}")
    if len(st.session_state.logs) > 200:
        st.session_state.logs = st.session_state.logs[-200:]


def export_share_links_excel():
    if not st.session_state.share_links:
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    Path("results").mkdir(exist_ok=True)
    
    filename = f"results/yuanbao_share_links_{timestamp}.xlsx"
    
    rows = []
    for item in st.session_state.share_links:
        rows.append({
            '序号': item.get('index', ''),
            '问题': item.get('question', ''),
            '分享链接': item.get('share_link', ''),
            '时间': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    
    if rows:
        df = pd.DataFrame(rows)
        df.to_excel(filename, index=False)
        return filename
    return None


def export_citations_excel():
    if not st.session_state.citations_results:
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    Path("results").mkdir(exist_ok=True)
    
    filename = f"results/yuanbao_citations_{timestamp}.xlsx"
    
    rows = []
    for r in st.session_state.citations_results:
        for cite in r.get('citations', []):
            rows.append({
                '问题序号': r.get('question_index', ''),
                '问题': r['question'],
                '引用序号': cite.get('seq', ''),
                '来源网站': cite.get('source', ''),
                '标题': cite.get('title', ''),
                '链接': cite.get('url', ''),
                '分享链接': r.get('share_link', ''),
                '时间': r.get('timestamp', '')[:19]
            })
    
    if rows:
        df = pd.DataFrame(rows)
        df.to_excel(filename, index=False)
        return filename
    return None


def run_get_share_links(questions, status_placeholder, log_container):
    """第一步：获取分享链接"""
    
    add_log(f"开始获取 {len(questions)} 个问题的分享链接")
    status_placeholder.markdown("🔄 **状态:** 正在启动浏览器获取分享链接...")
    
    temp_questions = Path("temp_questions.txt")
    with open(temp_questions, 'w', encoding='utf-8') as f:
        for q in questions:
            f.write(q + '\n')
    
    result_file = Path("temp_share_links.json")
    if result_file.exists():
        result_file.unlink()
    
    add_log("执行获取分享链接脚本...")
    
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    
    process = subprocess.Popen(
        [sys.executable, "-u", "run_yuanbao_step1.py", str(temp_questions)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        bufsize=1,
        env=env
    )
    
    current_question = 0
    total = len(questions)
    
    for line in iter(process.stdout.readline, ''):
        if line:
            line = line.strip()
            if line:
                add_log(line)
                
                if "第" in line and "个问题" in line:
                    match = re.search(r'第\s*(\d+)\s*个问题', line)
                    if match:
                        current_question = int(match.group(1))
                        status_placeholder.markdown(f"🔄 **状态:** 正在处理第 {current_question}/{total} 个问题...")
                elif "获取到分享链接" in line:
                    match = re.search(r'https?://yb\.tencent\.com/s/[a-zA-Z0-9]+', line)
                    if match:
                        status_placeholder.markdown(f"✅ **状态:** 问题 {current_question}/{total} 获取到分享链接")
                
                # 实时刷新日志显示
                log_html = "<br>".join(st.session_state.logs[-50:])
                log_container.markdown(f'<div class="log-container">{log_html}</div>', unsafe_allow_html=True)
    
    process.wait()
    
    try:
        temp_questions.unlink()
    except:
        pass
    
    if result_file.exists():
        with open(result_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        result_file.unlink()
        
        for i, item in enumerate(data):
            item['index'] = i + 1
        
        st.session_state.share_links = data
        add_log(f"获取完成！共获取 {len(data)} 个分享链接")
        status_placeholder.markdown(f"✅ **状态:** 获取完成！共获取 {len(data)} 个分享链接")
        
        # 最终刷新日志
        log_html = "<br>".join(st.session_state.logs[-50:])
        log_container.markdown(f'<div class="log-container">{log_html}</div>', unsafe_allow_html=True)
    else:
        add_log("获取失败：未找到结果文件")
        status_placeholder.markdown("❌ **状态:** 获取失败")


def run_analyze_citations(status_placeholder, log_container):
    """第二步：分析引用链接 - 清空日志重新开始"""
    
    # 清空之前的日志，重新开始
    st.session_state.logs = []
    add_log("=" * 50)
    add_log("开始分析引用链接")
    add_log("=" * 50)
    
    if not st.session_state.share_links:
        add_log("没有分享链接，请先执行第一步")
        status_placeholder.markdown("❌ **状态:** 没有分享链接，请先获取分享链接")
        return
    
    # 只分析有效的分享链接
    valid_links = [item for item in st.session_state.share_links if item.get('share_link')]
    if not valid_links:
        add_log("没有有效的分享链接")
        status_placeholder.markdown("❌ **状态:** 没有有效的分享链接")
        return
    
    add_log(f"开始分析 {len(valid_links)} 个分享链接的引用")
    status_placeholder.markdown(f"🔄 **状态:** 正在分析引用链接...")
    
    # 创建临时分享链接文件
    temp_links = Path("temp_share_links.txt")
    with open(temp_links, 'w', encoding='utf-8') as f:
        for item in valid_links:
            f.write(f"{item['question']}|{item['share_link']}\n")
    
    result_file = Path("temp_citations.json")
    if result_file.exists():
        result_file.unlink()
    
    add_log("执行分析引用脚本...")
    
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    
    process = subprocess.Popen(
        [sys.executable, "-u", "run_yuanbao_step2.py", str(temp_links)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        bufsize=1,
        env=env
    )
    
    current_index = 0
    total = len(valid_links)
    
    for line in iter(process.stdout.readline, ''):
        if line:
            line = line.strip()
            if line:
                add_log(line)
                
                # 更新状态显示进度
                if "处理第" in line:
                    match = re.search(r'第\s*(\d+)\s*个', line)
                    if match:
                        current_index = int(match.group(1))
                        status_placeholder.markdown(f"🔄 **状态:** 正在分析第 {current_index}/{total} 个分享链接...")
                elif "提取到" in line and "条引用" in line:
                    match = re.search(r'提取到 (\d+) 条引用', line)
                    if match:
                        status_placeholder.markdown(f"✅ **状态:** 第 {current_index}/{total} 完成，找到 {match.group(1)} 条引用")
                
                # 实时刷新日志显示
                log_html = "<br>".join(st.session_state.logs[-50:])
                log_container.markdown(f'<div class="log-container">{log_html}</div>', unsafe_allow_html=True)
    
    process.wait()
    
    try:
        temp_links.unlink()
    except:
        pass
    
    if result_file.exists():
        with open(result_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
        result_file.unlink()
        
        for i, r in enumerate(results):
            r['question_index'] = i + 1
        
        st.session_state.citations_results = results
        
        total_cites = sum(r['citation_count'] for r in results)
        add_log(f"分析完成！共提取 {total_cites} 条引用")
        status_placeholder.markdown(f"✅ **状态:** 分析完成！共提取 {total_cites} 条引用")
        
        # 最终刷新日志
        log_html = "<br>".join(st.session_state.logs[-50:])
        log_container.markdown(f'<div class="log-container">{log_html}</div>', unsafe_allow_html=True)
    else:
        add_log("分析失败：未找到结果文件")
        status_placeholder.markdown("❌ **状态:** 分析失败")


# ==================== 侧边栏 ====================
with st.sidebar:
    # 图标
    icon_path = "blsicon.png"
    if os.path.exists(icon_path):
        with open(icon_path, "rb") as f:
            img_data = base64.b64encode(f.read()).decode()
        st.markdown(f'<div style="text-align: center;"><img src="data:image/png;base64,{img_data}" width="100"></div>', unsafe_allow_html=True)
    else:
        st.markdown("### 🔗")
    
    st.markdown("---")
    
    st.markdown("### 📊 进度")
    if st.session_state.share_links:
        st.success(f"✅ 步骤1: {len(st.session_state.share_links)} 个分享链接")
    else:
        st.info("⏳ 步骤1: 待执行")
    
    if st.session_state.citations_results:
        total_cites = sum(r['citation_count'] for r in st.session_state.citations_results)
        st.success(f"✅ 步骤2: {total_cites} 条引用")
    elif st.session_state.share_links:
        st.warning("⏳ 步骤2: 待执行")
    
    st.markdown("---")
    
    if st.session_state.share_links:
        excel_file = export_share_links_excel()
        if excel_file:
            with open(excel_file, 'rb') as f:
                st.download_button(
                    label="📎 下载分享链接 Excel",
                    data=f,
                    file_name=Path(excel_file).name,
                    use_container_width=True
                )
    
    if st.session_state.citations_results:
        excel_file = export_citations_excel()
        if excel_file:
            with open(excel_file, 'rb') as f:
                st.download_button(
                    label="📎 下载引用结果 Excel",
                    data=f,
                    file_name=Path(excel_file).name,
                    use_container_width=True
                )
    
    st.markdown("---")
    st.caption("💡 使用说明")
    st.caption("1. 输入问题列表")
    st.caption("2. 点击「步骤1: 获取分享链接」")
    st.caption("3. 等待获取完成")
    st.caption("4. 点击「步骤2: 分析引用链接」")
    st.caption("5. 下载 Excel 结果")

# ==================== 主界面 ====================
st.markdown('<div class="main-header">🔗 元宝引用链接提取器</div>', unsafe_allow_html=True)

st.markdown("### 📝 问题列表")
questions_text = st.text_area(
    "每行一个问题",
    height=150,
    placeholder="例如：\n上海今天天气怎么样？\n生成式AI有哪些应用？"
)

questions = [q.strip() for q in questions_text.split('\n') if q.strip()]

col1, col2, col3 = st.columns(3)
with col1:
    step1_btn = st.button("🚀 步骤1: 获取分享链接", type="primary", use_container_width=True)
with col2:
    step2_btn = st.button("🔗 步骤2: 分析引用链接", type="primary", use_container_width=True, disabled=not st.session_state.share_links)
with col3:
    clear_btn = st.button("🗑️ 清空所有", use_container_width=True)

if clear_btn:
    st.session_state.share_links = []
    st.session_state.citations_results = []
    st.session_state.logs = []
    st.rerun()

# 状态显示
status_placeholder = st.empty()

# 分享链接列表
if st.session_state.share_links:
    st.markdown("---")
    st.markdown("### 📋 分享链接列表")
    
    table_data = []
    for item in st.session_state.share_links:
        table_data.append({
            "序号": item.get('index', ''),
            "问题": item.get('question', '')[:80] + ('...' if len(item.get('question', '')) > 80 else ''),
            "分享链接": item.get('share_link', '获取失败')
        })
    
    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

# 引用结果列表
if st.session_state.citations_results:
    st.markdown("---")
    st.markdown("### 📊 引用分析结果")
    
    for result in st.session_state.citations_results:
        question = result.get('question', '')
        citations = result.get('citations', [])
        idx = result.get('question_index', 0)
        share_link = result.get('share_link', '')
        
        with st.expander(f"📌 {idx}. {question[:80]}... ({len(citations)} 条引用)", expanded=False):
            if share_link:
                st.caption(f"🔗 分享链接: {share_link}")
            if citations:
                cite_data = []
                for cite in citations:
                    cite_data.append({
                        "序号": cite.get('seq', ''),
                        "来源网站": cite.get('source', ''),
                        "标题": cite.get('title', '')[:60],
                        "链接": cite.get('url', '')[:60]
                    })
                cite_df = pd.DataFrame(cite_data)
                st.dataframe(cite_df, use_container_width=True, hide_index=True)
            else:
                st.info("未找到引用")

# 日志显示区域
st.markdown("---")
st.markdown("### 📋 运行日志")
log_container = st.empty()

# 开始获取
if step1_btn and questions:
    if not st.session_state.is_running:
        st.session_state.is_running = True
        run_get_share_links(questions, status_placeholder, log_container)
        st.session_state.is_running = False
        st.rerun()

# 分析引用
if step2_btn and st.session_state.share_links:
    if not st.session_state.is_running:
        st.session_state.is_running = True
        run_analyze_citations(status_placeholder, log_container)
        st.session_state.is_running = False
        st.rerun()

# 显示已有日志
if not st.session_state.is_running:
    if st.session_state.logs:
        log_html = "<br>".join(st.session_state.logs[-100:])
        log_container.markdown(f'<div class="log-container">{log_html}</div>', unsafe_allow_html=True)
    else:
        log_container.info("暂无日志")