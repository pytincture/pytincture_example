FROM python:3.13-slim

COPY . /pyTincture/
WORKDIR /pyTincture

RUN pip install --no-cache-dir .

WORKDIR /pyTincture/example

EXPOSE 8070

ENTRYPOINT ["python", "run.py"]
