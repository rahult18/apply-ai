"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Search, ChevronLeft, ChevronRight } from "lucide-react"
import { JobCard } from "@/components/widgets/JobCard"
import { JobFilters } from "@/components/widgets/JobFilters"
import { fetchJobs } from "@/lib/api/jobs"
import { DiscoveredJob, JobFilters as JobFiltersType } from "@/types/jobs"

const PAGE_SIZE = 20
const DEBOUNCE_MS = 400

function JobCardSkeleton() {
  return (
    <Card>
      <CardContent className="p-5 space-y-3">
        <div className="flex justify-between">
          <Skeleton className="h-5 w-16" />
          <Skeleton className="h-4 w-20" />
        </div>
        <Skeleton className="h-5 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-2/3" />
        <div className="flex justify-end pt-2">
          <Skeleton className="h-8 w-20" />
        </div>
      </CardContent>
    </Card>
  )
}

function EmptyState({ hasFilters, onClear }: { hasFilters: boolean; onClear: () => void }) {
  return (
    <Card className="border-dashed">
      <CardContent className="flex flex-col items-center justify-center py-16 text-center">
        <div className="rounded-full bg-muted p-4 mb-4">
          <Search className="h-8 w-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold mb-2">
          {hasFilters ? "No jobs match your filters" : "No jobs found"}
        </h3>
        <p className="text-muted-foreground max-w-sm">
          {hasFilters
            ? "Try adjusting your search criteria or clearing filters."
            : "Check back later for new job listings."}
        </p>
        {hasFilters && (
          <Button variant="outline" className="mt-4" onClick={onClear}>
            Clear Filters
          </Button>
        )}
      </CardContent>
    </Card>
  )
}

export default function DiscoverPage() {
  // UI state for inputs (updates immediately for responsive typing)
  const [filters, setFilters] = useState<JobFiltersType>({
    keyword: "",
    provider: "all",
    remote: "any",
    location: "",
  })
  // Debounced filters that trigger API calls
  const [debouncedFilters, setDebouncedFilters] = useState<JobFiltersType>(filters)
  const [jobs, setJobs] = useState<DiscoveredJob[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const debounceRef = useRef<NodeJS.Timeout | null>(null)

  const hasFilters =
    filters.keyword !== "" ||
    filters.provider !== "all" ||
    filters.remote !== "any" ||
    filters.location !== ""

  const totalPages = Math.ceil(totalCount / PAGE_SIZE)

  // Debounce text inputs, apply dropdown changes immediately
  useEffect(() => {
    // Check if only text fields changed
    const textFieldsChanged =
      filters.keyword !== debouncedFilters.keyword ||
      filters.location !== debouncedFilters.location
    const dropdownsChanged =
      filters.provider !== debouncedFilters.provider ||
      filters.remote !== debouncedFilters.remote

    if (dropdownsChanged) {
      // Apply dropdown changes immediately
      if (debounceRef.current) {
        clearTimeout(debounceRef.current)
      }
      setDebouncedFilters(filters)
      setCurrentPage(1)
    } else if (textFieldsChanged) {
      // Debounce text field changes
      if (debounceRef.current) {
        clearTimeout(debounceRef.current)
      }
      debounceRef.current = setTimeout(() => {
        setDebouncedFilters(filters)
        setCurrentPage(1)
      }, DEBOUNCE_MS)
    }

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current)
      }
    }
  }, [filters, debouncedFilters])

  const loadJobs = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const params: Parameters<typeof fetchJobs>[0] = {
        limit: PAGE_SIZE,
        offset: (currentPage - 1) * PAGE_SIZE,
      }

      if (debouncedFilters.keyword) {
        params.keyword = debouncedFilters.keyword
      }
      if (debouncedFilters.provider !== "all") {
        params.provider = debouncedFilters.provider
      }
      if (debouncedFilters.remote === "remote") {
        params.remote = true
      } else if (debouncedFilters.remote === "onsite") {
        params.remote = false
      }
      if (debouncedFilters.location) {
        params.location = debouncedFilters.location
      }

      const response = await fetchJobs(params)
      setJobs(response.jobs)
      setTotalCount(response.total_count)
    } catch (err) {
      console.error("Failed to fetch jobs:", err)
      setError("Failed to load jobs. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }, [debouncedFilters, currentPage])

  // Load jobs when debounced filters or page changes
  useEffect(() => {
    loadJobs()
  }, [loadJobs])

  // Update UI filters immediately (no page reset here - debounce handles it)
  const handleFiltersChange = (newFilters: JobFiltersType) => {
    setFilters(newFilters)
  }

  const handleClearFilters = () => {
    const clearedFilters = {
      keyword: "",
      provider: "all" as const,
      remote: "any" as const,
      location: "",
    }
    setFilters(clearedFilters)
    setDebouncedFilters(clearedFilters)
    setCurrentPage(1)
  }

  const handlePreviousPage = () => {
    setCurrentPage((prev) => Math.max(1, prev - 1))
  }

  const handleNextPage = () => {
    setCurrentPage((prev) => Math.min(totalPages, prev + 1))
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold mb-1">Discover Jobs</h1>
        <p className="text-muted-foreground">
          Browse and search jobs from top companies
        </p>
      </div>

      {/* Filters */}
      <JobFilters
        filters={filters}
        onFiltersChange={handleFiltersChange}
        isLoading={isLoading}
      />

      {/* Results count */}
      {!isLoading && !error && (
        <div className="text-sm text-muted-foreground">
          {totalCount === 0
            ? "No jobs found"
            : `Showing ${(currentPage - 1) * PAGE_SIZE + 1}-${Math.min(
                currentPage * PAGE_SIZE,
                totalCount
              )} of ${totalCount.toLocaleString()} jobs`}
        </div>
      )}

      {/* Error state */}
      {error && (
        <Card className="border-destructive">
          <CardContent className="flex flex-col items-center justify-center py-8 text-center">
            <p className="text-destructive mb-4">{error}</p>
            <Button onClick={loadJobs}>Try Again</Button>
          </CardContent>
        </Card>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <JobCardSkeleton key={i} />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !error && jobs.length === 0 && (
        <EmptyState hasFilters={hasFilters} onClear={handleClearFilters} />
      )}

      {/* Jobs grid */}
      {!isLoading && !error && jobs.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {jobs.map((job) => (
            <JobCard key={job.id} job={job} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {!isLoading && !error && totalPages > 1 && (
        <div className="flex items-center justify-center gap-4 pt-4">
          <Button
            variant="outline"
            size="sm"
            onClick={handlePreviousPage}
            disabled={currentPage === 1}
          >
            <ChevronLeft className="h-4 w-4 mr-1" />
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {currentPage} of {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={handleNextPage}
            disabled={currentPage === totalPages}
          >
            Next
            <ChevronRight className="h-4 w-4 ml-1" />
          </Button>
        </div>
      )}
    </div>
  )
}
