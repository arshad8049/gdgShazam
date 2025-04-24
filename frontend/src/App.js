import React from "react";
import UploadForm from "./UploadForm";

function App() {
  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Audio→Transcript Demo</h1>
      <UploadForm />
    </div>
  );
}

export default App;