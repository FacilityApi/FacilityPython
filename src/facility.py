import base64
import enum
import decimal
import re
import requests
import requests.adapters
from requests.exceptions import ChunkedEncodingError, ContentDecodingError
from typing import Any, Optional, Dict, Callable, Generic, TypeVar, Union
from urllib.parse import quote


T = TypeVar("T")


def encode(value) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        value = f"{value}"
    return quote(value)


ERROR_CODE_TO_HTTP_STATUS_CODE = {
    'InvalidRequest': 400,
    'InternalError': 500,
    'InvalidResponse': 500,
    'ServiceUnavailable': 503,
    'Timeout': 500,
    'NotAuthenticated': 401,
    'NotAuthorized': 403,
    'NotFound': 404,
    'NotModified': 304,
    'Conflict': 409,
    'TooManyRequests': 429,
    'RequestTooLarge': 413,
    'InternalServerError': 500,
}
HTTP_STATUS_CODE_TO_ERROR_CODE = {sc: ec for ec, sc in ERROR_CODE_TO_HTTP_STATUS_CODE.items()}


def map_error_code_to_http_status_code(error_code: str) -> int:
    """
    Map the Facility internal error code to the http equivalent status code
    500 if not found
    :param error_code: Facility internal error code
    :type error_code: str
    :return: http status code
    :rtype: int
    """
    return ERROR_CODE_TO_HTTP_STATUS_CODE.get(error_code, 500)


class DTO:
    """
    A data transfer object.
    """
    def __init__(self):
        pass

    def __repr__(self):
        return self.__dict__.__repr__()

    def to_data(self) -> Dict[str, Any]:
        """
        Returns a serializable dictionary for the DTO.
        """
        return dict(
            (DTO._create_data_name(k), DTO._create_data_value(v))
            for k, v in self.__dict__.items()
            if v is not None
        )

    _camel_case_regex = re.compile(r'_([a-z])')

    @staticmethod
    def _create_data_name(name: str) -> str:
        return DTO._camel_case_regex.sub(lambda x: x.group(1).upper(), name).rstrip("_")

    @staticmethod
    def _create_data_value(value):
        if isinstance(value, DTO):
            return value.to_data()
        elif isinstance(value, (bytearray, bytes)):
            return base64.b64encode(value).decode("ascii")
        elif isinstance(value, list):
            return [DTO._create_data_value(x) for x in value]
        elif isinstance(value, dict):
            return {k: DTO._create_data_value(v) for k, v in value.items()}
        elif isinstance(value, decimal.Decimal):
            s = str(value)
            return int(s) if re.fullmatch(r'\d+', s) else float(s)
        elif isinstance(value, Enum):
            return value.value
        return value

    @classmethod
    def from_data(cls: T, data: Dict[str, Any]) -> T:
        raise NotImplementedError()


