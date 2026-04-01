import { DepthMode } from './ProjectContextPanel';

const OPTIONS: { value: DepthMode; label: string; description: string }[] = [
  { value: 'quick',    label: 'Quick',     description: 'Fast factual lookups' },
  { value: 'balanced', label: 'Balanced',  description: 'Standard advisory queries' },
  { value: 'deep',     label: 'Deep Dive', description: 'Complex, multi-faceted research' },
];

const DEPTH_INDEX: Record<DepthMode, number> = { quick: 0, balanced: 1, deep: 2 };
const INDEX_DEPTH: DepthMode[] = ['quick', 'balanced', 'deep'];

interface Props {
  depth: DepthMode;
  onChange: (depth: DepthMode) => void;
}

export default function DepthSlider({ depth, onChange }: Props) {
  const idx = DEPTH_INDEX[depth];

  return (
    <div className="w-full max-w-xs mx-auto px-2 pb-1">
      <input
        type="range"
        min={0}
        max={2}
        step={1}
        value={idx}
        onChange={(e) => onChange(INDEX_DEPTH[Number(e.target.value)])}
        className="w-full h-1.5 rounded-full appearance-none cursor-pointer
          bg-gradient-to-r from-blue-200 via-blue-400 to-blue-600
          [&::-webkit-slider-thumb]:appearance-none
          [&::-webkit-slider-thumb]:w-4
          [&::-webkit-slider-thumb]:h-4
          [&::-webkit-slider-thumb]:rounded-full
          [&::-webkit-slider-thumb]:bg-blue-600
          [&::-webkit-slider-thumb]:shadow-md
          [&::-webkit-slider-thumb]:border-2
          [&::-webkit-slider-thumb]:border-white"
      />
      <div className="flex justify-between mt-1.5">
        {OPTIONS.map((o, i) => (
          <span
            key={o.value}
            className={`text-xs font-medium transition-colors ${
              depth === o.value ? 'text-blue-600 dark:text-blue-300' : 'text-gray-400'
            } ${i === 0 ? 'text-left' : i === OPTIONS.length - 1 ? 'text-right' : 'text-center'} w-1/3`}
          >
            {o.label}
          </span>
        ))}
      </div>
      <p className="text-xs text-gray-400 dark:text-gray-400 text-center mt-1">
        {OPTIONS.find((o) => o.value === depth)?.description}
      </p>
    </div>
  );
}
