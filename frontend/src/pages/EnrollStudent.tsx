import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import CameraCapture from "../components/CameraCapture";
import * as api from "../api/client";
import { ENROLLMENT_STEPS } from "../constants";

export default function EnrollStudent() {
  const { courseId, studentId } = useParams();
  const cId = Number(courseId);
  const sId = Number(studentId);
  const navigate = useNavigate();

  const [stepIndex, setStepIndex] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const step = ENROLLMENT_STEPS[stepIndex];

  const handleCapture = async (blob: Blob) => {
    setSubmitting(true);
    setError("");
    try {
      const result = await api.enrollFace(cId, sId, step.label, blob);
      if (stepIndex + 1 < ENROLLMENT_STEPS.length) {
        setStepIndex(stepIndex + 1);
      } else if (result.angles_captured >= result.required_angles) {
        setDone(true);
      }
    } catch (err: any) {
      if (err?.response?.status === 422) {
        setError("No face detected — make sure your face is clearly visible and try again.");
      } else {
        setError("Something went wrong. Try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (done) {
    return (
      <div className="max-w-md mx-auto px-4 py-16 text-center">
        <div className="text-4xl mb-3">✅</div>
        <h1 className="text-xl font-bold text-gray-900 mb-2">Enrollment complete</h1>
        <p className="text-gray-500 text-sm mb-6">
          All {ENROLLMENT_STEPS.length} angles captured. This student can now be recognized during attendance.
        </p>
        <button
          onClick={() => navigate(`/courses/${cId}`)}
          className="bg-indigo-600 text-white font-semibold px-5 py-2.5 rounded-lg hover:bg-indigo-700 transition-colors"
        >
          Back to course
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto px-4 py-8">
      <Link to={`/courses/${cId}`} className="text-sm text-gray-400 hover:text-gray-600">
        ← Cancel
      </Link>
      <div className="text-center mt-4 mb-6">
        <p className="text-xs font-medium text-indigo-600 mb-1">
          Step {stepIndex + 1} of {ENROLLMENT_STEPS.length}
        </p>
        <h1 className="text-lg font-bold text-gray-900">{step.instruction}</h1>
      </div>

      <CameraCapture
        onCapture={handleCapture}
        overlayText={step.instruction}
        captureLabel={submitting ? "Processing…" : "Capture this angle"}
        disabled={submitting}
      />

      {error && (
        <p className="text-red-600 text-sm bg-red-50 border border-red-100 rounded-lg px-3 py-2 mt-4 text-center">
          {error}
        </p>
      )}

      <div className="flex justify-center gap-1.5 mt-6">
        {ENROLLMENT_STEPS.map((_, i) => (
          <div
            key={i}
            className={`h-1.5 w-8 rounded-full ${i <= stepIndex ? "bg-indigo-600" : "bg-gray-200"}`}
          />
        ))}
      </div>
    </div>
  );
}
