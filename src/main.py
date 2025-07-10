import pandas as pd
import os
import json
from pathlib import Path
from IPython.display import HTML
import re

def load_and_process_data():
    all_data = {}
    
    report_type_mapping = {
        'balance_sheet': '资产负债表',
        'cash_flow': '现金流量表',
        'income_statement': '利润表'
    }
    
    # 获取当前目录下的所有CSV文件
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    
    for filename in os.listdir(parent_dir):
        if filename.endswith('.csv'):
            try:
                # 解析文件名获取股票代码和报表类型
                match = re.match(r'(.+[-_])?([A-Z0-9]+)_(.+)_年度\.csv', filename)
                if not match:
                    print(f"跳过不符合命名规则的文件: {filename}")
                    continue
                
                stock_code = match.group(2)
                file_report_type = match.group(3).lower()
                
                # 确定报表类型
                if 'balance' in file_report_type:
                    report_type = 'balance_sheet'
                elif 'cash' in file_report_type:
                    report_type = 'cash_flow'
                elif 'income' in file_report_type:
                    report_type = 'income_statement'
                else:
                    continue
                
                # 读取CSV文件
                try:
                    df = pd.read_csv(os.path.join(parent_dir, filename), encoding='gb18030')
                except:
                    df = pd.read_csv(os.path.join(parent_dir, filename), encoding='utf-8')
                
                # 检查必要列是否存在
                required_cols = ['STD_ITEM_NAME', 'AMOUNT', 'REPORT_DATE']
                if not all(col in df.columns for col in required_cols):
                    print(f"文件 {filename} 缺少必要列，跳过处理")
                    continue
                
                # 数据处理
                df['YEAR'] = pd.to_datetime(df['REPORT_DATE']).dt.year
                df['AMOUNT'] = pd.to_numeric(df['AMOUNT'], errors='coerce').fillna(0)
                
                # 创建透视表
                pivot_df = df.pivot_table(
                    index='STD_ITEM_NAME',
                    columns='YEAR',
                    values='AMOUNT',
                    aggfunc='sum',
                    fill_value=0
                ).reset_index()
                
                # 格式化金额
                for col in pivot_df.columns[1:]:
                    if pd.api.types.is_numeric_dtype(pivot_df[col]):
                        pivot_df[col] = pivot_df[col].apply(lambda x: f"{x:,.2f}" if pd.notna(x) else "-")
                
                # 存储数据
                if stock_code not in all_data:
                    all_data[stock_code] = {}
                
                all_data[stock_code][report_type] = {
                    'display_name': report_type_mapping[report_type],
                    'data': pivot_df
                }
                
                print(f"成功处理文件: {filename}")
                
            except Exception as e:
                print(f"处理文件 {filename} 时出错: {str(e)}")
    
    return all_data

def generate_html_report(data):
    css = """
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        .control-panel { margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 5px; }
        select { padding: 8px; border-radius: 4px; border: 1px solid #ddd; min-width: 200px; }
        .tabs { display: flex; border-bottom: 1px solid #ddd; margin-bottom: 20px; }
        .tab { padding: 10px 20px; cursor: pointer; background: #f1f1f1; margin-right: 5px; border-radius: 5px 5px 0 0; }
        .tab.active { background: #3498db; color: white; }
        .tab-content { display: none; padding: 15px; border: 1px solid #ddd; border-top: none; }
        .tab-content.active { display: block; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th { background: #3498db; color: white; padding: 12px; text-align: left; }
        td { padding: 10px; border-bottom: 1px solid #ddd; }
        tr:nth-child(even) { background: #f8f9fa; }
        .amount { text-align: right; font-family: monospace; }
        .stock-info { font-size: 18px; margin: 10px 0; color: #2c3e50; }
        /* AI Chat Styles */
        .ai-chat { margin-top: 30px; border-top: 1px solid #ddd; padding-top: 20px; }
        .chat-container { height: 300px; overflow-y: auto; border: 1px solid #ddd; padding: 15px; margin-bottom: 15px; background: #f9f9f9; }
        .message { margin-bottom: 10px; padding: 10px; border-radius: 5px; max-width: 80%; }
        .user-message { background: #e3f2fd; margin-left: auto; }
        .ai-message { background: #f1f1f1; margin-right: auto; }
        .chat-input { display: flex; gap: 10px; }
        #chat-input { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
        #send-btn { padding: 10px 20px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; }
        .suggested-questions { margin-top: 15px; display: flex; flex-wrap: wrap; gap: 10px; }
        .suggested-question { padding: 5px 10px; background: #e3f2fd; border-radius: 15px; cursor: pointer; font-size: 14px; }
        .loading { display: inline-block; width: 20px; height: 20px; border: 3px solid rgba(0,0,0,.3); border-radius: 50%; border-top-color: #3498db; animation: spin 1s ease-in-out infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
    """
    
    stock_options = ''.join([f'<option value="{code}">{code}</option>' for code in data.keys()])
    
    js_data = {}
    for stock_code, reports in data.items():
        js_data[stock_code] = {}
        for report_type, report_data in reports.items():
            js_data[stock_code][report_type] = report_data['data'].to_dict('records')

    first_stock = next(iter(data.keys())) if data else None
    initial_balance = data[first_stock]['balance_sheet']['data'].to_html(index=False) if first_stock and 'balance_sheet' in data[first_stock] else '<p>暂无数据</p>'
    initial_cash = data[first_stock]['cash_flow']['data'].to_html(index=False) if first_stock and 'cash_flow' in data[first_stock] else '<p>暂无数据</p>'
    initial_income = data[first_stock]['income_statement']['data'].to_html(index=False) if first_stock and 'income_statement' in data[first_stock] else '<p>暂无数据</p>'

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>股票财务报告</title>
    {css}
