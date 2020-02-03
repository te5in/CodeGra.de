import typing as t

from .grade import Grade
from .service_connector import ServiceConnector, _ServiceConnectorResponse


class AssignmentsGradesService:
    def __init__(
        self,
        service_connector: ServiceConnector,
        service_data: t.Dict[str, object],
    ) -> None:
        ...

    # This is a response from the service_connector
    def put_grade(self, grade: Grade) -> _ServiceConnectorResponse:
        ...
