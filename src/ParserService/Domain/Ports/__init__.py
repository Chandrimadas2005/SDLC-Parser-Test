"""Ports (typing.Protocol) that the Infrastructure layer implements."""

from ParserService.Domain.Ports.ArtifactStore import ArtifactStore
from ParserService.Domain.Ports.Clock import Clock
from ParserService.Domain.Ports.JobQueue import JobQueue
from ParserService.Domain.Ports.JobRepository import JobRepository

__all__ = ["ArtifactStore", "Clock", "JobQueue", "JobRepository"]
