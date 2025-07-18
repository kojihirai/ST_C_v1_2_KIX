import { Pause, Play } from 'lucide-react'
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { useEffect } from "react"
import { DcuDirection } from "@/lib/constants"

interface DcuControlTabProps {
  dcuDirection: DcuDirection
  setDcuDirection: (direction: DcuDirection) => void
  executeDcuCommand: () => void
  executeOnChange?: boolean
  isReadOnly?: boolean
  projectDirection?: DcuDirection
}

export default function DcuControlTab({
  dcuDirection,
  setDcuDirection,
  executeDcuCommand,
  executeOnChange = false,
  isReadOnly = false,
  projectDirection
}: DcuControlTabProps) {
  // Set OFF as default direction
  useEffect(() => {
    if (!isReadOnly) {
      setDcuDirection(DcuDirection.off);
    }
  }, [setDcuDirection, isReadOnly]);

  // Convert string direction to enum if needed
  const getProjectDirectionEnum = () => {
    if (typeof projectDirection === 'string') {
      if (projectDirection === 'on') return DcuDirection.on;
      if (projectDirection === 'off') return DcuDirection.off;
    }
    return projectDirection;
  };

  const projectDirectionEnum = getProjectDirectionEnum();

  // Handle direction change with optional command execution
  const handleDirectionChange = (newDirection: DcuDirection) => {
    if (!isReadOnly) {
      setDcuDirection(newDirection);
      // Only execute command if executeOnChange is true
      if (executeOnChange) {
        executeDcuCommand();
      }
    }
  };

  return (
    <div className="space-y-3">
      {/* Contactor Control */}
      <div>
        <Label className="text-xs mb-1 block">Contactor Control</Label>
        <div className="grid grid-cols-2 gap-2">
          <Button
            variant={isReadOnly ? (projectDirectionEnum === DcuDirection.on ? "default" : "outline") : (dcuDirection === DcuDirection.on ? "default" : "outline")}
            onClick={() => handleDirectionChange(DcuDirection.on)}
            className="flex items-center justify-center gap-1 py-1.5 h-9 text-xs"
            disabled={isReadOnly}
          >
            <Play className="w-3 h-3" />
            ON
          </Button>
          <Button
            variant={isReadOnly ? (projectDirectionEnum === DcuDirection.off ? "default" : "outline") : (dcuDirection === DcuDirection.off ? "default" : "outline")}
            onClick={() => handleDirectionChange(DcuDirection.off)}
            className="flex items-center justify-center gap-1 py-1.5 h-9 text-xs"
            disabled={isReadOnly}
          >
            <Pause className="w-3 h-3" />
            OFF
          </Button>
        </div>
      </div>

      {/* Status Display */}
      <div className="text-xs text-muted-foreground">
        <p>Current State: {dcuDirection === DcuDirection.on ? 'ON' : 'OFF'}</p>
      </div>
    </div>
  )
}
