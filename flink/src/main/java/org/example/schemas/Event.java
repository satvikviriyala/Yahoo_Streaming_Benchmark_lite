package org.example.schemas;

import org.apache.flink.shaded.jackson2.com.fasterxml.jackson.annotation.JsonProperty;

public class Event {
    @JsonProperty("user_id")
    public String userId;

    @JsonProperty("ad_id")
    public String adId;

    @JsonProperty("campaign_id")
    public String campaignId;

    @JsonProperty("event_type")
    public String eventType;

    @JsonProperty("event_time_ns")
    public long eventTimeNs;

    @JsonProperty("insertion_time_ms")
    public long insertionTimeMs;

    public Event() {
    }

    @Override
    public String toString() {
        return "Event{" +
                "userId='" + userId + '\'' +
                ", adId='" + adId + '\'' +
                ", campaignId='" + campaignId + '\'' +
                ", eventType='" + eventType + '\'' +
                ", eventTimeNs=" + eventTimeNs +
                ", insertionTimeMs=" + insertionTimeMs +
                '}';
    }
}
