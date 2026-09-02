# Blind implementation review

## Ticket

Add a multi-step form wizard component to the frontend.

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
diff --git a/frontend/src/components/Common/MultiStepFormWizard.tsx b/frontend/src/components/Common/MultiStepFormWizard.tsx
new file mode 100644
index 0000000..a7a2ce8
--- /dev/null
+++ b/frontend/src/components/Common/MultiStepFormWizard.tsx
@@ -0,0 +1,464 @@
+import { zodResolver } from "@hookform/resolvers/zod"
+import {
+  ArrowLeft,
+  ArrowRight,
+  Check,
+  CheckCircle2,
+  ClipboardCheck,
+  RotateCcw,
+  SlidersHorizontal,
+  Sparkles,
+} from "lucide-react"
+import { type FormEvent, useState } from "react"
+import { useForm } from "react-hook-form"
+import { z } from "zod"
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
+import { Checkbox } from "@/components/ui/checkbox"
+import {
+  Form,
+  FormControl,
+  FormDescription,
+  FormField,
+  FormItem,
+  FormLabel,
+  FormMessage,
+} from "@/components/ui/form"
+import { Input } from "@/components/ui/input"
+import {
+  Select,
+  SelectContent,
+  SelectItem,
+  SelectTrigger,
+  SelectValue,
+} from "@/components/ui/select"
+import useCustomToast from "@/hooks/useCustomToast"
+import { cn } from "@/lib/utils"
+
+const wizardFormSchema = z.object({
+  projectName: z
+    .string()
+    .trim()
+    .min(2, { message: "Enter at least 2 characters." })
+    .max(60, { message: "Keep the name under 60 characters." }),
+  projectDescription: z
+    .string()
+    .trim()
+    .max(160, { message: "Keep the description under 160 characters." }),
+  projectType: z.string().min(1, { message: "Choose a project type." }),
+  teamSize: z.string().min(1, { message: "Choose a team size." }),
+  receiveUpdates: z.boolean(),
+})
+
+type WizardFormValues = z.infer<typeof wizardFormSchema>
+type WizardFieldName = keyof WizardFormValues
+
+type WizardStep = {
+  title: string
+  shortTitle: string
+  description: string
+  fields: WizardFieldName[]
+  icon: typeof Sparkles
+}
+
+const wizardSteps: WizardStep[] = [
+  {
+    title: "Tell us about your project",
+    shortTitle: "Project",
+    description: "Start with a name and a short description.",
+    fields: ["projectName", "projectDescription"],
+    icon: Sparkles,
+  },
+  {
+    title: "Choose your preferences",
+    shortTitle: "Preferences",
+    description: "These choices help tailor your starting workspace.",
+    fields: ["projectType", "teamSize", "receiveUpdates"],
+    icon: SlidersHorizontal,
+  },
+  {
+    title: "Review your setup",
+    shortTitle: "Review",
+    description: "Make sure everything looks right before you finish.",
+    fields: [],
+    icon: ClipboardCheck,
+  },
+]
+
+const projectTypeLabels: Record<string, string> = {
+  personal: "Personal project",
+  team: "Team project",
+  client: "Client work",
+}
+
+const teamSizeLabels: Record<string, string> = {
+  solo: "Just me",
+  small: "2–5 people",
+  medium: "6–20 people",
+  large: "21+ people",
+}
+
+const defaultValues: WizardFormValues = {
+  projectName: "",
+  projectDescription: "",
+  projectType: "",
+  teamSize: "",
+  receiveUpdates: true,
+}
+
+function WizardProgress({ activeStep }: { activeStep: number }) {
+  return (
+    <nav aria-label="Setup progress" className="px-6 pt-6 sm:px-8">
+      <ol className="grid grid-cols-3">
+        {wizardSteps.map((step, index) => {
+          const isComplete = index < activeStep
+          const isActive = index === activeStep
+          const StepIcon = step.icon
+
+          return (
+            <li
+              key={step.shortTitle}
+              className="relative flex flex-col items-center gap-2 text-center"
+              aria-current={isActive ? "step" : undefined}
+            >
+              {index > 0 && (
+                <span
+                  aria-hidden="true"
+                  className={cn(
+                    "absolute right-1/2 top-5 h-px w-full -translate-y-1/2",
+                    isComplete || isActive ? "bg-primary" : "bg-border",
+                  )}
+                />
+              )}
+              <span
+                className={cn(
+                  "relative z-10 flex size-10 items-center justify-center rounded-full border bg-background transition-colors duration-200 motion-reduce:transition-none",
+                  isComplete &&
+                    "border-primary bg-primary text-primary-foreground",
+                  isActive &&
+                    "border-primary text-primary ring-4 ring-primary/10",
+                  !isComplete && !isActive && "text-muted-foreground",
+                )}
+              >
+                {isComplete ? (
+                  <Check aria-hidden="true" className="size-4" />
+                ) : (
+                  <StepIcon aria-hidden="true" className="size-4" />
+                )}
+                <span className="sr-only">
+                  {isComplete ? "Completed: " : ""}
+                  {step.shortTitle}
+                </span>
+              </span>
+              <span
+                className={cn(
+                  "hidden text-xs font-medium sm:block",
+                  isActive ? "text-foreground" : "text-muted-foreground",
+                )}
+              >
+                {step.shortTitle}
+              </span>
+            </li>
+          )
+        })}
+      </ol>
+    </nav>
+  )
+}
+
+function ProjectStep() {
+  return (
+    <div className="grid gap-5">
+      <FormField
+        name="projectName"
+        render={({ field }) => (
+          <FormItem>
+            <FormLabel>
+              Project name <span className="text-destructive">*</span>
+            </FormLabel>
+            <FormControl>
+              <Input
+                autoComplete="off"
+                placeholder="e.g. Product launch"
+                {...field}
+              />
+            </FormControl>
+            <FormDescription>This can be changed later.</FormDescription>
+            <FormMessage />
+          </FormItem>
+        )}
+      />
+      <FormField
+        name="projectDescription"
+        render={({ field }) => (
+          <FormItem>
+            <FormLabel>Description</FormLabel>
+            <FormControl>
+              <textarea
+                className="border-input placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-ring/50 aria-invalid:border-destructive aria-invalid:ring-destructive/20 min-h-24 w-full resize-none rounded-md border bg-transparent px-3 py-2 text-sm shadow-xs outline-none transition-[color,box-shadow] focus-visible:ring-[3px]"
+                placeholder="What would you like to accomplish?"
+                {...field}
+              />
+            </FormControl>
+            <div className="flex items-start justify-between gap-4">
+              <FormDescription>Optional, up to 160 characters.</FormDescription>
+              <span className="text-muted-foreground text-xs tabular-nums">
+                {field.value.length}/160
+              </span>
+            </div>
+            <FormMessage />
+          </FormItem>
+        )}
+      />
+    </div>
+  )
+}
+
+function PreferencesStep() {
+  return (
+    <div className="grid gap-5 sm:grid-cols-2">
+      <FormField
+        name="projectType"
+        render={({ field }) => (
+          <FormItem>
+            <FormLabel>
+              Project type <span className="text-destructive">*</span>
+            </FormLabel>
+            <Select onValueChange={field.onChange} value={field.value}>
+              <FormControl>
+                <SelectTrigger className="w-full">
+                  <SelectValue placeholder="Select a type" />
+                </SelectTrigger>
+              </FormControl>
+              <SelectContent>
+                <SelectItem value="personal">Personal project</SelectItem>
+                <SelectItem value="team">Team project</SelectItem>
+                <SelectItem value="client">Client work</SelectItem>
+              </SelectContent>
+            </Select>
+            <FormMessage />
+          </FormItem>
+        )}
+      />
+      <FormField
+        name="teamSize"
+        render={({ field }) => (
+          <FormItem>
+            <FormLabel>
+              Team size <span className="text-destructive">*</span>
+            </FormLabel>
+            <Select onValueChange={field.onChange} value={field.value}>
+              <FormControl>
+                <SelectTrigger className="w-full">
+                  <SelectValue placeholder="Select a size" />
+                </SelectTrigger>
+              </FormControl>
+              <SelectContent>
+                <SelectItem value="solo">Just me</SelectItem>
+                <SelectItem value="small">2–5 people</SelectItem>
+                <SelectItem value="medium">6–20 people</SelectItem>
+                <SelectItem value="large">21+ people</SelectItem>
+              </SelectContent>
+            </Select>
+            <FormMessage />
+          </FormItem>
+        )}
+      />
+      <FormField
+        name="receiveUpdates"
+        render={({ field }) => (
+          <FormItem className="sm:col-span-2">
+            <div className="bg-muted/40 flex items-start gap-3 rounded-lg border p-4">
+              <FormControl>
+                <Checkbox
+                  checked={field.value}
+                  onCheckedChange={(isChecked) =>
+                    field.onChange(isChecked === true)
+                  }
+                />
+              </FormControl>
+              <div className="grid gap-1">
+                <FormLabel>Send me setup tips</FormLabel>
+                <FormDescription>
+                  Get occasional guidance as your project takes shape.
+                </FormDescription>
+              </div>
+            </div>
+          </FormItem>
+        )}
+      />
+    </div>
+  )
+}
+
+function ReviewStep({ values }: { values: WizardFormValues }) {
+  const reviewItems = [
+    { label: "Project name", value: values.projectName },
+    {
+      label: "Description",
+      value: values.projectDescription || "No description added",
+    },
+    {
+      label: "Project type",
+      value: projectTypeLabels[values.projectType],
+    },
+    { label: "Team size", value: teamSizeLabels[values.teamSize] },
+    {
+      label: "Setup tips",
+      value: values.receiveUpdates ? "Enabled" : "Disabled",
+    },
+  ]
+
+  return (
+    <dl className="divide-y rounded-lg border">
+      {reviewItems.map((item) => (
+        <div
+          key={item.label}
+          className="grid gap-1 px-4 py-3 sm:grid-cols-[9rem_1fr] sm:gap-4"
+        >
+          <dt className="text-muted-foreground text-sm">{item.label}</dt>
+          <dd className="text-sm font-medium break-words">{item.value}</dd>
+        </div>
+      ))}
+    </dl>
+  )
+}
+
+function MultiStepFormWizard() {
+  const [activeStep, setActiveStep] = useState(0)
+  const [isComplete, setIsComplete] = useState(false)
+  const { showSuccessToast } = useCustomToast()
+  const form = useForm<WizardFormValues>({
+    resolver: zodResolver(wizardFormSchema),
+    mode: "onBlur",
+    defaultValues,
+  })
+
+  const currentStep = wizardSteps[activeStep]
+  const isLastStep = activeStep === wizardSteps.length - 1
+
+  const handleNext = async () => {
+    const isStepValid = await form.trigger(currentStep.fields, {
+      shouldFocus: true,
+    })
+
+    if (isStepValid) {
+      setActiveStep((currentActiveStep) => currentActiveStep + 1)
+    }
+  }
+
+  const handlePrevious = () => {
+    setActiveStep((currentActiveStep) => currentActiveStep - 1)
+  }
+
+  const handleSubmit = () => {
+    setIsComplete(true)
+    showSuccessToast("Your project setup is complete.")
+  }
+
+  const handleFormSubmit = (event: FormEvent<HTMLFormElement>) => {
+    if (!isLastStep) {
+      event.preventDefault()
+      void handleNext()
+      return
+    }
+
+    void form.handleSubmit(handleSubmit)(event)
+  }
+
+  const handleStartOver = () => {
+    form.reset(defaultValues)
+    setActiveStep(0)
+    setIsComplete(false)
+  }
+
+  if (isComplete) {
+    return (
+      <Card className="overflow-hidden">
+        <CardContent className="flex min-h-96 flex-col items-center justify-center px-6 py-12 text-center">
+          <span className="mb-5 flex size-16 items-center justify-center rounded-full bg-primary/10 text-primary">
+            <CheckCircle2 aria-hidden="true" className="size-8" />
+          </span>
+          <p className="text-muted-foreground mb-2 text-sm font-medium">
+            All steps complete
+          </p>
+          <h2 className="text-2xl font-semibold tracking-tight">
+            Your project is ready
+          </h2>
+          <p className="text-muted-foreground mt-2 max-w-md text-sm">
+            You finished the setup for {form.getValues("projectName")}.
+          </p>
+          <Button
+            className="mt-7"
+            type="button"
+            variant="outline"
+            onClick={handleStartOver}
+          >
+            <RotateCcw aria-hidden="true" />
+            Start over
+          </Button>
+        </CardContent>
+      </Card>
+    )
+  }
+
+  return (
+    <Card className="overflow-hidden py-0">
+      <WizardProgress activeStep={activeStep} />
+      <Form {...form}>
+        <form onSubmit={handleFormSubmit} noValidate>
+          <CardHeader
+            className="border-b px-6 pb-6 pt-7 sm:px-8"
+            aria-live="polite"
+          >
+            <p className="text-primary text-xs font-semibold tracking-wider uppercase">
+              Step {activeStep + 1} of {wizardSteps.length}
+            </p>
+            <CardTitle className="text-xl">{currentStep.title}</CardTitle>
+            <CardDescription>{currentStep.description}</CardDescription>
+          </CardHeader>
+          <CardContent
+            key={currentStep.shortTitle}
+            className="min-h-72 px-6 py-7 motion-safe:animate-in motion-safe:fade-in-0 motion-safe:slide-in-from-right-2 motion-safe:duration-200 sm:px-8"
+          >
+            {activeStep === 0 && <ProjectStep />}
+            {activeStep === 1 && <PreferencesStep />}
+            {activeStep === 2 && <ReviewStep values={form.getValues()} />}
+          </CardContent>
+          <CardFooter className="justify-between gap-3 border-t bg-muted/20 px-6 py-5 sm:px-8">
+            <Button
+              type="button"
+              variant="ghost"
+              onClick={handlePrevious}
+              disabled={activeStep === 0}
+            >
+              <ArrowLeft aria-hidden="true" />
+              Back
+            </Button>
+            {isLastStep ? (
+              <Button type="submit">
+                Complete setup
+                <Check aria-hidden="true" />
+              </Button>
+            ) : (
+              <Button type="button" onClick={handleNext}>
+                Continue
+                <ArrowRight aria-hidden="true" />
+              </Button>
+            )}
+          </CardFooter>
+        </form>
+      </Form>
+    </Card>
+  )
+}
+
+export default MultiStepFormWizard
diff --git a/frontend/src/routes/_layout/index.tsx b/frontend/src/routes/_layout/index.tsx
index 3e640cb..e7b37f3 100644
--- a/frontend/src/routes/_layout/index.tsx
+++ b/frontend/src/routes/_layout/index.tsx
@@ -1,5 +1,6 @@
 import { createFileRoute } from "@tanstack/react-router"
 
