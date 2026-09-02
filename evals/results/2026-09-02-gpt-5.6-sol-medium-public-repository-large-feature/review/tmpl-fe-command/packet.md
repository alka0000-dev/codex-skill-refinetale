# Blind implementation review

## Ticket

Add a command palette (searchable command menu) to the frontend.

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
diff --git a/frontend/src/components/Common/CommandPalette.tsx b/frontend/src/components/Common/CommandPalette.tsx
new file mode 100644
index 0000000..0625d67
--- /dev/null
+++ b/frontend/src/components/Common/CommandPalette.tsx
@@ -0,0 +1,292 @@
+import { useNavigate } from "@tanstack/react-router"
+import {
+  ArrowDown,
+  ArrowUp,
+  Briefcase,
+  CornerDownLeft,
+  Home,
+  type LucideIcon,
+  Search,
+  Settings,
+  Users,
+} from "lucide-react"
+import { useEffect, useState } from "react"
+
+import { Button } from "@/components/ui/button"
+import {
+  Dialog,
+  DialogContent,
+  DialogDescription,
+  DialogHeader,
+  DialogTitle,
+} from "@/components/ui/dialog"
+import { Input } from "@/components/ui/input"
+import { cn } from "@/lib/utils"
+
+type CommandDestination = "/" | "/items" | "/admin" | "/settings"
+
+type NavigationCommand = {
+  id: string
+  title: string
+  description: string
+  destination: CommandDestination
+  icon: LucideIcon
+  keywords: string[]
+  requiresSuperuser?: boolean
+}
+
+const navigationCommands: NavigationCommand[] = [
+  {
+    id: "dashboard",
+    title: "Dashboard",
+    description: "Go to your dashboard",
+    destination: "/",
+    icon: Home,
+    keywords: ["home", "overview"],
+  },
+  {
+    id: "items",
+    title: "Items",
+    description: "View and manage items",
+    destination: "/items",
+    icon: Briefcase,
+    keywords: ["list", "manage"],
+  },
+  {
+    id: "settings",
+    title: "User Settings",
+    description: "Manage your profile and password",
+    destination: "/settings",
+    icon: Settings,
+    keywords: ["account", "profile", "password"],
+  },
+  {
+    id: "admin",
+    title: "Admin",
+    description: "Manage application users",
+    destination: "/admin",
+    icon: Users,
+    keywords: ["users", "people"],
+    requiresSuperuser: true,
+  },
+]
+
+interface CommandPaletteProps {
+  isSuperuser: boolean
+}
+
+export function CommandPalette({ isSuperuser }: CommandPaletteProps) {
+  const navigate = useNavigate()
+  const [isOpen, setIsOpen] = useState(false)
+  const [query, setQuery] = useState("")
+  const [activeIndex, setActiveIndex] = useState(0)
+
+  const availableCommands = navigationCommands.filter(
+    (command) => !command.requiresSuperuser || isSuperuser,
+  )
+  const normalizedQuery = query.trim().toLowerCase()
+  const filteredCommands = normalizedQuery
+    ? availableCommands.filter((command) =>
+        [command.title, command.description, ...command.keywords]
+          .join(" ")
+          .toLowerCase()
+          .includes(normalizedQuery),
+      )
+    : availableCommands
+
+  useEffect(() => {
+    const handleShortcut = (event: KeyboardEvent) => {
+      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
+        event.preventDefault()
+        setIsOpen((currentIsOpen) => !currentIsOpen)
+        setQuery("")
+        setActiveIndex(0)
+      }
+    }
+
+    document.addEventListener("keydown", handleShortcut)
+    return () => document.removeEventListener("keydown", handleShortcut)
+  }, [])
+
+  const handleOpenChange = (nextIsOpen: boolean) => {
+    setIsOpen(nextIsOpen)
+    if (!nextIsOpen) {
+      setQuery("")
+      setActiveIndex(0)
+    }
+  }
+
+  const runCommand = (command: NavigationCommand) => {
+    handleOpenChange(false)
+    navigate({ to: command.destination })
+  }
+
+  const handleInputKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
+    if (event.key === "ArrowDown") {
+      event.preventDefault()
+      setActiveIndex((currentIndex) =>
+        filteredCommands.length > 0
+          ? (currentIndex + 1) % filteredCommands.length
+          : 0,
+      )
+      return
+    }
+
+    if (event.key === "ArrowUp") {
+      event.preventDefault()
+      setActiveIndex((currentIndex) =>
+        filteredCommands.length > 0
+          ? (currentIndex - 1 + filteredCommands.length) %
+            filteredCommands.length
+          : 0,
+      )
+      return
+    }
+
+    if (event.key === "Enter") {
+      event.preventDefault()
+      const selectedCommand = filteredCommands[activeIndex]
+      if (selectedCommand) {
+        runCommand(selectedCommand)
+      }
+    }
+  }
+
+  const handleQueryChange = (event: React.ChangeEvent<HTMLInputElement>) => {
+    setQuery(event.target.value)
+    setActiveIndex(0)
+  }
+
+  const activeCommandId = filteredCommands[activeIndex]?.id
+    ? `command-${filteredCommands[activeIndex].id}`
+    : undefined
+
+  return (
+    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
+      <Button
+        type="button"
+        variant="outline"
+        className="ml-auto min-w-0 max-w-sm flex-1 justify-start text-muted-foreground"
+        aria-label="Open command palette"
+        aria-keyshortcuts="Meta+K Control+K"
+        onClick={() => handleOpenChange(true)}
+      >
+        <Search data-icon="inline-start" />
+        <span className="truncate">Search commands...</span>
+        <kbd className="ml-auto hidden rounded border bg-muted px-1.5 py-0.5 font-mono text-xs sm:inline-flex">
+          ⌘K
+        </kbd>
+      </Button>
+
+      <DialogContent
+        className="gap-0 overflow-hidden p-0 sm:max-w-xl"
+        showCloseButton={false}
+      >
+        <DialogHeader className="sr-only">
+          <DialogTitle>Command palette</DialogTitle>
+          <DialogDescription>
+            Search for a page, then select a command to navigate.
+          </DialogDescription>
+        </DialogHeader>
+
+        <div className="flex items-center gap-2 border-b px-3">
+          <Search className="size-4 shrink-0 text-muted-foreground" />
+          <Input
+            autoFocus
+            value={query}
+            role="combobox"
+            aria-autocomplete="list"
+            aria-controls="command-palette-results"
+            aria-expanded={isOpen}
+            aria-activedescendant={activeCommandId}
+            placeholder="Search pages and settings..."
+            className="h-12 border-0 px-0 shadow-none focus-visible:ring-0"
+            onChange={handleQueryChange}
+            onKeyDown={handleInputKeyDown}
+          />
+        </div>
+
+        <div className="max-h-80 overflow-y-auto p-2">
+          {filteredCommands.length > 0 ? (
+            <div className="flex flex-col gap-1">
+              <p className="px-2 py-1.5 text-xs font-medium text-muted-foreground">
+                Navigation
+              </p>
+              <div
+                id="command-palette-results"
+                role="listbox"
+                aria-label="Commands"
+                className="flex flex-col gap-1"
+              >
+                {filteredCommands.map((command, index) => {
+                  const isActive = index === activeIndex
+
+                  return (
+                    <Button
+                      key={command.id}
+                      id={`command-${command.id}`}
+                      type="button"
+                      role="option"
+                      aria-selected={isActive}
+                      variant="ghost"
+                      className={cn(
+                        "h-auto w-full justify-start px-3 py-2.5",
+                        isActive && "bg-accent text-accent-foreground",
+                      )}
+                      onClick={() => runCommand(command)}
+                      onMouseEnter={() => setActiveIndex(index)}
+                    >
+                      <command.icon data-icon="inline-start" />
+                      <span className="flex min-w-0 flex-col items-start gap-0.5">
+                        <span>{command.title}</span>
+                        <span className="truncate text-xs font-normal text-muted-foreground">
+                          {command.description}
+                        </span>
+                      </span>
+                    </Button>
+                  )
+                })}
+              </div>
+            </div>
+          ) : (
+            <div>
+              <div
+                id="command-palette-results"
+                role="listbox"
+                aria-label="Commands"
+              />
+              <p
+                role="status"
+                className="px-3 py-10 text-center text-sm text-muted-foreground"
+              >
+                No commands found.
+              </p>
+            </div>
+          )}
+        </div>
+
+        <div className="hidden items-center justify-end gap-3 border-t bg-muted/40 px-3 py-2 text-xs text-muted-foreground sm:flex">
+          <span className="flex items-center gap-1">
+            <kbd className="flex rounded border bg-background p-1">
+              <ArrowUp className="size-3" />
+              <ArrowDown className="size-3" />
+            </kbd>
+            Navigate
+          </span>
+          <span className="flex items-center gap-1">
+            <kbd className="flex rounded border bg-background p-1">
+              <CornerDownLeft className="size-3" />
+            </kbd>
+            Open
+          </span>
+          <span className="flex items-center gap-1">
+            <kbd className="rounded border bg-background px-1.5 py-1 font-mono">
+              Esc
+            </kbd>
+            Close
+          </span>
+        </div>
+      </DialogContent>
+    </Dialog>
+  )
+}
diff --git a/frontend/src/routes/_layout.tsx b/frontend/src/routes/_layout.tsx
index 1697305..a128b74 100644
--- a/frontend/src/routes/_layout.tsx
+++ b/frontend/src/routes/_layout.tsx
@@ -1,5 +1,6 @@
 import { createFileRoute, Outlet, redirect } from "@tanstack/react-router"
 
