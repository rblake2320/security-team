from .auth_session import AuthSessionHygieneCheck
from .dependency_scan import DependencyVulnerabilityCheck
from .http_headers import HttpHeadersCheck
from .repository_posture import RepositoryPostureCheck
from .source import SourceStaticCheck
from .web_misconfig import WebMisconfigCheck

BUILTIN_CHECKS = {
    SourceStaticCheck.check_id: SourceStaticCheck(),
    HttpHeadersCheck.check_id: HttpHeadersCheck(),
    RepositoryPostureCheck.check_id: RepositoryPostureCheck(),
    DependencyVulnerabilityCheck.check_id: DependencyVulnerabilityCheck(),
    WebMisconfigCheck.check_id: WebMisconfigCheck(),
    AuthSessionHygieneCheck.check_id: AuthSessionHygieneCheck(),
}

__all__ = [
    "BUILTIN_CHECKS", "AuthSessionHygieneCheck", "DependencyVulnerabilityCheck",
    "HttpHeadersCheck", "RepositoryPostureCheck", "SourceStaticCheck", "WebMisconfigCheck",
]
