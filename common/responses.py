from rest_framework.response import Response
from rest_framework import status


def extract_error_message(errors, default_message="An error occurred"):
    """
    Extracts a clean, single message string from DRF serializer errors or exceptions.
    Example:
        {"name": ["category with this name already exists."]} -> "category with this name already exists."
    """
    if not errors:
        return default_message
    if isinstance(errors, str):
        return errors
    if isinstance(errors, dict):
        for field, value in errors.items():
            if isinstance(value, list) and value:
                return str(value[0])
            elif isinstance(value, dict):
                return extract_error_message(value, default_message)
            return str(value)
    elif isinstance(errors, list) and errors:
        return str(errors[0])
    return str(errors)


def api_response(
    message="Success",
    code=status.HTTP_200_OK,
    data=None,
    source=None,
    status_code=None,
    **kwargs
):
    """
    Standardized API response format:
    {
        "code": 200,
        "message": "...",
        "source": "CATEGORY",
        "data": null / { ... }
    }
    """
    source_val = source.value if hasattr(source, "value") else source

    payload = {
        "code": code,
        "message": message,
        "source": source_val,
        "data": data,
    }
    if kwargs:
        payload.update(kwargs)

    return Response(payload, status=status_code or code)


class APIResponse:
    @staticmethod
    def success(
        message="Success",
        data=None,
        source=None,
        code=status.HTTP_200_OK,
        status_code=None,
        **kwargs
    ):
        return api_response(
            message=message,
            code=code,
            data=data,
            source=source,
            status_code=status_code or code,
            **kwargs
        )

    @staticmethod
    def error(
        message=None,
        errors=None,
        source=None,
        code=status.HTTP_400_BAD_REQUEST,
        status_code=None,
        data=None,
        **kwargs
    ):
        """
        Returns error response with {code, message, source, data: null}.
        If 'errors' (e.g. serializer.errors) is provided and 'message' is None,
        extracts the human-readable error string into 'message'.
        """
        if errors and not message:
            message = extract_error_message(errors)
        elif not message:
            message = "An error occurred"

        return api_response(
            message=message,
            code=code,
            source=source,
            data=data,  # Defaults to None (null in JSON)
            status_code=status_code or code,
            **kwargs
        )
