# -*- coding: utf-8 -*-
from django.conf import settings
from rest_framework.response import Response
from rest_framework_json_api import utils
from rest_framework_json_api.exceptions import rendered_with_json_api
from jsonschema import Draft6Validator
import json


class SimpleJsonschemaMiddleware:
    def __init__(self):
        self.set_schemas(settings.SIMPLE_JSONSCHEMA)
        self.default_encoding = 'utf-8'

    def get_encoding(self, request):
        return request.encoding if request.encoding else self.default_encoding

    def set_schemas(self, simple_jsonschema):
        self._schemas = {}
        for key, schema in simple_jsonschema.items():
            methods, view_name = key
            if isinstance(methods, tuple):
                for method in methods:
                    schema_id = method.upper() + ':' + view_name
                    self._schemas[schema_id] = Draft6Validator(schema)
            elif isinstance(methods, str):
                schema_id = methods.upper() + ':' + view_name
                self._schemas[schema_id] = Draft6Validator(schema)

    def get_schema(self, request):
        view_name = request.resolver_match.view_name
        method = request.method
        key = method + ':' + view_name
        return self._schemas[key]

    def process_view(self, request, view_func, view_args, view_kwargs):
        try:
            schema = self.get_schema(request)
        except KeyError:
            return None
        encoding = self.get_encoding(request)
        json_data = json.loads(request.body.decode(encoding), encoding=encoding)
        errors = list(schema.iter_errors(json_data))
        if len(errors):
            errors = [
                {'detail': e.message, 'source': e.schema_path, 'status': '400'}
                for e in errors
            ]
            response = Response(errors, status='400')

            is_json_api_view = view_func and rendered_with_json_api(view_func.cls)
            if not is_json_api_view:
                response.data = utils.format_errors(response.data)

            return response
        return None
