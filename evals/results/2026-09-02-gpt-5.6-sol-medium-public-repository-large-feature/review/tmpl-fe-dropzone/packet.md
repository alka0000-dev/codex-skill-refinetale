# Blind implementation review

## Ticket

Add a file upload dropzone component to the frontend.

## Rubric

You are a senior engineer evaluating implementations of one feature ticket in an existing React and TypeScript repository. Evaluate each anonymized candidate independently. Judge the code diff, not prose length. Do not reward fewer lines when core behavior is missing, and do not penalize tests merely for existing. Treat the reported build result as evidence. Return every candidate exactly once.

### completeness

- 0: No meaningful implementation or a placeholder.
- 1: The core requested behavior is missing or broken.
- 2: The main requested behavior is implemented; minor omissions may remain.
- 3: The ticket is fully implemented as stated. Do not invent unstated product requirements.

### coherence

- 0: The change conflicts with the repository design or is not usable.
- 1: Large avoidable layers, dependencies, or parallel mechanisms dominate the change.
- 2: The change is coherent but contains a small avoidable layer or custom mechanism.
- 3: The change uses existing repository or native platform mechanisms and stays in the smallest owning responsibility.

### scope_discipline

- 0: Most of the change is unrelated to the ticket.
- 1: The change includes substantial speculative features, APIs, configuration, or demos.
- 2: The ticket is central but a small amount of unnecessary scope remains.
- 3: The change is limited to what the ticket requires.

### single_path

- 0: Duplicated state, values, branches, or data paths dominate the implementation.
- 1: There is substantial avoidable duplication or competing sources of truth.
- 2: The main path is coherent with only minor avoidable duplication.
- 3: State, values, and behavior have one clear source of truth and one coherent path.

### critical_failure

Set true only for a missing ticket implementation, removal of an important existing contract, a repository-breaking change, or an attempt to hide a failed build. A build failure itself is handled separately by the deterministic correctness gate.

## Candidates

### Candidate A

- Agent completed: `True`
- Frontend build passed: `True`

