import base64
import re
import requests
from requests.exceptions import ChunkedEncodingError, ContentDecodingError
from typing import Any, Optional, Dict, Callable, Generic, TypeVar


ERROR_CODE_TO_HTTP_STATUS_CODE = {'InvalidRequest': 400,
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
                                  'RequestTooLarge': 413
                                  }


def map_error_code_to_http_status_code(error_code):
    """
    Map the Facility internal error code to the http equivalent status code
    500 if not found
    :param error_code: Facility internal error code
    :type error_code: str
    :return: http status code
    :rtype: int
    """
    return ERROR_CODE_TO_HTTP_STATUS_CODE.get(error_code, 500)


def map_http_status_code_to_error_code(status_code):
    """
    Map the http status code to internal error code
    InvalidResponse if not found
    :param status_code: HTTP status code
    :type status_code: int
    :return: internal error code
    :rtype: str
    """
    for key, value in ERROR_CODE_TO_HTTP_STATUS_CODE.items():
        if value == status_code:
            return key
    return 'InvalidResponse'


class DTO:
    """
    A data transfer object.
    """
    def __init__(self):
        pass

    def __repr__(self):
        return self.__dict__.__repr__()

    def to_data(self):
        """
        Returns a serializable dictionary for the DTO.
        """
        return dict(
            (DTO._create_data_name(k), DTO._create_data_value(v))
            for k, v in self.__dict__.items()
            if v is not None
        )

    _create_data_name_regex = re.compile(r'_([a-z])')

    @staticmethod
    def _create_data_name(name):
        return DTO._create_data_name_regex.sub(lambda x: x.group(1).upper(), name)

    @staticmethod
    def _create_data_value(value):
        if isinstance(value, DTO):
            return value.to_data()
        elif isinstance(value, bytearray):
            return str(base64.b64encode(value))
        elif isinstance(value, list):
            return list(map(DTO._create_data_value, value))
        else:
            return value


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
        super(Error, self).__init__()
        assert code is None or isinstance(code, str)
        assert message is None or isinstance(message, str)
        assert details is None or isinstance(details, object)
        assert inner_error is None or isinstance(inner_error, Error)
        self.code = code
        self.message = message
        self.details = details
        self.innerError = inner_error

    @staticmethod
    def from_data(data):
        return Error(
            code=data.get('code'),
            message=data.get('message'),
            details=data.get('details'),
            inner_error=Error.from_data(data['innerError']) if 'innerError' in data else None,
        )

    @staticmethod
    def from_response(response):
        assert isinstance(response, requests.Response)
        if response.headers.get('Content-Type') == 'application/json':
            response_json = response.json()
            if response_json.get('code'):
                return Error.from_data(response_json)
        error_code = map_http_status_code_to_error_code(response.status_code)
        return Error(code='InternalError', message=f'unexpected HTTP status code {response.status_code} {error_code}')


T = TypeVar("T")


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
        super(Result, self).__init__()
        assert (value is None) ^ (error is None)
        assert error is None or isinstance(error, Error)
        self.value = value
        self.error = error

    @staticmethod
    def from_data(data: Dict[str, Any], create_value: Optional[Callable[[Any], T]] = None):
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
            resp.content  # Consume socket so it can be released
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
