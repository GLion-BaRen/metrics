# Prometheus + Grafana 监控部署

## 概述
这个配置包含了完整的监控堆栈，用于监控Flask应用的性能指标。

## 组件
- **Prometheus**: 指标收集和存储
- **Grafana**: 可视化仪表板
- **Metrics容器**: 包含Flask应用和系统监控的容器化服务

## 快速启动

### 1. 启动监控堆栈
```bash
cd deploy
docker-compose up -d
```

### 2. 访问服务
- **Grafana**: http://localhost:3000
  - 用户名: `admin`
  - 密码: `admin`
- **Prometheus**: http://localhost:9090

### 3. 验证服务状态
```bash
# 检查所有容器是否正常运行
docker-compose ps

# 查看metrics容器日志
docker-compose logs -f metrics
```

### 4. 手动启动（可选）
如果需要在宿主机上手动启动应用：
```bash
# 在项目根目录下启动Flask应用监控
opentelemetry-instrument --service_name otlp_app python otlp_app.py

# 启动系统指标监控（另一个终端）
opentelemetry-instrument --service_name http_metrics python http_metrics.py
```

## 配置详情

### Grafana配置
- **数据源**: 自动配置Prometheus数据源
- **仪表板**: 预配置了三个仪表板
  - OpenTelemetry指标仪表板 - HTTP请求监控
  - Python进程监控仪表板 - 进程资源监控
  - 系统监控仪表板 - 系统资源监控
- **持久化**: 使用Docker卷保存配置和数据

### Prometheus配置
- **抓取间隔**: 15秒
- **采集目标**: 
  - Flask应用: `metrics:5001/metrics` (容器内服务)
  - 系统监控: `metrics:9100/metrics` (容器内服务)
- **配置文件**: `prometheus.yml`
- **网络**: 使用自定义bridge网络 `monitoring`

### Metrics容器配置
- **镜像**: `metric:0.0.1`
- **端口映射**: 5001:5001, 9100:9100
- **日志挂载**: `./logs:/hac/logs`
- **系统目录挂载**: 
  - `/proc:/proc:ro` - CPU、内存、负载等系统信息
  - `/sys:/sys:ro` - 系统设备信息
  - `/dev:/dev:ro` - 设备文件
- **特权模式**: `privileged: true` - 系统监控需要特殊权限
- **自动重启**: `unless-stopped`

### 网络优化
- **容器通信**: Grafana通过服务名 `prometheus` 连接到Prometheus
- **网络隔离**: 使用专用的 `monitoring` 网络
- **服务发现**: 通过Docker Compose的内置DNS解析服务名

## 目录结构
```
deploy/
├── docker-compose.yml          # Docker Compose配置
├── prometheus.yml              # Prometheus配置
├── logs/                       # 容器日志目录
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/
│   │   │   └── prometheus.yml  # 数据源配置
│   │   └── dashboards/
│   │       └── dashboards.yml  # 仪表板配置
│   └── dashboards/
│       ├── otel-metrics-dashboard.json      # OTel指标仪表板
│       ├── python-process-dashboard.json   # Python进程仪表板
│       └── system-monitoring-dashboard.json # 系统监控仪表板
└── README.md                   # 本文件
```

## 监控指标

### OpenTelemetry HTTP指标
- `http_server_duration_milliseconds`: HTTP请求持续时间直方图 (毫秒)
- `http_server_active_requests`: 当前活跃的HTTP请求数

### Python进程指标
- `process_resident_memory_bytes`: 进程常驻内存使用
- `process_virtual_memory_bytes`: 进程虚拟内存使用
- `process_cpu_seconds_total`: 进程CPU使用时间
- `process_open_fds`: 打开的文件描述符数量
- `python_gc_collections_total`: Python垃圾回收统计
- `python_gc_objects_collected_total`: 垃圾回收对象统计

### 服务信息指标
- `target_info{service_name="my-flask-app"}`: 服务元信息

### 系统监控指标（OpenTelemetry格式）
- `system_cpu_usage_ratio`: 系统CPU使用率
- `system_memory_total_bytes`: 系统总内存
- `system_memory_used_bytes`: 系统已用内存
- `system_load_average{period="1m|5m|15m"}`: 系统负载平均值
- `system_disk_io_operations_total{device,operation}`: 磁盘I/O操作统计
- `system_network_bytes_total{device,direction}`: 网络流量统计

## 重要说明

### 🔒 安全注意事项
- **特权模式**: metrics容器使用 `privileged: true` 运行，具有宿主机系统级权限
- **系统挂载**: 容器可以读取宿主机的系统信息（只读模式）
- **生产环境**: 建议在生产环境中使用更精确的权限控制，避免使用特权模式
- **网络隔离**: 所有容器运行在专用网络中，不直接暴露到外部

### 🐧 Linux系统要求
- **操作系统**: 需要Linux系统（/proc, /sys文件系统）
- **Docker版本**: 支持privileged模式的Docker版本
- **权限**: Docker需要有足够权限挂载系统目录

## 故障排除

### 1. Grafana无法连接Prometheus
- 检查两个容器是否都在运行
- 确认两个容器都在同一个 `monitoring` 网络中
- 验证Grafana能够通过服务名 `prometheus` 解析到Prometheus容器

### 2. 没有数据显示
- 确认Flask应用正在运行并监听5001端口
- 检查Prometheus目标状态: http://localhost:9090/targets
- 确认metrics端点返回正确的Content-Type

### 3. 系统监控数据异常
- **权限问题**: 确认容器运行在特权模式下
- **挂载问题**: 检查 `/proc`, `/sys`, `/dev` 目录是否正确挂载
- **平台兼容性**: 确认运行在Linux系统上（Windows/macOS不支持）
- **容器日志**: 查看 `docker-compose logs metrics` 检查错误信息

### 4. 仪表板显示"No data"
- 等待几分钟让数据收集
- 检查时间范围设置
- 验证查询表达式是否正确

## 扩展配置

### 添加新的监控目标
编辑 `prometheus.yml` 文件，在 `scrape_configs` 下添加新的job。

### 创建自定义仪表板
1. 在Grafana UI中创建仪表板
2. 导出JSON配置
3. 保存到 `grafana/dashboards/` 目录
4. 重启Grafana容器

### 修改数据源配置
编辑 `grafana/provisioning/datasources/prometheus.yml` 文件。
