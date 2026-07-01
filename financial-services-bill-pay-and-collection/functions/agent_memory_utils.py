import json
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

import plog
from _gen import *  # <AUTO GENERATED>
from pydantic.v1 import BaseModel, validator

TIMEZONE = "UTC"


class Engram(BaseModel):
    timezone: str = TIMEZONE
    created_on: Optional[datetime] = None

    @validator("created_on", pre=True, always=True)
    def set_created_on(cls, v, values):
        if v is None:
            dt = datetime.now(ZoneInfo(values.get("timezone", TIMEZONE)))
            # Trim to hours for compliance
            return dt.replace(minute=0, second=0, microsecond=0)
        return v

    @classmethod
    def from_json(cls, data) -> MetricEngram:
        """Build an Engram from JSON string or dict."""
        if isinstance(data, str):
            parsed = json.loads(data)
        else:
            parsed = data
        return cls.parse_obj(parsed)


class MetricEngram(Engram):
    datetime: Optional[str] = None
    conv_id: Optional[str] = None
    qa_metrics: Optional[list[str]] = []
    handoff_to: Optional[str] = None
    handoff_reason: Optional[str] = None
    crc: Optional[str] = None
    skill: Optional[str] = None
    sms_sent: Optional[bool] = False


def age_in_days(engram: Engram) -> Optional[float]:
    """Returns the age of the Engram in days as a float (1 decimal place)"""
    if engram.created_on is None:
        plog.warn("created_on is not set for engram")
        return None

    tz = ZoneInfo(TIMEZONE)
    # Trim to hours for compliance (same behavior as existing code)
    current_datetime = datetime.now(tz).replace(minute=0, second=0, microsecond=0)
    delta = current_datetime - engram.created_on

    days = delta.total_seconds() / 86400
    return round(days, 1)


def age_in_hours(engram: Engram):
    """Returns the age of the Engram in hours"""
    if engram.created_on is None:
        plog.warn("created_on is not set for engram")
        return None

    tz = ZoneInfo(TIMEZONE)
    # Trim to hours
    current_datetime = datetime.now(tz).replace(minute=0, second=0, microsecond=0)
    delta = current_datetime - engram.created_on
    return int(delta.total_seconds() // 3600)


def write_repeat_caller_metrics(conv: Conversation):
    """Check memory for repeat calls"""
    metric_engram_json = conv.memory.get("metric_engram")
    if metric_engram_json:
        metric_engram = MetricEngram().from_json(metric_engram_json)
        metric_age = age_in_days(metric_engram)

        if metric_age is not None and metric_age <= 1:
            conv.write_metric("REPEAT_CALLER_24_HOURS")
        elif metric_age is not None:
            conv.write_metric("REPEAT_CALLER_90_DAYS")

        if metric_age is not None:
            conv.write_metric("REPEAT_CALLER_DAYS_SINCE_PREVIOUS_CALL", metric_age)

        if metric_engram.qa_metrics:
            for qa_metric in metric_engram.qa_metrics:
                conv.write_metric(
                    "REPEAT_CALLER_QA",
                    qa_metric,
                )

        if metric_engram.handoff_reason:
            conv.write_metric(
                "REPEAT_CALLER_HANDOFF_REASON",
                metric_engram.handoff_reason,
            )

        if metric_engram.crc:
            conv.write_metric(
                "REPEAT_CALLER_CRC",
                metric_engram.crc,
            )

        if metric_engram.handoff_to:
            conv.write_metric(
                "REPEAT_CALLER_HANDOFF_TO",
                metric_engram.handoff_to,
            )

        if metric_engram.conv_id:
            conv.write_metric(
                "REPEAT_CALLER_CONV_ID",
                metric_engram.conv_id,
            )

        if metric_engram.datetime:
            conv.write_metric(
                "REPEAT_CALLER_DATETIME",
                metric_engram.datetime,
            )

        if metric_engram.sms_sent:
            conv.write_metric(
                "REPEAT_CALLER_SMS_SENT",
                metric_engram.sms_sent,
            )

    return


@func_description("[UTIL] Contains utils for agent memory - not currently used")
def agent_memory_utils(conv: Conversation):
    # No-op main function
    pass
