export default function CameraLogo({ size = 36 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 28 28" fill="none">
      <rect x="2" y="7" width="24" height="17" rx="3" fill="#4F46E5" />
      <path d="M9 7L11 3.5H17L19 7" stroke="#4F46E5" strokeWidth="2" strokeLinejoin="round" />
      <circle cx="14" cy="15.5" r="5.5" fill="white" />
      <circle cx="14" cy="15.5" r="3" fill="#4F46E5" />
      <circle cx="21.5" cy="10.5" r="1.2" fill="white" />
    </svg>
  );
}
