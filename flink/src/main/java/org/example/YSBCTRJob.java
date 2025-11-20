package org.example;

import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import org.apache.flink.api.common.functions.AggregateFunction;
import org.apache.flink.api.common.serialization.SimpleStringSchema;
import org.apache.flink.connector.base.DeliveryGuarantee;
import org.apache.flink.connector.kafka.sink.KafkaRecordSerializationSchema;
import org.apache.flink.connector.kafka.sink.KafkaSink;
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.connector.kafka.source.enumerator.initializer.OffsetsInitializer;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.windowing.assigners.TumblingEventTimeWindows;
import org.apache.flink.streaming.api.windowing.time.Time;
import org.apache.flink.streaming.api.windowing.windows.TimeWindow;
import org.apache.flink.util.Collector;
import org.apache.flink.streaming.api.functions.windowing.WindowFunction;

import org.apache.flink.shaded.jackson2.com.fasterxml.jackson.databind.ObjectMapper;

import org.example.config.JobConfig;
import org.example.schemas.Event;

import java.time.Duration;

public class YSBCTRJob {

    public static void main(String[] args) throws Exception {
        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
        
        // Kafka Source
        KafkaSource<Event> source = KafkaSource.<Event>builder()
                .setBootstrapServers(JobConfig.KAFKA_BOOTSTRAP_SERVERS)
                .setTopics(JobConfig.INPUT_TOPIC)
                .setGroupId("flink-ysb-group")
                .setStartingOffsets(OffsetsInitializer.earliest())
                .setValueOnlyDeserializer(new EventDeserializationSchema())
                .build();

        DataStream<Event> events = env.fromSource(source, 
                WatermarkStrategy.<Event>forBoundedOutOfOrderness(Duration.ofSeconds(JobConfig.WATERMARK_DELAY_SECONDS))
                    .withTimestampAssigner((event, timestamp) -> event.eventTimeNs / 1_000_000)
                    .withIdleness(Duration.ofSeconds(1)), // Handle idle partitions
                "Kafka Source");

        // Windowed Aggregation
        DataStream<String> results = events
                .keyBy(event -> event.campaignId)
                .window(TumblingEventTimeWindows.of(Time.seconds(JobConfig.WINDOW_SIZE_SECONDS)))
                .aggregate(new CTRAggregator(), new CTRWindowResult());

        // Kafka Sink
        KafkaSink<String> sink = KafkaSink.<String>builder()
                .setBootstrapServers(JobConfig.KAFKA_BOOTSTRAP_SERVERS)
                .setRecordSerializer(KafkaRecordSerializationSchema.builder()
                        .setTopic(JobConfig.OUTPUT_TOPIC)
                        .setValueSerializationSchema(new SimpleStringSchema())
                        .build()
                )
                .setDeliveryGuarantee(DeliveryGuarantee.AT_LEAST_ONCE)
                .build();

        results.sinkTo(sink);

        env.execute("YSB CTR Flink Job");
    }

    // Custom Deserializer
    public static class EventDeserializationSchema implements org.apache.flink.api.common.serialization.DeserializationSchema<Event> {
        private static final ObjectMapper mapper = new ObjectMapper();

        @Override
        public Event deserialize(byte[] message) {
            try {
                return mapper.readValue(message, Event.class);
            } catch (Exception e) {
                return null;
            }
        }

        @Override
        public boolean isEndOfStream(Event nextElement) {
            return false;
        }

        @Override
        public org.apache.flink.api.common.typeinfo.TypeInformation<Event> getProducedType() {
            return org.apache.flink.api.common.typeinfo.TypeInformation.of(Event.class);
        }
    }

    // Aggregator
    public static class CTRAggregator implements AggregateFunction<Event, CTRAccumulator, CTRResult> {
        @Override
        public CTRAccumulator createAccumulator() {
            return new CTRAccumulator();
        }

        @Override
        public CTRAccumulator add(Event event, CTRAccumulator acc) {
            if ("view".equals(event.eventType)) {
                acc.views++;
            } else if ("click".equals(event.eventType)) {
                acc.clicks++;
            }
            acc.minInsertionTimeMs = Math.min(acc.minInsertionTimeMs, event.insertionTimeMs);
            return acc;
        }

        @Override
        public CTRResult getResult(CTRAccumulator acc) {
            CTRResult result = new CTRResult();
            result.views = acc.views;
            result.clicks = acc.clicks;
            result.ctr = acc.views > 0 ? (double) acc.clicks / acc.views : 0.0;
            result.minInsertionTimeMs = acc.minInsertionTimeMs;
            return result;
        }

        @Override
        public CTRAccumulator merge(CTRAccumulator a, CTRAccumulator b) {
            a.views += b.views;
            a.clicks += b.clicks;
            a.minInsertionTimeMs = Math.min(a.minInsertionTimeMs, b.minInsertionTimeMs);
            return a;
        }
    }

    public static class CTRAccumulator {
        public long views = 0;
        public long clicks = 0;
        public long minInsertionTimeMs = Long.MAX_VALUE;
    }

    public static class CTRResult {
        public String campaignId;
        public long windowEndTime;
        public long views;
        public long clicks;
        public double ctr;
        public long resultGenerationTimeMs;
        public long minInsertionTimeMs;
    }

    // Window Function to add window metadata
    public static class CTRWindowResult implements WindowFunction<CTRResult, String, String, TimeWindow> {
        private static final ObjectMapper mapper = new ObjectMapper();

        @Override
        public void apply(String key, TimeWindow window, Iterable<CTRResult> input, Collector<String> out) throws Exception {
            CTRResult result = input.iterator().next();
            result.campaignId = key;
            result.windowEndTime = window.getEnd();
            result.resultGenerationTimeMs = System.currentTimeMillis();
            out.collect(mapper.writeValueAsString(result));
        }
    }
}
