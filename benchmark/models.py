from pydantic import BaseModel, Field


class NatsVarzMetrics(BaseModel):
    """NATS server metrics from /varz endpoint"""
    cpu: float = Field(ge=0, le=100, description="CPU percentage (0-100%)")
    mem: int = Field(gt=0, description="Memory usage in bytes")
    in_bytes: int = Field(ge=0, description="Network bytes received")
    out_bytes: int = Field(ge=0, description="Network bytes sent")
    in_msgs: int = Field(ge=0, description="Messages received")
    out_msgs: int = Field(ge=0, description="Messages sent")


class JetStreamJszMetrics(BaseModel):
    """JetStream metrics from /jsz endpoint"""
    streams: int = Field(ge=0, description="Number of streams")
    consumers: int = Field(ge=0, description="Number of consumers")
    messages: int = Field(ge=0, description="Total messages")
    bytes: int = Field(ge=0, description="Total storage bytes")
    memory: int = Field(ge=0, description="Memory usage in bytes")
    storage: int = Field(ge=0, description="Storage usage in bytes")


class DockerStatsMetrics(BaseModel):
    """Docker container stats metrics"""
    container_name: str = Field(description="Container name")
    cpu_percent: float = Field(ge=0, le=100, description="CPU usage percentage")
    mem_usage_bytes: int = Field(gt=0, description="Memory usage in bytes")
    net_in_bytes: int = Field(ge=0, description="Network bytes received")
    net_out_bytes: int = Field(ge=0, description="Network bytes sent")


class ShufflerMetrics(BaseModel):
    """Shuffler (firehose consumer) application metrics from /metrics endpoint"""
    firehose_messages_read_total: int = Field(ge=0, description="Total messages read from ATProto firehose")
    firehose_cursor_position: int = Field(ge=0, description="Current cursor position (sequence number)")


class ConsumerMetrics(BaseModel):
    """Consumer service application metrics from /metrics endpoint"""
    consumer_messages_processed_total: int = Field(ge=0, description="Total messages processed by all consumers")
