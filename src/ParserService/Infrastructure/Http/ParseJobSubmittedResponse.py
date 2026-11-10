from typing import Self

from pydantic import BaseModel, ConfigDict

from ParserService.Application.Dto.ParseJobSubmitted import ParseJobSubmitted
from ParserService.Domain.Jobs.JobStatus import JobStatus


class ParseJobSubmittedResponse(BaseModel):
    """Body of the ``202 Accepted`` answer to a submission."""

    model_config = ConfigDict(frozen=True)

    job_id: str
    status: JobStatus
    already_existed: bool

    @classmethod
    def of(cls, submitted: ParseJobSubmitted) -> Self:
        """Build the response from the use case result.

        Args:
            submitted: What the use case returned.

        Returns:
            The response body.
        """
        return cls(
            job_id=submitted.job_id.value,
            status=submitted.status,
            already_existed=submitted.already_existed,
        )
