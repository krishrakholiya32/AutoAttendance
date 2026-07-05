import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import * as api from "../api/client";
import type { AttendanceSession, Course, Student } from "../api/client";
import { REQUIRED_ANGLES } from "../constants";

export default function CourseDetail() {
  const { courseId } = useParams();
  const id = Number(courseId);
  const navigate = useNavigate();

  const [course, setCourse] = useState<Course | null>(null);
  const [students, setStudents] = useState<Student[]>([]);
  const [sessions, setSessions] = useState<AttendanceSession[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [roll, setRoll] = useState("");
  const [creating, setCreating] = useState(false);
  const [startingSession, setStartingSession] = useState(false);

  const load = () => {
    api.getCourse(id).then(setCourse);
    api.listStudents(id).then(setStudents);
    api.listSessions(id).then(setSessions);
  };

  useEffect(load, [id]);

  const handleAddStudent = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      await api.addStudent(id, name, roll);
      setName("");
      setRoll("");
      setShowForm(false);
      load();
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteStudent = async (studentId: number) => {
    if (!confirm("Remove this student and their enrolled face data?")) return;
    await api.deleteStudent(id, studentId);
    load();
  };

  const handleTakeAttendance = async () => {
    setStartingSession(true);
    try {
      const session = await api.createSession(id);
      navigate(`/courses/${id}/sessions/${session.id}/take`);
    } finally {
      setStartingSession(false);
    }
  };

  if (!course) return <p className="text-center text-gray-400 text-sm py-10">Loading…</p>;

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
      <Link to="/dashboard" className="text-sm text-gray-400 hover:text-gray-600">
        ← Back to courses
      </Link>
      <div className="flex items-center justify-between mt-2 mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">{course.name}</h1>
          <span className="text-xs font-medium text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">
            {course.code}
          </span>
        </div>
        <button
          onClick={handleTakeAttendance}
          disabled={startingSession || students.length === 0}
          className="text-sm font-semibold bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
        >
          {startingSession ? "Starting…" : "📷 Take attendance"}
        </button>
      </div>

      <section className="mb-8">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-gray-800">Students ({students.length})</h2>
          <button
            onClick={() => setShowForm((s) => !s)}
            className="text-sm font-medium text-indigo-600 hover:text-indigo-800"
          >
            + Add student
          </button>
        </div>

        {showForm && (
          <form
            onSubmit={handleAddStudent}
            className="bg-white border border-gray-200 rounded-xl p-4 mb-3 flex flex-col sm:flex-row gap-3 items-end"
          >
            <div className="flex-1 w-full">
              <label className="block text-xs font-medium text-gray-600 mb-1">Name</label>
              <input
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <div className="w-full sm:w-40">
              <label className="block text-xs font-medium text-gray-600 mb-1">Roll number</label>
              <input
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                value={roll}
                onChange={(e) => setRoll(e.target.value)}
                required
              />
            </div>
            <button
              type="submit"
              disabled={creating}
              className="bg-indigo-600 text-white text-sm font-semibold px-4 py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-60 transition-colors whitespace-nowrap"
            >
              {creating ? "Adding…" : "Add"}
            </button>
          </form>
        )}

        {students.length === 0 ? (
          <div className="bg-white border border-gray-200 border-dashed rounded-xl p-8 text-center text-gray-500 text-sm">
            No students added yet.
          </div>
        ) : (
          <div className="bg-white border border-gray-200 rounded-xl divide-y divide-gray-100">
            {students.map((s) => (
              <div key={s.id} className="flex items-center justify-between px-4 py-3">
                <div>
                  <p className="font-medium text-gray-900 text-sm">{s.name}</p>
                  <p className="text-xs text-gray-500">{s.roll_number}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span
                    className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                      s.angles_captured >= REQUIRED_ANGLES
                        ? "text-green-700 bg-green-50"
                        : "text-amber-700 bg-amber-50"
                    }`}
                  >
                    {s.angles_captured}/{REQUIRED_ANGLES} angles
                  </span>
                  <Link
                    to={`/courses/${id}/students/${s.id}/enroll`}
                    className="text-xs font-medium text-indigo-600 hover:text-indigo-800"
                  >
                    {s.angles_captured >= REQUIRED_ANGLES ? "Re-enroll" : "Enroll face"}
                  </Link>
                  <button
                    onClick={() => handleDeleteStudent(s.id)}
                    className="text-xs text-gray-400 hover:text-red-600"
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="font-semibold text-gray-800 mb-3">Attendance history</h2>
        {sessions.length === 0 ? (
          <div className="bg-white border border-gray-200 border-dashed rounded-xl p-8 text-center text-gray-500 text-sm">
            No attendance taken yet.
          </div>
        ) : (
          <div className="bg-white border border-gray-200 rounded-xl divide-y divide-gray-100">
            {sessions.map((s) => (
              <Link
                key={s.id}
                to={`/courses/${id}/sessions/${s.id}`}
                className="flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors"
              >
                <span className="text-sm text-gray-900">{s.session_date}</span>
                <span className="text-xs text-gray-400">View roster →</span>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
