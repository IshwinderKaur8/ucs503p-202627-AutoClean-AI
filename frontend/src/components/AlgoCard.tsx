import { motion } from "framer-motion";
import type { AlgorithmRecommendation } from "../types";
import { useTilt } from "../hooks/useTilt";

interface Props {
  rec: AlgorithmRecommendation;
  index: number;
}

export default function AlgoCard({ rec, index }: Props) {
  const tilt = useTilt<HTMLDivElement>();

  return (
    <motion.div
      ref={tilt.ref}
      onMouseMove={tilt.onMouseMove}
      onMouseLeave={tilt.onMouseLeave}
      className="algo-card tilt-card"
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.35 }}
    >
      <h4>{rec.algorithm}</h4>
      <div className="score-bar-track">
        <div className="score-bar-fill" style={{ width: `${Math.round(rec.score * 100)}%` }} />
      </div>
      <div className="hint">{Math.round(rec.score * 100)}% fit</div>
      {rec.reasons.length > 0 && (
        <ul className="algo-reasons">
          {rec.reasons.map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      )}
      {rec.caveats.length > 0 && (
        <ul className="algo-caveats">
          {rec.caveats.map((c, i) => (
            <li key={i}>{c}</li>
          ))}
        </ul>
      )}
    </motion.div>
  );
}