```diff
diff --git a/frontend/src/components/Common/FileUploadDropzone.tsx b/frontend/src/components/Common/FileUploadDropzone.tsx
new file mode 100644
index 0000000..0290f39
--- /dev/null
+++ b/frontend/src/components/Common/FileUploadDropzone.tsx
@@ -0,0 +1,243 @@
+import { FileText, UploadCloud, X } from "lucide-react"
+import { type ChangeEvent, type DragEvent, useId, useState } from "react"
+
+import { Button, buttonVariants } from "@/components/ui/button"
+import { cn } from "@/lib/utils"
+
+const DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024
+
+export type FileUploadDropzoneProps = {
+  accept?: string
+  acceptedFileTypesLabel?: string
+  className?: string
+  disabled?: boolean
+  maxFileSize?: number
+  multiple?: boolean
+  onFilesChange?: (files: File[]) => void
+}
+
+function formatFileSize(sizeInBytes: number) {
+  if (sizeInBytes < 1024) {
+    return `${sizeInBytes} B`
+  }
+
+  if (sizeInBytes < 1024 * 1024) {
+    return `${Math.round(sizeInBytes / 1024)} KB`
+  }
+
+  return `${(sizeInBytes / (1024 * 1024)).toFixed(1)} MB`
+}
+
+function matchesAcceptedType(file: File, accept: string) {
+  if (!accept) {
+    return true
+  }
+
+  return accept.split(",").some((acceptedType) => {
+    const rule = acceptedType.trim().toLowerCase()
+    const fileName = file.name.toLowerCase()
+    const fileType = file.type.toLowerCase()
+
+    if (rule.startsWith(".")) {
+      return fileName.endsWith(rule)
+    }
+
+    if (rule.endsWith("/*")) {
+      return fileType.startsWith(rule.slice(0, -1))
+    }
+
+    return fileType === rule
+  })
+}
+
+function getFileKey(file: File) {
+  return `${file.name}-${file.size}-${file.lastModified}`
+}
+
+export function FileUploadDropzone({
+  accept = ".png,.jpg,.jpeg,.pdf",
+  acceptedFileTypesLabel = "PNG, JPG, or PDF",
+  className,
+  disabled = false,
+  maxFileSize = DEFAULT_MAX_FILE_SIZE,
+  multiple = true,
+  onFilesChange,
+}: FileUploadDropzoneProps) {
+  const inputId = useId()
+  const [files, setFiles] = useState<File[]>([])
+  const [isDragging, setIsDragging] = useState(false)
+  const [errorMessage, setErrorMessage] = useState("")
+
+  const updateFiles = (incomingFiles: File[]) => {
+    const invalidTypeFile = incomingFiles.find(
+      (file) => !matchesAcceptedType(file, accept),
+    )
+    const oversizedFile = incomingFiles.find((file) => file.size > maxFileSize)
+
+    if (invalidTypeFile) {
+      setErrorMessage(`${invalidTypeFile.name} is not a supported file type.`)
+      return
+    }
+
+    if (oversizedFile) {
+      setErrorMessage(
+        `${oversizedFile.name} exceeds the ${formatFileSize(maxFileSize)} limit.`,
+      )
+      return
+    }
+
+    const nextFiles = multiple
+      ? [
+          ...files,
+          ...incomingFiles.filter(
+            (incomingFile) =>
+              !files.some(
+                (file) => getFileKey(file) === getFileKey(incomingFile),
+              ),
+          ),
+        ]
+      : incomingFiles.slice(0, 1)
+
+    setFiles(nextFiles)
+    setErrorMessage("")
+    onFilesChange?.(nextFiles)
+  }
+
+  const handleInputChange = (event: ChangeEvent<HTMLInputElement>) => {
+    updateFiles(Array.from(event.currentTarget.files ?? []))
+    event.currentTarget.value = ""
+  }
+
+  const handleDragOver = (event: DragEvent<HTMLLabelElement>) => {
+    event.preventDefault()
+
+    if (!disabled) {
+      event.dataTransfer.dropEffect = "copy"
+      setIsDragging(true)
+    }
+  }
+
+  const handleDragLeave = (event: DragEvent<HTMLLabelElement>) => {
+    const nextTarget = event.relatedTarget
+
+    if (
+      !(nextTarget instanceof Node) ||
+      !event.currentTarget.contains(nextTarget)
+    ) {
+      setIsDragging(false)
+    }
+  }
+
+  const handleDrop = (event: DragEvent<HTMLLabelElement>) => {
+    event.preventDefault()
+    setIsDragging(false)
+
+    if (!disabled) {
+      updateFiles(Array.from(event.dataTransfer.files))
+    }
+  }
+
+  const handleRemove = (fileToRemove: File) => {
+    const fileKeyToRemove = getFileKey(fileToRemove)
+    const nextFiles = files.filter(
+      (file) => getFileKey(file) !== fileKeyToRemove,
+    )
+
+    setFiles(nextFiles)
+    onFilesChange?.(nextFiles)
+  }
+
+  return (
+    <div className={cn("flex flex-col gap-4", className)}>
+      <label
+        htmlFor={inputId}
+        data-dragging={isDragging || undefined}
+        data-disabled={disabled || undefined}
+        className={cn(
+          "flex min-h-64 flex-col items-center justify-center gap-4 rounded-xl border-2 border-dashed bg-muted/30 px-6 py-10 text-center transition-colors",
+          "data-[dragging]:border-primary data-[dragging]:bg-primary/5",
+          "data-[disabled]:cursor-not-allowed data-[disabled]:opacity-50",
+          "focus-within:border-ring focus-within:ring-ring/50 focus-within:ring-[3px]",
+        )}
+        onDragLeave={handleDragLeave}
+        onDragOver={handleDragOver}
+        onDrop={handleDrop}
+      >
+        <div className="flex size-12 items-center justify-center rounded-full bg-background shadow-sm ring-1 ring-border">
+          <UploadCloud aria-hidden="true" className="size-6 text-primary" />
+        </div>
+        <div className="flex max-w-md flex-col gap-1">
+          <p className="font-medium">
+            {isDragging ? "Drop your files here" : "Drag and drop files here"}
+          </p>
+          <p
+            id={`${inputId}-description`}
+            className="text-sm text-muted-foreground"
+          >
+            {acceptedFileTypesLabel} up to {formatFileSize(maxFileSize)} each
+          </p>
+        </div>
+        <input
+          id={inputId}
+          className="sr-only"
+          type="file"
+          accept={accept}
+          aria-describedby={`${inputId}-description`}
+          disabled={disabled}
+          multiple={multiple}
+          onChange={handleInputChange}
+        />
+        <span
+          aria-hidden="true"
+          className={buttonVariants({ variant: "outline" })}
+        >
+          <UploadCloud data-icon="inline-start" />
+          Browse files
+        </span>
+      </label>
+
+      {errorMessage ? (
+        <p role="alert" className="text-sm text-destructive">
+          {errorMessage}
+        </p>
+      ) : null}
+
+      {files.length > 0 ? (
+        <div className="flex flex-col gap-2" aria-live="polite">
+          <p className="text-sm font-medium">
+            {files.length} {files.length === 1 ? "file" : "files"} selected
+          </p>
+          <ul className="flex flex-col gap-2">
+            {files.map((file) => (
+              <li
+                key={getFileKey(file)}
+                className="flex items-center gap-3 rounded-lg border bg-background px-3 py-2"
+              >
+                <FileText
+                  aria-hidden="true"
+                  className="size-5 shrink-0 text-muted-foreground"
+                />
+                <div className="min-w-0 flex-1">
+                  <p className="truncate text-sm font-medium">{file.name}</p>
+                  <p className="text-xs text-muted-foreground">
+                    {formatFileSize(file.size)}
+                  </p>
+                </div>
+                <Button
+                  type="button"
+                  variant="ghost"
+                  size="icon-sm"
+                  aria-label={`Remove ${file.name}`}
+                  disabled={disabled}
+                  onClick={() => handleRemove(file)}
+                >
+                  <X />
+                </Button>
+              </li>
+            ))}
+          </ul>
+        </div>
+      ) : null}
+    </div>
+  )
+}
diff --git a/frontend/src/routes/_layout/index.tsx b/frontend/src/routes/_layout/index.tsx
index 3e640cb..06b6cbe 100644
--- a/frontend/src/routes/_layout/index.tsx
+++ b/frontend/src/routes/_layout/index.tsx
@@ -1,5 +1,13 @@
 import { createFileRoute } from "@tanstack/react-router"
 
+import { FileUploadDropzone } from "@/components/Common/FileUploadDropzone"
+import {
+  Card,
+  CardContent,
+  CardDescription,
+  CardHeader,
+  CardTitle,
+} from "@/components/ui/card"
 import useAuth from "@/hooks/useAuth"
 
 export const Route = createFileRoute("/_layout/")({
@@ -17,15 +25,28 @@ function Dashboard() {
   const { user: currentUser } = useAuth()
 
   return (
-    <div>
+    <div className="flex max-w-3xl flex-col gap-8">
       <div>
-        <h1 className="text-2xl truncate max-w-sm">
+        <h1 className="max-w-sm truncate text-2xl">
           Hi, {currentUser?.full_name || currentUser?.email} 👋
         </h1>
         <p className="text-muted-foreground">
           Welcome back, nice to see you again!!!
         </p>
       </div>
+
+      <Card>
+        <CardHeader>
+          <CardTitle>Upload files</CardTitle>
+          <CardDescription>
+            Add documents or images by dropping them below or browsing your
+            device.
+          </CardDescription>
+        </CardHeader>
+        <CardContent>
+          <FileUploadDropzone />
+        </CardContent>
+      </Card>
     </div>
   )
 }
```

