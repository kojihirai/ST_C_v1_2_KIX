"use client"

import { Label } from "@/components/ui/label"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"

/*interface ModeSelectorProps {
  mode: "manual" | "experiment" | "program"
  setMode: (mode: "manual" | "experiment" | "program") => void
}*/
interface ModeSelectorProps {
  mode: "manual" | "experiment"
  setMode: (mode: "manual" | "experiment") => void
}

export default function ModeSelector({ mode, setMode }: ModeSelectorProps) {
  return (
    <div>
      <Label className="text-sm mb-2 block">Mode</Label>
      <Tabs value={mode} onValueChange={(value) => setMode(value as "manual" | "experiment")}>
        <TabsList className="grid grid-cols-2 h-10">
          <TabsTrigger value="manual" className="text-sm py-2">
            Manual
          </TabsTrigger>
          <TabsTrigger value="experiment" className="text-sm py-2">
            Experiment
          </TabsTrigger>
          {/* Program mode temporarily disabled - will be re-enabled later
          <TabsTrigger value="program" className="text-sm py-2">
            Program
          </TabsTrigger>
          */}
        </TabsList>
      </Tabs>
    </div>
  )
}

