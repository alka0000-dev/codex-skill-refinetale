# Blind implementation review

## Ticket

Add a date picker component to the frontend.

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
diff --git a/frontend/src/components/ui/date-picker.tsx b/frontend/src/components/ui/date-picker.tsx
new file mode 100644
index 0000000..88fe83e
--- /dev/null
+++ b/frontend/src/components/ui/date-picker.tsx
@@ -0,0 +1,23 @@
+import * as React from "react"
+
+import { cn } from "@/lib/utils"
+import { Input } from "@/components/ui/input"
+
+type DatePickerProps = Omit<React.ComponentProps<"input">, "type">
+
+function DatePicker({ className, ...props }: DatePickerProps) {
+  return (
+    <Input
+      type="date"
+      data-slot="date-picker"
+      className={cn(
+        "[color-scheme:light] dark:[color-scheme:dark]",
+        className,
+      )}
+      {...props}
+    />
+  )
+}
+
+export { DatePicker }
+export type { DatePickerProps }
```

### Candidate B

- Agent completed: `True`
- Frontend build passed: `True`

```diff
diff --git a/frontend/src/components/ui/date-picker.tsx b/frontend/src/components/ui/date-picker.tsx
new file mode 100644
index 0000000..f74c73f
--- /dev/null
+++ b/frontend/src/components/ui/date-picker.tsx
@@ -0,0 +1,11 @@
+import * as React from "react"
+
+import { Input } from "@/components/ui/input"
+
+type DatePickerProps = Omit<React.ComponentProps<typeof Input>, "type">
+
+function DatePicker({ ...props }: DatePickerProps) {
+  return <Input type="date" data-slot="date-picker" {...props} />
+}
+
+export { DatePicker, type DatePickerProps }
```

### Candidate C

- Agent completed: `True`
- Frontend build passed: `True`

```diff
diff --git a/frontend/src/components/ui/date-picker.tsx b/frontend/src/components/ui/date-picker.tsx
new file mode 100644
index 0000000..ae7f2a4
--- /dev/null
+++ b/frontend/src/components/ui/date-picker.tsx
@@ -0,0 +1,12 @@
+import * as React from "react"
+
+import { Input } from "@/components/ui/input"
+
+type DatePickerProps = Omit<React.ComponentProps<typeof Input>, "type">
+
+function DatePicker(props: DatePickerProps) {
+  return <Input {...props} type="date" />
+}
+
+export { DatePicker }
+export type { DatePickerProps }
```

### Candidate D

- Agent completed: `True`
- Frontend build passed: `True`

```diff
diff --git a/frontend/src/components/ui/date-picker.tsx b/frontend/src/components/ui/date-picker.tsx
new file mode 100644
index 0000000..3d739ec
--- /dev/null
+++ b/frontend/src/components/ui/date-picker.tsx
@@ -0,0 +1,11 @@
+import * as React from "react"
+
+import { Input } from "@/components/ui/input"
+
+type DatePickerProps = Omit<React.ComponentProps<typeof Input>, "type">
+
+function DatePicker(props: DatePickerProps) {
+  return <Input {...props} type="date" />
+}
+
+export { DatePicker }
```

### Candidate E

- Agent completed: `True`
- Frontend build passed: `True`

```diff
diff --git a/frontend/src/components/ui/date-picker.tsx b/frontend/src/components/ui/date-picker.tsx
new file mode 100644
index 0000000..e3263d7
--- /dev/null
+++ b/frontend/src/components/ui/date-picker.tsx
@@ -0,0 +1,480 @@
+import * as React from "react"
+import {
+  CalendarDaysIcon,
+  ChevronLeftIcon,
+  ChevronRightIcon,
+} from "lucide-react"
+
+import { Button } from "@/components/ui/button"
+import { cn } from "@/lib/utils"
+
+type WeekStart = 0 | 1
+
+type DatePickerProps = Omit<
+  React.ComponentProps<"button">,
+  "defaultValue" | "onChange" | "value"
+> & {
+  value?: Date | null
+  defaultValue?: Date | null
+  onChange?: (date: Date | null) => void
+  onValueChange?: (date: Date | null) => void
+  minDate?: Date
+  maxDate?: Date
+  placeholder?: string
+  locale?: string
+  weekStartsOn?: WeekStart
+  name?: string
+}
+
+const daysInCalendar = 42
+
+function toCalendarDate(date: Date) {
+  return new Date(date.getFullYear(), date.getMonth(), date.getDate())
+}
+
+function isValidDate(date: Date | null | undefined): date is Date {
+  return date instanceof Date && !Number.isNaN(date.getTime())
+}
+
+function addDays(date: Date, amount: number) {
+  return new Date(date.getFullYear(), date.getMonth(), date.getDate() + amount)
+}
+
+function addMonths(date: Date, amount: number) {
+  return new Date(date.getFullYear(), date.getMonth() + amount, 1)
+}
+
+function addCalendarMonths(date: Date, amount: number) {
+  const targetMonth = addMonths(date, amount)
+  const lastDayOfTargetMonth = new Date(
+    targetMonth.getFullYear(),
+    targetMonth.getMonth() + 1,
+    0
+  ).getDate()
+
+  return new Date(
+    targetMonth.getFullYear(),
+    targetMonth.getMonth(),
+    Math.min(date.getDate(), lastDayOfTargetMonth)
+  )
+}
+
+function isSameDay(firstDate: Date, secondDate: Date) {
+  return (
+    firstDate.getFullYear() === secondDate.getFullYear() &&
+    firstDate.getMonth() === secondDate.getMonth() &&
+    firstDate.getDate() === secondDate.getDate()
+  )
+}
+
+function isSameMonth(firstDate: Date, secondDate: Date) {
+  return (
+    firstDate.getFullYear() === secondDate.getFullYear() &&
+    firstDate.getMonth() === secondDate.getMonth()
+  )
+}
+
+function toDateValue(date: Date) {
+  const year = date.getFullYear()
+  const month = String(date.getMonth() + 1).padStart(2, "0")
+  const day = String(date.getDate()).padStart(2, "0")
+
+  return `${year}-${month}-${day}`
+}
+
+function getCalendarStart(month: Date, weekStartsOn: WeekStart) {
+  const firstDay = new Date(month.getFullYear(), month.getMonth(), 1)
+  const precedingDayCount = (firstDay.getDay() - weekStartsOn + 7) % 7
+
+  return addDays(firstDay, -precedingDayCount)
+}
+
+function getWeekdays(locale: string, weekStartsOn: WeekStart) {
+  const sunday = new Date(2024, 0, 7)
+
+  return Array.from({ length: 7 }, (_, index) => {
+    const weekday = addDays(sunday, index + weekStartsOn)
+    return {
+      long: new Intl.DateTimeFormat(locale, { weekday: "long" }).format(weekday),
+      short: new Intl.DateTimeFormat(locale, { weekday: "narrow" }).format(
+        weekday
+      ),
+    }
+  })
+}
+
+function DatePicker({
+  value,
+  defaultValue = null,
+  onChange,
+  onValueChange,
+  minDate,
+  maxDate,
+  placeholder = "Pick a date",
+  locale = "en-US",
+  weekStartsOn = 0,
+  name,
+  className,
+  disabled,
+  id,
+  onClick,
+  ref,
+  "aria-label": ariaLabel,
+  ...props
+}: DatePickerProps) {
+  const isControlled = value !== undefined
+  const initialDate = isValidDate(value)
+    ? toCalendarDate(value)
+    : isValidDate(defaultValue)
+      ? toCalendarDate(defaultValue)
+      : null
+  const [uncontrolledValue, setUncontrolledValue] =
+    React.useState<Date | null>(initialDate)
+  const selectedDate = isControlled
+    ? isValidDate(value)
+      ? toCalendarDate(value)
+      : null
+    : uncontrolledValue
+  const today = React.useMemo(() => toCalendarDate(new Date()), [])
+  const minimumDate = isValidDate(minDate) ? toCalendarDate(minDate) : undefined
+  const maximumDate = isValidDate(maxDate) ? toCalendarDate(maxDate) : undefined
+  const initialMonth = selectedDate ?? minimumDate ?? today
+  const [visibleMonth, setVisibleMonth] = React.useState(
+    new Date(initialMonth.getFullYear(), initialMonth.getMonth(), 1)
+  )
+  const [focusedDate, setFocusedDate] = React.useState(initialMonth)
+  const [isOpen, setIsOpen] = React.useState(false)
+  const containerRef = React.useRef<HTMLDivElement>(null)
+  const triggerRef = React.useRef<HTMLButtonElement>(null)
+  const dayButtonRefs = React.useRef(new Map<string, HTMLButtonElement>())
+  const generatedId = React.useId()
+  const triggerId = id ?? `date-picker-${generatedId}`
+  const dialogId = `${triggerId}-dialog`
+  const monthLabelId = `${triggerId}-month-label`
+
+  const dateFormatter = React.useMemo(
+    () => new Intl.DateTimeFormat(locale, { dateStyle: "medium" }),
+    [locale]
+  )
+  const monthFormatter = React.useMemo(
+    () =>
+      new Intl.DateTimeFormat(locale, {
+        month: "long",
+        year: "numeric",
+      }),
+    [locale]
+  )
+  const dayFormatter = React.useMemo(
+    () =>
+      new Intl.DateTimeFormat(locale, {
+        day: "numeric",
+        month: "long",
+        year: "numeric",
+      }),
+    [locale]
+  )
+  const weekdays = React.useMemo(
+    () => getWeekdays(locale, weekStartsOn),
+    [locale, weekStartsOn]
+  )
+  const calendarDates = React.useMemo(() => {
+    const calendarStart = getCalendarStart(visibleMonth, weekStartsOn)
+    return Array.from({ length: daysInCalendar }, (_, index) =>
+      addDays(calendarStart, index)
+    )
+  }, [visibleMonth, weekStartsOn])
+
+  const isDateDisabled = React.useCallback(
+    (date: Date) =>
+      Boolean(
+        (minimumDate && date < minimumDate) ||
+          (maximumDate && date > maximumDate)
+      ),
+    [maximumDate, minimumDate]
+  )
+
+  const canShowPreviousMonth = !minimumDate || visibleMonth > new Date(
+    minimumDate.getFullYear(),
+    minimumDate.getMonth(),
+    1
+  )
+  const canShowNextMonth = !maximumDate || visibleMonth < new Date(
+    maximumDate.getFullYear(),
+    maximumDate.getMonth(),
+    1
+  )
+
+  React.useEffect(() => {
+    if (!isOpen) return
+
+    const handlePointerDown = (event: PointerEvent) => {
+      if (!containerRef.current?.contains(event.target as Node)) {
+        setIsOpen(false)
+      }
+    }
+
+    document.addEventListener("pointerdown", handlePointerDown)
+    return () => document.removeEventListener("pointerdown", handlePointerDown)
+  }, [isOpen])
+
+  React.useEffect(() => {
+    if (!isOpen) return
+
+    dayButtonRefs.current.get(toDateValue(focusedDate))?.focus()
+  }, [focusedDate, isOpen, visibleMonth])
+
+  const updateValue = (date: Date | null) => {
+    if (!isControlled) setUncontrolledValue(date)
+    onChange?.(date)
+    onValueChange?.(date)
+  }
+
+  const handleTriggerClick = (event: React.MouseEvent<HTMLButtonElement>) => {
+    onClick?.(event)
+    if (event.defaultPrevented) return
+
+    if (!isOpen) {
+      const nextFocusedDate = selectedDate ?? minimumDate ?? today
+      setFocusedDate(nextFocusedDate)
+      setVisibleMonth(
+        new Date(nextFocusedDate.getFullYear(), nextFocusedDate.getMonth(), 1)
+      )
+    }
+    setIsOpen((currentIsOpen) => !currentIsOpen)
+  }
+
+  const handleSelectDate = (date: Date) => {
+    updateValue(date)
+    setIsOpen(false)
+    triggerRef.current?.focus()
+  }
+
+  const focusCalendarDate = (date: Date) => {
+    let nextDate = date
+    if (minimumDate && nextDate < minimumDate) nextDate = minimumDate
+    if (maximumDate && nextDate > maximumDate) nextDate = maximumDate
+
+    setFocusedDate(nextDate)
+    if (!isSameMonth(nextDate, visibleMonth)) {
+      setVisibleMonth(
+        new Date(nextDate.getFullYear(), nextDate.getMonth(), 1)
+      )
+    }
+  }
+
+  const handleDayKeyDown = (
+    event: React.KeyboardEvent<HTMLButtonElement>,
+    date: Date
+  ) => {
+    let nextDate: Date | undefined
+
+    switch (event.key) {
+      case "ArrowLeft":
+        nextDate = addDays(date, -1)
+        break
+      case "ArrowRight":
+        nextDate = addDays(date, 1)
+        break
+      case "ArrowUp":
+        nextDate = addDays(date, -7)
+        break
+      case "ArrowDown":
+        nextDate = addDays(date, 7)
+        break
+      case "Home":
+        nextDate = addDays(date, -((date.getDay() - weekStartsOn + 7) % 7))
+        break
+      case "End":
+        nextDate = addDays(date, 6 - ((date.getDay() - weekStartsOn + 7) % 7))
+        break
+      case "PageUp":
+        nextDate = addCalendarMonths(date, -1)
+        break
+      case "PageDown":
+        nextDate = addCalendarMonths(date, 1)
+        break
+      case "Escape":
+        event.preventDefault()
+        setIsOpen(false)
+        triggerRef.current?.focus()
+        return
+      default:
+        return
+    }
+
+    event.preventDefault()
+    focusCalendarDate(nextDate)
+  }
+
+  return (
+    <div ref={containerRef} data-slot="date-picker" className="relative w-fit">
+      <Button
+        ref={(element) => {
+          triggerRef.current = element
+          if (typeof ref === "function") ref(element)
+          else if (ref) ref.current = element
+        }}
+        {...props}
+        id={triggerId}
+        type="button"
+        variant="outline"
+        aria-controls={isOpen ? dialogId : undefined}
+        aria-expanded={isOpen}
+        aria-haspopup="dialog"
+        aria-label={ariaLabel}
+        className={cn(
+          "w-[17rem] justify-start text-left font-normal",
+          !selectedDate && "text-muted-foreground",
+          className
+        )}
+        disabled={disabled}
+        onClick={handleTriggerClick}
+      >
+        <CalendarDaysIcon aria-hidden="true" />
+        <span className="truncate">
+          {selectedDate ? dateFormatter.format(selectedDate) : placeholder}
+        </span>
+      </Button>
+
+      {name && (
+        <input
+          type="hidden"
+          name={name}
+          value={selectedDate ? toDateValue(selectedDate) : ""}
+          disabled={disabled}
+        />
+      )}
+
+      {isOpen && (
+        <div
+          id={dialogId}
+          role="dialog"
+          aria-label="Choose date"
+          aria-modal="false"
+          className="bg-popover text-popover-foreground absolute top-full left-0 z-50 mt-2 w-[19rem] rounded-md border p-3 shadow-md"
+          onKeyDown={(event) => {
+            if (event.key === "Escape") {
+              event.preventDefault()
+              setIsOpen(false)
+              triggerRef.current?.focus()
+            }
+          }}
+        >
+          <div className="mb-2 flex items-center justify-between">
+            <Button
+              type="button"
+              variant="ghost"
+              size="icon-sm"
+              aria-label="Previous month"
+              disabled={!canShowPreviousMonth}
+              onClick={() => focusCalendarDate(addMonths(visibleMonth, -1))}
+            >
+              <ChevronLeftIcon aria-hidden="true" />
+            </Button>
+            <div
+              id={monthLabelId}
+              aria-live="polite"
+              className="text-sm font-medium"
+            >
+              {monthFormatter.format(visibleMonth)}
+            </div>
+            <Button
+              type="button"
+              variant="ghost"
+              size="icon-sm"
+              aria-label="Next month"
+              disabled={!canShowNextMonth}
+              onClick={() => focusCalendarDate(addMonths(visibleMonth, 1))}
+            >
+              <ChevronRightIcon aria-hidden="true" />
+            </Button>
+          </div>
+
+          <div
+            role="grid"
+            aria-labelledby={monthLabelId}
+            className="grid grid-cols-7"
+          >
+            {weekdays.map((weekday) => (
+              <div
+                key={weekday.long}
+                role="columnheader"
+                aria-label={weekday.long}
+                className="text-muted-foreground flex h-8 items-center justify-center text-xs font-normal"
+              >
+                {weekday.short}
+              </div>
+            ))}
+            {calendarDates.map((date) => {
+              const dateValue = toDateValue(date)
+              const isSelected = Boolean(
+                selectedDate && isSameDay(date, selectedDate)
+              )
+              const isToday = isSameDay(date, today)
+              const isOutsideMonth = !isSameMonth(date, visibleMonth)
+              const isDisabled = isDateDisabled(date)
+
+              return (
+                <button
+                  ref={(element) => {
+                    if (element) dayButtonRefs.current.set(dateValue, element)
+                    else dayButtonRefs.current.delete(dateValue)
+                  }}
+                  key={dateValue}
+                  type="button"
+                  role="gridcell"
+                  tabIndex={isSameDay(date, focusedDate) ? 0 : -1}
+                  aria-label={dayFormatter.format(date)}
+                  aria-selected={isSelected}
+                  aria-current={isToday ? "date" : undefined}
+                  disabled={isDisabled}
+                  data-outside-month={isOutsideMonth || undefined}
+                  className={cn(
+                    "relative flex size-10 items-center justify-center rounded-md text-sm outline-none transition-colors",
+                    "hover:bg-accent hover:text-accent-foreground focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px]",
+                    "disabled:pointer-events-none disabled:opacity-30",
+                    isOutsideMonth && "text-muted-foreground opacity-50",
+                    isToday && !isSelected && "bg-accent text-accent-foreground",
+                    isSelected &&
+                      "bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground"
+                  )}
+                  onClick={() => handleSelectDate(date)}
+                  onKeyDown={(event) => handleDayKeyDown(event, date)}
+                >
+                  {date.getDate()}
+                </button>
+              )
+            })}
+          </div>
+
+          <div className="mt-2 flex items-center justify-between border-t pt-2">
+            <Button
+              type="button"
+              variant="ghost"
+              size="sm"
+              disabled={isDateDisabled(today)}
+              onClick={() => handleSelectDate(today)}
+            >
+              Today
+            </Button>
+            <Button
+              type="button"
+              variant="ghost"
+              size="sm"
+              disabled={!selectedDate}
+              onClick={() => {
+                updateValue(null)
+                setIsOpen(false)
+                triggerRef.current?.focus()
+              }}
+            >
+              Clear
+            </Button>
+          </div>
+        </div>
+      )}
+    </div>
+  )
+}
+
+export { DatePicker, type DatePickerProps }
```

### Candidate F

- Agent completed: `True`
- Frontend build passed: `True`

```diff
diff --git a/frontend/src/components/ui/date-picker.tsx b/frontend/src/components/ui/date-picker.tsx
new file mode 100644
index 0000000..669f4aa
--- /dev/null
+++ b/frontend/src/components/ui/date-picker.tsx
@@ -0,0 +1,9 @@
+import * as React from "react"
+
+import { Input } from "@/components/ui/input"
+
+function DatePicker(props: Omit<React.ComponentProps<typeof Input>, "type">) {
+  return <Input data-slot="date-picker" type="date" {...props} />
+}
+
+export { DatePicker }
```

## Output

Return JSON matching the supplied schema. Include every candidate exactly once. Use only these exact one-letter values for `id`: A, B, C, D, E, F. 
For evidence, cite concrete files or code choices from the diff and do not guess the hidden condition.
