import { ProjectList } from "@/components/project-list"
import { CreateProjectButton } from "@/components/create-project-button"

export default function Home() {
  return (
    <div className="container mx-auto py-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold">Projects</h1>
        <CreateProjectButton />
      </div>
      <ProjectList />
    </div>
  )
}
