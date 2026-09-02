# Blind implementation review

## Ticket

Add a star rating input component to the frontend.

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
diff --git a/frontend/src/components/ui/star-rating.tsx b/frontend/src/components/ui/star-rating.tsx
new file mode 100644
index 0000000..a20ac96
--- /dev/null
+++ b/frontend/src/components/ui/star-rating.tsx
@@ -0,0 +1,194 @@
+import { StarIcon } from "lucide-react"
+import * as React from "react"
+
+import { cn } from "@/lib/utils"
+
+const DEFAULT_MAX_RATING = 5
+
+type StarRatingProps = Omit<
+  React.ComponentProps<"div">,
+  "defaultValue" | "onChange"
+> & {
+  value?: number
+  defaultValue?: number
+  onValueChange?: (value: number) => void
+  max?: number
+  name?: string
+  disabled?: boolean
+  readOnly?: boolean
+}
+
+function normalizeMaxRating(max: number | undefined) {
+  if (max === undefined || !Number.isFinite(max)) {
+    return DEFAULT_MAX_RATING
+  }
+
+  return Math.max(1, Math.floor(max))
+}
+
+function normalizeRating(value: number | undefined, max: number) {
+  if (value === undefined || !Number.isFinite(value)) {
+    return 0
+  }
+
+  return Math.min(max, Math.max(0, Math.round(value)))
+}
+
+function StarRating({
+  value,
+  defaultValue = 0,
+  onValueChange,
+  max,
+  name,
+  disabled = false,
+  readOnly = false,
+  className,
+  onKeyDown,
+  onMouseLeave,
+  "aria-label": ariaLabel,
+  "aria-labelledby": ariaLabelledBy,
+  ...props
+}: StarRatingProps) {
+  const maxRating = normalizeMaxRating(max)
+  const [uncontrolledValue, setUncontrolledValue] = React.useState(() =>
+    normalizeRating(defaultValue, maxRating)
+  )
+  const [hoveredValue, setHoveredValue] = React.useState<number | null>(null)
+  const buttonRefs = React.useRef<Array<HTMLButtonElement | null>>([])
+  const currentValue = normalizeRating(value ?? uncontrolledValue, maxRating)
+  const displayedValue = hoveredValue ?? currentValue
+  const ratingOptions = Array.from(
+    { length: maxRating },
+    (_, index) => index + 1
+  )
+  const accessibleLabel = ariaLabel ?? (ariaLabelledBy ? undefined : "Rating")
+
+  function updateValue(nextValue: number) {
+    if (disabled || readOnly) {
+      return
+    }
+
+    const normalizedValue = normalizeRating(nextValue, maxRating)
+
+    if (value === undefined) {
+      setUncontrolledValue(normalizedValue)
+    }
+
+    if (normalizedValue !== currentValue) {
+      onValueChange?.(normalizedValue)
+    }
+  }
+
+  function handleKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
+    onKeyDown?.(event)
+
+    if (event.defaultPrevented || disabled || readOnly) {
+      return
+    }
+
+    let nextValue: number | undefined
+
+    switch (event.key) {
+      case "ArrowLeft":
+      case "ArrowDown":
+        nextValue = Math.max(1, currentValue - 1)
+        break
+      case "ArrowRight":
+      case "ArrowUp":
+        nextValue = Math.min(maxRating, currentValue + 1)
+        break
+      case "Home":
+        nextValue = 1
+        break
+      case "End":
+        nextValue = maxRating
+        break
+      default:
+        return
+    }
+
+    event.preventDefault()
+    updateValue(nextValue)
+    buttonRefs.current[nextValue - 1]?.focus()
+  }
+
+  function handleMouseLeave(event: React.MouseEvent<HTMLDivElement>) {
+    setHoveredValue(null)
+    onMouseLeave?.(event)
+  }
+
+  return (
+    <div
+      role="radiogroup"
+      data-slot="star-rating"
+      data-disabled={disabled || undefined}
+      data-readonly={readOnly || undefined}
+      aria-label={accessibleLabel}
+      aria-labelledby={ariaLabelledBy}
+      aria-disabled={disabled || undefined}
+      aria-readonly={readOnly || undefined}
+      className={cn(
+        "inline-flex items-center gap-1 rounded-md aria-invalid:ring-destructive/20 aria-invalid:ring-[3px]",
+        className
+      )}
+      onKeyDown={handleKeyDown}
+      onMouseLeave={handleMouseLeave}
+      {...props}
+    >
+      {name ? (
+        <input
+          type="hidden"
+          data-slot="star-rating-input"
+          name={name}
+          value={currentValue}
+          disabled={disabled}
+          readOnly
+        />
+      ) : null}
+
+      {ratingOptions.map((rating) => {
+        const isActive = rating <= displayedValue
+        const isSelected = rating === currentValue
+        const isTabStop = isSelected || (currentValue === 0 && rating === 1)
+
+        return (
+          <button
+            key={rating}
+            ref={(element) => {
+              buttonRefs.current[rating - 1] = element
+            }}
+            type="button"
+            role="radio"
+            data-slot="star-rating-item"
+            data-state={isActive ? "on" : "off"}
+            aria-label={`${rating} of ${maxRating} stars`}
+            aria-checked={isSelected}
+            aria-readonly={readOnly || undefined}
+            disabled={disabled}
+            tabIndex={disabled ? -1 : isTabStop ? 0 : -1}
+            className={cn(
+              "text-muted-foreground rounded-sm outline-none transition-colors focus-visible:ring-ring/50 focus-visible:ring-[3px] disabled:cursor-not-allowed disabled:opacity-50",
+              isActive && "text-primary"
+            )}
+            onClick={() => updateValue(rating)}
+            onMouseEnter={() => {
+              if (!disabled && !readOnly) {
+                setHoveredValue(rating)
+              }
+            }}
+          >
+            <StarIcon
+              aria-hidden="true"
+              className={cn(
+                "size-6 transition-colors",
+                isActive ? "fill-current" : "fill-transparent"
+              )}
+            />
+          </button>
+        )
+      })}
+    </div>
+  )
+}
+
+export { StarRating, type StarRatingProps }
```

### Candidate B

- Agent completed: `True`
- Frontend build passed: `True`

```diff
diff --git a/frontend/src/components/ui/star-rating.tsx b/frontend/src/components/ui/star-rating.tsx
new file mode 100644
index 0000000..0089272
--- /dev/null
+++ b/frontend/src/components/ui/star-rating.tsx
@@ -0,0 +1,124 @@
+import * as React from "react"
+import { StarIcon } from "lucide-react"
+
+import { cn } from "@/lib/utils"
+
+type StarRatingProps = Omit<
+  React.ComponentProps<"div">,
+  "defaultValue" | "onChange"
+> & {
+  defaultValue?: number
+  disabled?: boolean
+  label?: string
+  max?: number
+  name?: string
+  onValueChange?: (value: number) => void
+  required?: boolean
+  value?: number
+}
+
+function StarRating({
+  className,
+  defaultValue = 0,
+  disabled = false,
+  label = "Rating",
+  max = 5,
+  name,
+  onBlur,
+  onMouseLeave,
+  onValueChange,
+  required = false,
+  value,
+  ...props
+}: StarRatingProps) {
+  const generatedName = React.useId()
+  const [internalValue, setInternalValue] = React.useState(defaultValue)
+  const [previewValue, setPreviewValue] = React.useState<number | null>(null)
+  const starCount = Number.isFinite(max) ? Math.max(1, Math.floor(max)) : 5
+  const selectedValue = value ?? internalValue
+  const displayedValue = previewValue ?? selectedValue
+  const inputName = name ?? `${generatedName}-rating`
+
+  const handleValueChange = (nextValue: number) => {
+    if (value === undefined) {
+      setInternalValue(nextValue)
+    }
+
+    onValueChange?.(nextValue)
+  }
+
+  const handleBlur = (event: React.FocusEvent<HTMLDivElement>) => {
+    if (!event.currentTarget.contains(event.relatedTarget)) {
+      setPreviewValue(null)
+    }
+
+    onBlur?.(event)
+  }
+
+  const handleMouseLeave = (event: React.MouseEvent<HTMLDivElement>) => {
+    setPreviewValue(null)
+    onMouseLeave?.(event)
+  }
+
+  return (
+    <div
+      role="radiogroup"
+      aria-label={label}
+      aria-disabled={disabled || undefined}
+      aria-required={required || undefined}
+      data-disabled={disabled || undefined}
+      data-slot="star-rating"
+      className={cn("flex w-fit items-center", className)}
+      onBlur={handleBlur}
+      onMouseLeave={handleMouseLeave}
+      {...props}
+    >
+      {Array.from({ length: starCount }, (_, index) => {
+        const ratingValue = index + 1
+        const isFilled = ratingValue <= displayedValue
+
+        return (
+          <label
+            key={ratingValue}
+            data-slot="star-rating-item"
+            className={cn(
+              "relative inline-flex size-9 items-center justify-center rounded-md transition-colors has-[:focus-visible]:ring-ring/50 has-[:focus-visible]:ring-[3px]",
+              disabled
+                ? "cursor-not-allowed opacity-50"
+                : "cursor-pointer hover:bg-accent"
+            )}
+            onMouseEnter={() => {
+              if (!disabled) {
+                setPreviewValue(ratingValue)
+              }
+            }}
+          >
+            <input
+              type="radio"
+              className="sr-only"
+              name={inputName}
+              value={ratingValue}
+              checked={ratingValue === selectedValue}
+              aria-label={`${ratingValue} of ${starCount} stars`}
+              disabled={disabled}
+              required={required}
+              onChange={() => handleValueChange(ratingValue)}
+              onFocus={() => setPreviewValue(ratingValue)}
+            />
+            <StarIcon
+              aria-hidden="true"
+              className={cn(
+                "size-6 transition-colors",
+                isFilled
+                  ? "fill-amber-400 text-amber-400"
+                  : "fill-transparent text-muted-foreground/60"
+              )}
+            />
+          </label>
+        )
+      })}
+    </div>
+  )
+}
+
+export { StarRating, type StarRatingProps }
```

### Candidate C

- Agent completed: `True`
- Frontend build passed: `True`

```diff
diff --git a/frontend/src/components/ui/star-rating.tsx b/frontend/src/components/ui/star-rating.tsx
new file mode 100644
index 0000000..830a19f
--- /dev/null
+++ b/frontend/src/components/ui/star-rating.tsx
@@ -0,0 +1,70 @@
+import { StarIcon } from "lucide-react"
+import * as React from "react"
+
+import { cn } from "@/lib/utils"
+
+const ratingValues = [1, 2, 3, 4, 5] as const
+
+type StarRatingProps = Omit<
+  React.ComponentProps<"fieldset">,
+  "onChange"
+> & {
+  value: number
+  onValueChange: (value: number) => void
+  required?: boolean
+}
+
+function StarRating({
+  "aria-label": ariaLabel = "Rating",
+  className,
+  form,
+  name,
+  onValueChange,
+  required,
+  value,
+  ...props
+}: StarRatingProps) {
+  const generatedName = React.useId()
+  const inputName = name ?? generatedName
+
+  return (
+    <fieldset
+      aria-label={ariaLabel}
+      data-slot="star-rating"
+      className={cn("w-fit border-0 p-0", className)}
+      form={form}
+      {...props}
+    >
+      <div className="flex gap-1">
+        {ratingValues.map((rating) => (
+          <label
+            key={rating}
+            className="cursor-pointer rounded-sm has-[:disabled]:pointer-events-none has-[:disabled]:opacity-50 hover:[&>svg]:text-primary has-[:focus-visible]:ring-ring/50 has-[:focus-visible]:ring-[3px]"
+          >
+            <input
+              className="sr-only"
+              type="radio"
+              name={inputName}
+              value={rating}
+              checked={value === rating}
+              form={form}
+              required={required}
+              onChange={() => onValueChange(rating)}
+            />
+            <StarIcon
+              aria-hidden="true"
+              className={cn(
+                "size-7 text-muted-foreground transition-colors",
+                rating <= value && "fill-primary text-primary",
+              )}
+            />
+            <span className="sr-only">{rating} out of 5 stars</span>
+          </label>
+        ))}
+      </div>
+    </fieldset>
+  )
+}
+
+export { StarRating }
+export type { StarRatingProps }
```

### Candidate D

- Agent completed: `True`
- Frontend build passed: `True`

```diff
diff --git a/frontend/src/components/ui/star-rating.tsx b/frontend/src/components/ui/star-rating.tsx
new file mode 100644
index 0000000..094ce32
--- /dev/null
+++ b/frontend/src/components/ui/star-rating.tsx
@@ -0,0 +1,98 @@
+import * as RadioGroupPrimitive from "@radix-ui/react-radio-group"
+import { StarIcon } from "lucide-react"
+import * as React from "react"
+
+import { cn } from "@/lib/utils"
+
+type StarRatingProps = Omit<
+  React.ComponentProps<typeof RadioGroupPrimitive.Root>,
+  "defaultValue" | "onValueChange" | "orientation" | "value"
+> & {
+  defaultValue?: number
+  max?: number
+  onValueChange?: (value: number) => void
+  value?: number
+}
+
+function normalizeRating(value: number, max: number) {
+  if (!Number.isFinite(value)) return 0
+
+  return Math.min(Math.max(Math.round(value), 0), max)
+}
+
+function StarRating({
+  "aria-label": ariaLabel = "Rating",
+  className,
+  defaultValue = 0,
+  disabled,
+  max = 5,
+  onPointerLeave,
+  onValueChange,
+  value,
+  ...props
+}: StarRatingProps) {
+  const starCount = Number.isFinite(max) ? Math.max(1, Math.floor(max)) : 5
+  const [uncontrolledValue, setUncontrolledValue] = React.useState(() =>
+    normalizeRating(defaultValue, starCount),
+  )
+  const [hoveredValue, setHoveredValue] = React.useState<number | null>(null)
+  const selectedValue = normalizeRating(value ?? uncontrolledValue, starCount)
+  const displayedValue = hoveredValue ?? selectedValue
+
+  function handleValueChange(nextValue: string) {
+    const nextRating = normalizeRating(Number(nextValue), starCount)
+
+    if (value === undefined) setUncontrolledValue(nextRating)
+    onValueChange?.(nextRating)
+  }
+
+  function handlePointerLeave(event: React.PointerEvent<HTMLDivElement>) {
+    setHoveredValue(null)
+    onPointerLeave?.(event)
+  }
+
+  return (
+    <RadioGroupPrimitive.Root
+      aria-label={ariaLabel}
+      data-slot="star-rating"
+      className={cn("flex w-fit items-center gap-0.5", className)}
+      disabled={disabled}
+      orientation="horizontal"
+      value={selectedValue > 0 ? String(selectedValue) : null}
+      onPointerLeave={handlePointerLeave}
+      onValueChange={handleValueChange}
+      {...props}
+    >
+      {Array.from({ length: starCount }, (_, index) => {
+        const rating = index + 1
+        const isFilled = rating <= displayedValue
+
+        return (
+          <RadioGroupPrimitive.Item
+            aria-label={`${rating} of ${starCount} stars`}
+            data-slot="star-rating-item"
+            className="rounded-sm p-0.5 outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
+            key={rating}
+            type="button"
+            value={String(rating)}
+            onPointerEnter={() => {
+              if (!disabled) setHoveredValue(rating)
+            }}
+          >
+            <StarIcon
+              aria-hidden="true"
+              className={cn(
+                "size-6",
+                isFilled
+                  ? "fill-yellow-400 text-yellow-400"
+                  : "fill-transparent text-muted-foreground/40",
+              )}
+            />
+          </RadioGroupPrimitive.Item>
+        )
+      })}
+    </RadioGroupPrimitive.Root>
+  )
+}
+
+export { StarRating, type StarRatingProps }
```

### Candidate E

- Agent completed: `True`
- Frontend build passed: `True`

```diff
diff --git a/frontend/src/components/ui/star-rating.tsx b/frontend/src/components/ui/star-rating.tsx
new file mode 100644
index 0000000..3994157
--- /dev/null
+++ b/frontend/src/components/ui/star-rating.tsx
@@ -0,0 +1,57 @@
+import * as RadioGroupPrimitive from "@radix-ui/react-radio-group"
+import { StarIcon } from "lucide-react"
+import type * as React from "react"
+
+import { cn } from "@/lib/utils"
+
+const starRatingValues = [1, 2, 3, 4, 5] as const
+
+type StarRatingProps = Omit<
+  React.ComponentProps<typeof RadioGroupPrimitive.Root>,
+  "children" | "defaultValue" | "onValueChange" | "value"
+> & {
+  value: number
+  onValueChange: (value: number) => void
+}
+
+function StarRating({
+  className,
+  value,
+  onValueChange,
+  ...props
+}: StarRatingProps) {
+  return (
+    <RadioGroupPrimitive.Root
+      data-slot="star-rating"
+      aria-label="Rating"
+      className={cn(
+        "flex w-fit items-center gap-1 rounded-md aria-invalid:ring-[3px] aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40",
+        className
+      )}
+      value={String(value)}
+      onValueChange={(nextValue) => onValueChange(Number(nextValue))}
+      {...props}
+    >
+      {starRatingValues.map((rating) => (
+        <RadioGroupPrimitive.Item
+          type="button"
+          key={rating}
+          data-slot="star-rating-item"
+          aria-label={`${rating} out of ${starRatingValues.length} stars`}
+          className="rounded-sm p-1 text-muted-foreground transition-colors outline-none hover:text-amber-400 focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50"
+          value={String(rating)}
+        >
+          <StarIcon
+            aria-hidden="true"
+            className={cn(
+              "size-6",
+              rating <= value && "fill-amber-400 text-amber-400"
+            )}
+          />
+        </RadioGroupPrimitive.Item>
+      ))}
+    </RadioGroupPrimitive.Root>
+  )
+}
+
+export { StarRating, type StarRatingProps }
```

### Candidate F

- Agent completed: `True`
- Frontend build passed: `True`

```diff
diff --git a/frontend/src/components/ui/star-rating.tsx b/frontend/src/components/ui/star-rating.tsx
new file mode 100644
index 0000000..6a54b18
--- /dev/null
+++ b/frontend/src/components/ui/star-rating.tsx
@@ -0,0 +1,55 @@
+import * as RadioGroupPrimitive from "@radix-ui/react-radio-group"
+import { StarIcon } from "lucide-react"
+import type * as React from "react"
+
+import { cn } from "@/lib/utils"
+
+const ratings = [1, 2, 3, 4, 5] as const
+
+type StarRatingProps = Omit<
+  React.ComponentProps<typeof RadioGroupPrimitive.Root>,
+  "defaultValue" | "onValueChange" | "value"
+> & {
+  value: number
+  onValueChange: (value: number) => void
+}
+
+function StarRating({
+  className,
+  value,
+  onValueChange,
+  "aria-label": ariaLabel = "Rating",
+  ...props
+}: StarRatingProps) {
+  return (
+    <RadioGroupPrimitive.Root
+      data-slot="star-rating"
+      aria-label={ariaLabel}
+      className={cn("flex w-fit items-center gap-1", className)}
+      value={String(value)}
+      onValueChange={(nextValue) => onValueChange(Number(nextValue))}
+      {...props}
+    >
+      {ratings.map((rating) => (
+        <RadioGroupPrimitive.Item
+          key={rating}
+          type="button"
+          value={String(rating)}
+          aria-label={`${rating} out of 5 stars`}
+          className="rounded-sm text-muted-foreground outline-none transition-colors hover:text-primary focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50"
+        >
+          <StarIcon
+            aria-hidden="true"
+            className={cn(
+              "size-6",
+              rating <= value && "fill-primary text-primary",
+            )}
+          />
+        </RadioGroupPrimitive.Item>
+      ))}
+    </RadioGroupPrimitive.Root>
+  )
+}
+
+export type { StarRatingProps }
+export { StarRating }
```

## Output

Return JSON matching the supplied schema. Include every candidate exactly once. Use only these exact one-letter values for `id`: A, B, C, D, E, F. 
For evidence, cite concrete files or code choices from the diff and do not guess the hidden condition.
