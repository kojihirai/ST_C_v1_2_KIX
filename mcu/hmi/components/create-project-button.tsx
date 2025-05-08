"use client"

import { Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import Link from "next/link"

export function CreateProjectButton() {
  return (
    <Button asChild>
      <Link href="/projects/new">
        <Plus className="mr-2 h-4 w-4" /> Create Project
      </Link>
    </Button>
  )
}
