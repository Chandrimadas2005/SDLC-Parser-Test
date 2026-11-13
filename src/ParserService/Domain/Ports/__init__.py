"""Ports (typing.Protocol) that the Infrastructure layer implements."""

from ParserService.Domain.Ports.ArtifactStore import ArtifactStore
from ParserService.Domain.Ports.BatchStore import BatchStore
from ParserService.Domain.Ports.Clock import Clock
from ParserService.Domain.Ports.DiskSpace import DiskSpace
from ParserService.Domain.Ports.DocumentParser import DocumentParser
from ParserService.Domain.Ports.Extractor import Extractor
from ParserService.Domain.Ports.JobQueue import JobQueue
from ParserService.Domain.Ports.JobRepository import JobRepository
from ParserService.Domain.Ports.SummaryGenerator import SummaryGenerator
from ParserService.Domain.Ports.TemporaryFileCleaner import TemporaryFileCleaner
from ParserService.Domain.Ports.TypeDetector import TypeDetector

__all__ = [
    "ArtifactStore",
    "BatchStore",
    "Clock",
    "DiskSpace",
    "DocumentParser",
    "Extractor",
    "JobQueue",
    "JobRepository",
    "SummaryGenerator",
    "TemporaryFileCleaner",
    "TypeDetector",
]
