import { useEffect, useRef } from "react";

const GRID = 18;
const W = 400;
const CX = W / 2, CY = W / 2;
const RADIUS = 157;

function buildDots() {
  const dots = [];
  for (let row = 0; ; row++) {
    const y = row * GRID;
    if (y - CY > RADIUS + GRID) break;
    for (let col = 0; ; col++) {
      const x = col * GRID;
      if (x - CX > RADIUS + GRID) break;
      const dx = x - CX, dy = y - CY;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < RADIUS) {
        dots.push({
          x, y,
          normDist: dist / RADIUS,
          idleFreq:  5 + Math.random() * 4,
          idlePhase: Math.random() * Math.PI * 2,
          idleAmp:   0.35 + Math.random() * 0.3,
        });
      }
    }
  }
  return dots;
}
const DOTS = buildDots();

export default function JarvisOrb() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");

    const BPM = 36;
    const BEAT_INTERVAL = 60 / BPM;

    const s = {
      breathPhase: 0,
      lastTs: 0,
      timeSinceBeat: BEAT_INTERVAL,
      time: 0,
      beatT: 999,
    };

    let rafId;

    function frame(ts) {
      const dt = Math.min((ts - s.lastTs) / 1000, 0.05);
      s.lastTs = ts;
      s.time += dt;
      s.beatT += dt;
      s.timeSinceBeat += dt;

      if (s.timeSinceBeat >= BEAT_INTERVAL) {
        s.beatT = 0;
        s.timeSinceBeat = 0;
      }

      s.breathPhase += dt * (Math.PI / 6);
      const breath = Math.sin(s.breathPhase) * 0.5 + 0.5;

      // wave front travels CENTER (0) → EDGE (1)
      const WAVE_DUR = 1.2;
      const WAVE_SPEED = 1.0 / WAVE_DUR; // reaches edge in WAVE_DUR seconds

      let waveFront = -1;
      let waveAmp = 0;

      if (s.beatT < WAVE_DUR) {
        waveFront = s.beatT * WAVE_SPEED;           // 0 → 1
        waveAmp = 1.0 - (s.beatT / WAVE_DUR) * 0.5; // fades slightly as it travels
      }

      ctx.clearRect(0, 0, W, W);

      DOTS.forEach((dot) => {
        const { x, y, normDist } = dot;

        const restR = 2.8 + (1 - normDist) * 1.0;
        const idleWiggle = Math.sin(s.time * dot.idleFreq + dot.idlePhase) * dot.idleAmp;

        let waveGrow = 0;
        let waveAlpha = 0;

        if (waveFront >= 0) {
          const d = normDist - waveFront;
          const bell = Math.exp(-(d * d) / 0.012) * waveAmp;
          waveGrow  = bell * 9.5;
          waveAlpha = bell * 0.72;
        }

        const brR = breath * 0.6;
        const r = Math.max(1.4, restR + idleWiggle + waveGrow + brR);

        const baseAlpha = 0.26 + breath * 0.05;
        const alpha = Math.min(0.97, baseAlpha + waveAlpha);

        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255,255,255,${alpha})`;
        ctx.fill();
      });

      rafId = requestAnimationFrame(frame);
    }

    rafId = requestAnimationFrame(ts => {
      s.lastTs = ts;
      rafId = requestAnimationFrame(frame);
    });
    return () => cancelAnimationFrame(rafId);
  }, []);

  return (
    <div style={{
      width: "100vw",
      height: "100vh",
      background: "#000",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
    }}>
      <canvas
        ref={canvasRef}
        width={W}
        height={W}
        style={{ borderRadius: "50%", display: "block" }}
      />
    </div>
  );
}
