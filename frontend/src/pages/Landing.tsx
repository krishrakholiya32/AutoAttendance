import { Link } from "react-router-dom";
import CameraLogo from "../components/CameraLogo";

export default function Landing() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-20 text-center">
        <div className="flex justify-center mb-4">
          <CameraLogo size={48} />
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 tracking-tight">
          Attendance in one photo, not one roll call
        </h1>
        <p className="text-gray-500 mt-4 max-w-xl mx-auto">
          Enroll each student once from a few guided angles. From then on, take a single
          classroom photo from your phone or laptop and every enrolled face is matched and
          marked present automatically — scoped to your course roster, not the whole university.
        </p>
        <div className="flex gap-3 justify-center mt-8">
          <Link
            to="/signup"
            className="bg-indigo-600 text-white font-semibold px-5 py-2.5 rounded-lg hover:bg-indigo-700 transition-colors"
          >
            Get started free
          </Link>
          <Link
            to="/login"
            className="text-gray-700 font-semibold px-5 py-2.5 rounded-lg border border-gray-300 hover:bg-gray-100 transition-colors"
          >
            Log in
          </Link>
        </div>

        <div className="grid sm:grid-cols-3 gap-4 mt-16 text-left">
          <div className="bg-white border border-gray-200 rounded-xl p-5">
            <p className="font-semibold text-gray-900 text-sm mb-1">Per-professor login</p>
            <p className="text-xs text-gray-500">
              Each professor manages their own courses and rosters independently.
            </p>
          </div>
          <div className="bg-white border border-gray-200 rounded-xl p-5">
            <p className="font-semibold text-gray-900 text-sm mb-1">Multi-angle enrollment</p>
            <p className="text-xs text-gray-500">
              A guided 5-angle capture per student improves real-world matching accuracy.
            </p>
          </div>
          <div className="bg-white border border-gray-200 rounded-xl p-5">
            <p className="font-semibold text-gray-900 text-sm mb-1">One photo, whole class</p>
            <p className="text-xs text-gray-500">
              Every enrolled face in a single classroom photo is detected and matched at once.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
