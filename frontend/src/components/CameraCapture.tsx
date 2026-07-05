import { useEffect, useRef, useState } from "react";

interface CameraCaptureProps {
  onCapture: (blob: Blob) => void;
  facingMode?: "user" | "environment";
  overlayText?: string;
  captureLabel?: string;
  disabled?: boolean;
}

export default function CameraCapture({
  onCapture,
  facingMode = "user",
  overlayText,
  captureLabel = "Capture",
  disabled = false,
}: CameraCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;

    navigator.mediaDevices
      .getUserMedia({ video: { facingMode, width: { ideal: 1280 }, height: { ideal: 960 } } })
      .then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
        setReady(true);
      })
      .catch((err) => {
        setError(
          err.name === "NotAllowedError"
            ? "Camera permission denied. Please allow camera access and reload."
            : "Could not access camera: " + err.message
        );
      });

    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, [facingMode]);

  const capture = () => {
    const video = videoRef.current;
    if (!video) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(
      (blob) => {
        if (blob) onCapture(blob);
      },
      "image/jpeg",
      0.92
    );
  };

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center text-red-700 text-sm">
        {error}
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative w-full max-w-md aspect-[4/3] rounded-xl overflow-hidden bg-black">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="w-full h-full object-cover -scale-x-100"
        />
        {overlayText && (
          <div className="absolute bottom-0 inset-x-0 bg-black/60 text-white text-sm text-center py-2">
            {overlayText}
          </div>
        )}
        {!ready && (
          <div className="absolute inset-0 flex items-center justify-center text-white text-sm">
            Starting camera...
          </div>
        )}
      </div>
      <button
        onClick={capture}
        disabled={!ready || disabled}
        className="bg-indigo-600 text-white font-semibold px-6 py-2.5 rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {captureLabel}
      </button>
    </div>
  );
}