+import MultiStepFormWizard from "@/components/Common/MultiStepFormWizard"
 import useAuth from "@/hooks/useAuth"
 
 export const Route = createFileRoute("/_layout/")({
@@ -17,15 +18,18 @@ function Dashboard() {
   const { user: currentUser } = useAuth()
 
   return (
-    <div>
+    <div className="grid gap-8">
       <div>
-        <h1 className="text-2xl truncate max-w-sm">
+        <h1 className="max-w-sm truncate text-2xl font-bold tracking-tight">
           Hi, {currentUser?.full_name || currentUser?.email} 👋
         </h1>
         <p className="text-muted-foreground">
-          Welcome back, nice to see you again!!!
+          Welcome back. Let&apos;s get your next project ready.
         </p>
       </div>
+      <div className="mx-auto w-full max-w-3xl">
+        <MultiStepFormWizard />
+      </div>
     </div>
   )
 }
```

### Candidate B

- Agent completed: `True`
- Frontend build passed: `True`

```diff
diff --git a/frontend/src/components/Common/MultiStepForm.tsx b/frontend/src/components/Common/MultiStepForm.tsx
new file mode 100644
index 0000000..d1ebdfe
--- /dev/null
+++ b/frontend/src/components/Common/MultiStepForm.tsx
@@ -0,0 +1,137 @@
+import {
+  type ComponentProps,
+  type MouseEvent,
+  type ReactNode,
+  useId,
+  useState,
+} from "react"
+
+import { Button } from "@/components/ui/button"
+import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card"
+import { cn } from "@/lib/utils"
+
+type MultiStepFormStep = {
+  title: string
+  description?: string
+  content: ReactNode
+}
+
+type MultiStepFormProps = Omit<ComponentProps<"form">, "children"> & {
+  steps: readonly [MultiStepFormStep, ...MultiStepFormStep[]]
+}
+
+type FormControl = HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement
+
+function MultiStepForm({ className, steps, ...props }: MultiStepFormProps) {
+  const [currentStepIndex, setCurrentStepIndex] = useState(0)
+  const formWizardId = `form-wizard-${useId().replace(/[^a-z0-9-]/gi, "")}`
+  const isLastStep = currentStepIndex === steps.length - 1
+
+  const handleBack = () => {
+    setCurrentStepIndex((stepIndex) => stepIndex - 1)
+  }
+
+  const handleNext = (event: MouseEvent<HTMLButtonElement>) => {
+    const form = event.currentTarget.form!
+    const currentStep = form.querySelector(
+      `#${formWizardId}-step-${currentStepIndex + 1}`,
+    )!
+    const invalidControl = currentStep.querySelector<FormControl>(
+      "input:invalid, select:invalid, textarea:invalid",
+    )
+
+    if (!form.noValidate && invalidControl) {
+      invalidControl.reportValidity()
+      return
+    }
+
+    setCurrentStepIndex((stepIndex) => stepIndex + 1)
+  }
+
+  return (
+    <form className={cn("w-full", className)} {...props}>
+      <Card>
+        <CardHeader>
+          <ol aria-label="Form progress" className="flex flex-wrap gap-2">
+            {steps.map((step, stepIndex) => {
+              const isCurrentStep = stepIndex === currentStepIndex
+              const stepState =
+                stepIndex < currentStepIndex
+                  ? "complete"
+                  : isCurrentStep
+                    ? "current"
+                    : "upcoming"
+
+              return (
+                <li
+                  key={stepIndex}
+                  aria-current={isCurrentStep ? "step" : undefined}
+                  data-state={stepState}
+                  className="flex min-w-32 flex-1 items-center gap-2 rounded-md border p-3 text-sm text-muted-foreground data-[state=complete]:border-primary/50 data-[state=complete]:text-foreground data-[state=current]:border-primary data-[state=current]:text-foreground"
+                >
+                  <span className="flex size-6 shrink-0 items-center justify-center rounded-full border text-xs font-medium">
+                    {stepIndex + 1}
+                  </span>
+                  <span className="font-medium">{step.title}</span>
+                </li>
+              )
+            })}
+          </ol>
+        </CardHeader>
+
+        <CardContent>
+          <p className="sr-only" aria-live="polite">
+            Step {currentStepIndex + 1} of {steps.length}
+          </p>
+          {steps.map((step, stepIndex) => {
+            const stepNumber = stepIndex + 1
+            const stepId = `${formWizardId}-step-${stepNumber}`
+            const descriptionId = `${stepId}-description`
+
+            return (
+              <fieldset
+                key={stepIndex}
+                id={stepId}
+                aria-describedby={step.description ? descriptionId : undefined}
+                hidden={stepIndex !== currentStepIndex}
+              >
+                <legend className="text-xl font-semibold">{step.title}</legend>
+                {step.description && (
+                  <p
+                    id={descriptionId}
+                    className="mt-2 text-sm text-muted-foreground"
+                  >
+                    {step.description}
+                  </p>
+                )}
+                <div className="mt-6">{step.content}</div>
+              </fieldset>
+            )
+          })}
+        </CardContent>
+
+        <CardFooter className="gap-3 border-t">
+          <Button
+            type="button"
+            variant="outline"
+            disabled={currentStepIndex === 0}
+            onClick={handleBack}
+          >
+            Back
+          </Button>
+          {isLastStep ? (
+            <Button type="submit" className="ml-auto">
+              Submit
+            </Button>
+          ) : (
+            <Button type="button" className="ml-auto" onClick={handleNext}>
+              Next
+            </Button>
+          )}
+        </CardFooter>
+      </Card>
+    </form>
+  )
+}
+
+export { MultiStepForm, type MultiStepFormProps, type MultiStepFormStep }
```

### Candidate C

- Agent completed: `True`
- Frontend build passed: `True`

```diff
diff --git a/frontend/src/components/Common/MultiStepFormWizard.tsx b/frontend/src/components/Common/MultiStepFormWizard.tsx
new file mode 100644
index 0000000..06c9e52
--- /dev/null
+++ b/frontend/src/components/Common/MultiStepFormWizard.tsx
@@ -0,0 +1,516 @@
+import { zodResolver } from "@hookform/resolvers/zod"
+import {
+  ArrowLeft,
+  ArrowRight,
+  Check,
+  CheckCircle2,
+  Rocket,
+  Sparkles,
+  Users,
+} from "lucide-react"
+import { type FormEvent, useEffect, useRef, useState } from "react"
+import { useForm } from "react-hook-form"
+import { z } from "zod"
+
+import { Button } from "@/components/ui/button"
+import { Card, CardContent } from "@/components/ui/card"
+import {
+  Form,
+  FormControl,
+  FormField,
+  FormItem,
+  FormLabel,
+  FormMessage,
+} from "@/components/ui/form"
+import { Input } from "@/components/ui/input"
+import { cn } from "@/lib/utils"
+
+const wizardSchema = z.object({
+  fullName: z.string().trim().min(2, "Enter your full name"),
+  role: z.string().min(1, "Choose your role"),
+  workspaceName: z.string().trim().min(2, "Enter a workspace name"),
+  teamSize: z.string().min(1, "Choose a team size"),
+  goals: z.array(z.string()).min(1, "Choose at least one goal"),
+  productUpdates: z.boolean(),
+})
+
+type WizardFormData = z.infer<typeof wizardSchema>
+type WizardFieldName = keyof WizardFormData
+
+interface MultiStepFormWizardProps {
+  initialFullName?: string
+  onComplete?: (formData: WizardFormData) => void
+}
+
+const steps = [
+  {
+    eyebrow: "Personal details",
+    title: "Tell us about yourself",
+    description: "A few details help us tailor your workspace experience.",
+    fields: ["fullName", "role"] satisfies WizardFieldName[],
+  },
+  {
+    eyebrow: "Your workspace",
+    title: "Set up your team",
+    description:
+      "Create a home for your projects and the people you work with.",
+    fields: ["workspaceName", "teamSize"] satisfies WizardFieldName[],
+  },
+  {
+    eyebrow: "Your goals",
+    title: "What are you here to do?",
+    description: "Pick the areas that matter most. You can change these later.",
+    fields: ["goals", "productUpdates"] satisfies WizardFieldName[],
+  },
+] as const
+
+const teamSizes = ["Just me", "2–10", "11–50", "51+"]
+
+const goalOptions = [
+  {
+    value: "plan-projects",
+    title: "Plan projects",
+    description: "Keep work clear and on schedule.",
+    icon: Rocket,
+  },
+  {
+    value: "collaborate",
+    title: "Collaborate",
+    description: "Bring teammates and ideas together.",
+    icon: Users,
+  },
+  {
+    value: "organize-work",
+    title: "Organize work",
+    description: "Build a calmer, focused workflow.",
+    icon: Sparkles,
+  },
+]
+
+export function MultiStepFormWizard({
+  initialFullName = "",
+  onComplete,
+}: MultiStepFormWizardProps) {
+  const [currentStepIndex, setCurrentStepIndex] = useState(0)
+  const [isComplete, setIsComplete] = useState(false)
+  const stepHeadingRef = useRef<HTMLHeadingElement>(null)
+  const form = useForm<WizardFormData>({
+    resolver: zodResolver(wizardSchema),
+    mode: "onBlur",
+    defaultValues: {
+      fullName: initialFullName,
+      role: "",
+      workspaceName: "",
+      teamSize: "",
+      goals: [],
+      productUpdates: true,
+    },
+  })
+
+  const currentStep = steps[currentStepIndex]
+  const progressPercentage = ((currentStepIndex + 1) / steps.length) * 100
+
+  useEffect(() => {
+    if (currentStepIndex > 0) {
+      stepHeadingRef.current?.focus()
+    }
+  }, [currentStepIndex])
+
+  const handleNext = async () => {
+    const isStepValid = await form.trigger(currentStep.fields)
+
+    if (isStepValid && currentStepIndex < steps.length - 1) {
+      setCurrentStepIndex((stepIndex) => stepIndex + 1)
+    }
+  }
+
+  const handleBack = () => {
+    setCurrentStepIndex((stepIndex) => Math.max(0, stepIndex - 1))
+  }
+
+  const handleGoalToggle = (goal: string) => {
+    const selectedGoals = form.getValues("goals")
+    const updatedGoals = selectedGoals.includes(goal)
+      ? selectedGoals.filter((selectedGoal) => selectedGoal !== goal)
+      : [...selectedGoals, goal]
+
+    form.setValue("goals", updatedGoals, {
+      shouldDirty: true,
+      shouldTouch: true,
+      shouldValidate: true,
+    })
+  }
+
+  const handleSubmit = (formData: WizardFormData) => {
+    onComplete?.(formData)
+    setIsComplete(true)
+  }
+
+  const handleFormSubmit = (event: FormEvent<HTMLFormElement>) => {
+    event.preventDefault()
+
+    if (currentStepIndex === steps.length - 1) {
+      void form.handleSubmit(handleSubmit)(event)
+      return
+    }
+
+    void handleNext()
+  }
+
+  const handleStartOver = () => {
+    form.reset()
+    setCurrentStepIndex(0)
+    setIsComplete(false)
+  }
+
+  if (isComplete) {
+    return (
+      <Card className="overflow-hidden border-primary/20 shadow-lg shadow-primary/5">
+        <CardContent className="flex min-h-[34rem] flex-col items-center justify-center px-6 py-16 text-center sm:px-12">
+          <div className="mb-6 flex size-16 items-center justify-center rounded-full bg-primary/10 text-primary">
+            <CheckCircle2 className="size-8" aria-hidden="true" />
+          </div>
+          <p className="mb-2 text-sm font-semibold tracking-wide text-primary uppercase">
+            You&apos;re all set
+          </p>
+          <h2 className="max-w-md text-3xl font-semibold tracking-tight sm:text-4xl">
+            Your workspace is ready
+          </h2>
+          <p className="mt-4 max-w-lg text-balance text-muted-foreground">
+            Everything is configured. You can now invite your team and start
+            turning plans into progress.
+          </p>
+          <Button type="button" className="mt-8" onClick={handleStartOver}>
+            Create another workspace
+            <ArrowRight aria-hidden="true" />
+          </Button>
+        </CardContent>
+      </Card>
+    )
+  }
+
+  return (
+    <Card className="overflow-hidden p-0 shadow-lg shadow-black/5">
+      <div className="grid min-h-[38rem] lg:grid-cols-[18rem_1fr]">
+        <aside className="relative overflow-hidden bg-zinc-950 p-6 text-white sm:p-8">
+          <div className="absolute -top-20 -right-20 size-56 rounded-full bg-primary/20 blur-3xl" />
+          <div className="relative flex h-full flex-col">
+            <div>
+              <div className="mb-8 flex size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
+                <Sparkles className="size-5" aria-hidden="true" />
+              </div>
+              <p className="text-xs font-semibold tracking-[0.18em] text-zinc-400 uppercase">
+                Quick setup
+              </p>
+              <h2 className="mt-2 text-xl font-semibold">
+                Build your workspace
+              </h2>
+              <p className="mt-2 text-sm leading-6 text-zinc-400">
+                Three simple steps. About two minutes.
+              </p>
+            </div>
+
+            <nav className="mt-10" aria-label="Setup progress">
+              <ol className="space-y-1">
+                {steps.map((step, stepIndex) => {
+                  const isActive = stepIndex === currentStepIndex
+                  const isFinished = stepIndex < currentStepIndex
+
+                  return (
+                    <li key={step.title}>
+                      <div
+                        className={cn(
+                          "flex items-center gap-3 rounded-lg px-2 py-2.5 text-sm transition-colors",
+                          isActive && "bg-white/10 text-white",
+                          !isActive && "text-zinc-400",
+                        )}
+                        aria-current={isActive ? "step" : undefined}
+                      >
+                        <span
+                          className={cn(
+                            "flex size-7 shrink-0 items-center justify-center rounded-full border text-xs font-semibold",
+                            isActive &&
+                              "border-primary bg-primary text-primary-foreground",
+                            isFinished &&
+                              "border-primary bg-primary/15 text-primary",
+                            !isActive && !isFinished && "border-zinc-700",
+                          )}
+                        >
+                          {isFinished ? (
+                            <Check className="size-3.5" aria-hidden="true" />
+                          ) : (
+                            stepIndex + 1
+                          )}
+                        </span>
+                        <span>{step.eyebrow}</span>
+                      </div>
+                    </li>
+                  )
+                })}
+              </ol>
+            </nav>
+
+            <p className="mt-auto hidden pt-10 text-xs leading-5 text-zinc-500 lg:block">
+              Your answers are saved while you move between steps.
+            </p>
+          </div>
+        </aside>
+
+        <div className="flex min-w-0 flex-col">
+          <div className="h-1 bg-muted" aria-hidden="true">
+            <div
+              className="h-full bg-primary transition-[width] duration-300 motion-reduce:transition-none"
+              style={{ width: `${progressPercentage}%` }}
+            />
+          </div>
+
+          <Form {...form}>
+            <form className="flex flex-1 flex-col" onSubmit={handleFormSubmit}>
+              <div
+                key={currentStep.title}
+                className="flex-1 animate-in px-6 py-9 duration-300 fade-in slide-in-from-bottom-2 motion-reduce:animate-none sm:px-10 sm:py-12"
+              >
+                <p className="text-sm font-medium text-primary">
+                  Step {currentStepIndex + 1} of {steps.length}
+                </p>
+                <h2
+                  ref={stepHeadingRef}
+                  tabIndex={-1}
+                  className="mt-2 text-2xl font-semibold tracking-tight outline-none sm:text-3xl"
+                >
+                  {currentStep.title}
+                </h2>
+                <p className="mt-3 max-w-xl text-sm leading-6 text-muted-foreground sm:text-base">
+                  {currentStep.description}
+                </p>
+
+                <div className="mt-9 max-w-2xl">
+                  {currentStepIndex === 0 && (
+                    <div className="grid gap-6 sm:grid-cols-2">
+                      <FormField
+                        control={form.control}
+                        name="fullName"
+                        render={({ field }) => (
+                          <FormItem>
+                            <FormLabel>Full name</FormLabel>
+                            <FormControl>
+                              <Input
+                                type="text"
+                                placeholder="Alex Morgan"
+                                autoComplete="name"
+                                {...field}
+                              />
+                            </FormControl>
+                            <FormMessage />
+                          </FormItem>
+                        )}
+                      />
+                      <FormField
+                        control={form.control}
+                        name="role"
+                        render={({ field }) => (
+                          <FormItem>
+                            <FormLabel>Role</FormLabel>
+                            <FormControl>
+                              <select
+                                className="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 aria-invalid:border-destructive"
+                                {...field}
+                              >
+                                <option value="" disabled>
+                                  Select your role
+                                </option>
+                                <option value="founder">Founder</option>
+                                <option value="product">Product</option>
+                                <option value="design">Design</option>
+                                <option value="engineering">Engineering</option>
+                                <option value="operations">Operations</option>
+                                <option value="other">Other</option>
+                              </select>
+                            </FormControl>
+                            <FormMessage />
+                          </FormItem>
+                        )}
+                      />
+                    </div>
+                  )}
+
+                  {currentStepIndex === 1 && (
+                    <div className="space-y-7">
+                      <FormField
+                        control={form.control}
+                        name="workspaceName"
+                        render={({ field }) => (
+                          <FormItem>
+                            <FormLabel>Workspace name</FormLabel>
+                            <FormControl>
+                              <Input
+                                type="text"
+                                placeholder="Acme Studio"
+                                autoComplete="organization"
+                                {...field}
+                              />
+                            </FormControl>
+                            <FormMessage />
+                          </FormItem>
+                        )}
+                      />
+                      <FormField
+                        control={form.control}
+                        name="teamSize"
+                        render={({ field }) => (
+                          <FormItem>
+                            <fieldset>
+                              <FormLabel asChild>
+                                <legend>Team size</legend>
+                              </FormLabel>
+                              <div className="mt-2 grid grid-cols-2 gap-3 sm:grid-cols-4">
+                                {teamSizes.map((teamSize) => (
+                                  <button
+                                    key={teamSize}
+                                    type="button"
+                                    className={cn(
+                                      "rounded-lg border px-3 py-3 text-sm font-medium transition-colors hover:border-primary/60 hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
+                                      field.value === teamSize &&
+                                        "border-primary bg-primary/10 text-primary",
+                                    )}
+                                    aria-pressed={field.value === teamSize}
+                                    onClick={() => field.onChange(teamSize)}
+                                  >
+                                    {teamSize}
+                                  </button>
+                                ))}
+                              </div>
+                            </fieldset>
+                            <FormMessage />
+                          </FormItem>
+                        )}
+                      />
+                    </div>
+                  )}
+
+                  {currentStepIndex === 2 && (
+                    <div className="space-y-7">
+                      <FormField
+                        control={form.control}
+                        name="goals"
+                        render={({ field, fieldState }) => (
+                          <FormItem>
+                            <fieldset>
+                              <legend className="sr-only">
+                                Workspace goals
+                              </legend>
+                              <div className="grid gap-3 sm:grid-cols-3">
+                                {goalOptions.map((goal) => {
+                                  const isSelected = field.value.includes(
+                                    goal.value,
+                                  )
+
+                                  return (
+                                    <button
+                                      key={goal.value}
+                                      type="button"
+                                      className={cn(
+                                        "relative rounded-xl border p-4 text-left transition-colors hover:border-primary/60 hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
+                                        isSelected &&
+                                          "border-primary bg-primary/10",
+                                      )}
+                                      aria-pressed={isSelected}
+                                      onClick={() =>
+                                        handleGoalToggle(goal.value)
+                                      }
+                                    >
+                                      {isSelected && (
+                                        <span className="absolute top-3 right-3 flex size-5 items-center justify-center rounded-full bg-primary text-primary-foreground">
+                                          <Check
+                                            className="size-3"
+                                            aria-hidden="true"
+                                          />
+                                        </span>
+                                      )}
+                                      <goal.icon
+                                        className="mb-6 size-5 text-primary"
+                                        aria-hidden="true"
+                                      />
+                                      <span className="block text-sm font-semibold">
+                                        {goal.title}
+                                      </span>
+                                      <span className="mt-1 block text-xs leading-5 text-muted-foreground">
+                                        {goal.description}
+                                      </span>
+                                    </button>
+                                  )
+                                })}
+                              </div>
+                            </fieldset>
+                            {fieldState.error && (
+                              <p
+                                className="text-sm text-destructive"
+                                role="alert"
+                              >
+                                {fieldState.error.message}
+                              </p>
+                            )}
+                          </FormItem>
+                        )}
+                      />
+
+                      <FormField
+                        control={form.control}
+                        name="productUpdates"
+                        render={({ field }) => (
+                          <FormItem>
+                            <label className="flex cursor-pointer items-start gap-3 rounded-lg border bg-muted/30 p-4">
+                              <input
+                                type="checkbox"
+                                className="mt-0.5 size-4 accent-primary"
+                                checked={field.value}
+                                onChange={field.onChange}
+                              />
+                              <span>
+                                <span className="block text-sm font-medium">
+                                  Send me practical product tips
+                                </span>
+                                <span className="mt-1 block text-xs leading-5 text-muted-foreground">
+                                  Occasional guidance to help your team get more
+                                  from the workspace.
+                                </span>
+                              </span>
+                            </label>
+                          </FormItem>
+                        )}
+                      />
+                    </div>
+                  )}
+                </div>
+              </div>
+
+              <div className="flex items-center justify-between gap-4 border-t px-6 py-5 sm:px-10">
+                <Button
+                  type="button"
+                  variant="ghost"
+                  onClick={handleBack}
+                  disabled={currentStepIndex === 0}
+                  className={cn(currentStepIndex === 0 && "invisible")}
+                >
+                  <ArrowLeft aria-hidden="true" />
+                  Back
+                </Button>
+                {currentStepIndex === steps.length - 1 ? (
+                  <Button type="submit">
+                    Complete setup
+                    <Check aria-hidden="true" />
+                  </Button>
+                ) : (
+                  <Button type="button" onClick={handleNext}>
+                    Continue
+                    <ArrowRight aria-hidden="true" />
+                  </Button>
+                )}
+              </div>
+            </form>
+          </Form>
+        </div>
+      </div>
+    </Card>
+  )
+}
diff --git a/frontend/src/routes/_layout/index.tsx b/frontend/src/routes/_layout/index.tsx
index 3e640cb..fba9ce1 100644
--- a/frontend/src/routes/_layout/index.tsx
+++ b/frontend/src/routes/_layout/index.tsx
@@ -1,5 +1,6 @@
 import { createFileRoute } from "@tanstack/react-router"
 
+import { MultiStepFormWizard } from "@/components/Common/MultiStepFormWizard"
 import useAuth from "@/hooks/useAuth"
 
 export const Route = createFileRoute("/_layout/")({
@@ -17,15 +18,18 @@ function Dashboard() {
   const { user: currentUser } = useAuth()
 
   return (
-    <div>
-      <div>
-        <h1 className="text-2xl truncate max-w-sm">
-          Hi, {currentUser?.full_name || currentUser?.email} 👋
+    <div className="space-y-8">
+      <div className="max-w-2xl">
+        <p className="text-sm font-medium text-primary">Welcome aboard</p>
+        <h1 className="mt-1 text-3xl font-semibold tracking-tight">
+          Let&apos;s get you set up
         </h1>
-        <p className="text-muted-foreground">
-          Welcome back, nice to see you again!!!
+        <p className="mt-2 text-muted-foreground">
+          Create a workspace that fits how you and your team like to work.
         </p>
       </div>
+
+      <MultiStepFormWizard initialFullName={currentUser?.full_name ?? ""} />
     </div>
   )
 }
```

### Candidate D

- Agent completed: `True`
- Frontend build passed: `True`

```diff
diff --git a/frontend/src/components/Common/MultiStepForm.tsx b/frontend/src/components/Common/MultiStepForm.tsx
new file mode 100644
index 0000000..b6d0d8b
--- /dev/null
+++ b/frontend/src/components/Common/MultiStepForm.tsx
@@ -0,0 +1,272 @@
+import { zodResolver } from "@hookform/resolvers/zod"
+import { Check } from "lucide-react"
+import type { FormEvent } from "react"
+import { useState } from "react"
+import { type FieldPath, useForm } from "react-hook-form"
+import { z } from "zod"
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
+import {
+  Form,
+  FormControl,
+  FormField,
+  FormItem,
+  FormLabel,
+  FormMessage,
+} from "@/components/ui/form"
+import { Input } from "@/components/ui/input"
+import { cn } from "@/lib/utils"
+
+const profileSetupSchema = z.object({
+  fullName: z.string().trim().min(1, "Full name is required"),
+  email: z.email("Enter a valid email address"),
+  company: z.string().trim().min(1, "Company is required"),
+  role: z.string().trim().min(1, "Role is required"),
+})
+
+export type ProfileSetupData = z.infer<typeof profileSetupSchema>
+
+type WizardStep = {
+  title: string
+  description: string
+  fields: WizardField[]
+}
+
+type WizardField = {
+  name: FieldPath<ProfileSetupData>
+  label: string
+  placeholder: string
+  autoComplete: string
+  type?: "email" | "text"
+}
+
+const wizardSteps: WizardStep[] = [
+  {
+    title: "Your details",
+    description: "Tell us how to identify you.",
+    fields: [
+      {
+        name: "fullName",
+        label: "Full name",
+        placeholder: "Alex Morgan",
+        autoComplete: "name",
+      },
+      {
+        name: "email",
+        label: "Email",
+        placeholder: "alex@example.com",
+        autoComplete: "email",
+        type: "email",
+      },
+    ],
+  },
+  {
+    title: "Work details",
+    description: "Add a little context about your work.",
+    fields: [
+      {
+        name: "company",
+        label: "Company",
+        placeholder: "Acme Inc.",
+        autoComplete: "organization",
+      },
+      {
+        name: "role",
+        label: "Role",
+        placeholder: "Product designer",
+        autoComplete: "organization-title",
+      },
+    ],
+  },
+  {
+    title: "Review",
+    description: "Check your answers before finishing.",
+    fields: [],
+  },
+]
+
+interface MultiStepFormProps {
+  onComplete: (data: ProfileSetupData) => void
+}
+
+export function MultiStepForm({ onComplete }: MultiStepFormProps) {
+  const [currentStepIndex, setCurrentStepIndex] = useState(0)
+  const form = useForm<ProfileSetupData>({
+    resolver: zodResolver(profileSetupSchema),
+    mode: "onBlur",
+    defaultValues: {
+      fullName: "",
+      email: "",
+      company: "",
+      role: "",
+    },
+  })
+
+  const currentStep = wizardSteps[currentStepIndex]
+  const isFirstStep = currentStepIndex === 0
+  const isLastStep = currentStepIndex === wizardSteps.length - 1
+
+  const handlePrevious = () => {
+    setCurrentStepIndex((stepIndex) => stepIndex - 1)
+  }
+
+  const handleComplete = (data: ProfileSetupData) => {
+    onComplete(data)
+    form.reset()
+    setCurrentStepIndex(0)
+  }
+
+  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
+    event.preventDefault()
+
+    if (isLastStep) {
+      await form.handleSubmit(handleComplete)()
+      return
+    }
+
+    const isStepValid = await form.trigger(
+      currentStep.fields.map(({ name }) => name),
+      { shouldFocus: true },
+    )
+    if (isStepValid) {
+      setCurrentStepIndex((stepIndex) => stepIndex + 1)
+    }
+  }
+
+  const profile = form.watch()
+
+  return (
+    <Card className="w-full max-w-2xl">
+      <CardHeader>
+        <CardTitle>Set up your profile</CardTitle>
+        <CardDescription>
+          Complete the steps below to personalize your workspace.
+        </CardDescription>
+      </CardHeader>
+
+      <CardContent>
+        <nav aria-label="Profile setup progress" className="mb-8">
+          <ol className="grid grid-cols-3 gap-2">
+            {wizardSteps.map((step, stepIndex) => {
+              const isCompleted = stepIndex < currentStepIndex
+              const isCurrent = stepIndex === currentStepIndex
+
+              return (
+                <li
+                  key={step.title}
+                  aria-current={isCurrent ? "step" : undefined}
+                  className="flex min-w-0 items-center gap-2"
+                >
+                  <span
+                    className={cn(
+                      "flex size-8 shrink-0 items-center justify-center rounded-full border text-sm font-medium",
+                      (isCompleted || isCurrent) &&
+                        "border-primary bg-primary text-primary-foreground",
+                    )}
+                  >
+                    {isCompleted ? (
+                      <Check aria-hidden="true" className="size-4" />
+                    ) : (
+                      stepIndex + 1
+                    )}
+                  </span>
+                  <span
+                    className={cn(
+                      "hidden truncate text-sm sm:block",
+                      isCurrent
+                        ? "font-medium text-foreground"
+                        : "text-muted-foreground",
+                    )}
+                  >
+                    {step.title}
+                  </span>
+                </li>
+              )
+            })}
+          </ol>
+        </nav>
+
+        <div className="mb-6">
+          <p className="text-sm text-muted-foreground">
+            Step {currentStepIndex + 1} of {wizardSteps.length}
+          </p>
+          <h2 className="text-xl font-semibold">{currentStep.title}</h2>
+          <p className="text-sm text-muted-foreground">
+            {currentStep.description}
+          </p>
+        </div>
+
+        <Form {...form}>
+          <form id="profile-setup-form" onSubmit={handleSubmit}>
+            <div className="grid gap-4 sm:grid-cols-2">
+              {currentStep.fields.map((stepField) => (
+                <FormField
+                  key={stepField.name}
+                  control={form.control}
+                  name={stepField.name}
+                  render={({ field }) => (
+                    <FormItem>
+                      <FormLabel>{stepField.label}</FormLabel>
+                      <FormControl>
+                        <Input
+                          type={stepField.type ?? "text"}
+                          autoComplete={stepField.autoComplete}
+                          placeholder={stepField.placeholder}
+                          {...field}
+                        />
+                      </FormControl>
+                      <FormMessage />
+                    </FormItem>
+                  )}
+                />
+              ))}
+            </div>
+
+            {isLastStep && (
+              <dl className="grid gap-4 rounded-lg border bg-muted/30 p-4 sm:grid-cols-2">
+                <div>
+                  <dt className="text-sm text-muted-foreground">Full name</dt>
+                  <dd className="font-medium">{profile.fullName}</dd>
+                </div>
+                <div>
+                  <dt className="text-sm text-muted-foreground">Email</dt>
+                  <dd className="break-all font-medium">{profile.email}</dd>
+                </div>
+                <div>
+                  <dt className="text-sm text-muted-foreground">Company</dt>
+                  <dd className="font-medium">{profile.company}</dd>
+                </div>
+                <div>
+                  <dt className="text-sm text-muted-foreground">Role</dt>
+                  <dd className="font-medium">{profile.role}</dd>
+                </div>
+              </dl>
+            )}
+          </form>
+        </Form>
+      </CardContent>
+
+      <CardFooter className="justify-between border-t">
+        <Button
+          type="button"
+          variant="outline"
+          onClick={handlePrevious}
+          disabled={isFirstStep}
+        >
+          Back
+        </Button>
+        <Button type="submit" form="profile-setup-form">
+          {isLastStep ? "Complete setup" : "Continue"}
+        </Button>
+      </CardFooter>
+    </Card>
+  )
+}
diff --git a/frontend/src/routes/_layout/index.tsx b/frontend/src/routes/_layout/index.tsx
index 3e640cb..aa5a79a 100644
--- a/frontend/src/routes/_layout/index.tsx
+++ b/frontend/src/routes/_layout/index.tsx
@@ -1,6 +1,11 @@
 import { createFileRoute } from "@tanstack/react-router"
 
+import {
+  MultiStepForm,
+  type ProfileSetupData,
+} from "@/components/Common/MultiStepForm"
 import useAuth from "@/hooks/useAuth"
+import useCustomToast from "@/hooks/useCustomToast"
 
 export const Route = createFileRoute("/_layout/")({
   component: Dashboard,
@@ -15,9 +20,14 @@ export const Route = createFileRoute("/_layout/")({
 
 function Dashboard() {
   const { user: currentUser } = useAuth()
+  const { showSuccessToast } = useCustomToast()
+
+  const handleProfileSetup = (data: ProfileSetupData) => {
+    showSuccessToast(`${data.fullName}, your profile setup is complete.`)
+  }
 
   return (
-    <div>
+    <div className="space-y-8">
       <div>
         <h1 className="text-2xl truncate max-w-sm">
           Hi, {currentUser?.full_name || currentUser?.email} 👋
@@ -26,6 +36,7 @@ function Dashboard() {
           Welcome back, nice to see you again!!!
         </p>
       </div>
+      <MultiStepForm onComplete={handleProfileSetup} />
     </div>
   )
 }
```

### Candidate E

- Agent completed: `True`
- Frontend build passed: `True`

```diff
diff --git a/frontend/src/components/Common/MultiStepForm.tsx b/frontend/src/components/Common/MultiStepForm.tsx
new file mode 100644
index 0000000..8ba629d
--- /dev/null
+++ b/frontend/src/components/Common/MultiStepForm.tsx
@@ -0,0 +1,119 @@
+import { Check } from "lucide-react"
+import { type FormEvent, type ReactNode, useState } from "react"
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
+export interface MultiStepFormStep {
+  content: ReactNode
+  description?: string
+  title: string
+}
+
+interface MultiStepFormProps {
+  className?: string
+  onSubmit: (event: FormEvent<HTMLFormElement>) => void
+  steps: readonly [MultiStepFormStep, ...MultiStepFormStep[]]
+}
+
+const MultiStepForm = ({ className, onSubmit, steps }: MultiStepFormProps) => {
+  const [currentStepIndex, setCurrentStepIndex] = useState(0)
+  const currentStep = steps[currentStepIndex]
+  const isLastStep = currentStepIndex === steps.length - 1
+
+  const handleBack = () => {
+    setCurrentStepIndex((stepIndex) => stepIndex - 1)
+  }
+
+  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
+    event.preventDefault()
+
+    if (isLastStep) {
+      onSubmit(event)
+      return
+    }
+
+    setCurrentStepIndex((stepIndex) => stepIndex + 1)
+  }
+
+  return (
+    <Card className={cn("w-full", className)}>
+      <CardHeader className="gap-6">
+        <nav aria-label="Form progress">
+          <ol className="flex overflow-x-auto pb-2">
+            {steps.map((step, stepIndex) => {
+              const isCompleted = stepIndex < currentStepIndex
+              const isCurrent = stepIndex === currentStepIndex
+
+              return (
+                <li
+                  key={stepIndex}
+                  aria-current={isCurrent ? "step" : undefined}
+                  className={cn(
+                    "flex min-w-32 flex-1 items-start gap-3 border-t-2 pt-3",
+                    stepIndex <= currentStepIndex
+                      ? "border-primary"
+                      : "border-muted",
+                  )}
+                >
+                  <span
+                    className={cn(
+                      "flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold",
+                      isCurrent && "bg-primary text-primary-foreground",
+                      isCompleted && "bg-primary/15 text-primary",
+                      !isCurrent &&
+                        !isCompleted &&
+                        "bg-muted text-muted-foreground",
+                    )}
+                    aria-hidden="true"
+                  >
+                    {isCompleted ? <Check className="size-4" /> : stepIndex + 1}
+                  </span>
+                  <span
+                    className={cn(
+                      "pr-4 text-sm font-medium",
+                      !isCurrent && "text-muted-foreground",
+                    )}
+                  >
+                    {step.title}
+                  </span>
+                </li>
+              )
+            })}
+          </ol>
+        </nav>
+        <div className="space-y-2" aria-live="polite">
+          <CardTitle>
+            <h2>{currentStep.title}</h2>
+          </CardTitle>
+          {currentStep.description && (
+            <CardDescription>{currentStep.description}</CardDescription>
+          )}
+        </div>
+      </CardHeader>
+      <form onSubmit={handleSubmit} aria-label={currentStep.title}>
+        <CardContent>{currentStep.content}</CardContent>
+        <CardFooter className="mt-6 justify-between border-t">
+          <div>
+            {currentStepIndex > 0 && (
+              <Button type="button" variant="outline" onClick={handleBack}>
+                Back
+              </Button>
+            )}
+          </div>
+          <Button type="submit">{isLastStep ? "Submit" : "Next"}</Button>
+        </CardFooter>
+      </form>
+    </Card>
+  )
+}
+
+export default MultiStepForm
```

### Candidate F

- Agent completed: `True`
- Frontend build passed: `True`

```diff
diff --git a/frontend/src/components/Common/WorkspaceSetupWizard.tsx b/frontend/src/components/Common/WorkspaceSetupWizard.tsx
new file mode 100644
index 0000000..3935c93
--- /dev/null
+++ b/frontend/src/components/Common/WorkspaceSetupWizard.tsx
@@ -0,0 +1,488 @@
+import { zodResolver } from "@hookform/resolvers/zod"
+import {
+  ArrowLeft,
+  ArrowRight,
+  Check,
+  CheckCircle2,
+  Settings2,
+  Sparkles,
+  Users,
+} from "lucide-react"
+import { type FormEvent, useState } from "react"
+import { type FieldPath, useForm } from "react-hook-form"
+import { z } from "zod"
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
+import { Checkbox } from "@/components/ui/checkbox"
+import {
+  Form,
+  FormControl,
+  FormDescription,
+  FormField,
+  FormItem,
+  FormLabel,
+  FormMessage,
+} from "@/components/ui/form"
+import { Input } from "@/components/ui/input"
+import {
+  Select,
+  SelectContent,
+  SelectGroup,
+  SelectItem,
+  SelectTrigger,
+  SelectValue,
+} from "@/components/ui/select"
+import { cn } from "@/lib/utils"
+
+const workspaceSetupSchema = z.object({
+  workspaceName: z
+    .string()
+    .trim()
+    .min(2, "Workspace name must be at least 2 characters")
+    .max(60, "Workspace name must be 60 characters or fewer"),
+  website: z.union([
+    z.literal(""),
+    z.url("Enter a complete URL, such as https://example.com"),
+  ]),
+  teamSize: z.enum(["just-me", "2-10", "11-50", "51-plus"], {
+    message: "Select a team size",
+  }),
+  primaryGoal: z.enum(["projects", "clients", "operations", "other"], {
+    message: "Select a primary goal",
+  }),
+  receiveProductTips: z.boolean(),
+})
+
+export type WorkspaceSetupValues = z.infer<typeof workspaceSetupSchema>
+
+type WizardStep = {
+  title: string
+  description: string
+  fields: FieldPath<WorkspaceSetupValues>[]
+  icon: typeof Settings2
+}
+
+const wizardSteps: WizardStep[] = [
+  {
+    title: "Workspace",
+    description: "Name your new workspace",
+    fields: ["workspaceName", "website"],
+    icon: Settings2,
+  },
+  {
+    title: "Preferences",
+    description: "Tailor it to your team",
+    fields: ["teamSize", "primaryGoal", "receiveProductTips"],
+    icon: Users,
+  },
+  {
+    title: "Review",
+    description: "Confirm your choices",
+    fields: [],
+    icon: Sparkles,
+  },
+]
+
+const teamSizeLabels: Record<WorkspaceSetupValues["teamSize"], string> = {
+  "just-me": "Just me",
+  "2-10": "2–10 people",
+  "11-50": "11–50 people",
+  "51-plus": "51+ people",
+}
+
+const primaryGoalLabels: Record<WorkspaceSetupValues["primaryGoal"], string> = {
+  projects: "Plan and deliver projects",
+  clients: "Manage client work",
+  operations: "Run team operations",
+  other: "Something else",
+}
+
+const defaultValues: WorkspaceSetupValues = {
+  workspaceName: "",
+  website: "",
+  teamSize: "just-me",
+  primaryGoal: "projects",
+  receiveProductTips: true,
+}
+
+type StepIndicatorProps = {
+  currentStepIndex: number
+}
+
+function StepIndicator({ currentStepIndex }: StepIndicatorProps) {
+  return (
+    <nav aria-label="Workspace setup progress">
+      <ol className="grid grid-cols-3 gap-2">
+        {wizardSteps.map((step, stepIndex) => {
+          const isCurrent = currentStepIndex === stepIndex
+          const isComplete = currentStepIndex > stepIndex
+          const StepIcon = step.icon
+
+          return (
+            <li
+              key={step.title}
+              aria-current={isCurrent ? "step" : undefined}
+              className="relative flex min-w-0 flex-col items-center gap-2 text-center"
+            >
+              {stepIndex < wizardSteps.length - 1 ? (
+                <span
+                  aria-hidden="true"
+                  className={cn(
+                    "absolute top-4 left-[calc(50%+1rem)] h-px w-[calc(100%-2rem)] bg-border",
+                    isComplete && "bg-primary",
+                  )}
+                />
+              ) : null}
+              <span
+                className={cn(
+                  "relative flex size-8 items-center justify-center rounded-full border bg-background text-muted-foreground",
+                  isCurrent &&
+                    "border-primary text-primary ring-4 ring-primary/10",
+                  isComplete &&
+                    "border-primary bg-primary text-primary-foreground",
+                )}
+              >
+                {isComplete ? (
+                  <Check className="size-4" aria-hidden="true" />
+                ) : (
+                  <StepIcon className="size-4" aria-hidden="true" />
+                )}
+              </span>
+              <span className="min-w-0">
+                <span
+                  className={cn(
+                    "block truncate text-xs font-medium text-muted-foreground sm:text-sm",
+                    (isCurrent || isComplete) && "text-foreground",
+                  )}
+                >
+                  {step.title}
+                </span>
+                <span className="sr-only">{step.description}</span>
+              </span>
+            </li>
+          )
+        })}
+      </ol>
+    </nav>
+  )
+}
+
+type WorkspaceSetupWizardProps = {
+  onComplete?: (values: WorkspaceSetupValues) => void
+}
+
+export function WorkspaceSetupWizard({
+  onComplete,
+}: WorkspaceSetupWizardProps) {
+  const [currentStepIndex, setCurrentStepIndex] = useState(0)
+  const [isComplete, setIsComplete] = useState(false)
+  const form = useForm<WorkspaceSetupValues>({
+    resolver: zodResolver(workspaceSetupSchema),
+    mode: "onBlur",
+    defaultValues,
+  })
+
+  const currentStep = wizardSteps[currentStepIndex]
+  const isFinalStep = currentStepIndex === wizardSteps.length - 1
+
+  const handleNext = async () => {
+    const isStepValid = await form.trigger(currentStep.fields, {
+      shouldFocus: true,
+    })
+
+    if (isStepValid) {
+      setCurrentStepIndex((stepIndex) =>
+        Math.min(stepIndex + 1, wizardSteps.length - 1),
+      )
+    }
+  }
+
+  const handleBack = () => {
+    setCurrentStepIndex((stepIndex) => Math.max(stepIndex - 1, 0))
+  }
+
+  const handleComplete = (values: WorkspaceSetupValues) => {
+    onComplete?.(values)
+    setIsComplete(true)
+  }
+
+  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
+    event.preventDefault()
+
+    if (isFinalStep) {
+      await form.handleSubmit(handleComplete)()
+      return
+    }
+
+    await handleNext()
+  }
+
+  const handleReset = () => {
+    form.reset(defaultValues)
+    setCurrentStepIndex(0)
+    setIsComplete(false)
+  }
+
+  if (isComplete) {
+    return (
+      <Card className="mx-auto w-full max-w-3xl">
+        <CardContent className="flex flex-col items-center gap-5 py-10 text-center sm:py-14">
+          <span className="flex size-14 items-center justify-center rounded-full bg-primary/10 text-primary">
+            <CheckCircle2 className="size-7" aria-hidden="true" />
+          </span>
+          <div className="flex max-w-md flex-col gap-2">
+            <h2 className="text-2xl font-semibold tracking-tight">
+              Your workspace is ready
+            </h2>
+            <p className="text-sm text-muted-foreground sm:text-base">
+              {form.getValues("workspaceName")} has been configured with your
+              team preferences.
+            </p>
+          </div>
+          <Button type="button" onClick={handleReset}>
+            Set up another workspace
+            <ArrowRight data-icon="inline-end" />
+          </Button>
+        </CardContent>
+      </Card>
+    )
+  }
+
+  return (
+    <Card className="mx-auto w-full max-w-3xl overflow-hidden">
+      <CardHeader className="border-b bg-muted/30">
+        <CardTitle>Set up your workspace</CardTitle>
+        <CardDescription>
+          A few quick details will help us personalize your experience.
+        </CardDescription>
+        <div className="pt-4">
+          <StepIndicator currentStepIndex={currentStepIndex} />
+        </div>
+      </CardHeader>
+
+      <Form {...form}>
+        <form onSubmit={handleSubmit} noValidate>
+          <CardContent className="min-h-80 py-7 sm:py-9">
+            <div className="mb-7 flex flex-col gap-1">
+              <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
+                Step {currentStepIndex + 1} of {wizardSteps.length}
+              </p>
+              <h2 className="text-xl font-semibold tracking-tight">
+                {currentStep.title}
+              </h2>
+              <p className="text-sm text-muted-foreground">
+                {currentStep.description}
+              </p>
+            </div>
+
+            {currentStepIndex === 0 ? (
+              <div className="grid gap-5 sm:grid-cols-2">
+                <FormField
+                  control={form.control}
+                  name="workspaceName"
+                  render={({ field }) => (
+                    <FormItem className="sm:col-span-2">
+                      <FormLabel>Workspace name</FormLabel>
+                      <FormControl>
+                        <Input
+                          type="text"
+                          placeholder="Acme Studio"
+                          autoComplete="organization"
+                          {...field}
+                        />
+                      </FormControl>
+                      <FormDescription>
+                        This is the name your team will see.
+                      </FormDescription>
+                      <FormMessage />
+                    </FormItem>
+                  )}
+                />
+                <FormField
+                  control={form.control}
+                  name="website"
+                  render={({ field }) => (
+                    <FormItem className="sm:col-span-2">
+                      <FormLabel>Website</FormLabel>
+                      <FormControl>
+                        <Input
+                          type="url"
+                          placeholder="https://example.com"
+                          autoComplete="url"
+                          {...field}
+                        />
+                      </FormControl>
+                      <FormDescription>Optional</FormDescription>
+                      <FormMessage />
+                    </FormItem>
+                  )}
+                />
+              </div>
+            ) : null}
+
+            {currentStepIndex === 1 ? (
+              <div className="grid gap-5 sm:grid-cols-2">
+                <FormField
+                  control={form.control}
+                  name="teamSize"
+                  render={({ field }) => (
+                    <FormItem>
+                      <FormLabel>Team size</FormLabel>
+                      <Select
+                        value={field.value}
+                        onValueChange={field.onChange}
+                      >
+                        <FormControl>
+                          <SelectTrigger className="w-full">
+                            <SelectValue placeholder="Select a team size" />
+                          </SelectTrigger>
+                        </FormControl>
+                        <SelectContent>
+                          <SelectGroup>
+                            {Object.entries(teamSizeLabels).map(
+                              ([value, label]) => (
+                                <SelectItem key={value} value={value}>
+                                  {label}
+                                </SelectItem>
+                              ),
+                            )}
+                          </SelectGroup>
+                        </SelectContent>
+                      </Select>
+                      <FormMessage />
+                    </FormItem>
+                  )}
+                />
+                <FormField
+                  control={form.control}
+                  name="primaryGoal"
+                  render={({ field }) => (
+                    <FormItem>
+                      <FormLabel>Primary goal</FormLabel>
+                      <Select
+                        value={field.value}
+                        onValueChange={field.onChange}
+                      >
+                        <FormControl>
+                          <SelectTrigger className="w-full">
+                            <SelectValue placeholder="Select a goal" />
+                          </SelectTrigger>
+                        </FormControl>
+                        <SelectContent>
+                          <SelectGroup>
+                            {Object.entries(primaryGoalLabels).map(
+                              ([value, label]) => (
+                                <SelectItem key={value} value={value}>
+                                  {label}
+                                </SelectItem>
+                              ),
+                            )}
+                          </SelectGroup>
+                        </SelectContent>
+                      </Select>
+                      <FormMessage />
+                    </FormItem>
+                  )}
+                />
+                <FormField
+                  control={form.control}
+                  name="receiveProductTips"
+                  render={({ field }) => (
+                    <FormItem className="flex items-start gap-3 rounded-lg border p-4 sm:col-span-2">
+                      <FormControl>
+                        <Checkbox
+                          checked={field.value}
+                          onCheckedChange={field.onChange}
+                        />
+                      </FormControl>
+                      <div className="grid gap-1 leading-none">
+                        <FormLabel className="font-medium">
+                          Send me workspace tips
+                        </FormLabel>
+                        <FormDescription>
+                          Get occasional guidance for making the most of your
+                          workspace.
+                        </FormDescription>
+                      </div>
+                    </FormItem>
+                  )}
+                />
+              </div>
+            ) : null}
+
+            {currentStepIndex === 2 ? (
+              <dl className="grid gap-5 rounded-lg border bg-muted/20 p-5 sm:grid-cols-2 sm:p-6">
+                <div className="grid gap-1">
+                  <dt className="text-sm text-muted-foreground">
+                    Workspace name
+                  </dt>
+                  <dd className="font-medium">
+                    {form.getValues("workspaceName")}
+                  </dd>
+                </div>
+                <div className="grid gap-1">
+                  <dt className="text-sm text-muted-foreground">Website</dt>
+                  <dd className="break-words font-medium">
+                    {form.getValues("website") || "Not provided"}
+                  </dd>
+                </div>
+                <div className="grid gap-1">
+                  <dt className="text-sm text-muted-foreground">Team size</dt>
+                  <dd className="font-medium">
+                    {teamSizeLabels[form.getValues("teamSize")]}
+                  </dd>
+                </div>
+                <div className="grid gap-1">
+                  <dt className="text-sm text-muted-foreground">
+                    Primary goal
+                  </dt>
+                  <dd className="font-medium">
+                    {primaryGoalLabels[form.getValues("primaryGoal")]}
+                  </dd>
+                </div>
+                <div className="grid gap-1 sm:col-span-2">
+                  <dt className="text-sm text-muted-foreground">
+                    Workspace tips
+                  </dt>
+                  <dd className="font-medium">
+                    {form.getValues("receiveProductTips")
+                      ? "Subscribed"
+                      : "Not subscribed"}
+                  </dd>
+                </div>
+              </dl>
+            ) : null}
+          </CardContent>
+
+          <CardFooter className="justify-between gap-3 border-t bg-muted/20 py-5">
+            <Button
+              type="button"
+              variant="ghost"
+              onClick={handleBack}
+              disabled={currentStepIndex === 0}
+            >
+              <ArrowLeft data-icon="inline-start" />
+              Back
+            </Button>
+            <Button type="submit">
+              {isFinalStep ? "Create workspace" : "Continue"}
+              {isFinalStep ? (
+                <Check data-icon="inline-end" />
+              ) : (
+                <ArrowRight data-icon="inline-end" />
+              )}
+            </Button>
+          </CardFooter>
+        </form>
+      </Form>
+    </Card>
+  )
+}
diff --git a/frontend/src/routes/_layout/index.tsx b/frontend/src/routes/_layout/index.tsx
index 3e640cb..f7a96b4 100644
--- a/frontend/src/routes/_layout/index.tsx
+++ b/frontend/src/routes/_layout/index.tsx
@@ -1,5 +1,6 @@
 import { createFileRoute } from "@tanstack/react-router"
 
+import { WorkspaceSetupWizard } from "@/components/Common/WorkspaceSetupWizard"
 import useAuth from "@/hooks/useAuth"
 
 export const Route = createFileRoute("/_layout/")({
@@ -17,8 +18,8 @@ function Dashboard() {
   const { user: currentUser } = useAuth()
 
   return (
-    <div>
-      <div>
+    <div className="flex flex-col gap-8">
+      <div className="flex flex-col gap-1">
         <h1 className="text-2xl truncate max-w-sm">
           Hi, {currentUser?.full_name || currentUser?.email} 👋
         </h1>
@@ -26,6 +27,7 @@ function Dashboard() {
           Welcome back, nice to see you again!!!
         </p>
       </div>
+      <WorkspaceSetupWizard />
     </div>
   )
 }
```

## Output

Return JSON matching the supplied schema. Include every candidate exactly once. Use only these exact one-letter values for `id`: A, B, C, D, E, F. 
For evidence, cite concrete files or code choices from the diff and do not guess the hidden condition.
