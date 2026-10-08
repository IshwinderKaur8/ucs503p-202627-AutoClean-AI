import { useRef } from "react";
import type { MouseEvent } from "react";

const MAX_TILT_DEG = 6;

/**
 * Pointer-driven 3D tilt for a card element. Pair the returned handlers with
 * the `.tilt-card` CSS class (transform-style: preserve-3d + transition).
 * Plain mousemove math, no extra dependency.
 */
export function useTilt<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);

  const onMouseMove = (e: MouseEvent<T>) => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width; // 0..1
    const py = (e.clientY - rect.top) / rect.height; // 0..1
    const rotateY = (px - 0.5) * 2 * MAX_TILT_DEG;
    const rotateX = (0.5 - py) * 2 * MAX_TILT_DEG;
    el.style.transform = `perspective(700px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateZ(0)`;
  };

  const onMouseLeave = () => {
    const el = ref.current;
    if (!el) return;
    el.style.transform = "perspective(700px) rotateX(0deg) rotateY(0deg) translateZ(0)";
  };

  return { ref, onMouseMove, onMouseLeave };
}
