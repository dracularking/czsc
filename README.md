# CZSC - 缠中说禅技术分析工具

## 项目简介

CZSC（缠中说禅）是一个基于缠论的技术分析工具库，用于量化交易和技术分析。

## 核心功能

- **缠论技术分析**：笔、线段、中枢识别
- **CTA 策略回测**：完整的策略开发和回测框架
- **信号-事件-交易体系**：灵活的信号组合和事件驱动交易
- **可视化报告**：多种图表和报告生成工具

## 快速开始

### 安装

```bash
pip install czsc
```

### 基础使用

```python
from czsc import CZSC, Freq, format_standard_kline
from czsc.mock import generate_symbol_kines

# 获取数据
df = generate_symbol_kines('000001', '日线', '20200101', '20230101')
bars = format_standard_kline(df, freq=Freq.D)

# 缠论分析
czsc_obj = CZSC(bars)

# 查看结果
print(f"分型数量: {len(czsc_obj.fx_list)}")
print(f"笔数量: {len(czsc_obj.bi_list)}")
```

## 文档

- [项目使用指南](docs/项目使用指南.md)
- [示例代码](examples/)

## 许可证

Apache-2.0
