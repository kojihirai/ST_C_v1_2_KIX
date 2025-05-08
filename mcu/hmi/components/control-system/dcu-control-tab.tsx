import { RotateCw } from 'lucide-react'
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { useEffect } from "react"
import { DcuDirection } from "@/lib/constants"

// Input range configurations
const INPUT_RANGES = {
  speed: {
    min: 0,
    max: 24,
    step: 0.1,
    label: "Effective Voltage (V)"
  }
} as const

interface DcuControlTabProps {
  dcuDirection: DcuDirection
  setDcuDirection: (direction: DcuDirection) => void
  dcuTarget: number
  setDcuTarget: (target: number) => void
  executeDcuCommand: () => void
  executeOnChange?: boolean
  isReadOnly?: boolean
  projectDirection?: DcuDirection
}

export default function DcuControlTab({
  dcuDirection,
  setDcuDirection,
  dcuTarget,
  setDcuTarget,
  executeDcuCommand,
  executeOnChange = false,
  isReadOnly = false,
  projectDirection
}: DcuControlTabProps) {
  // Set CW as default direction
  useEffect(() => {
    if (!isReadOnly) {
      setDcuDirection(DcuDirection.cw);
    }
  }, [setDcuDirection, isReadOnly]);

  // Execute command when values change if executeOnChange is true and not in idle mode
  useEffect(() => {
    if (executeOnChange && !isReadOnly) {
      executeDcuCommand()
    }
  }, [dcuTarget, dcuDirection, executeOnChange, executeDcuCommand, isReadOnly])

  // Convert string direction to enum if needed
  const getProjectDirectionEnum = () => {
    if (typeof projectDirection === 'string') {
      if (projectDirection === 'cw') return DcuDirection.cw;
      if (projectDirection === 'ccw') return DcuDirection.ccw;
    }
    return projectDirection;
  };

  const projectDirectionEnum = getProjectDirectionEnum();

  return (
    <div className="space-y-3">
      {/* Direction Selection */}
      <div>
        <Label className="text-xs mb-1 block">Direction</Label>
        <div className="grid grid-cols-2 gap-2">
          <Button
            variant={isReadOnly ? (projectDirectionEnum === DcuDirection.cw ? "default" : "outline") : (dcuDirection === DcuDirection.cw ? "default" : "outline")}
            onClick={() => !isReadOnly && setDcuDirection(DcuDirection.cw)}
            className="flex items-center justify-center gap-1 py-1.5 h-9 text-xs"
            disabled={isReadOnly}
          >
            Clockwise
            <RotateCw className="w-3 h-3" />
          </Button>
          <Button
            variant={isReadOnly ? (projectDirectionEnum === DcuDirection.ccw ? "default" : "outline") : (dcuDirection === DcuDirection.ccw ? "default" : "outline")}
            onClick={() => !isReadOnly && setDcuDirection(DcuDirection.ccw)}
            className="flex items-center justify-center gap-1 py-1.5 h-9 text-xs"
            disabled={isReadOnly}
          >
            Counter-CW
            <RotateCw className="w-3 h-3 -scale-x-100" />
          </Button>
        </div>
      </div>

      {/* Target Value */}
      <div>
        <Label className="text-xs mb-1 block">{INPUT_RANGES.speed.label}</Label>
        <div className="flex items-center gap-2">
          <Slider
            value={[dcuTarget]}
            min={INPUT_RANGES.speed.min}
            max={INPUT_RANGES.speed.max}
            step={INPUT_RANGES.speed.step}
            onValueChange={(value) => !isReadOnly && setDcuTarget(value[0])}
            className="h-5"
            disabled={isReadOnly}
          />
          <Input
            type="number"
            value={dcuTarget}
            min={INPUT_RANGES.speed.min}
            max={INPUT_RANGES.speed.max}
            step={INPUT_RANGES.speed.step}
            onChange={(e) => !isReadOnly && setDcuTarget(Number.parseFloat(e.target.value))}
            className="w-20 h-8 text-xs"
            disabled={isReadOnly}
          />
        </div>
      </div>
    </div>
  )
}