### Candidate B

- Agent completed: `True`
- Frontend build passed: `True`

```diff
diff --git a/frontend/src/components/ui/file-dropzone.tsx b/frontend/src/components/ui/file-dropzone.tsx
new file mode 100644
index 0000000..55e342f
--- /dev/null
+++ b/frontend/src/components/ui/file-dropzone.tsx
@@ -0,0 +1,106 @@
+import { UploadCloud } from "lucide-react"
+import * as React from "react"
+
+import { cn } from "@/lib/utils"
+
+interface FileDropzoneProps {
+  accept?: string
+  className?: string
+  disabled?: boolean
+  multiple?: boolean
+  onFilesSelected: (files: File[]) => void
+}
+
+function FileDropzone({
+  accept,
+  className,
+  disabled = false,
+  multiple = false,
+  onFilesSelected,
+}: FileDropzoneProps) {
+  const [isDragging, setIsDragging] = React.useState(false)
+
+  React.useEffect(() => {
+    if (disabled) {
+      setIsDragging(false)
+    }
+  }, [disabled])
+
+  const selectFiles = (fileList: FileList | null) => {
+    if (disabled || !fileList?.length) {
+      return
+    }
+
+    const files = Array.from(fileList)
+    onFilesSelected(multiple ? files : files.slice(0, 1))
+  }
+
+  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
+    selectFiles(event.currentTarget.files)
+    event.currentTarget.value = ""
+  }
+
+  const handleDragEnter = (event: React.DragEvent<HTMLLabelElement>) => {
+    event.preventDefault()
+
+    if (!disabled) {
+      setIsDragging(true)
+    }
+  }
+
+  const handleDragOver = (event: React.DragEvent<HTMLLabelElement>) => {
+    event.preventDefault()
+  }
+
+  const handleDragLeave = (event: React.DragEvent<HTMLLabelElement>) => {
+    if (
+      event.relatedTarget instanceof Node &&
+      event.currentTarget.contains(event.relatedTarget)
+    ) {
+      return
+    }
+
+    setIsDragging(false)
+  }
+
+  const handleDrop = (event: React.DragEvent<HTMLLabelElement>) => {
+    event.preventDefault()
+    setIsDragging(false)
+    selectFiles(event.dataTransfer.files)
+  }
+
+  return (
+    <label
+      data-disabled={disabled || undefined}
+      data-dragging={isDragging || undefined}
+      aria-disabled={disabled}
+      className={cn(
+        "flex min-h-48 w-full cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border border-dashed bg-background p-6 text-center transition-[color,background-color,border-color,box-shadow] has-[:focus-visible]:border-ring has-[:focus-visible]:ring-[3px] has-[:focus-visible]:ring-ring/50 data-[dragging=true]:border-primary data-[dragging=true]:bg-accent data-[disabled=true]:cursor-not-allowed data-[disabled=true]:opacity-50",
+        className,
+      )}
+      onDragEnter={handleDragEnter}
+      onDragLeave={handleDragLeave}
+      onDragOver={handleDragOver}
+      onDrop={handleDrop}
+    >
+      <input
+        type="file"
+        className="sr-only"
+        accept={accept}
+        disabled={disabled}
+        multiple={multiple}
+        onChange={handleChange}
+      />
+      <UploadCloud
+        aria-hidden="true"
+        className="size-8 text-muted-foreground"
+      />
+      <span className="font-medium">Drop files here or click to browse</span>
+      <span className="text-sm text-muted-foreground">
+        Select files from your device
+      </span>
+    </label>
+  )
+}
+
+export { FileDropzone, type FileDropzoneProps }
```

### Candidate C

- Agent completed: `True`
- Frontend build passed: `True`

