import axios from "axios";

const apiUrl = import.meta.env.VITE_API_URL;
const client = axios.create({
  baseURL: apiUrl !== undefined ? apiUrl : "http://localhost:8000",
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (res) => res,
  (err) => {
    const isAuthEndpoint = err.config?.url?.startsWith("/auth/");
    if (err.response?.status === 401 && !isAuthEndpoint) {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export interface Professor {
  id: number;
  email: string;
  name: string;
}

export interface Course {
  id: number;
  name: string;
  code: string;
  created_at: string;
  student_count: number;
}

export interface Student {
  id: number;
  name: string;
  roll_number: string;
  created_at: string;
  angles_captured: number;
}

export interface EnrollFaceResult {
  angle_label: string;
  angles_captured: number;
  required_angles: number;
}

export interface AttendanceSession {
  id: number;
  session_date: string;
  created_at: string;
}

export interface MatchedStudent {
  student_id: number;
  name: string;
  roll_number: string;
  confidence: number;
}

export interface MarkAttendanceResult {
  matched: MatchedStudent[];
  unmatched_face_count: number;
  spoofed_face_count: number;
}

export type JobStatus = "pending" | "processing" | "done" | "failed";

export interface MarkJobAccepted {
  job_id: number;
  status: JobStatus;
}

export interface JobStatusResponse {
  job_id: number;
  status: JobStatus;
  result: MarkAttendanceResult | null;
  error: string | null;
}

export interface AttendanceRecord {
  student_id: number;
  name: string;
  roll_number: string;
  present: boolean;
  confidence: number | null;
}

export async function signup(email: string, password: string, name: string) {
  const { data } = await client.post("/auth/signup", { email, password, name });
  return data.access_token as string;
}

export async function login(email: string, password: string) {
  const { data } = await client.post("/auth/login", { email, password });
  return data.access_token as string;
}

export async function getMe() {
  const { data } = await client.get<Professor>("/auth/me");
  return data;
}

export async function listCourses() {
  const { data } = await client.get<Course[]>("/courses");
  return data;
}

export async function createCourse(name: string, code: string) {
  const { data } = await client.post<Course>("/courses", { name, code });
  return data;
}

export async function getCourse(courseId: number) {
  const { data } = await client.get<Course>(`/courses/${courseId}`);
  return data;
}

export async function deleteCourse(courseId: number) {
  await client.delete(`/courses/${courseId}`);
}

export async function listStudents(courseId: number) {
  const { data } = await client.get<Student[]>(`/courses/${courseId}/students`);
  return data;
}

export async function addStudent(courseId: number, name: string, rollNumber: string) {
  const { data } = await client.post<Student>(`/courses/${courseId}/students`, {
    name,
    roll_number: rollNumber,
  });
  return data;
}

export async function deleteStudent(courseId: number, studentId: number) {
  await client.delete(`/courses/${courseId}/students/${studentId}`);
}

export async function enrollFace(
  courseId: number,
  studentId: number,
  angleLabel: string,
  blob: Blob
) {
  const form = new FormData();
  form.append("file", blob, `${angleLabel}.jpg`);
  const { data } = await client.post<EnrollFaceResult>(
    `/courses/${courseId}/students/${studentId}/enroll-face?angle_label=${angleLabel}`,
    form,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return data;
}

export async function createSession(courseId: number) {
  const { data } = await client.post<AttendanceSession>(`/courses/${courseId}/attendance/sessions`, {});
  return data;
}

export async function listSessions(courseId: number) {
  const { data } = await client.get<AttendanceSession[]>(`/courses/${courseId}/attendance/sessions`);
  return data;
}

export async function markAttendance(courseId: number, sessionId: number, blob: Blob) {
  const form = new FormData();
  form.append("file", blob, "classroom.jpg");
  const { data } = await client.post<MarkJobAccepted>(
    `/courses/${courseId}/attendance/sessions/${sessionId}/mark`,
    form,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return data;
}

export async function getJobStatus(courseId: number, sessionId: number, jobId: number) {
  const { data } = await client.get<JobStatusResponse>(
    `/courses/${courseId}/attendance/sessions/${sessionId}/jobs/${jobId}`
  );
  return data;
}

/**
 * Polls a mark-attendance job until it reaches a terminal state (done/failed).
 * `onTick` fires after every poll so the caller can reflect the latest status.
 */
export async function pollJobStatus(
  courseId: number,
  sessionId: number,
  jobId: number,
  onTick?: (status: JobStatusResponse) => void,
  intervalMs = 1500,
  timeoutMs = 60000
): Promise<JobStatusResponse> {
  const deadline = Date.now() + timeoutMs;
  while (true) {
    const status = await getJobStatus(courseId, sessionId, jobId);
    onTick?.(status);
    if (status.status === "done" || status.status === "failed") {
      return status;
    }
    if (Date.now() >= deadline) {
      throw new Error("Attendance processing timed out");
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
}

export async function getSessionRecords(courseId: number, sessionId: number) {
  const { data } = await client.get<AttendanceRecord[]>(
    `/courses/${courseId}/attendance/sessions/${sessionId}`
  );
  return data;
}

export default client;
