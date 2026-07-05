import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import * as api from "../api/client";
import type { AttendanceRecord } from "../api/client";

export default function SessionResult() {
  const { courseId, sessionId } = useParams();
  const cId = Number(courseId);
  const sessId = Number(sessionId);

  const [records, setRecords] = useState<AttendanceRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getSessionRecords(cId, sessId)
      .then(setRecords)
      .finally(() => setLoading(false));
  }, [cId, sessId]);

  const presentCount = records.filter((r) => r.present).length;

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8">
      <Link to={`/courses/${cId}`} className="text-sm text-gray-400 hover:text-gray-600">
        ← Back to course
      </Link>
      <div className="flex items-center justify-between mt-2 mb-6">
        <h1 className="text-xl font-bold text-gray-900">Attendance roster</h1>
        {!loading && (
          <span className="text-sm text-gray-500">
            {presentCount}/{records.length} present
          </span>
        )}
      </div>

      {loading ? (
        <p className="text-gray-400 text-sm">Loading…</p>
      ) : (
        <div className="bg-white border border-gray-200 rounded-xl divide-y divide-gray-100">
          {records.map((r) => (
            <div key={r.student_id} className="flex items-center justify-between px-4 py-3">
              <div>
                <p className="font-medium text-gray-900 text-sm">{r.name}</p>
                <p className="text-xs text-gray-500">{r.roll_number}</p>
              </div>
              {r.present ? (
                <span className="text-xs font-medium text-green-700 bg-green-50 px-2 py-0.5 rounded-full">
                  Present{r.confidence != null ? ` · ${(r.confidence * 100).toFixed(0)}%` : ""}
                </span>
              ) : (
                <span className="text-xs font-medium text-gray-400 bg-gray-50 px-2 py-0.5 rounded-full">
                  Absent
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
