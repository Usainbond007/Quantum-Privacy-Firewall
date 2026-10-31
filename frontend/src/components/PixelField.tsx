import { useEffect, useRef } from "react";

const GRID = 92;

export function PixelField() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const pointer = useRef<{ x: number; y: number } | null>(null);

  useEffect(() => {
    if (typeof ResizeObserver === "undefined") return;
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d", { alpha: false });
    if (!canvas || !context) return;

    const source = new Image();
    source.src = "/visuals/pixel-field.png";
    let frame = 0;
    let lastFrame = 0;
    let colors: Uint8ClampedArray | null = null;
    const reducedMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

    const resize = () => {
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(canvas.clientWidth * ratio);
      canvas.height = Math.round(canvas.clientHeight * ratio);
    };
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    resize();

    source.onload = () => {
      const sample = document.createElement("canvas");
      sample.width = GRID;
      sample.height = GRID;
      const sampleContext = sample.getContext("2d", { willReadFrequently: true });
      if (!sampleContext) return;
      sampleContext.imageSmoothingEnabled = false;
      sampleContext.drawImage(source, 0, 0, GRID, GRID);
      colors = sampleContext.getImageData(0, 0, GRID, GRID).data;

      const draw = (time: number) => {
        if (!colors || !context) return;
        if (!reducedMotion && time - lastFrame < 45) {
          frame = requestAnimationFrame(draw);
          return;
        }
        lastFrame = time;
        const width = canvas.width;
        const height = canvas.height;
        const size = Math.max(width / GRID, height / GRID);
        const offsetX = (width - size * GRID) / 2;
        const offsetY = (height - size * GRID) / 2;
        context.fillStyle = "#101115";
        context.fillRect(0, 0, width, height);

        for (let y = 0; y < GRID; y += 1) {
          for (let x = 0; x < GRID; x += 1) {
            const index = (y * GRID + x) * 4;
            const red = colors[index];
            const green = colors[index + 1];
            const blue = colors[index + 2];
            if (Math.max(red, green, blue) < 70) continue;
            const wave = Math.sin(time * 0.002 - x * 0.13 - y * 0.1);
            const point = pointer.current;
            const distance = point
              ? Math.hypot(x - point.x * GRID, y - point.y * GRID)
              : 100;
            const ripple = point ? Math.max(0, 1 - distance / 18) : 0;
            context.globalAlpha = reducedMotion ? 1 : Math.min(1, 0.84 + wave * 0.12 + ripple * 0.18);
            context.fillStyle = `rgb(${red}, ${green}, ${blue})`;
            context.fillRect(
              Math.round(offsetX + x * size),
              Math.round(offsetY + y * size),
              Math.ceil(size * (ripple > 0.1 ? 0.96 : 0.86)),
              Math.ceil(size * (ripple > 0.1 ? 0.96 : 0.86)),
            );
          }
        }
        context.globalAlpha = 1;
        if (!reducedMotion) frame = requestAnimationFrame(draw);
      };
      frame = requestAnimationFrame(draw);
    };

    return () => {
      source.onload = null;
      cancelAnimationFrame(frame);
      observer.disconnect();
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="pixel-field-canvas"
      aria-hidden="true"
      onPointerMove={(event) => {
        const bounds = event.currentTarget.getBoundingClientRect();
        pointer.current = {
          x: (event.clientX - bounds.left) / bounds.width,
          y: (event.clientY - bounds.top) / bounds.height,
        };
      }}
      onPointerLeave={() => { pointer.current = null; }}
    />
  );
}
