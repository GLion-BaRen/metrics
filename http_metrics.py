#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统指标采集 → OpenTelemetry Prometheus Exporter
基于 OpenTelemetry 的系统监控指标采集器
"""

import time
import platform
from flask import Flask, Response

# OpenTelemetry 导入
from opentelemetry import metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from prometheus_client import generate_latest

# OpenTelemetry 配置
resource = Resource(attributes={
    "service.name": "system-metrics-exporter",
    "service.version": "1.0.0",
    "host.name": platform.node()
})

# 配置Prometheus Exporter
reader = PrometheusMetricReader()
provider = MeterProvider(resource=resource, metric_readers=[reader])
metrics.set_meter_provider(provider)

# 创建 meter
meter = metrics.get_meter("system_metrics", "1.0.0")

# 创建 Flask 应用
app = Flask(__name__)

# 创建系统指标
cpu_usage_gauge = meter.create_gauge(
    "system_cpu_usage_ratio",
    description="System CPU usage ratio"
)

memory_total_gauge = meter.create_gauge(
    "system_memory_total_bytes", 
    description="Total system memory in bytes"
)

memory_used_gauge = meter.create_gauge(
    "system_memory_used_bytes",
    description="Used system memory in bytes"
)

load_average_gauge = meter.create_gauge(
    "system_load_average",
    description="System load average"
)

disk_io_counter = meter.create_counter(
    "system_disk_io_operations_total",
    description="Total disk I/O operations"
)

network_bytes_counter = meter.create_counter(
    "system_network_bytes_total", 
    description="Total network bytes transferred"
)

# ---------- CPU ----------
def read_cpu_stat():
    with open("/proc/stat") as f:
        first_line = f.readline().split()
    values = list(map(int, first_line[1:]))
    total = sum(values)
    idle = values[3] + values[4]  # idle + iowait
    return total, idle

def cpu_usage(interval=0.2):
    total1, idle1 = read_cpu_stat()
    time.sleep(interval)
    total2, idle2 = read_cpu_stat()
    total_diff = total2 - total1
    idle_diff = idle2 - idle1
    return 1 - idle_diff / total_diff if total_diff > 0 else 0

# ---------- Memory ----------
def mem_info():
    mem = {}
    with open("/proc/meminfo") as f:
        for line in f:
            k, v, *_ = line.split()
            mem[k.strip(":")] = int(v) * 1024  # 转 bytes
    mem_total = mem["MemTotal"]
    mem_available = mem["MemAvailable"]
    mem_used = mem_total - mem_available
    return mem_total, mem_used

# ---------- Load Avg ----------
def load_avg():
    with open("/proc/loadavg") as f:
        parts = f.read().split()
    return float(parts[0]), float(parts[1]), float(parts[2])

# ---------- Disk IOPS ----------
def read_diskstats():
    stats = {}
    with open("/proc/diskstats") as f:
        for line in f:
            parts = line.split()
            dev = parts[2]
            if dev.startswith(("sd", "nvme")):
                reads = int(parts[3])
                writes = int(parts[7])
                stats[dev] = (reads, writes)
    return stats

def disk_iops(interval=0.2):
    s1 = read_diskstats()
    time.sleep(interval)
    s2 = read_diskstats()
    result = {}
    for dev in s1:
        r1, w1 = s1[dev]
        r2, w2 = s2[dev]
        result[dev] = (r2 - r1, w2 - w1)
    return result

# ---------- Network ----------
def read_netdev():
    stats = {}
    with open("/proc/net/dev") as f:
        lines = f.readlines()[2:]
        for line in lines:
            iface, data = line.split(":")
            iface = iface.strip()
            vals = data.split()
            rx_bytes, tx_bytes = int(vals[0]), int(vals[8])
            stats[iface] = (rx_bytes, tx_bytes)
    return stats

def net_rate(interval=0.2):
    s1 = read_netdev()
    time.sleep(interval)
    s2 = read_netdev()
    result = {}
    for iface in s1:
        rx1, tx1 = s1[iface]
        rx2, tx2 = s2[iface]
        result[iface] = (
            (rx2 - rx1) / interval,
            (tx2 - tx1) / interval
        )
    return result

# ---------- 更新指标 ----------
def update_metrics():
    """更新所有系统指标到OpenTelemetry"""
    
    # CPU使用率
    cpu = cpu_usage()
    cpu_usage_gauge.set(cpu)

    # 内存使用
    mem_total, mem_used = mem_info()
    memory_total_gauge.set(mem_total)
    memory_used_gauge.set(mem_used)

    # 负载平均值
    la1, la5, la15 = load_avg()
    load_average_gauge.set(la1, {"period": "1m"})
    load_average_gauge.set(la5, {"period": "5m"})
    load_average_gauge.set(la15, {"period": "15m"})

    # 磁盘I/O (累积计数器需要特殊处理)
    try:
        for dev, (riops, wiops) in disk_iops().items():
            if riops > 0:
                disk_io_counter.add(riops, {"device": dev, "operation": "read"})
            if wiops > 0:
                disk_io_counter.add(wiops, {"device": dev, "operation": "write"})
    except Exception:
        pass  # 忽略磁盘读取错误

    # 网络流量 (累积计数器需要特殊处理)
    try:
        for iface, (rx_bps, tx_bps) in net_rate().items():
            if rx_bps > 0:
                network_bytes_counter.add(int(rx_bps), {"device": iface, "direction": "rx"})
            if tx_bps > 0:
                network_bytes_counter.add(int(tx_bps), {"device": iface, "direction": "tx"})
    except Exception:
        pass  # 忽略网络读取错误

# ---------- Flask 路由 ----------
@app.route('/metrics')
def metrics_endpoint():
    """Prometheus metrics endpoint"""
    # 更新所有指标
    update_metrics()
    # 返回Prometheus格式的指标
    return Response(generate_latest(), mimetype='text/plain; version=0.0.4; charset=utf-8')

@app.route('/')
def index():
    """健康检查端点"""
    return "System Metrics Exporter - OpenTelemetry"

@app.route('/health')
def health():
    """健康检查端点"""
    return {"status": "healthy", "service": "system-metrics-exporter"}

if __name__ == "__main__":
    print("System Metrics Exporter starting...")
    print("OpenTelemetry enabled")
    print(f"Service: {resource.attributes['service.name']}")
    print(f"Host: {resource.attributes['host.name']}")
    print("Metrics endpoint: http://0.0.0.0:9100/metrics")
    app.run(host='0.0.0.0', port=9100, debug=True)
