from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import storage, speech, pubsub_v1, firestore
import uuid
import os

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pydantic import BaseModel

app = FastAPI()

# Enable CORS for React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Google Cloud clients
storage_client = storage.Client()
speech_client = speech.SpeechClient()
pubsub_publisher = pubsub_v1.PublisherClient()
firestore_client = firestore.Client()

# Initialize Google Custom Search client
SEARCH_API_KEY = os.getenv("SEARCH_API_KEY")
SEARCH_CX      = os.getenv("SEARCH_CX")
search_client  = build("customsearch", "v1", developerKey=SEARCH_API_KEY)

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

class SearchRequest(BaseModel):
    jobId: str

@app.post("/search")
def search_results(request: SearchRequest):
    jobId = request.jobId
    # 1) Fetch transcript
    doc_ref = firestore_client.collection("jobs").document(jobId)
    doc     = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Job not found")
    data       = doc.to_dict()
    transcript = data.get("transcript")
    if not transcript:
        raise HTTPException(status_code=400, detail="Transcript not available")

    # 2) Call Custom Search
    try:
        resp = search_client.cse().list(
            q=transcript[:200],
            cx=SEARCH_CX,
            num=5,
            key=SEARCH_API_KEY
        ).execute()
    except HttpError as e:
        # Return a friendly error if the search API call fails
        raise HTTPException(
            status_code=502,
            detail=f"Search API error: {e.error_details or e._get_reason()}"
        )

    # 3) Extract and persist results
    hits = [
        {"title": item["title"], "url": item["link"], "snippet": item["snippet"]}
        for item in resp.get("items", [])
    ]
    doc_ref.update({"searchResults": hits})
    return {"searchResults": hits}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