class Response(Generic[T], DTO):
    """
    A non-error response.
    """
    @classmethod
    def from_response(
        cls: "Response[T]",
        response: requests.Response,
        body: str = "",
        header_map: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> "Response[T]":
        data = response.json() if response.content else dict()
        if not data and "default" in kwargs:
            data = kwargs["default"]
        if body:
            data = {body: data}
        if header_map and response.headers:
            for header_key, field_name in header_map.items():
                if header_key in response.headers:
                    data[field_name] = response.headers[header_key]
        return cls.from_data(data)

    @classmethod
    def from_data(cls: "Response[T]", data: Dict[str, Any]) -> "Response[T]":
        raise NotImplementedError()


class Error(DTO):
    """
    An error.
    """
    def __init__(self,
                 code: Optional[str] = None,
                 message: Optional[str] = None,
                 details: Any = None,
                 inner_error: Optional["Error"] = None):
        """
        @type code: str
        @param code: The error code.
        @type message: str
        @param message: The error message. (For developers, not end users.)
        @type details: object
        @param details: Advanced error details.
        @type inner_error: Error
        @param inner_error: The inner error.
        """
        super().__init__()
        assert code is None or isinstance(code, str)
        assert message is None or isinstance(message, str)
        assert details is None or isinstance(details, object)
        assert inner_error is None or isinstance(inner_error, Error)
        self.code = code
        self.message = message
        self.details = details
        self.innerError = inner_error

    @classmethod
    def from_data(cls: "Error", data: dict) -> "Error":
        return Error(
            code=data.get('code'),
            message=data.get('message'),
            details=data.get('details'),
            inner_error=Error.from_data(data['innerError']) if 'innerError' in data else None,
        )

    @classmethod
    def from_response(cls: "Error", response: requests.Response, error_code: str = "") -> "Error":
        assert isinstance(response, requests.Response)
        if response.headers.get('Content-Type') == 'application/json' and response.content:
            try:
                response_json = response.json()
                if response_json.get('code'):
                    return Error.from_data(response_json)
            except (ValueError, AttributeError):
                pass
        error_code = error_code or HTTP_STATUS_CODE_TO_ERROR_CODE.get(response.status_code, 'InvalidResponse')
        return Error(code=error_code, message=f'unexpected HTTP status code {response.status_code} {error_code}')


class Result(Generic[T], DTO):
    """
    A service result value or error.
    """
    def __init__(self, value: Optional[T] = None, error: Optional[Error] = None):
        """
        @type value: object
        @param value: The value.
        @type error: Error
        @param error: The error.
        """
        super().__init__()
        assert (value is None) ^ (error is None)
        assert error is None or isinstance(error, Error)
        self.value = value
        self.error = error

    @classmethod
    def from_data(cls: "Result[T]", data: Dict[str, Any], create_value: Optional[Callable[[Any], T]] = None) -> "Result[T]":
        return Result(
            value=(create_value(data['value']) if create_value else data['value']) if 'value' in data else None,
            error=Error.from_data(data['error']) if 'error' in data else None,
        )


class OAuthSettings:
    """
    Settings for OAuth clients.
    """
    def __init__(self,
                 consumer_token: str,
                 consumer_secret: str,
                 access_token: Optional[str] = None,
                 access_secret: Optional[str] = None):
        self.consumer_token = consumer_token
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.access_secret = access_secret

    def to_header(self) -> str:
        """
        Creates an Authorization header value.
        """
        prefix = f'OAuth oauth_consumer_key="{self.consumer_token}",oauth_signature="{self.consumer_secret}'
        suffix = '",oauth_signature_method="PLAINTEXT",oauth_version="1.0"'
        if self.access_token is None and self.access_secret is None:
            return f'{prefix}{suffix}'
        ampersand = "%26"
        return f'{prefix}{ampersand}{self.access_secret}",oauth_token="{self.access_token}{suffix}'


class ClientBase:
    """
    Base class for HTTP client classes.
    """
    def __init__(self,
                 base_uri: str, *,
                 headers: Optional[Dict[str, str]] = None,
                 oauth: Optional[OAuthSettings] = None,
                 max_retries: int = 0):
        self.base_uri = base_uri.rstrip("/")
        self.headers = headers
        self.oauth = oauth
        self.max_retries = int(max_retries)
        self.session = None

    def send_request(self, method: str, uri: str, *,
                     query: Optional[dict] = None,
                     request: Any = None,
                     headers: Optional[Dict[str, str]] = None) -> requests.Response:
        headers_ = dict()
        if self.oauth is not None:
            headers_['Authorization'] = self.oauth.to_header()
        if request is not None:
            headers_['Content-Type'] = 'application/json'
        if self.headers is not None:
            headers_.update(self.headers)
        if headers is not None:
            headers_.update(headers)
        if self.session is None:
            self.session = requests.sessions.Session()
            if self.max_retries > 0:
                self.session.mount("http://", requests.adapters.HTTPAdapter(max_retries=self.max_retries))
                self.session.mount("https://", requests.adapters.HTTPAdapter(max_retries=self.max_retries))
        resp = self.session.request(
            method=method,
            url=f"{self.base_uri}{uri}",
            params=query or dict(),
            json=request,
            headers=headers_
        )
        try:
            _ = resp.content  # Consume socket so it can be released
        except (ChunkedEncodingError, ContentDecodingError, RuntimeError):
            resp.raw.read(decode_content=False)
        return resp

    def close(self):
        if self.session is not None:
            self.session.close()
            self.session = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class Enum(enum.Enum):

    @classmethod
    def get(cls, value: str, default: Optional["Enum"] = None) -> Optional["Enum"]:
        return cls.get_value_map().get(value, default)

    @classmethod
    def get_value_map(cls):
        key = '_value_map'
        v2e = getattr(cls, key, None)
        if v2e is None:
            v2e = {s.value: s for s in cls}
            setattr(cls, key, v2e)
        return v2e

    def __str__(self):
        return self.value


def string_to_bool(value: Union[str, bool, type(None)]) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if (not isinstance(value, str)) or len(value) == 0:
        return None
    if value[0] in "tT1yY":
        return True
    if value[0] in "fF0nN":
        return False
