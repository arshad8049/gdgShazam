# gdg Challenge Shazam
**Initial test commit**
**Things do so far**
1. GCP resource provisioning
* Enabled the Speech‑to‑Text, Storage, Firestore, Pub/Sub and Run APIs.
* Created a Cloud Storage bucket (gdgclouddev-audio-uploads) with a lifecycle rule.
* Initialized Firestore and confirmed the jobs collection is writable.
* Created the Pub/Sub topic (audio-processing) and subscription (audio-processing-worker).
* Provisioned a dedicated service account (audio-backend-sa) and granted it roles for Speech, Storage, Firestore and Pub/Sub.
* Still need to figure out on how to give access to yall

2. Local environment configuration
* Downloaded the service‑account JSON key and set GOOGLE_APPLICATION_CREDENTIALS to point at it.
* Exported GOOGLE_CLOUD_PROJECT, AUDIO_BUCKET and PUBSUB_TOPIC so both server and worker pick them up.

3.	Backend API (main.py)
* Built a FastAPI app with three endpoints:
	*	POST /upload-audio: saves the file to GCS, writes a Firestore doc with status=PENDING, and publishes a Pub/Sub message.
	*	GET /status/{job_id}: reads and returns that Firestore doc.
	*	POST /search: stubbed out for later, fetches the transcript and will run search/summarization.
* Added a Uvicorn entrypoint so python main.py or uvicorn main:app both work.
* Verified locally that /upload-audio returns 202 Accepted and creates a jobs/{jobId} doc.

4.	Background worker (worker.py)- needs work
* Subscribes to audio-processing-worker, pulls each message, marks the Firestore doc RUNNING, calls speech.long_running_recognize on the GCS URI, assembles the transcript, then updates the doc with status=COMPLETED and the transcript.
* Confirmed the subscription existed (created it after realizing it was missing) and still needs fixing credential permissions so the worker can update Firestore without 403s that I am having right now.