// Must match backend/app/core/config.py: max_embeddings_per_student
export const REQUIRED_ANGLES = 5;

export const ENROLLMENT_STEPS: { label: string; instruction: string }[] = [
  { label: "front", instruction: "Look straight at the camera" },
  { label: "left", instruction: "Turn your head slightly to the left" },
  { label: "right", instruction: "Turn your head slightly to the right" },
  { label: "up", instruction: "Tilt your chin up slightly" },
  { label: "down", instruction: "Tilt your chin down slightly" },
];