</head>
<body>
    <div class="container">
        <h1>股票财务报告</h1>
        
        <div class="control-panel">
            <label for="stock-select">选择股票: </label>
            <select id="stock-select">
                {stock_options}
            </select>
            <div id="stock-info" class="stock-info"></div>
        </div>
        
        <div class="tabs">
            <div class="tab active" data-tab="balance_sheet">资产负债表</div>
            <div class="tab" data-tab="cash_flow">现金流量表</div>
            <div class="tab" data-tab="income_statement">利润表</div>
        </div>
        
        <div id="balance_sheet" class="tab-content active">
            {initial_balance}
        </div>
        
        <div id="cash_flow" class="tab-content">
            {initial_cash}
        </div>
        
        <div id="income_statement" class="tab-content">
            {initial_income}
        </div>
        
        <!-- AI Chat Section -->
        <div class="ai-chat">
            <h2>财务分析助手</h2>
            <p>询问有关当前股票的财务问题，例如："营业额的每年平均增长是多少？"</p>
            
            <div class="chat-container" id="chat-container">
                <div class="message ai-message">
                    您好！我是财务分析助手。我可以帮助您分析当前选定股票的财务数据。
                    您可以问我类似以下的问题：<br><br>
                    • 营业额的每年平均增长是多少？<br>
                    • 净利润率的变化趋势如何？<br>
                    • 资产负债率是否健康？<br>
                    • 现金流状况如何？<br>
                    • 与同行业相比表现如何？
                </div>
            </div>
            
            <div class="suggested-questions">
                <div class="suggested-question" onclick="askQuestion('营业额的每年平均增长是多少？')">营业额的每年平均增长</div>
                <div class="suggested-question" onclick="askQuestion('净利润率的变化趋势如何？')">净利润率趋势</div>
                <div class="suggested-question" onclick="askQuestion('资产负债率是否健康？')">资产负债率健康度</div>
                <div class="suggested-question" onclick="askQuestion('现金流状况如何？')">现金流状况</div>
            </div>
            
            <div class="chat-input">
                <input type="text" id="chat-input" placeholder="输入您的财务问题..." onkeypress="handleKeyPress(event)">
                <button id="send-btn" onclick="sendMessage()">发送</button>
            </div>
        </div>
    </div>
    
    <script>
        const reportsData = {json.dumps(js_data, ensure_ascii=False)};
        const DEEPSEEK_API_KEY = 'sk-78af28495b7249e280efae4eb52a12bc';
        let currentStock = document.getElementById('stock-select').value;
        
        // 股票选择变化事件
        document.getElementById('stock-select').addEventListener('change', function() {{
            currentStock = this.value;
            updateDisplay();
        }});
        
        // 标签页切换事件
        document.querySelectorAll('.tab').forEach(tab => {{
            tab.addEventListener('click', function() {{
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                this.classList.add('active');
                
                const tabId = this.getAttribute('data-tab');
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                document.getElementById(tabId).classList.add('active');
            }});
        }});
        
        // 更新显示
        function updateDisplay() {{
            const stockData = reportsData[currentStock];
            document.getElementById('stock-info').textContent = '当前查看: ' + currentStock;
            
            updateTable('balance_sheet', stockData);
            updateTable('cash_flow', stockData);
            updateTable('income_statement', stockData);
        }}
        
        // 更新表格
        function updateTable(tableId, stockData) {{
            const tableDiv = document.getElementById(tableId);
            if (stockData && stockData[tableId]) {{
                const headers = Object.ke