+import { CommandPalette } from "@/components/Common/CommandPalette"
 import { Footer } from "@/components/Common/Footer"
 import AppSidebar from "@/components/Sidebar/AppSidebar"
 import {
@@ -7,7 +8,7 @@ import {
   SidebarProvider,
   SidebarTrigger,
 } from "@/components/ui/sidebar"
-import { isLoggedIn } from "@/hooks/useAuth"
+import useAuth, { isLoggedIn } from "@/hooks/useAuth"
 
 export const Route = createFileRoute("/_layout")({
   component: Layout,
@@ -21,12 +22,15 @@ export const Route = createFileRoute("/_layout")({
 })
 
 function Layout() {
+  const { user: currentUser } = useAuth()
+
   return (
     <SidebarProvider>
       <AppSidebar />
       <SidebarInset>
         <header className="sticky top-0 z-10 flex h-16 shrink-0 items-center gap-2 border-b px-4">
           <SidebarTrigger className="-ml-1 text-muted-foreground" />
+          <CommandPalette isSuperuser={currentUser?.is_superuser ?? false} />
         </header>
         <main className="flex-1 p-6 md:p-8">
           <div className="mx-auto max-w-7xl">
```

### Candidate B

- Agent completed: `True`
- Frontend build passed: `True`

```diff
diff --git a/frontend/src/components/Common/CommandPalette.tsx b/frontend/src/components/Common/CommandPalette.tsx
new file mode 100644
index 0000000..e297f3a
--- /dev/null
+++ b/frontend/src/components/Common/CommandPalette.tsx
@@ -0,0 +1,258 @@
+import { useNavigate } from "@tanstack/react-router"
+import {
+  ArrowDown,
+  ArrowUp,
+  Briefcase,
+  CornerDownLeft,
+  Home,
+  type LucideIcon,
+  Search,
+  Settings,
+  Users,
+} from "lucide-react"
+import { useEffect, useMemo, useState } from "react"
+
+import { Button } from "@/components/ui/button"
+import {
+  Dialog,
+  DialogContent,
+  DialogDescription,
+  DialogTitle,
+  DialogTrigger,
+} from "@/components/ui/dialog"
+import useAuth from "@/hooks/useAuth"
+import { cn } from "@/lib/utils"
+
+interface Command {
+  id: string
+  icon: LucideIcon
+  label: string
+  description: string
+  searchTerms: string[]
+  run: () => void
+}
+
+export function CommandPalette() {
+  const navigate = useNavigate()
+  const { user: currentUser } = useAuth()
+  const [isOpen, setIsOpen] = useState(false)
+  const [query, setQuery] = useState("")
+  const [selectedIndex, setSelectedIndex] = useState(0)
+
+  const commands = useMemo<Command[]>(
+    () => [
+      {
+        id: "dashboard",
+        icon: Home,
+        label: "Dashboard",
+        description: "Go to your dashboard",
+        searchTerms: ["dashboard", "home", "overview"],
+        run: () => navigate({ to: "/" }),
+      },
+      {
+        id: "items",
+        icon: Briefcase,
+        label: "Items",
+        description: "View and manage items",
+        searchTerms: ["items", "manage", "list"],
+        run: () => navigate({ to: "/items" }),
+      },
+      {
+        id: "settings",
+        icon: Settings,
+        label: "User Settings",
+        description: "Manage your account settings",
+        searchTerms: ["settings", "account", "profile", "password"],
+        run: () => navigate({ to: "/settings" }),
+      },
+      ...(currentUser?.is_superuser
+        ? [
+            {
+              id: "admin",
+              icon: Users,
+              label: "Admin",
+              description: "Manage users",
+              searchTerms: ["admin", "users", "manage"],
+              run: () => navigate({ to: "/admin" }),
+            },
+          ]
+        : []),
+    ],
+    [currentUser?.is_superuser, navigate],
+  )
+
+  const normalizedQuery = query.trim().toLocaleLowerCase()
+  const filteredCommands = commands.filter(
+    (command) =>
+      normalizedQuery.length === 0 ||
+      [command.label, command.description, ...command.searchTerms]
+        .join(" ")
+        .toLocaleLowerCase()
+        .includes(normalizedQuery),
+  )
+
+  useEffect(() => {
+    const handleShortcut = (event: KeyboardEvent) => {
+      if (
+        event.key.toLocaleLowerCase() === "k" &&
+        (event.metaKey || event.ctrlKey)
+      ) {
+        event.preventDefault()
+        setIsOpen((isCurrentlyOpen) => !isCurrentlyOpen)
+      }
+    }
+
+    document.addEventListener("keydown", handleShortcut)
+    return () => document.removeEventListener("keydown", handleShortcut)
+  }, [])
+
+  useEffect(() => {
+    if (!isOpen) {
+      setQuery("")
+      setSelectedIndex(0)
+    }
+  }, [isOpen])
+
+  const runCommand = (command: Command) => {
+    command.run()
+    setIsOpen(false)
+  }
+
+  const handleInputKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
+    if (filteredCommands.length === 0 || event.nativeEvent.isComposing) {
+      return
+    }
+
+    if (event.key === "ArrowDown") {
+      event.preventDefault()
+      setSelectedIndex((currentIndex) =>
+        currentIndex === filteredCommands.length - 1 ? 0 : currentIndex + 1,
+      )
+    }
+
+    if (event.key === "ArrowUp") {
+      event.preventDefault()
+      setSelectedIndex((currentIndex) =>
+        currentIndex === 0 ? filteredCommands.length - 1 : currentIndex - 1,
+      )
+    }
+
+    if (event.key === "Enter") {
+      event.preventDefault()
+      const selectedCommand = filteredCommands[selectedIndex]
+      if (selectedCommand) {
+        runCommand(selectedCommand)
+      }
+    }
+  }
+
+  return (
+    <Dialog open={isOpen} onOpenChange={setIsOpen}>
+      <DialogTrigger asChild>
+        <Button
+          type="button"
+          variant="outline"
+          className="ml-auto h-9 w-9 justify-center p-0 text-muted-foreground shadow-none sm:w-full sm:max-w-64 sm:justify-start sm:px-3"
+          aria-label="Open command palette"
+        >
+          <Search className="size-4" />
+          <span className="hidden sm:inline">Search commands</span>
+          <kbd className="ml-auto hidden rounded border bg-muted px-1.5 py-0.5 font-mono text-[10px] font-medium sm:inline-flex">
+            ⌘K
+          </kbd>
+        </Button>
+      </DialogTrigger>
+      <DialogContent
+        className="top-[20%] max-w-xl translate-y-0 gap-0 overflow-hidden p-0"
+        showCloseButton={false}
+      >
+        <DialogTitle className="sr-only">Command palette</DialogTitle>
+        <DialogDescription className="sr-only">
+          Search for a command, then use the arrow keys and Enter to run it.
+        </DialogDescription>
+        <div className="flex items-center gap-3 border-b px-4">
+          <Search className="size-5 shrink-0 text-muted-foreground" />
+          <input
+            type="search"
+            role="combobox"
+            aria-autocomplete="list"
+            aria-controls="command-palette-results"
+            aria-expanded={isOpen}
+            aria-activedescendant={
+              filteredCommands[selectedIndex]
+                ? `command-${filteredCommands[selectedIndex].id}`
+                : undefined
+            }
+            autoComplete="off"
+            autoFocus
+            className="h-14 w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
+            placeholder="Type a command or search…"
+            value={query}
+            onChange={(event) => {
+              setQuery(event.target.value)
+              setSelectedIndex(0)
+            }}
+            onKeyDown={handleInputKeyDown}
+          />
+        </div>
+        <div
+          id="command-palette-results"
+          role="listbox"
+          aria-label="Commands"
+          className="max-h-80 overflow-y-auto p-2"
+        >
+          {filteredCommands.length > 0 ? (
+            filteredCommands.map((command, index) => {
+              const Icon = command.icon
+              const isSelected = index === selectedIndex
+
+              return (
+                <button
+                  id={`command-${command.id}`}
+                  key={command.id}
+                  type="button"
+                  role="option"
+                  aria-selected={isSelected}
+                  tabIndex={-1}
+                  className={cn(
+                    "flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left text-sm outline-none",
+                    isSelected && "bg-accent text-accent-foreground",
+                  )}
+                  onClick={() => runCommand(command)}
+                  onPointerMove={() => setSelectedIndex(index)}
+                >
+                  <span className="flex size-9 shrink-0 items-center justify-center rounded-md border bg-background">
+                    <Icon className="size-4" />
+                  </span>
+                  <span className="min-w-0 flex-1">
+                    <span className="block font-medium">{command.label}</span>
+                    <span className="block truncate text-xs text-muted-foreground">
+                      {command.description}
+                    </span>
+                  </span>
+                  {isSelected && (
+                    <CornerDownLeft className="size-4 text-muted-foreground" />
+                  )}
+                </button>
+              )
+            })
+          ) : (
+            <p className="px-3 py-10 text-center text-sm text-muted-foreground">
+              No commands found.
+            </p>
+          )}
+        </div>
+        <div className="flex items-center gap-4 border-t bg-muted/40 px-4 py-2 text-xs text-muted-foreground">
+          <span className="flex items-center gap-1">
+            <ArrowUp className="size-3" />
+            <ArrowDown className="size-3" /> navigate
+          </span>
+          <span className="flex items-center gap-1">
+            <CornerDownLeft className="size-3" /> select
+          </span>
+          <span className="ml-auto">esc close</span>
+        </div>
+      </DialogContent>
+    </Dialog>
+  )
+}
diff --git a/frontend/src/routes/_layout.tsx b/frontend/src/routes/_layout.tsx
index 1697305..10fb072 100644
--- a/frontend/src/routes/_layout.tsx
+++ b/frontend/src/routes/_layout.tsx
@@ -1,5 +1,6 @@
 import { createFileRoute, Outlet, redirect } from "@tanstack/react-router"
 
+import { CommandPalette } from "@/components/Common/CommandPalette"
 import { Footer } from "@/components/Common/Footer"
 import AppSidebar from "@/components/Sidebar/AppSidebar"
 import {
@@ -27,6 +28,7 @@ function Layout() {
       <SidebarInset>
         <header className="sticky top-0 z-10 flex h-16 shrink-0 items-center gap-2 border-b px-4">
           <SidebarTrigger className="-ml-1 text-muted-foreground" />
+          <CommandPalette />
         </header>
         <main className="flex-1 p-6 md:p-8">
           <div className="mx-auto max-w-7xl">
```

### Candidate C

- Agent completed: `True`
- Frontend build passed: `True`

```diff
diff --git a/frontend/src/components/Common/CommandPalette.tsx b/frontend/src/components/Common/CommandPalette.tsx
new file mode 100644
index 0000000..4ea977b
--- /dev/null
+++ b/frontend/src/components/Common/CommandPalette.tsx
@@ -0,0 +1,140 @@
+import { useNavigate } from "@tanstack/react-router"
+import { Search } from "lucide-react"
+import { type KeyboardEvent, useEffect, useRef, useState } from "react"
+
+import type { NavigationItem } from "@/components/Sidebar/Main"
+import { Button } from "@/components/ui/button"
+import {
+  Dialog,
+  DialogContent,
+  DialogDescription,
+  DialogTitle,
+} from "@/components/ui/dialog"
+import { Input } from "@/components/ui/input"
+
+interface CommandPaletteProps {
+  items: NavigationItem[]
+}
+
+export function CommandPalette({ items }: CommandPaletteProps) {
+  const navigate = useNavigate()
+  const [isOpen, setIsOpen] = useState(false)
+  const [searchQuery, setSearchQuery] = useState("")
+  const commandButtonRefs = useRef<(HTMLButtonElement | null)[]>([])
+  const normalizedQuery = searchQuery.trim().toLocaleLowerCase()
+  const filteredItems = items.filter(({ path, title }) =>
+    `${title} ${path}`.toLocaleLowerCase().includes(normalizedQuery),
+  )
+
+  useEffect(() => {
+    const handleKeyDown = (event: globalThis.KeyboardEvent) => {
+      if (event.key === "k" && (event.metaKey || event.ctrlKey)) {
+        event.preventDefault()
+        setIsOpen((currentIsOpen) => !currentIsOpen)
+      }
+    }
+
+    window.addEventListener("keydown", handleKeyDown)
+    return () => window.removeEventListener("keydown", handleKeyDown)
+  }, [])
+
+  const handleOpenChange = (nextIsOpen: boolean) => {
+    setIsOpen(nextIsOpen)
+    if (!nextIsOpen) {
+      setSearchQuery("")
+    }
+  }
+
+  const handleSelect = (path: NavigationItem["path"]) => {
+    handleOpenChange(false)
+    void navigate({ to: path })
+  }
+
+  const handleSearchKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
+    if (event.key === "Enter" && filteredItems[0]) {
+      handleSelect(filteredItems[0].path)
+    }
+    if (event.key === "ArrowDown") {
+      event.preventDefault()
+      commandButtonRefs.current[0]?.focus()
+    }
+  }
+
+  const handleCommandKeyDown = (
+    event: KeyboardEvent<HTMLButtonElement>,
+    itemIndex: number,
+  ) => {
+    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") {
+      return
+    }
+
+    event.preventDefault()
+    const nextIndex =
+      event.key === "ArrowDown"
+        ? (itemIndex + 1) % filteredItems.length
+        : (itemIndex - 1 + filteredItems.length) % filteredItems.length
+    commandButtonRefs.current[nextIndex]?.focus()
+  }
+
+  return (
+    <>
+      <Button variant="outline" onClick={() => setIsOpen(true)}>
+        <Search data-icon="inline-start" />
+        <span className="hidden sm:inline">Search commands</span>
+        <kbd className="hidden rounded border bg-muted px-1.5 font-mono text-xs text-muted-foreground md:inline">
+          ⌘K / Ctrl K
+        </kbd>
+      </Button>
+      <Dialog open={isOpen} onOpenChange={handleOpenChange}>
+        <DialogContent
+          className="gap-0 overflow-hidden p-0 sm:max-w-xl"
+          showCloseButton={false}
+        >
+          <DialogTitle className="sr-only">Command palette</DialogTitle>
+          <DialogDescription className="sr-only">
+            Search for a page to navigate to.
+          </DialogDescription>
+          <div className="border-b p-3">
+            <Input
+              aria-label="Search commands"
+              autoFocus
+              placeholder="Search pages..."
+              type="search"
+              value={searchQuery}
+              onChange={(event) => setSearchQuery(event.target.value)}
+              onKeyDown={handleSearchKeyDown}
+            />
+          </div>
+          <div className="max-h-72 overflow-y-auto p-2">
+            {filteredItems.length > 0 ? (
+              <ul className="flex flex-col gap-1">
+                {filteredItems.map((item, itemIndex) => (
+                  <li key={item.path}>
+                    <Button
+                      ref={(button) => {
+                        commandButtonRefs.current[itemIndex] = button
+                      }}
+                      className="h-auto w-full justify-start px-3 py-2"
+                      variant="ghost"
+                      onClick={() => handleSelect(item.path)}
+                      onKeyDown={(event) =>
+                        handleCommandKeyDown(event, itemIndex)
+                      }
+                    >
+                      <item.icon data-icon="inline-start" />
+                      {item.title}
+                    </Button>
+                  </li>
+                ))}
+              </ul>
+            ) : (
+              <p className="p-6 text-center text-sm text-muted-foreground">
+                No commands found.
+              </p>
+            )}
+          </div>
+        </DialogContent>
+      </Dialog>
+    </>
+  )
+}
diff --git a/frontend/src/components/Sidebar/AppSidebar.tsx b/frontend/src/components/Sidebar/AppSidebar.tsx
index 8502bcb..9243d42 100644
--- a/frontend/src/components/Sidebar/AppSidebar.tsx
+++ b/frontend/src/components/Sidebar/AppSidebar.tsx
@@ -1,5 +1,4 @@
-import { Briefcase, Home, Users } from "lucide-react"
-
+import type { UserPublic } from "@/client"
 import { SidebarAppearance } from "@/components/Common/Appearance"
 import { Logo } from "@/components/Common/Logo"
 import {
@@ -8,22 +7,15 @@ import {
   SidebarFooter,
   SidebarHeader,
 } from "@/components/ui/sidebar"
-import useAuth from "@/hooks/useAuth"
-import { type Item, Main } from "./Main"
+import { Main, type NavigationItem } from "./Main"
 import { User } from "./User"
 
-const baseItems: Item[] = [
-  { icon: Home, title: "Dashboard", path: "/" },
-  { icon: Briefcase, title: "Items", path: "/items" },
-]
-
-export function AppSidebar() {
-  const { user: currentUser } = useAuth()
-
-  const items = currentUser?.is_superuser
-    ? [...baseItems, { icon: Users, title: "Admin", path: "/admin" }]
-    : baseItems
+interface AppSidebarProps {
+  items: NavigationItem[]
+  user: UserPublic | null | undefined
+}
 
+export function AppSidebar({ items, user }: AppSidebarProps) {
   return (
     <Sidebar collapsible="icon">
       <SidebarHeader className="px-4 py-6 group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:items-center">
@@ -34,7 +26,7 @@ export function AppSidebar() {
       </SidebarContent>
       <SidebarFooter>
         <SidebarAppearance />
-        <User user={currentUser} />
+        <User user={user} />
       </SidebarFooter>
     </Sidebar>
   )
diff --git a/frontend/src/components/Sidebar/Main.tsx b/frontend/src/components/Sidebar/Main.tsx
index db4d7bc..1e1b65e 100644
--- a/frontend/src/components/Sidebar/Main.tsx
+++ b/frontend/src/components/Sidebar/Main.tsx
@@ -1,5 +1,5 @@
 import { Link as RouterLink, useRouterState } from "@tanstack/react-router"
-import type { LucideIcon } from "lucide-react"
+import { Briefcase, Home, type LucideIcon, Users } from "lucide-react"
 
 import {
   SidebarGroup,
@@ -10,14 +10,31 @@ import {
   useSidebar,
 } from "@/components/ui/sidebar"
 
-export type Item = {
+export type NavigationItem = {
   icon: LucideIcon
   title: string
-  path: string
+  path: "/" | "/items" | "/admin"
 }
 
 interface MainProps {
-  items: Item[]
+  items: NavigationItem[]
+}
+
+const baseNavigationItems: NavigationItem[] = [
+  { icon: Home, title: "Dashboard", path: "/" },
+  { icon: Briefcase, title: "Items", path: "/items" },
+]
+
+const adminNavigationItem: NavigationItem = {
+  icon: Users,
+  title: "Admin",
+  path: "/admin",
+}
+
+export function getNavigationItems(isSuperuser: boolean) {
+  return isSuperuser
+    ? [...baseNavigationItems, adminNavigationItem]
+    : baseNavigationItems
 }
 
 export function Main({ items }: MainProps) {
diff --git a/frontend/src/routes/_layout.tsx b/frontend/src/routes/_layout.tsx
index 1697305..51787a6 100644
--- a/frontend/src/routes/_layout.tsx
+++ b/frontend/src/routes/_layout.tsx
@@ -1,13 +1,15 @@
 import { createFileRoute, Outlet, redirect } from "@tanstack/react-router"
 
+import { CommandPalette } from "@/components/Common/CommandPalette"
 import { Footer } from "@/components/Common/Footer"
 import AppSidebar from "@/components/Sidebar/AppSidebar"
+import { getNavigationItems } from "@/components/Sidebar/Main"
 import {
   SidebarInset,
   SidebarProvider,
   SidebarTrigger,
 } from "@/components/ui/sidebar"
-import { isLoggedIn } from "@/hooks/useAuth"
+import useAuth, { isLoggedIn } from "@/hooks/useAuth"
 
 export const Route = createFileRoute("/_layout")({
   component: Layout,
@@ -21,12 +23,16 @@ export const Route = createFileRoute("/_layout")({
 })
 
 function Layout() {
+  const { user: currentUser } = useAuth()
+  const navigationItems = getNavigationItems(currentUser?.is_superuser === true)
+
   return (
     <SidebarProvider>
-      <AppSidebar />
+      <AppSidebar items={navigationItems} user={currentUser} />
       <SidebarInset>
-        <header className="sticky top-0 z-10 flex h-16 shrink-0 items-center gap-2 border-b px-4">
+        <header className="sticky top-0 z-10 flex h-16 shrink-0 items-center justify-between gap-2 border-b px-4">
           <SidebarTrigger className="-ml-1 text-muted-foreground" />
+          <CommandPalette items={navigationItems} />
         </header>
         <main className="flex-1 p-6 md:p-8">
           <div className="mx-auto max-w-7xl">
```

### Candidate D

- Agent completed: `True`
- Frontend build passed: `True`

```diff
diff --git a/frontend/src/components/Common/CommandPalette.tsx b/frontend/src/components/Common/CommandPalette.tsx
new file mode 100644
index 0000000..76aac93
--- /dev/null
+++ b/frontend/src/components/Common/CommandPalette.tsx
@@ -0,0 +1,261 @@
+import { useNavigate } from "@tanstack/react-router"
+import {
+  Briefcase,
+  Home,
+  type LucideIcon,
+  Search,
+  Settings,
+  Users,
+} from "lucide-react"
+import {
+  type ChangeEvent,
+  type KeyboardEvent,
+  useEffect,
+  useRef,
+  useState,
+} from "react"
+
+import { Button } from "@/components/ui/button"
+import {
+  Dialog,
+  DialogContent,
+  DialogDescription,
+  DialogHeader,
+  DialogTitle,
+  DialogTrigger,
+} from "@/components/ui/dialog"
+import { Input } from "@/components/ui/input"
+import useAuth from "@/hooks/useAuth"
+
+type CommandPath = "/" | "/admin" | "/items" | "/settings"
+
+type NavigationCommand = {
+  description: string
+  icon: LucideIcon
+  keywords: string[]
+  path: CommandPath
+  title: string
+}
+
+const navigationCommands: NavigationCommand[] = [
+  {
+    description: "Return to your dashboard",
+    icon: Home,
+    keywords: ["home", "overview"],
+    path: "/",
+    title: "Dashboard",
+  },
+  {
+    description: "Create and manage your items",
+    icon: Briefcase,
+    keywords: ["projects", "content"],
+    path: "/items",
+    title: "Items",
+  },
+  {
+    description: "Update your profile and account",
+    icon: Settings,
+    keywords: ["profile", "password", "account"],
+    path: "/settings",
+    title: "Settings",
+  },
+]
+
+const adminCommand: NavigationCommand = {
+  description: "Manage users and permissions",
+  icon: Users,
+  keywords: ["users", "permissions", "accounts"],
+  path: "/admin",
+  title: "Admin",
+}
+
+function matchesQuery(command: NavigationCommand, query: string) {
+  const searchableText = [
+    command.title,
+    command.description,
+    ...command.keywords,
+  ]
+    .join(" ")
+    .toLowerCase()
+
+  return searchableText.includes(query.trim().toLowerCase())
+}
+
+export function CommandPalette() {
+  const navigate = useNavigate()
+  const { user: currentUser } = useAuth()
+  const inputRef = useRef<HTMLInputElement>(null)
+  const [isOpen, setIsOpen] = useState(false)
+  const [query, setQuery] = useState("")
+  const [selectedIndex, setSelectedIndex] = useState(0)
+
+  const availableCommands = currentUser?.is_superuser
+    ? [...navigationCommands, adminCommand]
+    : navigationCommands
+  const filteredCommands = availableCommands.filter((command) =>
+    matchesQuery(command, query),
+  )
+  const activeIndex = Math.min(
+    selectedIndex,
+    Math.max(filteredCommands.length - 1, 0),
+  )
+  const activeCommand = filteredCommands[activeIndex]
+
+  useEffect(() => {
+    const handleShortcut = (event: globalThis.KeyboardEvent) => {
+      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
+        event.preventDefault()
+        setQuery("")
+        setSelectedIndex(0)
+        setIsOpen((currentIsOpen) => !currentIsOpen)
+      }
+    }
+
+    document.addEventListener("keydown", handleShortcut)
+    return () => document.removeEventListener("keydown", handleShortcut)
+  }, [])
+
+  const handleOpenChange = (nextIsOpen: boolean) => {
+    setIsOpen(nextIsOpen)
+
+    if (!nextIsOpen) {
+      setQuery("")
+      setSelectedIndex(0)
+    }
+  }
+
+  const handleQueryChange = (event: ChangeEvent<HTMLInputElement>) => {
+    setQuery(event.target.value)
+    setSelectedIndex(0)
+  }
+
+  const runCommand = (command: NavigationCommand) => {
+    handleOpenChange(false)
+    navigate({ to: command.path })
+  }
+
+  const handleInputKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
+    if (filteredCommands.length === 0) {
+      return
+    }
+
+    if (event.key === "ArrowDown") {
+      event.preventDefault()
+      setSelectedIndex((currentIndex) =>
+        currentIndex >= filteredCommands.length - 1 ? 0 : currentIndex + 1,
+      )
+    }
+
+    if (event.key === "ArrowUp") {
+      event.preventDefault()
+      setSelectedIndex((currentIndex) =>
+        currentIndex <= 0 ? filteredCommands.length - 1 : currentIndex - 1,
+      )
+    }
+
+    if (event.key === "Enter" && activeCommand) {
+      event.preventDefault()
+      runCommand(activeCommand)
+    }
+  }
+
+  return (
+    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
+      <DialogTrigger asChild>
+        <Button
+          type="button"
+          variant="outline"
+          size="sm"
+          className="ml-auto w-9 justify-start px-2 sm:w-64 sm:px-3"
+          aria-label="Open command palette"
+        >
+          <Search data-icon="inline-start" />
+          <span className="hidden text-muted-foreground sm:inline">
+            Search commands...
+          </span>
+          <kbd className="ml-auto hidden rounded border bg-muted px-1.5 py-0.5 font-mono text-xs text-muted-foreground sm:inline-flex">
+            Ctrl K
+          </kbd>
+        </Button>
+      </DialogTrigger>
+      <DialogContent
+        className="gap-3 sm:max-w-xl"
+        onOpenAutoFocus={(event) => {
+          event.preventDefault()
+          inputRef.current?.focus()
+        }}
+      >
+        <DialogHeader className="sr-only">
+          <DialogTitle>Command palette</DialogTitle>
+          <DialogDescription>
+            Search for a destination, then press Enter to navigate.
+          </DialogDescription>
+        </DialogHeader>
+
+        <Input
+          ref={inputRef}
+          value={query}
+          onChange={handleQueryChange}
+          onKeyDown={handleInputKeyDown}
+          placeholder="Search pages and actions..."
+          aria-autocomplete="list"
+          aria-controls="command-palette-results"
+          aria-expanded={isOpen}
+          aria-activedescendant={
+            activeCommand
+              ? `command-${activeCommand.path.replace("/", "") || "dashboard"}`
+              : undefined
+          }
+          aria-label="Search commands"
+          role="combobox"
+        />
+
+        <div
+          id="command-palette-results"
+          className="max-h-80 overflow-y-auto rounded-md border p-1"
+          role="listbox"
+          aria-label="Commands"
+        >
+          {filteredCommands.length > 0 ? (
+            filteredCommands.map((command, index) => {
+              const isActive = index === activeIndex
+
+              return (
+                <Button
+                  id={`command-${command.path.replace("/", "") || "dashboard"}`}
+                  key={command.path}
+                  type="button"
+                  variant={isActive ? "secondary" : "ghost"}
+                  className="h-auto w-full justify-start px-3 py-3 text-left"
+                  role="option"
+                  aria-selected={isActive}
+                  tabIndex={-1}
+                  onClick={() => runCommand(command)}
+                  onMouseMove={() => setSelectedIndex(index)}
+                >
+                  <command.icon data-icon="inline-start" />
+                  <span className="flex min-w-0 flex-col items-start gap-0.5">
+                    <span>{command.title}</span>
+                    <span className="truncate text-xs font-normal text-muted-foreground">
+                      {command.description}
+                    </span>
+                  </span>
+                </Button>
+              )
+            })
+          ) : (
+            <p className="px-3 py-8 text-center text-sm text-muted-foreground">
+              No commands found.
+            </p>
+          )}
+        </div>
+
+        <div className="flex items-center gap-3 text-xs text-muted-foreground">
+          <span>↑↓ Navigate</span>
+          <span>↵ Open</span>
+          <span>Esc Close</span>
+        </div>
+      </DialogContent>
+    </Dialog>
+  )
+}
diff --git a/frontend/src/routes/_layout.tsx b/frontend/src/routes/_layout.tsx
index 1697305..10fb072 100644
--- a/frontend/src/routes/_layout.tsx
+++ b/frontend/src/routes/_layout.tsx
@@ -1,5 +1,6 @@
 import { createFileRoute, Outlet, redirect } from "@tanstack/react-router"
 
+import { CommandPalette } from "@/components/Common/CommandPalette"
 import { Footer } from "@/components/Common/Footer"
 import AppSidebar from "@/components/Sidebar/AppSidebar"
 import {
@@ -27,6 +28,7 @@ function Layout() {
       <SidebarInset>
         <header className="sticky top-0 z-10 flex h-16 shrink-0 items-center gap-2 border-b px-4">
           <SidebarTrigger className="-ml-1 text-muted-foreground" />
+          <CommandPalette />
         </header>
         <main className="flex-1 p-6 md:p-8">
           <div className="mx-auto max-w-7xl">
```

### Candidate E

- Agent completed: `True`
- Frontend build passed: `True`

```diff
diff --git a/frontend/src/components/Common/CommandPalette.tsx b/frontend/src/components/Common/CommandPalette.tsx
new file mode 100644
index 0000000..c1d2895
--- /dev/null
+++ b/frontend/src/components/Common/CommandPalette.tsx
@@ -0,0 +1,149 @@
+import { Link as RouterLink } from "@tanstack/react-router"
+import { Search } from "lucide-react"
+import {
+  type KeyboardEvent as ReactKeyboardEvent,
+  useCallback,
+  useEffect,
+  useState,
+} from "react"
+
+import type { NavigationItem } from "@/components/Sidebar/navigation"
+import { Button } from "@/components/ui/button"
+import {
+  Dialog,
+  DialogContent,
+  DialogDescription,
+  DialogHeader,
+  DialogTitle,
+  DialogTrigger,
+} from "@/components/ui/dialog"
+import { Input } from "@/components/ui/input"
+
+interface CommandPaletteProps {
+  navigationItems: NavigationItem[]
+}
+
+export function CommandPalette({ navigationItems }: CommandPaletteProps) {
+  const [isOpen, setIsOpen] = useState(false)
+  const [searchQuery, setSearchQuery] = useState("")
+
+  const filteredNavigationItems = navigationItems.filter((navigationItem) =>
+    navigationItem.title
+      .toLowerCase()
+      .includes(searchQuery.trim().toLowerCase()),
+  )
+
+  const handleOpenChange = useCallback((nextIsOpen: boolean) => {
+    setIsOpen(nextIsOpen)
+    if (!nextIsOpen) {
+      setSearchQuery("")
+    }
+  }, [])
+
+  useEffect(() => {
+    const handleShortcut = (event: KeyboardEvent) => {
+      if (event.key.toLowerCase() === "k" && (event.metaKey || event.ctrlKey)) {
+        event.preventDefault()
+        handleOpenChange(!isOpen)
+      }
+    }
+
+    document.addEventListener("keydown", handleShortcut)
+    return () => document.removeEventListener("keydown", handleShortcut)
+  }, [handleOpenChange, isOpen])
+
+  const handleCommandKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
+    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") {
+      return
+    }
+
+    const commandLinks = Array.from(
+      event.currentTarget.querySelectorAll<HTMLElement>("[data-command-item]"),
+    )
+    if (commandLinks.length === 0) {
+      return
+    }
+
+    event.preventDefault()
+    const focusedIndex = commandLinks.indexOf(
+      document.activeElement as HTMLElement,
+    )
+    const direction = event.key === "ArrowDown" ? 1 : -1
+    const nextIndex =
+      focusedIndex === -1
+        ? direction === 1
+          ? 0
+          : commandLinks.length - 1
+        : (focusedIndex + direction + commandLinks.length) % commandLinks.length
+
+    commandLinks[nextIndex]?.focus()
+  }
+
+  return (
+    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
+      <DialogTrigger asChild>
+        <Button
+          type="button"
+          variant="outline"
+          className="ml-auto text-muted-foreground"
+          aria-label="Open command palette"
+          aria-keyshortcuts="Meta+K Control+K"
+        >
+          <Search />
+          <span className="hidden sm:inline">Search commands</span>
+          <kbd className="hidden rounded border px-1.5 py-0.5 text-xs font-normal sm:inline">
+            ⌘/Ctrl K
+          </kbd>
+        </Button>
+      </DialogTrigger>
+      <DialogContent onKeyDown={handleCommandKeyDown}>
+        <DialogHeader>
+          <DialogTitle>Command palette</DialogTitle>
+          <DialogDescription>
+            Search for a page and select it to navigate.
+          </DialogDescription>
+        </DialogHeader>
+        <div className="relative">
+          <Search className="absolute top-1/2 left-3 -translate-y-1/2 text-muted-foreground" />
+          <Input
+            value={searchQuery}
+            onChange={(event) => setSearchQuery(event.target.value)}
+            className="pl-9"
+            placeholder="Search pages..."
+            aria-label="Search commands"
+          />
+        </div>
+        <nav
+          className="flex max-h-72 flex-col gap-1 overflow-y-auto"
+          aria-label="Command results"
+        >
+          {filteredNavigationItems.map((navigationItem) => (
+            <Button
+              key={navigationItem.path}
+              variant="ghost"
+              className="justify-start"
+              asChild
+            >
+              <RouterLink
+                to={navigationItem.path}
+                onClick={() => handleOpenChange(false)}
+                data-command-item
+              >
+                <navigationItem.icon />
+                {navigationItem.title}
+              </RouterLink>
+            </Button>
+          ))}
+          {filteredNavigationItems.length === 0 && (
+            <p
+              className="py-6 text-center text-sm text-muted-foreground"
+              role="status"
+            >
+              No commands found.
+            </p>
+          )}
+        </nav>
+      </DialogContent>
+    </Dialog>
+  )
+}
diff --git a/frontend/src/components/Sidebar/AppSidebar.tsx b/frontend/src/components/Sidebar/AppSidebar.tsx
index 8502bcb..1dfe729 100644
--- a/frontend/src/components/Sidebar/AppSidebar.tsx
+++ b/frontend/src/components/Sidebar/AppSidebar.tsx
@@ -1,5 +1,4 @@
-import { Briefcase, Home, Users } from "lucide-react"
-
+import type { UserPublic } from "@/client"
 import { SidebarAppearance } from "@/components/Common/Appearance"
 import { Logo } from "@/components/Common/Logo"
 import {
@@ -8,29 +7,23 @@ import {
   SidebarFooter,
   SidebarHeader,
 } from "@/components/ui/sidebar"
-import useAuth from "@/hooks/useAuth"
-import { type Item, Main } from "./Main"
+import { Main } from "./Main"
+import type { NavigationItem } from "./navigation"
 import { User } from "./User"
 
-const baseItems: Item[] = [
-  { icon: Home, title: "Dashboard", path: "/" },
-  { icon: Briefcase, title: "Items", path: "/items" },
-]
-
-export function AppSidebar() {
-  const { user: currentUser } = useAuth()
-
-  const items = currentUser?.is_superuser
-    ? [...baseItems, { icon: Users, title: "Admin", path: "/admin" }]
-    : baseItems
+interface AppSidebarProps {
+  currentUser?: UserPublic | null
+  navigationItems: NavigationItem[]
+}
 
+export function AppSidebar({ currentUser, navigationItems }: AppSidebarProps) {
   return (
     <Sidebar collapsible="icon">
       <SidebarHeader className="px-4 py-6 group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:items-center">
         <Logo variant="responsive" />
       </SidebarHeader>
       <SidebarContent>
-        <Main items={items} />
+        <Main items={navigationItems} />
       </SidebarContent>
       <SidebarFooter>
         <SidebarAppearance />
diff --git a/frontend/src/components/Sidebar/Main.tsx b/frontend/src/components/Sidebar/Main.tsx
index db4d7bc..f1d3f08 100644
--- a/frontend/src/components/Sidebar/Main.tsx
+++ b/frontend/src/components/Sidebar/Main.tsx
@@ -1,5 +1,4 @@
 import { Link as RouterLink, useRouterState } from "@tanstack/react-router"
-import type { LucideIcon } from "lucide-react"
 
 import {
   SidebarGroup,
@@ -9,15 +8,10 @@ import {
   SidebarMenuItem,
   useSidebar,
 } from "@/components/ui/sidebar"
-
-export type Item = {
-  icon: LucideIcon
-  title: string
-  path: string
-}
+import type { NavigationItem } from "./navigation"
 
 interface MainProps {
-  items: Item[]
+  items: NavigationItem[]
 }
 
 export function Main({ items }: MainProps) {
diff --git a/frontend/src/components/Sidebar/navigation.ts b/frontend/src/components/Sidebar/navigation.ts
new file mode 100644
index 0000000..cd21ec1
--- /dev/null
+++ b/frontend/src/components/Sidebar/navigation.ts
@@ -0,0 +1,24 @@
+import { Briefcase, Home, type LucideIcon, Users } from "lucide-react"
+
+export type NavigationItem = {
+  icon: LucideIcon
+  title: string
+  path: string
+}
+
+const baseNavigationItems: NavigationItem[] = [
+  { icon: Home, title: "Dashboard", path: "/" },
+  { icon: Briefcase, title: "Items", path: "/items" },
+]
+
+const adminNavigationItem: NavigationItem = {
+  icon: Users,
+  title: "Admin",
+  path: "/admin",
+}
+
+export function getNavigationItems(isSuperuser: boolean) {
+  return isSuperuser
+    ? [...baseNavigationItems, adminNavigationItem]
+    : baseNavigationItems
+}
diff --git a/frontend/src/routes/_layout.tsx b/frontend/src/routes/_layout.tsx
index 1697305..0b9b76b 100644
--- a/frontend/src/routes/_layout.tsx
+++ b/frontend/src/routes/_layout.tsx
@@ -1,13 +1,15 @@
 import { createFileRoute, Outlet, redirect } from "@tanstack/react-router"
 
+import { CommandPalette } from "@/components/Common/CommandPalette"
 import { Footer } from "@/components/Common/Footer"
 import AppSidebar from "@/components/Sidebar/AppSidebar"
+import { getNavigationItems } from "@/components/Sidebar/navigation"
 import {
   SidebarInset,
   SidebarProvider,
   SidebarTrigger,
 } from "@/components/ui/sidebar"
-import { isLoggedIn } from "@/hooks/useAuth"
+import useAuth, { isLoggedIn } from "@/hooks/useAuth"
 
 export const Route = createFileRoute("/_layout")({
   component: Layout,
@@ -21,12 +23,16 @@ export const Route = createFileRoute("/_layout")({
 })
 
 function Layout() {
+  const { user: currentUser } = useAuth()
+  const navigationItems = getNavigationItems(currentUser?.is_superuser === true)
+
   return (
     <SidebarProvider>
-      <AppSidebar />
+      <AppSidebar currentUser={currentUser} navigationItems={navigationItems} />
       <SidebarInset>
         <header className="sticky top-0 z-10 flex h-16 shrink-0 items-center gap-2 border-b px-4">
           <SidebarTrigger className="-ml-1 text-muted-foreground" />
+          <CommandPalette navigationItems={navigationItems} />
         </header>
         <main className="flex-1 p-6 md:p-8">
           <div className="mx-auto max-w-7xl">
```

### Candidate F

- Agent completed: `True`
- Frontend build passed: `True`

```diff
diff --git a/frontend/src/components/CommandPalette/CommandPalette.tsx b/frontend/src/components/CommandPalette/CommandPalette.tsx
new file mode 100644
index 0000000..a965e54
--- /dev/null
+++ b/frontend/src/components/CommandPalette/CommandPalette.tsx
@@ -0,0 +1,200 @@
+import { useNavigate } from "@tanstack/react-router"
+import { CornerDownLeft, Search } from "lucide-react"
+import {
+  type ChangeEvent,
+  type KeyboardEvent,
+  useEffect,
+  useState,
+} from "react"
+
+import {
+  getPrimaryNavigationItems,
+  type NavigationItem,
+  userSettingsNavigationItem,
+} from "@/components/Sidebar/navigation"
+import { Button } from "@/components/ui/button"
+import {
+  Dialog,
+  DialogContent,
+  DialogDescription,
+  DialogTitle,
+  DialogTrigger,
+} from "@/components/ui/dialog"
+import { Input } from "@/components/ui/input"
+import useAuth from "@/hooks/useAuth"
+
+export function CommandPalette() {
+  const { user: currentUser } = useAuth()
+  const navigate = useNavigate()
+  const [isOpen, setIsOpen] = useState(false)
+  const [query, setQuery] = useState("")
+  const [activeIndex, setActiveIndex] = useState(0)
+
+  const commands = [
+    ...getPrimaryNavigationItems(Boolean(currentUser?.is_superuser)),
+    userSettingsNavigationItem,
+  ]
+  const normalizedQuery = query.trim().toLocaleLowerCase()
+  const filteredCommands = commands.filter((command) =>
+    command.title.toLocaleLowerCase().includes(normalizedQuery),
+  )
+
+  useEffect(() => {
+    const handleKeyDown = (event: globalThis.KeyboardEvent) => {
+      if (
+        event.key.toLocaleLowerCase() === "k" &&
+        (event.metaKey || event.ctrlKey)
+      ) {
+        event.preventDefault()
+        setIsOpen((currentIsOpen) => !currentIsOpen)
+      }
+    }
+
+    window.addEventListener("keydown", handleKeyDown)
+    return () => window.removeEventListener("keydown", handleKeyDown)
+  }, [])
+
+  const handleOpenChange = (nextIsOpen: boolean) => {
+    setIsOpen(nextIsOpen)
+    if (nextIsOpen) {
+      setQuery("")
+      setActiveIndex(0)
+    }
+  }
+
+  const handleSearchChange = (event: ChangeEvent<HTMLInputElement>) => {
+    setQuery(event.target.value)
+    setActiveIndex(0)
+  }
+
+  const handleSelect = (command: NavigationItem) => {
+    setIsOpen(false)
+    void navigate({ to: command.path })
+  }
+
+  const handleSearchKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
+    if (filteredCommands.length === 0) return
+
+    if (event.key === "ArrowDown") {
+      event.preventDefault()
+      setActiveIndex(
+        (currentIndex) => (currentIndex + 1) % filteredCommands.length,
+      )
+    }
+
+    if (event.key === "ArrowUp") {
+      event.preventDefault()
+      setActiveIndex(
+        (currentIndex) =>
+          (currentIndex - 1 + filteredCommands.length) %
+          filteredCommands.length,
+      )
+    }
+
+    if (event.key === "Enter") {
+      event.preventDefault()
+      handleSelect(filteredCommands[activeIndex])
+    }
+  }
+
+  return (
+    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
+      <DialogTrigger asChild>
+        <Button
+          type="button"
+          variant="outline"
+          className="ml-auto w-9 justify-center px-0 text-muted-foreground sm:w-64 sm:justify-between sm:px-3"
+        >
+          <span className="flex items-center gap-2">
+            <Search />
+            <span className="sr-only sm:not-sr-only">Search commands</span>
+          </span>
+          <kbd className="hidden rounded border bg-muted px-1.5 py-0.5 font-mono text-[10px] sm:inline">
+            ⌘K / Ctrl K
+          </kbd>
+        </Button>
+      </DialogTrigger>
+
+      <DialogContent
+        className="gap-0 overflow-hidden p-0 sm:max-w-xl"
+        showCloseButton={false}
+      >
+        <DialogTitle className="sr-only">Command palette</DialogTitle>
+        <DialogDescription className="sr-only">
+          Search for a page and select it to navigate.
+        </DialogDescription>
+
+        <div className="relative border-b p-3">
+          <Search className="pointer-events-none absolute top-1/2 left-6 size-4 -translate-y-1/2 text-muted-foreground" />
+          <Input
+            aria-activedescendant={
+              filteredCommands.length > 0
+                ? `command-option-${activeIndex}`
+                : undefined
+            }
+            aria-controls="command-results"
+            aria-label="Search commands"
+            aria-autocomplete="list"
+            placeholder="Type a command or search..."
+            className="border-0 pl-9 shadow-none focus-visible:ring-0"
+            value={query}
+            onChange={handleSearchChange}
+            onKeyDown={handleSearchKeyDown}
+          />
+        </div>
+
+        <div className="max-h-72 overflow-y-auto p-2">
+          <p
+            id="command-results-label"
+            className="px-2 py-1.5 text-xs font-medium text-muted-foreground"
+          >
+            Pages
+          </p>
+          <div
+            id="command-results"
+            role="listbox"
+            aria-labelledby="command-results-label"
+          >
+            {filteredCommands.length > 0 ? (
+              filteredCommands.map((command, index) => {
+                const isActive = index === activeIndex
+
+                return (
+                  <button
+                    type="button"
+                    tabIndex={-1}
+                    id={`command-option-${index}`}
+                    role="option"
+                    aria-selected={isActive}
+                    key={command.path}
+                    className="flex w-full items-center gap-3 rounded-md px-2 py-2 text-left text-sm aria-selected:bg-accent aria-selected:text-accent-foreground"
+                    onClick={() => handleSelect(command)}
+                    onPointerEnter={() => setActiveIndex(index)}
+                  >
+                    <command.icon className="size-4 text-muted-foreground" />
+                    <span>{command.title}</span>
+                  </button>
+                )
+              })
+            ) : (
+              <p
+                role="status"
+                className="py-8 text-center text-sm text-muted-foreground"
+              >
+                No commands found.
+              </p>
+            )}
+          </div>
+        </div>
+
+        <div className="flex items-center justify-end gap-3 border-t bg-muted/40 px-4 py-2 text-xs text-muted-foreground">
+          <span>↑↓ to navigate</span>
+          <span className="flex items-center gap-1.5">
+            <CornerDownLeft className="size-3" />
+            <span>to select</span>
+          </span>
+        </div>
+      </DialogContent>
+    </Dialog>
+  )
+}
diff --git a/frontend/src/components/Sidebar/AppSidebar.tsx b/frontend/src/components/Sidebar/AppSidebar.tsx
index 8502bcb..134a801 100644
--- a/frontend/src/components/Sidebar/AppSidebar.tsx
+++ b/frontend/src/components/Sidebar/AppSidebar.tsx
@@ -1,5 +1,3 @@
-import { Briefcase, Home, Users } from "lucide-react"
-
 import { SidebarAppearance } from "@/components/Common/Appearance"
 import { Logo } from "@/components/Common/Logo"
 import {
@@ -9,20 +7,14 @@ import {
   SidebarHeader,
 } from "@/components/ui/sidebar"
 import useAuth from "@/hooks/useAuth"
-import { type Item, Main } from "./Main"
+import { Main } from "./Main"
+import { getPrimaryNavigationItems } from "./navigation"
 import { User } from "./User"
 
-const baseItems: Item[] = [
-  { icon: Home, title: "Dashboard", path: "/" },
-  { icon: Briefcase, title: "Items", path: "/items" },
-]
-
 export function AppSidebar() {
   const { user: currentUser } = useAuth()
 
-  const items = currentUser?.is_superuser
-    ? [...baseItems, { icon: Users, title: "Admin", path: "/admin" }]
-    : baseItems
+  const items = getPrimaryNavigationItems(Boolean(currentUser?.is_superuser))
 
   return (
     <Sidebar collapsible="icon">
diff --git a/frontend/src/components/Sidebar/Main.tsx b/frontend/src/components/Sidebar/Main.tsx
index db4d7bc..8893ab6 100644
--- a/frontend/src/components/Sidebar/Main.tsx
+++ b/frontend/src/components/Sidebar/Main.tsx
@@ -1,6 +1,4 @@
 import { Link as RouterLink, useRouterState } from "@tanstack/react-router"
-import type { LucideIcon } from "lucide-react"
-
 import {
   SidebarGroup,
   SidebarGroupContent,
@@ -9,15 +7,10 @@ import {
   SidebarMenuItem,
   useSidebar,
 } from "@/components/ui/sidebar"
-
-export type Item = {
-  icon: LucideIcon
-  title: string
-  path: string
-}
+import type { NavigationItem } from "./navigation"
 
 interface MainProps {
-  items: Item[]
+  items: NavigationItem[]
 }
 
 export function Main({ items }: MainProps) {
diff --git a/frontend/src/components/Sidebar/User.tsx b/frontend/src/components/Sidebar/User.tsx
index 12c6362..922dbbb 100644
--- a/frontend/src/components/Sidebar/User.tsx
+++ b/frontend/src/components/Sidebar/User.tsx
@@ -1,5 +1,5 @@
 import { Link as RouterLink } from "@tanstack/react-router"
-import { ChevronsUpDown, LogOut, Settings } from "lucide-react"
+import { ChevronsUpDown, LogOut } from "lucide-react"
 
 import { Avatar, AvatarFallback } from "@/components/ui/avatar"
 import {
@@ -18,6 +18,7 @@ import {
 } from "@/components/ui/sidebar"
 import useAuth from "@/hooks/useAuth"
 import { getInitials } from "@/utils"
+import { userSettingsNavigationItem } from "./navigation"
 
 interface UserInfoProps {
   fullName?: string
@@ -79,10 +80,13 @@ export function User({ user }: { user: any }) {
               <UserInfo fullName={user?.full_name} email={user?.email} />
             </DropdownMenuLabel>
             <DropdownMenuSeparator />
-            <RouterLink to="/settings" onClick={handleMenuClick}>
+            <RouterLink
+              to={userSettingsNavigationItem.path}
+              onClick={handleMenuClick}
+            >
               <DropdownMenuItem>
-                <Settings />
-                User Settings
+                <userSettingsNavigationItem.icon />
+                {userSettingsNavigationItem.title}
               </DropdownMenuItem>
             </RouterLink>
             <DropdownMenuItem onClick={handleLogout}>
diff --git a/frontend/src/components/Sidebar/navigation.ts b/frontend/src/components/Sidebar/navigation.ts
new file mode 100644
index 0000000..28ab1c0
--- /dev/null
+++ b/frontend/src/components/Sidebar/navigation.ts
@@ -0,0 +1,31 @@
+import type { LucideIcon } from "lucide-react"
+import { Briefcase, Home, Settings, Users } from "lucide-react"
+
+export type NavigationItem = {
+  icon: LucideIcon
+  title: string
+  path: "/" | "/admin" | "/items" | "/settings"
+}
+
+const primaryNavigationItems: NavigationItem[] = [
+  { icon: Home, title: "Dashboard", path: "/" },
+  { icon: Briefcase, title: "Items", path: "/items" },
+]
+
+const adminNavigationItem: NavigationItem = {
+  icon: Users,
+  title: "Admin",
+  path: "/admin",
+}
+
+export const userSettingsNavigationItem: NavigationItem = {
+  icon: Settings,
+  title: "User Settings",
+  path: "/settings",
+}
+
+export function getPrimaryNavigationItems(isSuperuser: boolean) {
+  return isSuperuser
+    ? [...primaryNavigationItems, adminNavigationItem]
+    : primaryNavigationItems
+}
diff --git a/frontend/src/routes/_layout.tsx b/frontend/src/routes/_layout.tsx
index 1697305..3215586 100644
--- a/frontend/src/routes/_layout.tsx
+++ b/frontend/src/routes/_layout.tsx
@@ -1,5 +1,6 @@
 import { createFileRoute, Outlet, redirect } from "@tanstack/react-router"
 
+import { CommandPalette } from "@/components/CommandPalette/CommandPalette"
 import { Footer } from "@/components/Common/Footer"
 import AppSidebar from "@/components/Sidebar/AppSidebar"
 import {
@@ -27,6 +28,7 @@ function Layout() {
       <SidebarInset>
         <header className="sticky top-0 z-10 flex h-16 shrink-0 items-center gap-2 border-b px-4">
           <SidebarTrigger className="-ml-1 text-muted-foreground" />
+          <CommandPalette />
         </header>
         <main className="flex-1 p-6 md:p-8">
           <div className="mx-auto max-w-7xl">
```

## Output

Return JSON matching the supplied schema. Include every candidate exactly once. Use only these exact one-letter values for `id`: A, B, C, D, E, F. 
For evidence, cite concrete files or code choices from the diff and do not guess the hidden condition.
