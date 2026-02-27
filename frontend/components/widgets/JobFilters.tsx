"use client"

import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Search, X } from "lucide-react"
import { JobFilters as JobFiltersType } from "@/types/jobs"

interface JobFiltersProps {
  filters: JobFiltersType
  onFiltersChange: (filters: JobFiltersType) => void
  isLoading?: boolean
}

export function JobFilters({ filters, onFiltersChange, isLoading }: JobFiltersProps) {
  const hasActiveFilters =
    filters.keyword !== "" ||
    filters.provider !== "all" ||
    filters.remote !== "any" ||
    filters.location !== ""

  const handleClearFilters = () => {
    onFiltersChange({
      keyword: "",
      provider: "all",
      remote: "any",
      location: "",
    })
  }

  return (
    <div className="space-y-4">
      {/* Search input */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search jobs by title, company, or keyword..."
          value={filters.keyword}
          onChange={(e) => onFiltersChange({ ...filters, keyword: e.target.value })}
          className="pl-9"
          disabled={isLoading}
        />
      </div>

      {/* Filter row */}
      <div className="flex flex-wrap gap-3 items-center">
        {/* Provider filter */}
        <Select
          value={filters.provider}
          onValueChange={(value) =>
            onFiltersChange({ ...filters, provider: value as JobFiltersType["provider"] })
          }
          disabled={isLoading}
        >
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="Provider" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Providers</SelectItem>
            <SelectItem value="ashby">Ashby</SelectItem>
            <SelectItem value="lever">Lever</SelectItem>
            <SelectItem value="greenhouse">Greenhouse</SelectItem>
          </SelectContent>
        </Select>

        {/* Remote filter */}
        <Select
          value={filters.remote}
          onValueChange={(value) =>
            onFiltersChange({ ...filters, remote: value as JobFiltersType["remote"] })
          }
          disabled={isLoading}
        >
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="Remote" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="any">Any</SelectItem>
            <SelectItem value="remote">Remote Only</SelectItem>
            <SelectItem value="onsite">On-site Only</SelectItem>
          </SelectContent>
        </Select>

        {/* Location filter */}
        <Input
          placeholder="Location..."
          value={filters.location}
          onChange={(e) => onFiltersChange({ ...filters, location: e.target.value })}
          className="w-[160px]"
          disabled={isLoading}
        />

        {/* Clear filters */}
        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClearFilters}
            disabled={isLoading}
            className="text-muted-foreground"
          >
            <X className="h-4 w-4 mr-1" />
            Clear
          </Button>
        )}
      </div>
    </div>
  )
}
