from flask import Flask, request, make_response
import time
import random
# 导入新库
from prometheus_client import Counter, Gauge, Histogram, generate_latest

app = Flask(__name__)

# 1. 创建Metrics对象
# Counter: 请求总数，带 method 和 endpoint 标签
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP Requests',
    ['method', 'endpoint']
)
# Counter: 错误总数
ERROR_COUNT = Counter(
    'http_errors_total',
    'Total HTTP Errors',
    ['method', 'endpoint']
)
# Gauge: 进行中的请求数
IN_PROGRESS_REQUESTS = Gauge(
    'http_requests_inprogress',
    'Number of in-progress HTTP requests'
)
# Histogram: 请求延迟，单位秒
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

# 2. 在应用中植入Metrics逻辑
@app.before_request
def before_request():
    # 请求开始前，增加进行中请求数，并记录开始时间
    IN_PROGRESS_REQUESTS.inc()
    request.start_time = time.time()

@app.after_request
def after_request(response):
    # 请求结束后，计算延迟，增加总请求数，减少进行中请求数
    latency = time.time() - request.start_time
    REQUEST_LATENCY.labels(request.method, request.path).observe(latency)
    REQUEST_COUNT.labels(request.method, request.path).inc()
    IN_PROGRESS_REQUESTS.dec()
    # 如果是5xx错误，增加错误计数
    if response.status_code >= 500:
        ERROR_COUNT.labels(request.method, request.path).inc()
    return response

# 3. 添加 /metrics 端点
@app.route('/metrics')
def metrics():
    return generate_latest()

@app.route('/')
def index():
    seconds = random.random() * 0.5
    print(f"自动范围的值{seconds}")
    time.sleep(seconds)
    return "Hello, SRE!"

@app.route('/users')
def get_users():
    time.sleep(random.random() * 0.2)
    if random.random() > 0.1:
        return {"users": ["alex", "bob", "charlie"]}, 200
    else:
        return {"error": "internal server error"}, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)