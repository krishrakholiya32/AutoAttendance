import { BrowserRouter, Routes, Route, Navigate, Link } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import CameraLogo from "./components/CameraLogo";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Dashboard from "./pages/Dashboard";
import CourseDetail from "./pages/CourseDetail";
import EnrollStudent from "./pages/EnrollStudent";
import TakeAttendance from "./pages/TakeAttendance";
import SessionResult from "./pages/SessionResult";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAuth();
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function Nav() {
  const { token, logout } = useAuth();
  if (!token) return null;
  return (
    <nav className="sticky top-0 z-20 bg-white border-b border-gray-100">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-3.5 flex items-center justify-between">
        <Link to="/dashboard" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
          <CameraLogo size={24} />
          <span className="font-bold text-gray-900 tracking-tight">AutoAttendance</span>
        </Link>
        <button
          onClick={logout}
          className="text-sm text-gray-500 hover:text-gray-800 transition-colors px-3 py-1.5 rounded-lg hover:bg-gray-50"
        >
          Log out
        </button>
      </div>
    </nav>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Nav />
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/courses/:courseId"
            element={
              <ProtectedRoute>
                <CourseDetail />
              </ProtectedRoute>
            }
          />
          <Route
            path="/courses/:courseId/students/:studentId/enroll"
            element={
              <ProtectedRoute>
                <EnrollStudent />
              </ProtectedRoute>
            }
          />
          <Route
            path="/courses/:courseId/sessions/:sessionId/take"
            element={
              <ProtectedRoute>
                <TakeAttendance />
              </ProtectedRoute>
            }
          />
          <Route
            path="/courses/:courseId/sessions/:sessionId"
            element={
              <ProtectedRoute>
                <SessionResult />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
