import React, { useState } from "react";

export default function UploadForm() {
  const [file, setFile] = useState(null);
  const [jobId, setJobId] = useState("");
  const [status, setStatus] = useState("");
  const [transcript, setTranscript] = useState("");

  const API = process.env.REACT_APP_API_URL;

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return alert("Please select an audio file");
    const form = new FormData();
    form.append("file", file);

    const res = await fetch(`${API}/upload-audio`, {
      method: "POST",
      body: form,
    });
    const data = await res.json();
    setJobId(data.jobId);
    setStatus("PENDING");
  };

  const checkStatus = async () => {
    if (!jobId) return;
    const res = await fetch(`${API}/status/${jobId}`);
    const data = await res.json();
    setStatus(data.status);
    if (data.transcript) setTranscript(data.transcript);
  };

  return (
    <div>
      <h2>Upload Audio</h2>
      <form onSubmit={handleUpload}>
        <input
          type="file"
          accept="audio/*"
          onChange={(e) => setFile(e.target.files[0])}
        />
        <button type="submit">Upload</button>
      </form>

      {jobId && (
        <div style={{ marginTop: 20 }}>
          <button onClick={checkStatus}>Check Status</button>
          <p>Status: {status}</p>
          {transcript && (
            <div>
              <h3>Transcript</h3>
              <pre>{transcript}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}