package org.example.config;

public class JobConfig {
    public static final String KAFKA_BOOTSTRAP_SERVERS = "127.0.0.1:9093";
    public static final String INPUT_TOPIC = "ysb-events";
    public static final String OUTPUT_TOPIC = "ysb-ctr-results-flink";
    public static final int WINDOW_SIZE_SECONDS = 10;
    public static final int WATERMARK_DELAY_SECONDS = 5;
}