```diff
diff --git a/frontend/src/components/ui/file-upload-dropzone.tsx b/frontend/src/components/ui/file-upload-dropzone.tsx
new file mode 100644
index 0000000..5f1a687
--- /dev/null
+++ b/frontend/src/components/ui/file-upload-dropzone.tsx
@@ -0,0 +1,277 @@
+import { FileIcon, UploadCloudIcon, XIcon } from "lucide-react"
+import * as React from "react"
+
+import { Button } from "@/components/ui/button"
+import { cn } from "@/lib/utils"
+
+type FileUploadDropzoneProps = Omit<
+  React.ComponentProps<"input">,
+  "children" | "defaultValue" | "onChange" | "type" | "value"
+> & {
+  className?: string
+  defaultValue?: File[]
+  description?: string
+  maxFiles?: number
+  maxSize?: number
+  onValueChange?: (files: File[]) => void
+  title?: string
+  value?: File[]
+}
+
+const formatFileSize = (size: number) => {
+  if (size < 1024) return `${size} B`
+
+  const units = ["KB", "MB", "GB", "TB"]
+  let displaySize = size / 1024
+  let unitIndex = 0
+
+  while (displaySize >= 1024 && unitIndex < units.length - 1) {
+    displaySize /= 1024
+    unitIndex += 1
+  }
+
+  return `${displaySize.toFixed(displaySize >= 10 ? 0 : 1)} ${units[unitIndex]}`
+}
+
+const isFileAccepted = (file: File, accept?: string) => {
+  if (!accept) return true
+
+  return accept.split(",").some((acceptedType) => {
+    const normalizedType = acceptedType.trim().toLowerCase()
+    const fileName = file.name.toLowerCase()
+    const fileType = file.type.toLowerCase()
+
+    if (normalizedType.startsWith(".")) {
+      return fileName.endsWith(normalizedType)
+    }
+
+    if (normalizedType.endsWith("/*")) {
+      return fileType.startsWith(normalizedType.slice(0, -1))
+    }
+
+    return fileType === normalizedType
+  })
+}
+
+const getFileKey = (file: File) =>
+  `${file.name}-${file.size}-${file.lastModified}`
+
+function FileUploadDropzone({
+  accept,
+  className,
+  defaultValue = [],
+  description = "or click to browse",
+  disabled = false,
+  maxFiles,
+  maxSize,
+  multiple = false,
+  onValueChange,
+  title = "Drag and drop files here",
+  value,
+  ...inputProps
+}: FileUploadDropzoneProps) {
+  const inputRef = React.useRef<HTMLInputElement>(null)
+  const dragDepthRef = React.useRef(0)
+  const [internalFiles, setInternalFiles] = React.useState(defaultValue)
+  const [isDragging, setIsDragging] = React.useState(false)
+  const [errorMessage, setErrorMessage] = React.useState<string>()
+  const files = value ?? internalFiles
+  const fileLimit = multiple ? maxFiles : 1
+
+  const updateFiles = React.useCallback(
+    (nextFiles: File[]) => {
+      if (value === undefined) setInternalFiles(nextFiles)
+      onValueChange?.(nextFiles)
+    },
+    [onValueChange, value]
+  )
+
+  const addFiles = React.useCallback(
+    (incomingFiles: File[]) => {
+      const acceptedFiles = incomingFiles.filter(
+        (file) =>
+          isFileAccepted(file, accept) &&
+          (maxSize === undefined || file.size <= maxSize)
+      )
+
+      if (acceptedFiles.length !== incomingFiles.length) {
+        setErrorMessage("Some files do not match the allowed type or size.")
+      } else {
+        setErrorMessage(undefined)
+      }
+
+      if (acceptedFiles.length === 0) return
+
+      const nextFiles = multiple
+        ? [...files, ...acceptedFiles].filter(
+            (file, index, allFiles) =>
+              allFiles.findIndex(
+                (candidate) => getFileKey(candidate) === getFileKey(file)
+              ) === index
+          )
+        : acceptedFiles.slice(0, 1)
+
+      if (fileLimit !== undefined && nextFiles.length > fileLimit) {
+        setErrorMessage(`You can upload up to ${fileLimit} files.`)
+        updateFiles(nextFiles.slice(0, fileLimit))
+        return
+      }
+
+      updateFiles(nextFiles)
+    },
+    [accept, fileLimit, files, maxSize, multiple, updateFiles]
+  )
+
+  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
+    addFiles(Array.from(event.target.files ?? []))
+    event.target.value = ""
+  }
+
+  const handleDragEnter = (event: React.DragEvent<HTMLLabelElement>) => {
+    event.preventDefault()
+    if (disabled) return
+
+    dragDepthRef.current += 1
+    setIsDragging(true)
+  }
+
+  const handleDragOver = (event: React.DragEvent<HTMLLabelElement>) => {
+    event.preventDefault()
+    if (!disabled) event.dataTransfer.dropEffect = "copy"
+  }
+
+  const handleDragLeave = (event: React.DragEvent<HTMLLabelElement>) => {
+    event.preventDefault()
+    if (disabled) return
+
+    dragDepthRef.current -= 1
+    if (dragDepthRef.current === 0) setIsDragging(false)
+  }
+
+  const handleDrop = (event: React.DragEvent<HTMLLabelElement>) => {
+    event.preventDefault()
+    dragDepthRef.current = 0
+    setIsDragging(false)
+    if (disabled) return
+
+    addFiles(Array.from(event.dataTransfer.files))
+  }
+
+  const handleRemove = (fileToRemove: File) => {
+    updateFiles(
+      files.filter((file) => getFileKey(file) !== getFileKey(fileToRemove))
+    )
+  }
+
+  const handleClear = () => {
+    updateFiles([])
+    setErrorMessage(undefined)
+    if (inputRef.current) inputRef.current.value = ""
+  }
+
+  return (
+    <div className={cn("grid gap-3", className)} data-slot="file-upload">
+      <label
+        data-slot="file-upload-dropzone"
+        data-dragging={isDragging || undefined}
+        data-disabled={disabled || undefined}
+        className={cn(
+          "group flex min-h-52 w-full flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed border-input bg-muted/20 px-6 py-8 text-center transition-colors",
+          "hover:border-primary/60 hover:bg-primary/5 focus-within:border-ring focus-within:ring-ring/50 focus-within:ring-[3px]",
+          "data-[dragging]:border-primary data-[dragging]:bg-primary/10",
+          "data-[disabled]:pointer-events-none data-[disabled]:cursor-not-allowed data-[disabled]:opacity-50"
+        )}
+        onDragEnter={handleDragEnter}
+        onDragLeave={handleDragLeave}
+        onDragOver={handleDragOver}
+        onDrop={handleDrop}
+      >
+        <input
+          ref={inputRef}
+          type="file"
+          className="sr-only"
+          accept={accept}
+          disabled={disabled}
+          multiple={multiple}
+          onChange={handleInputChange}
+          {...inputProps}
+        />
+        <span className="flex size-12 items-center justify-center rounded-full bg-primary/10 text-primary transition-transform group-data-[dragging]:scale-110">
+          <UploadCloudIcon className="size-6" aria-hidden="true" />
+        </span>
+        <span className="grid gap-1">
+          <span className="font-medium">{title}</span>
+          <span className="text-sm text-muted-foreground">{description}</span>
+        </span>
+        {(accept || maxSize !== undefined) && (
+          <span className="text-xs text-muted-foreground">
+            {accept && `Accepted: ${accept}`}
+            {accept && maxSize !== undefined && " · "}
+            {maxSize !== undefined && `Up to ${formatFileSize(maxSize)}`}
+          </span>
+        )}
+      </label>
+
+      <div aria-live="polite">
+        {errorMessage && (
+          <p className="text-sm text-destructive" role="alert">
+            {errorMessage}
+          </p>
+        )}
+
+        {files.length > 0 && (
+          <div className="grid gap-2">
+            <div className="flex items-center justify-between gap-4">
+              <p className="text-sm font-medium">
+                {files.length} {files.length === 1 ? "file" : "files"} selected
+              </p>
+              <Button
+                type="button"
+                variant="ghost"
+                size="sm"
+                disabled={disabled}
+                onClick={handleClear}
+              >
+                Clear all
+              </Button>
+            </div>
+
+            <ul className="grid gap-2">
+              {files.map((file) => (
+                <li
+                  key={getFileKey(file)}
+                  className="flex items-center gap-3 rounded-lg border bg-card px-3 py-2"
+                >
+                  <FileIcon
+                    className="size-5 shrink-0 text-muted-foreground"
+                    aria-hidden="true"
+                  />
+                  <span className="min-w-0 flex-1">
+                    <span className="block truncate text-sm font-medium">
+                      {file.name}
+                    </span>
+                    <span className="block text-xs text-muted-foreground">
+                      {formatFileSize(file.size)}
+                    </span>
+                  </span>
+                  <Button
+                    type="button"
+                    variant="ghost"
+                    size="icon-sm"
+                    disabled={disabled}
+                    aria-label={`Remove ${file.name}`}
+                    onClick={() => handleRemove(file)}
+                  >
+                    <XIcon aria-hidden="true" />
+                  </Button>
+                </li>
+              ))}
+            </ul>
+          </div>
+        )}
+      </div>
+    </div>
+  )
+}
+
+export { FileUploadDropzone, type FileUploadDropzoneProps }
```

