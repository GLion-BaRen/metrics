FROM bitnami/python:3.13.7-debian-12-r0
WORKDIR /hac
COPY ./otlp_app.py .
COPY ./http_metrics.py .
COPY ./requirements.txt .
COPY ./entrypoint.sh .
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
EXPOSE 5001 9100
ENTRYPOINT [ "entrypoint.sh" ]
