import sys
import time
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
import config

def main():
    spark = SparkSession.builder \
        .appName("YSB-CTR-Spark") \
        .config("spark.sql.streaming.schemaInference", "true") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
        .config("spark.driver.extraJavaOptions", "-Djava.net.preferIPv4Stack=true") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    # Define schema matching the generator output
    schema = StructType([
        StructField("user_id", StringType()),
        StructField("ad_id", StringType()),
        StructField("campaign_id", StringType()),
        StructField("event_type", StringType()),
        StructField("event_time_ns", LongType()),
        StructField("insertion_time_ms", LongType())
    ])

    # Read from Kafka
    df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", config.KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", config.INPUT_TOPIC) \
        .option("startingOffsets", "latest") \
        .load()

    # Parse JSON and extract fields
    events = df.selectExpr("CAST(value AS STRING) as json") \
        .select(from_json("json", schema).alias("data")) \
        .select("data.*")

    # Convert nanoseconds to timestamp for watermarking
    # Spark timestamps are in seconds (or microseconds/milliseconds depending on version, but cast handles it)
    # event_time_ns is nanoseconds. / 1e9 gives seconds.
    events_with_ts = events \
        .withColumn("event_time", (col("event_time_ns") / 1e9).cast("timestamp"))

    # Apply watermark
    watermarked = events_with_ts \
        .withWatermark("event_time", config.WATERMARK_DELAY)

    # Calculate CTR per window and campaign
    # CTR = clicks / views
    # We also want to keep track of the oldest insertion time to calculate end-to-end latency later
    
    windowed_counts = watermarked \
        .groupBy(
            window("event_time", config.WINDOW_DURATION),
            "campaign_id"
        ) \
        .agg(
            count(when(col("event_type") == "view", 1)).alias("views"),
            count(when(col("event_type") == "click", 1)).alias("clicks"),
            min("insertion_time_ms").alias("min_insertion_time_ms")
        ) \
        .withColumn("ctr", col("clicks") / col("views")) \
        .withColumn("window_end", col("window.end")) \
        .withColumn("result_generation_time_ms", (unix_timestamp() * 1000).cast("long"))

    # Select final columns for output
    output_df = windowed_counts.select(
        col("campaign_id"),
        col("window_end").cast("string").alias("window_end_time"),
        col("views"),
        col("clicks"),
        col("ctr"),
        col("result_generation_time_ms"),
        col("min_insertion_time_ms")
    )

    # Write to Kafka
    query = output_df \
        .selectExpr("to_json(struct(*)) AS value") \
        .writeStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", config.KAFKA_BOOTSTRAP_SERVERS) \
        .option("topic", config.OUTPUT_TOPIC) \
        .option("checkpointLocation", config.CHECKPOINT_LOCATION) \
        .outputMode("append") \
        .start()

    query.awaitTermination()

if __name__ == "__main__":
    main()
