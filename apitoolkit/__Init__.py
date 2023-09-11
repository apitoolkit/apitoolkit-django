import requests
from google.cloud import pubsub_v1
from google.oauth2 import service_account
from jsonpath_ng import parse
import json
import base64
import time
from datetime import datetime
import pytz
from django.conf import settings


class APIToolkit:
    def __init__(self, get_response):
        self.publisher = None
        self.topic_name = None
        self.meta = None
        self.redact_headers = getattr(
            settings, 'APITOOLKIT_REDACT_HEADERS', [])
        self.debug = getattr(settings, 'APITOOLKIT_DEBUG', False)
        self.redact_request_body = getattr(
            settings, 'APITOOLKIT_REDACT_REQ_BODY', [])
        self.redact_response_body = getattr(
            settings, 'APITOOLKIT_REDACT_RES_BODY', [])
        self.get_response = get_response

        api_key = getattr(settings, 'APITOOLKIT_KEY', '')
        root_url = getattr(settings, 'APITOOLKIT_ROOT_URL',
                           "https://app.apitoolkit.io")

        response = requests.get(url=root_url + "/api/client_metadata",
                                headers={"Authorization": f"Bearer {api_key}"})
        response.raise_for_status()
        data = response.json()
        credentials = service_account.Credentials.from_service_account_info(
            data["pubsub_push_service_account"])

        self.publisher = pubsub_v1.PublisherClient(credentials=credentials)
        self.topic_name = 'projects/{project_id}/topics/{topic}'.format(
            project_id=data['pubsub_project_id'],
            topic=data['topic_id'],
        )
        self.meta = data

    def publish_message(self, payload):
        data = json.dumps(payload).encode('utf-8')
        if self.debug:
            print("APIToolkit: publish message")
            json_formatted_str = json.dumps(payload, indent=2)
            print(json_formatted_str)
        future = self.publisher.publish(self.topic_name, data=data)
        return future.result()

    def redact_headers_func(self, headers):
        redacted_headers = {}
        for header_name, value in headers.items():
            if header_name.lower() in self.redact_headers or header_name in self.redact_headers:
                redacted_headers[header_name] = "[CLIENT_REDACTED]"
            else:
                redacted_headers[header_name] = value
        return redacted_headers

    def redact_fields(self, body, paths):
        try:
            data = json.loads(body)
            for path in paths:
                expr = parse(path)
                expr.update(data, "[CLIENT_REDACTED]")
            return json.dumps(data).encode("utf-8")
        except Exception as e:
            if isinstance(body, str):
                return body.encode('utf-8')
            return body

    def __call__(self, request):
        if self.debug:
            print("APIToolkit: making request")
        start_time = time.perf_counter_ns()
        request_method = request.method
        raw_url = request.get_full_path()
        request_body = None
        query_params = dict(request.GET.copy())
        request_headers = self.redact_headers_func(request.headers)
        content_type = request.headers.get('Content-Type', '')

        if content_type == 'application/json':
            request_body = json.loads(request.body.decode('utf-8'))
        if content_type == 'text/plain':
            request_body = request.body.decode('utf-8')
        if content_type == 'application/x-www-form-urlencoded' or 'multipart/form-data' in content_type:
            request_body = dict(request.POST.copy())

        response = self.get_response(request)
        if self.debug:
            print("APIToolkit: after request")
        end_time = time.perf_counter_ns()
        url_path = request.resolver_match.route
        path_params = request.resolver_match.kwargs
        duration = (end_time - start_time)
        status_code = response.status_code
        request_body = json.dumps(request_body)
        response_headers = self.redact_headers_func(response.headers)
        request_body = self.redact_fields(
            request_body, self.redact_request_body)
        response_body = self.redact_fields(
            response.content.decode('utf-8'), self.redact_response_body)
        timestamp = datetime.now(pytz.timezone("UTC")).isoformat()
        try:
            payload = {
                "query_params": query_params,
                "path_params": path_params,
                "request_headers": request_headers,
                "response_headers": response_headers,
                "proto_minor": 1,
                "proto_major": 1,
                "method": request_method,
                "url_path": url_path,
                "raw_url": raw_url,
                "request_body": base64.b64encode(request_body).decode("utf-8"),
                "response_body": base64.b64encode(response_body).decode("utf-8"),
                "host": request.headers.get('HOST'),
                "referer": request.headers.get('Referer', ""),
                "sdk_type": "PythonDjango",
                "project_id": self.meta["project_id"],
                "status_code": status_code,
                "duration": duration,
                "timestamp": timestamp
            }
            self.publish_message(payload)
        except Exception as e:
            print(e)
            return response
        return response
