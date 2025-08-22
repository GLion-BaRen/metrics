#!/usr/bin/env bash
# 启动Flask应用，并打印输出至logs目录，以及终端
opentelemetry-instrument --service_name otlp_app python otlp_app.py |tee logs/otlp_app.log 2>&1 &
# 启动系统指标监控，并打印输出至logs目录，以及终端
opentelemetry-instrument --service_name http_metrics python http_metrics.py |tee logs/http_metrics.log 2>&1 &
# 等待所有进程启动
wait
