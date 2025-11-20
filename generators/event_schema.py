import json
import time
import random
import uuid

CAMPAIGNS = [str(uuid.uuid4()) for _ in range(10)]
ADS_PER_CAMPAIGN = 100
ADS = {c: [str(uuid.uuid4()) for _ in range(ADS_PER_CAMPAIGN)] for c in CAMPAIGNS}
EVENT_TYPES = ["view", "click", "purchase"]

def generate_event(event_time_ns=None):
    if event_time_ns is None:
        event_time_ns = time.time_ns()
        
    campaign_id = random.choice(CAMPAIGNS)
    ad_id = random.choice(ADS[campaign_id])
    event_type = random.choices(EVENT_TYPES, weights=[0.9, 0.09, 0.01])[0]
    user_id = str(uuid.uuid4())
    
    return {
        "user_id": user_id,
        "ad_id": ad_id,
        "campaign_id": campaign_id,
        "event_type": event_type,
        "event_time_ns": event_time_ns,
        "insertion_time_ms": int(time.time() * 1000)
    }
