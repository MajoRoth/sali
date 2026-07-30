from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ChainDataStatus(BaseModel):
    ChainExtractedCode: str
    chainId: str
    chainName: str | None = None
    lastUpdate: datetime | None = None
    hoursSinceUpdate: float | None = None
    PromoListingCount: int
    storeCount: int
    productListingCount: int
    isStale: bool


class PipelineHealthResponse(BaseModel):
    status: str
    lastOverallUpdate: datetime | None = None
    hoursSinceLastUpdate: float | None = None
    totalChains: int
    chainsWithRecentData: int
    chainsWithStaleData: int
    chainStatuses: list[ChainDataStatus]
    dataSourceStats: dict[str, Any]


class DataFreshness(BaseModel):
    chainId: str
    chainName: str | None = None
    lastUpdate: datetime | None = None
    hasData: bool


class RowBucketMetric(BaseModel):
    totalLoaded: int
    totalPublished: int


class SiteBucketCountsResponse(BaseModel):
    site: str
    startTime: datetime
    endTime: datetime
    bucketMinutes: int
    useExtractedDate: bool
    fileCounts: list[int]
    rowMetrics: list[RowBucketMetric]


class UniqueSitesResponse(BaseModel):
    sites: list[str]
    count: int


class TimeBucketData(BaseModel):
    bucketStart: datetime
    bucketEnd: datetime
    fileCount: int


class SiteProcessingTimeline(BaseModel):
    extractedFromSite: str
    buckets: list[TimeBucketData]


class ProcessingTimelineResponse(BaseModel):
    startTime: datetime
    endTime: datetime
    bucketMinutes: int
    useExtractedDate: bool
    timelines: list[SiteProcessingTimeline]


class RowProcessingBucketData(BaseModel):
    bucketStart: datetime
    bucketEnd: datetime
    totalLoadedFromFile: int
    totalPublishedRecords: int


class SiteRowProcessingTimeline(BaseModel):
    extractedFromSite: str
    buckets: list[RowProcessingBucketData]


class RowProcessingTimelineResponse(BaseModel):
    startTime: datetime
    endTime: datetime
    bucketMinutes: int
    timelines: list[SiteRowProcessingTimeline]
