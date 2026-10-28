FROM m.daocloud.io/docker.io/hashicorp/terraform:1.16.6 AS terraform
FROM dockerproxy.net/semaphoreui/semaphore:v2.19.16
USER root
COPY --from=terraform /bin/terraform /usr/local/bin/terraform
COPY requirements.txt /opt/iac/requirements.txt
RUN python3 -m venv /opt/iac/venv \
    && /opt/iac/venv/bin/pip install --no-cache-dir --timeout 30 --retries 2 \
       --index-url https://repo.huaweicloud.com/repository/pypi/simple \
       -r /opt/iac/requirements.txt
ENV VIRTUAL_ENV=/opt/iac/venv
ENV PATH="/opt/iac/venv/bin:${PATH}"
WORKDIR /workspace
