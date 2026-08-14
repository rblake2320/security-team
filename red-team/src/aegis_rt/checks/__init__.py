from .http_headers import HttpHeadersCheck
from .repository_posture import RepositoryPostureCheck
from .source import SourceStaticCheck

BUILTIN_CHECKS = {
    SourceStaticCheck.check_id: SourceStaticCheck(),
    HttpHeadersCheck.check_id: HttpHeadersCheck(),
    RepositoryPostureCheck.check_id: RepositoryPostureCheck(),
}

__all__ = ["BUILTIN_CHECKS", "HttpHeadersCheck", "RepositoryPostureCheck", "SourceStaticCheck"]
