import os
from concurrent.futures import TimeoutError
from google.cloud import pubsub_v1, storage, speech, firestore

# Config from environment
PROJECT_ID     = os.getenv("GOOGLE_CLOUD_PROJECT", "gdgclouddev")
SUBSCRIPTION   = f"projects/{PROJECT_ID}/subscriptions/audio-processing-worker"
BUCKET_NAME    = os.getenv("AUDIO_BUCKET")

# Initialize clients
speech_client   = speech.SpeechClient()
storage_client  = storage.Client()
firestore_client = firestore.Client()

def callback(message: pubsub_v1.subscriber.message.Message):
    payload = message.data.decode("utf-8")
    job_id, gcs_uri = payload.split("|", 1)

    # 1) Mark RUNNING
    doc_ref = firestore_client.collection("jobs").document(job_id)
    doc_ref.update({"status": "RUNNING"})

    # 2) Transcribe
    audio = {"uri": gcs_uri}
    config = {
        "encoding": speech.RecognitionConfig.AudioEncoding.LINEAR16,
        "language_code": "en-US",
        "enable_automatic_punctuation": True
    }
    operation = speech_client.long_running_recognize(config=config, audio=audio)
    response = operation.result(timeout=300)

    # 3) Assemble transcript
    transcript = "\n".join(r.alternatives[0].transcript for r in response.results)

    # 4) Write back transcript & complete status
    doc_ref.update({
        "transcript": transcript,
        "status": "COMPLETED"
    })

    # 5) Ack the message so it doesn’t redeliver
    message.ack()

def main():
    subscriber = pubsub_v1.SubscriberClient()
    streaming_pull_future = subscriber.subscribe(SUBSCRIPTION, callback=callback)
    print(f"Listening for messages on {SUBSCRIPTION}…")
    try:
        streaming_pull_future.result()
    except TimeoutError:
        streaming_pull_future.cancel()

if __name__ == "__main__":
    main()