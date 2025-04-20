
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from google.cloud import storage, speech, pubsub_v1, firestore
import uuid
import os

app = FastAPI()

# Initialize Google Cloud clients
storage_client = storage.Client()
speech_client = speech.SpeechClient()
pubsub_publisher = pubsub_v1.PublisherClient()
firestore_client = firestore.Client()

# Environment/config
BUCKET_NAME = os.getenv("AUDIO_BUCKET")
PUBSUB_TOPIC = os.getenv("PUBSUB_TOPIC")

@app.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    # Save to GCS
    job_id = str(uuid.uuid4())
    blob = storage_client.bucket(BUCKET_NAME).blob(f"{job_id}/{file.filename}")
    content = await file.read()
    blob.upload_from_string(content, content_type=file.content_type)

    # Initialize Firestore doc
    doc_ref = firestore_client.collection("jobs").document(job_id)
    doc_ref.set({"status": "PENDING", "createdAt": firestore.SERVER_TIMESTAMP})

    # Publish Pub/Sub message for worker
    message = f"{job_id}|gs://{BUCKET_NAME}/{job_id}/{file.filename}"
    pubsub_publisher.publish(PUBSUB_TOPIC, message.encode("utf-8"))

    return JSONResponse(status_code=202, content={"jobId": job_id})

@app.get("/status/{job_id}")
def get_status(job_id: str):
    doc = firestore_client.collection("jobs").document(job_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Job not found")
    return doc.to_dict()

@app.post("/search")
def search_results(jobId: str):
    # TODO: fetch transcript from Firestore, call search/summarization, update Firestore, return results
    doc_ref = firestore_client.collection("jobs").document(jobId)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Job not found")
    data = doc.to_dict()
    transcript = data.get("transcript")
    if not transcript:
        raise HTTPException(status_code=400, detail="Transcript not available yet")

    # Placeholder response
    results = [{"title": "Example", "url": "https://example.com", "snippet": "Sample snippet"}]
    doc_ref.update({"searchResults": results})
    return {"searchResults": results}
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
