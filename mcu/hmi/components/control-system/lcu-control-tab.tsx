import { ArrowUp, ArrowDown } from 'lucide-react'
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { useEffect } from "react"
import { LcuDirection } from "@/lib/constants"

// Input range configurations
const INPUT_RANGES = {
  speed: {
    min: 0,
    max: 8,
    step: 0.01,
    label: "Speed Target (mm/s)"
  }
} as const

interface LcuControlTabProps {
  lcuDirection: LcuDirection
  setLcuDirection: (direction: LcuDirection) => void
  lcuTarget: number
  setLcuTarget: (target: number) => void
  executeLcuCommand: () => void
  executeOnChange?: boolean
  isReadOnly?: boolean
  projectDirection?: string
}

export default function LcuControlTab({
  lcuDirection,
  setLcuDirection,
  lcuTarget,
  setLcuTarget,
  executeLcuCommand,
  executeOnChange = false,
  isReadOnly = false,
  projectDirection
}: LcuControlTabProps) {
  // Set forward as default direction when component mounts
  useEffect(() => {
    if (!isReadOnly) {
      setLcuDirection(LcuDirection.fw);
    }
  }, [setLcuDirection, isReadOnly]);

  // Convert string direction to enum if needed
  const getProjectDirectionEnum = () => {
    if (typeof projectDirection === 'string') {
      if (projectDirection === 'fw') return LcuDirection.fw;
      if (projectDirection === 'bw') return LcuDirection.bw;
    }
    return projectDirection;
  };

  const projectDirectionEnum = getProjectDirectionEnum();

  // Handle direction change with optional command execution
  const handleDirectionChange = (newDirection: LcuDirection) => {
    if (!isReadOnly) {
      setLcuDirection(newDirection);
      // Only execute command if executeOnChange is true
      if (executeOnChange) {
        executeLcuCommand();
      }
    }
  };

  // Handle target change with optional command execution
  const handleTargetChange = (newTarget: number) => {
    if (!isReadOnly) {
      setLcuTarget(newTarget);
      // Only execute command if executeOnChange is true
      if (executeOnChange) {
        executeLcuCommand();
      }
    }
  };

  return (
    <div className="space-y-3">
      {/* Direction Selection */}
      <div>
        <Label className="text-xs mb-1 block">Direction</Label>
        <div className="grid grid-cols-2 gap-2">
          <Button
            variant={isReadOnly ? (projectDirectionEnum === LcuDirection.fw ? "default" : "outline") : (lcuDirection === LcuDirection.fw ? "default" : "outline")}
            onClick={() => handleDirectionChange(LcuDirection.fw)}
            className="flex items-center justify-center gap-1 py-1.5 h-9 text-xs"
            disabled={isReadOnly}
          >
            Forward
            <ArrowUp className="w-3 h-3" />
          </Button>
          <Button
            variant={isReadOnly ? (projectDirectionEnum === LcuDirection.bw ? "default" : "outline") : (lcuDirection === LcuDirection.bw ? "default" : "outline")}
            onClick={() => handleDirectionChange(LcuDirection.bw)}
            className="flex items-center justify-center gap-1 py-1.5 h-9 text-xs"
            disabled={isReadOnly}
          >
            Backward
            <ArrowDown className="w-3 h-3" />
          </Button>
        </div>
      </div>

      {/* Target Value */}
      <div>
        <Label className="text-xs mb-1 block">{INPUT_RANGES.speed.label}</Label>
        <div className="flex items-center gap-2">
          <Slider
            value={[lcuTarget]}
            min={INPUT_RANGES.speed.min}
            max={INPUT_RANGES.speed.max}
            step={INPUT_RANGES.speed.step}
            onValueChange={(value) => handleTargetChange(value[0])}
            className="h-5"
            disabled={isReadOnly}
          />
          <Input
            type="number"
            value={lcuTarget}
            min={INPUT_RANGES.speed.min}
            max={INPUT_RANGES.speed.max}
            step={INPUT_RANGES.speed.step}
            onChange={(e) => handleTargetChange(Number.parseFloat(e.target.value))}
            className="w-20 h-8 text-xs"
            disabled={isReadOnly}
          />
        </div>
      </div>
    </div>
  )
}