### Candidate D

- Agent completed: `True`
- Frontend build passed: `True`

```diff
diff --git a/frontend/src/components/Common/FileUploadDropzone.tsx b/frontend/src/components/Common/FileUploadDropzone.tsx
new file mode 100644
index 0000000..6b68ba0
--- /dev/null
+++ b/frontend/src/components/Common/FileUploadDropzone.tsx
@@ -0,0 +1,256 @@
+import { FileIcon, UploadCloud, X } from "lucide-react"
+import { type ChangeEvent, type DragEvent, useRef, useState } from "react"
+
+import { Button } from "@/components/ui/button"
+import {
+  Card,
+  CardContent,
+  CardDescription,
+  CardFooter,
+  CardHeader,
+  CardTitle,
+} from "@/components/ui/card"
+import { cn } from "@/lib/utils"
+
+interface FileUploadDropzoneProps {
+  accept?: string
+  className?: string
+  disabled?: boolean
+  maxFileSize?: number
+  multiple?: boolean
+  onFilesChange?: (files: File[]) => void
+}
+
+const fileSizeUnits = ["B", "KB", "MB", "GB"]
+
+function formatFileSize(bytes: number) {
+  if (bytes === 0) return "0 B"
+
+  const unitIndex = Math.min(
+    Math.floor(Math.log(bytes) / Math.log(1024)),
+    fileSizeUnits.length - 1,
+  )
+  const value = bytes / 1024 ** unitIndex
+
+  return `${value >= 10 || unitIndex === 0 ? value.toFixed(0) : value.toFixed(1)} ${fileSizeUnits[unitIndex]}`
+}
+
+function isAcceptedFile(file: File, accept?: string) {
+  if (!accept) return true
+
+  const acceptedTypes = accept
+    .split(",")
+    .map((acceptedType) => acceptedType.trim().toLowerCase())
+    .filter(Boolean)
+  const fileName = file.name.toLowerCase()
+  const fileType = file.type.toLowerCase()
+
+  return acceptedTypes.some((acceptedType) => {
+    if (acceptedType.startsWith(".")) return fileName.endsWith(acceptedType)
+    if (acceptedType.endsWith("/*")) {
+      return fileType.startsWith(acceptedType.slice(0, -1))
+    }
+
+    return fileType === acceptedType
+  })
+}
+
+function getFileKey(file: File) {
+  return `${file.name}-${file.size}-${file.lastModified}`
+}
+
+export function FileUploadDropzone({
+  accept,
+  className,
+  disabled = false,
+  maxFileSize,
+  multiple = true,
+  onFilesChange,
+}: FileUploadDropzoneProps) {
+  const dragDepthRef = useRef(0)
+  const inputRef = useRef<HTMLInputElement>(null)
+  const [errorMessage, setErrorMessage] = useState("")
+  const [isDragging, setIsDragging] = useState(false)
+  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
+
+  const updateSelectedFiles = (files: File[]) => {
+    setSelectedFiles(files)
+    onFilesChange?.(files)
+  }
+
+  const addFiles = (fileList: FileList | File[]) => {
+    const incomingFiles = Array.from(fileList)
+    const rejectedFiles = incomingFiles.filter(
+      (file) =>
+        !isAcceptedFile(file, accept) ||
+        (maxFileSize !== undefined && file.size > maxFileSize),
+    )
+    const acceptedFiles = incomingFiles.filter(
+      (file) => !rejectedFiles.includes(file),
+    )
+
+    if (rejectedFiles.length > 0) {
+      const firstRejectedFile = rejectedFiles[0]
+      const rejectionReason = !isAcceptedFile(firstRejectedFile, accept)
+        ? "is not an accepted file type"
+        : `is larger than ${formatFileSize(maxFileSize!)}`
+      setErrorMessage(`“${firstRejectedFile.name}” ${rejectionReason}.`)
+    } else if (!multiple && incomingFiles.length > 1) {
+      setErrorMessage("Only one file can be selected.")
+    } else {
+      setErrorMessage("")
+    }
+
+    if (acceptedFiles.length === 0) return
+
+    const nextFiles = multiple
+      ? [...selectedFiles, ...acceptedFiles].filter(
+          (file, index, files) =>
+            files.findIndex(
+              (candidate) => getFileKey(candidate) === getFileKey(file),
+            ) === index,
+        )
+      : [acceptedFiles[0]]
+    updateSelectedFiles(nextFiles)
+  }
+
+  const handleInputChange = (event: ChangeEvent<HTMLInputElement>) => {
+    if (event.target.files) addFiles(event.target.files)
+    event.target.value = ""
+  }
+
+  const handleDragEnter = (event: DragEvent<HTMLButtonElement>) => {
+    event.preventDefault()
+    if (disabled) return
+
+    dragDepthRef.current += 1
+    setIsDragging(true)
+  }
+
+  const handleDragOver = (event: DragEvent<HTMLButtonElement>) => {
+    event.preventDefault()
+    event.dataTransfer.dropEffect = "copy"
+  }
+
+  const handleDragLeave = (event: DragEvent<HTMLButtonElement>) => {
+    event.preventDefault()
+    dragDepthRef.current = Math.max(0, dragDepthRef.current - 1)
+    if (dragDepthRef.current === 0) setIsDragging(false)
+  }
+
+  const handleDrop = (event: DragEvent<HTMLButtonElement>) => {
+    event.preventDefault()
+    dragDepthRef.current = 0
+    setIsDragging(false)
+    if (!disabled) addFiles(event.dataTransfer.files)
+  }
+
+  const handleRemoveFile = (fileToRemove: File) => {
+    const fileKey = getFileKey(fileToRemove)
+    updateSelectedFiles(
+      selectedFiles.filter((file) => getFileKey(file) !== fileKey),
+    )
+    setErrorMessage("")
+  }
+
+  return (
+    <Card className={className}>
+      <CardHeader>
+        <CardTitle>Upload files</CardTitle>
+        <CardDescription>
+          Add files by dragging them into the area below or browsing your
+          device.
+        </CardDescription>
+      </CardHeader>
+      <CardContent className="flex flex-col gap-4">
+        <input
+          ref={inputRef}
+          className="hidden"
+          type="file"
+          accept={accept}
+          disabled={disabled}
+          multiple={multiple}
+          onChange={handleInputChange}
+        />
+        <button
+          type="button"
+          className={cn(
+            "flex min-h-52 w-full flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors outline-none",
+            "hover:border-primary/60 hover:bg-accent/50 focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]",
+            isDragging && "border-primary bg-accent/70",
+            disabled && "pointer-events-none cursor-not-allowed opacity-50",
+          )}
+          disabled={disabled}
+          aria-label="Choose files to upload"
+          onClick={() => inputRef.current?.click()}
+          onDragEnter={handleDragEnter}
+          onDragLeave={handleDragLeave}
+          onDragOver={handleDragOver}
+          onDrop={handleDrop}
+        >
+          <span className="flex size-12 items-center justify-center rounded-full bg-primary/10 text-primary">
+            <UploadCloud className="size-6" aria-hidden="true" />
+          </span>
+          <span className="font-medium">
+            {isDragging ? "Drop files here" : "Drag and drop files here"}
+          </span>
+          <span className="text-sm text-muted-foreground">
+            or click to browse your device
+          </span>
+          {maxFileSize !== undefined ? (
+            <span className="text-xs text-muted-foreground">
+              Maximum size: {formatFileSize(maxFileSize)} per file
+            </span>
+          ) : null}
+        </button>
+
+        {errorMessage ? (
+          <p className="text-sm text-destructive" role="alert">
+            {errorMessage}
+          </p>
+        ) : null}
+
+        {selectedFiles.length > 0 ? (
+          <ul className="flex flex-col gap-2" aria-label="Selected files">
+            {selectedFiles.map((file) => (
+              <li
+                key={getFileKey(file)}
+                className="flex items-center gap-3 rounded-lg border bg-muted/40 p-3"
+              >
+                <FileIcon
+                  className="size-5 shrink-0 text-muted-foreground"
+                  aria-hidden="true"
+                />
+                <span className="min-w-0 flex-1">
+                  <span className="block truncate text-sm font-medium">
+                    {file.name}
+                  </span>
+                  <span className="block text-xs text-muted-foreground">
+                    {formatFileSize(file.size)}
+                  </span>
+                </span>
+                <Button
+                  type="button"
+                  variant="ghost"
+                  size="icon-sm"
+                  aria-label={`Remove ${file.name}`}
+                  disabled={disabled}
+                  onClick={() => handleRemoveFile(file)}
+                >
+                  <X aria-hidden="true" />
+                </Button>
+              </li>
+            ))}
+          </ul>
+        ) : null}
+      </CardContent>
+      <CardFooter>
+        <p className="text-sm text-muted-foreground" aria-live="polite">
+          {selectedFiles.length === 0
+            ? "No files selected"
+            : `${selectedFiles.length} ${selectedFiles.length === 1 ? "file" : "files"} selected`}
+        </p>
+      </CardFooter>
+    </Card>
+  )
+}
diff --git a/frontend/src/routes/_layout/index.tsx b/frontend/src/routes/_layout/index.tsx
index 3e640cb..be4b552 100644
--- a/frontend/src/routes/_layout/index.tsx
+++ b/frontend/src/routes/_layout/index.tsx
@@ -1,5 +1,6 @@
 import { createFileRoute } from "@tanstack/react-router"
 
+import { FileUploadDropzone } from "@/components/Common/FileUploadDropzone"
 import useAuth from "@/hooks/useAuth"
 
 export const Route = createFileRoute("/_layout/")({
@@ -17,7 +18,7 @@ function Dashboard() {
   const { user: currentUser } = useAuth()
 
   return (
-    <div>
+    <div className="flex flex-col gap-8">
       <div>
         <h1 className="text-2xl truncate max-w-sm">
           Hi, {currentUser?.full_name || currentUser?.email} 👋
@@ -26,6 +27,10 @@ function Dashboard() {
           Welcome back, nice to see you again!!!
         </p>
       </div>
+      <FileUploadDropzone
+        className="max-w-2xl"
+        maxFileSize={10 * 1024 * 1024}
+      />
     </div>
   )
 }
```

