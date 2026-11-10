import pytest

from ParserService.Domain.Errors import JobQueueError, Result


class TestResult:
    """Result carries either a value or an error and refuses to unwrap the other side."""

    def test_ok_holds_a_value(self) -> None:
        result: Result[int, JobQueueError] = Result.ok(42)

        assert result.is_ok
        assert not result.is_err
        assert result.unwrap() == 42

    def test_ok_may_hold_none(self) -> None:
        result: Result[None, JobQueueError] = Result.ok(None)

        assert result.is_ok
        assert result.unwrap() is None

    def test_err_holds_an_error(self) -> None:
        result: Result[int, JobQueueError] = Result.err(JobQueueError.QUEUE_FULL)

        assert result.is_err
        assert result.unwrap_err() is JobQueueError.QUEUE_FULL

    def test_unwrapping_the_wrong_side_raises(self) -> None:
        ok: Result[int, JobQueueError] = Result.ok(1)
        err: Result[int, JobQueueError] = Result.err(JobQueueError.QUEUE_UNAVAILABLE)

        with pytest.raises(ValueError, match="unwrap called on a failed result"):
            err.unwrap()
        with pytest.raises(ValueError, match="unwrap_err called on a successful result"):
            ok.unwrap_err()
