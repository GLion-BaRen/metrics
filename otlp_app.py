from flask import Flask, request, Response
import time
import random

# 1. OTel的配置
from opentelemetry import metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from prometheus_client import generate_latest

# 2. OTel的自动植入
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.wsgi import OpenTelemetryMiddleware

# 服务名，会作为标签附加到所有指标上
resource = Resource(attributes={"service.name": "my-flask-app"})

# 配置Prometheus Exporter
reader = PrometheusMetricReader()
provider = MeterProvider(resource=resource, metric_readers=[reader])
metrics.set_meter_provider(provider)

app = Flask(__name__)

# 3. 关键！自动植入Flask应用
FlaskInstrumentor().instrument_app(app)
# 这个中间件是可选的，但可以捕获更多WSGI层面的信息
app.wsgi_app = OpenTelemetryMiddleware(app.wsgi_app)

# 4. 我们不再需要手动创建Counter/Histogram了！
# OTel自动植入库会帮我们创建符合语义化标准的Metrics
# 例如：http.server.duration, http.server.active_requests 等

@app.route('/metrics')
def metrics_endpoint():
    return Response(generate_latest(), mimetype='text/plain; version=0.0.4; charset=utf-8')

@app.route('/')
def index():
    time.sleep(random.random() * 0.5)
    return "Hello, OTel!"

@app.route('/users')
def get_users():
    time.sleep(random.random() * 0.2)
    if random.random() > 0.1:
        return {"users": ["alex", "bob", "charlie"]}, 200
    else:
        return {"error": "internal server error"}, 500

# 如果想添加自定义指标，可以这样做
meter = metrics.get_meter("my_app_meter")
user_fetch_counter = meter.create_counter(
    "user_fetch_total",
    description="Counts the number of user fetches"
)

@app.route('/fetch_data')
def fetch_data():
    # 假设这里是获取用户的逻辑
    # 我们可以为特定业务逻辑添加自定义指标
    user_fetch_counter.add(1, {"fetch_result": "success"})
    return "Data fetched!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