### Candidate E

- Agent completed: `True`
- Frontend build passed: `True`

```diff
diff --git a/frontend/src/components/ui/file-dropzone.tsx b/frontend/src/components/ui/file-dropzone.tsx
new file mode 100644
index 0000000..6fce1ca
--- /dev/null
+++ b/frontend/src/components/ui/file-dropzone.tsx
@@ -0,0 +1,94 @@
+import * as React from "react"
+import { Upload } from "lucide-react"
+
+import { cn } from "@/lib/utils"
+
+type FileDropzoneProps = Omit<
+  React.ComponentProps<"input">,
+  "children" | "className" | "multiple" | "onChange" | "type"
+> & {
+  className?: string
+  multiple?: boolean
+  onFilesSelected: (files: File[]) => void
+}
+
+function FileDropzone({
+  className,
+  disabled,
+  multiple = false,
+  onFilesSelected,
+  ...props
+}: FileDropzoneProps) {
+  const [isDragging, setIsDragging] = React.useState(false)
+
+  const selectFiles = (files: FileList) => {
+    const selectedFiles = Array.from(files)
+    onFilesSelected(multiple ? selectedFiles : selectedFiles.slice(0, 1))
+  }
+
+  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
+    if (event.target.files) {
+      selectFiles(event.target.files)
+    }
+  }
+
+  const handleDragOver = (event: React.DragEvent<HTMLLabelElement>) => {
+    event.preventDefault()
+
+    if (!disabled) {
+      setIsDragging(true)
+    }
+  }
+
+  const handleDragLeave = () => {
+    setIsDragging(false)
+  }
+
+  const handleDrop = (event: React.DragEvent<HTMLLabelElement>) => {
+    event.preventDefault()
+    setIsDragging(false)
+
+    if (!disabled && event.dataTransfer.files.length > 0) {
+      selectFiles(event.dataTransfer.files)
+    }
+  }
+
+  return (
+    <label
+      data-slot="file-dropzone"
+      data-dragging={isDragging || undefined}
+      className={cn(
+        "flex min-h-48 w-full cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed border-input bg-transparent p-6 text-center transition-colors",
+        "hover:border-ring hover:bg-muted/50 focus-within:border-ring focus-within:ring-ring/50 focus-within:ring-[3px]",
+        "data-[dragging]:border-primary data-[dragging]:bg-primary/5",
+        "has-[:disabled]:cursor-not-allowed has-[:disabled]:opacity-50 has-[:disabled]:hover:border-input has-[:disabled]:hover:bg-transparent",
+        className
+      )}
+      onDragLeave={handleDragLeave}
+      onDragOver={handleDragOver}
+      onDrop={handleDrop}
+    >
+      <input
+        type="file"
+        className="sr-only"
+        disabled={disabled}
+        multiple={multiple}
+        onChange={handleChange}
+        {...props}
+      />
+      <span className="rounded-full bg-muted p-3">
+        <Upload className="size-6 text-muted-foreground" aria-hidden="true" />
+      </span>
+      <span className="space-y-1">
+        <span className="block text-sm font-medium">
+          Drop files here or click to browse
+        </span>
+        <span className="block text-xs text-muted-foreground">
+          {multiple ? "Select one or more files" : "Select a file"}
+        </span>
+      </span>
+    </label>
+  )
+}
+
+export { FileDropzone, type FileDropzoneProps }
```

