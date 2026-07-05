import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import CameraCapture from "../components/CameraCapture";
import * as api from "../api/client";
import type { MarkAttendanceResult } from "../api/client";

export default function TakeAttendance() {
  const { courseId, sessionId } = useParams();
  const cId = Number(courseId);
  const sessId = Number(sessionId);
  const navigate = useNavigate();

  const [result, setResult] = useState<MarkAttendanceResult | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleCapture = async (blob: Blob) => {
    setSubmitting(true);
    setError("");
    try {
      const res = await api.markAttendance(cId, sessId, blob);
      setResult(res);
    } catch (err: any) {
      if (err?.response?.status === 422) {
        setError("No faces detected in the photo — try again with better lighting or framing.");
      } else {
        setError("Something went wrong. Try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (result) {
    return (
      <div className="max-w-md mx-auto px-4 py-10 text-center">
        <div className="text-4xl mb-3">📋</div>
        <h1 className="text-xl font-bold text-gray-900 mb-1">
          {result.matched.length} student{result.matched.length === 1 ? "" : "s"} marked present
        </h1>
        {result.unmatched_face_count > 0 && (
          <p className="text-sm text-amber-700 bg-amber-50 border border-amber-100 rounded-lg px-3 py-2 mt-3 inline-block">
            {result.unmatched_face_count} face{result.unmatched_face_count === 1 ? "" : "s"} in the photo
            didn't match any enrolled student
          </p>
        )}

        {result.matched.length > 0 && (
          <div className="bg-white border border-gray-200 rounded-xl divide-y divide-gray-100 mt-5 text-left">
            {result.matched.map((m) => (
              <div key={m.student_id} className="flex items-center justify-between px-4 py-3">
                <div>
                  <p className="font-medium text-gray-900 text-sm">{m.name}</p>
                  <p className="text-xs text-gray-500">{m.roll_number}</p>
                </div>
                <span className="text-xs text-gray-400">{(m.confidence * 100).toFixed(0)}% match</span>
              </div>
            ))}
          </div>
        )}

        <div className="flex gap-3 justify-center mt-6">
          <button
            onClick={() => setResult(null)}
            className="text-sm font-medium text-indigo-600 hover:text-indigo-800 px-4 py-2"
          >
            Capture another photo
          </button>
          <button
            onClick={() => navigate(`/courses/${cId}/sessions/${sessId}`)}
            className="bg-indigo-600 text-white text-sm font-semibold px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors"
          >
            View full roster
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto px-4 py-8">
      <Link to={`/courses/${cId}`} className="text-sm text-gray-400 hover:text-gray-600">
        ← Cancel
      </Link>
      <div className="text-center mt-4 mb-6">
        <h1 className="text-lg font-bold text-gray-900">Take attendance</h1>
        <p className="text-sm text-gray-500 mt-1">
          Point the camera at the classroom to capture everyone at once
        </p>
      </div>

      <CameraCapture
        onCapture={handleCapture}
        facingMode="environment"
        captureLabel={submitting ? "Processing…" : "Capture classroom photo"}
        disabled={submitting}
      />

      {error && (
        <p className="text-red-600 text-sm bg-red-50 border border-red-100 rounded-lg px-3 py-2 mt-4 text-center">
          {error}
        </p>
      )}
    </div>
  );
}
