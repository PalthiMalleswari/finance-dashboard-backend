from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        custom = {
            "error": True,
            "status_code": response.status_code,
            "message": _extract_message(response),
            "details": response.data if isinstance(response.data, dict) else None,
        }
        response.data = custom
        return response

    return Response(
        {
            "error": True,
            "status_code": 500,
            "message": "An unexpected error occurred.",
            "details": None,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _extract_message(response):
    data = response.data
    if isinstance(data, dict):
        if "detail" in data:
            return str(data["detail"])
        if "non_field_errors" in data:
            return "; ".join(str(e) for e in data["non_field_errors"])
    if isinstance(data, list):
        return "; ".join(str(e) for e in data)
    return "Validation error." if response.status_code < 500 else "Server error."