### Candidate F

- Agent completed: `True`
- Frontend build passed: `True`

```diff
diff --git a/frontend/src/components/ui/file-upload-dropzone.tsx b/frontend/src/components/ui/file-upload-dropzone.tsx
new file mode 100644
index 0000000..6bd91fc
--- /dev/null
+++ b/frontend/src/components/ui/file-upload-dropzone.tsx
@@ -0,0 +1,136 @@
+import { Upload } from "lucide-react"
+import type { ChangeEvent, DragEvent } from "react"
+import { useId, useState } from "react"
+
+import { cn } from "@/lib/utils"
+
+interface FileUploadDropzoneProps {
+  accept?: string
+  className?: string
+  disabled?: boolean
+  multiple?: boolean
+  onFilesSelected: (files: File[]) => void
+}
+
+function matchesAcceptedType(file: File, acceptedType: string) {
+  const normalizedType = acceptedType.toLowerCase()
+
+  if (normalizedType.startsWith(".")) {
+    return file.name.toLowerCase().endsWith(normalizedType)
+  }
+
+  if (normalizedType.endsWith("/*")) {
+    return file.type.toLowerCase().startsWith(normalizedType.slice(0, -1))
+  }
+
+  return file.type.toLowerCase() === normalizedType
+}
+
+function getAcceptedFiles(
+  files: FileList,
+  accept: string | undefined,
+  multiple: boolean,
+) {
+  const acceptedTypes = accept
+    ?.split(",")
+    .map((type) => type.trim())
+    .filter(Boolean)
+  const acceptedFiles = acceptedTypes?.length
+    ? Array.from(files).filter((file) =>
+        acceptedTypes.some((type) => matchesAcceptedType(file, type)),
+      )
+    : Array.from(files)
+
+  return multiple ? acceptedFiles : acceptedFiles.slice(0, 1)
+}
+
+function FileUploadDropzone({
+  accept,
+  className,
+  disabled = false,
+  multiple = false,
+  onFilesSelected,
+}: FileUploadDropzoneProps) {
+  const inputId = useId()
+  const [isDragging, setIsDragging] = useState(false)
+  const isDropActive = isDragging && !disabled
+
+  const selectFiles = (files: FileList) => {
+    const acceptedFiles = getAcceptedFiles(files, accept, multiple)
+
+    if (acceptedFiles.length > 0) {
+      onFilesSelected(acceptedFiles)
+    }
+  }
+
+  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
+    if (event.currentTarget.files) {
+      selectFiles(event.currentTarget.files)
+    }
+
+    event.currentTarget.value = ""
+  }
+
+  const handleDragOver = (event: DragEvent<HTMLLabelElement>) => {
+    event.preventDefault()
+
+    if (!disabled) {
+      setIsDragging(true)
+    }
+  }
+
+  const handleDragLeave = () => {
+    setIsDragging(false)
+  }
+
+  const handleDrop = (event: DragEvent<HTMLLabelElement>) => {
+    event.preventDefault()
+    setIsDragging(false)
+
+    if (!disabled) {
+      selectFiles(event.dataTransfer.files)
+    }
+  }
+
+  return (
+    <div data-slot="file-upload-dropzone">
+      <input
+        id={inputId}
+        type="file"
+        className="peer sr-only"
+        accept={accept}
+        disabled={disabled}
+        multiple={multiple}
+        onChange={handleChange}
+      />
+      <label
+        htmlFor={inputId}
+        className={cn(
+          "flex min-h-48 w-full cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border border-dashed bg-muted/30 px-6 py-10 text-center transition-colors hover:bg-muted/50 peer-focus-visible:border-ring peer-focus-visible:ring-ring/50 peer-focus-visible:ring-[3px] peer-disabled:cursor-not-allowed peer-disabled:opacity-50",
+          isDropActive && "border-primary bg-primary/10",
+          className,
+        )}
+        aria-disabled={disabled}
+        onDragEnter={handleDragOver}
+        onDragOver={handleDragOver}
+        onDragLeave={handleDragLeave}
+        onDrop={handleDrop}
+      >
+        <span className="pointer-events-none flex flex-col items-center gap-3">
+          <Upload className="size-8 text-muted-foreground" aria-hidden="true" />
+          <span className="text-sm font-medium">
+            {isDropActive
+              ? "Drop files here"
+              : "Drag and drop files here, or click to browse"}
+          </span>
+          <span className="text-xs text-muted-foreground">
+            Files are selected from your device
+          </span>
+        </span>
+      </label>
+    </div>
+  )
+}
+
+export { FileUploadDropzone }
+export type { FileUploadDropzoneProps }
```

## Output

Return JSON matching the supplied schema. Include every candidate exactly once. Use only these exact one-letter values for `id`: A, B, C, D, E, F. 
For evidence, cite concrete files or code choices from the diff and do not guess the hidden condition.
