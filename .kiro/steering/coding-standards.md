---
inclusion: always
---

# Universal Engineering Standards

These rules apply to ALL work produced in any project — code, infrastructure, configuration, scripts, pipelines, and operational procedures.

Goals: clean, readable, maintainable, secure, and scalable artifacts across every engineering discipline.

Roles covered: Backend Developer, Frontend Developer, DevOps Engineer, Platform Engineer, System Administrator, DBA, Security Engineer, SRE.

---

## 0. Scope & Applicability (Polyglot)

- These standards are technology-agnostic by default and apply to Backend, Frontend, scripts, infrastructure code, automation tools, CI/CD pipelines, database schemas, and operational runbooks
- Where language/framework specifics are required, treat them as examples, not hard constraints for other stacks
- If a rule conflicts with a language ecosystem convention, prefer the ecosystem convention and keep the intent of this document
- Every repository SHOULD define formatter/linter/type-check/test tools per stack, and automation MUST enforce them in CI
- Decisions must optimize readability, maintainability, testability, and scalability over personal style preferences
- Infrastructure and configuration files are treated with the same quality bar as application code

### Role Applicability Reference

Each section maps to one or more roles. Use the role tags to determine which rules apply to your current task.

Section 1-9 (Clean Code, Architecture):
- Developer: PRIMARY — all rules apply directly to application code
- DevOps/Platform: APPLIES — follow when writing scripts, IaC modules, automation tools
- SysAdmin: APPLIES — follow when writing shell scripts and automation
- DBA: APPLIES — follow when writing stored procedures, migration scripts
- Security: APPLIES — follow when writing security tools and scanners

Section 10 (Testing):
- Developer: PRIMARY — unit, integration, and e2e tests for application code
- DevOps/Platform: APPLIES — pipeline tests, IaC validation tests, smoke tests
- DBA: APPLIES — migration tests, query performance tests
- Security: APPLIES — security regression tests, penetration test automation

Section 11 (Security):
- Developer: APPLIES — application-layer security (input validation, auth, encryption)
- DevOps/Platform: APPLIES — infrastructure-layer security (network, IAM, secrets)
- SysAdmin: APPLIES — OS-layer security (hardening, patching, access control)
- DBA: APPLIES — database-layer security (access control, encryption, audit)
- Security: PRIMARY — all security rules are your core responsibility

Section 12 (Performance):
- Developer: APPLIES — application performance (queries, caching, async I/O)
- DevOps/Platform: APPLIES — infrastructure sizing, auto-scaling, load balancing
- SysAdmin: APPLIES — OS tuning, kernel parameters, storage I/O
- DBA: APPLIES — query tuning, indexing, connection pooling

Section 13 (API Design):
- Developer: PRIMARY — design and implement API contracts
- DevOps/Platform: APPLIES — API gateway, service mesh configuration
- Security: APPLIES — API authentication, authorization, rate limiting

Section 14 (Version Control):
- Developer: APPLIES
- DevOps/Platform: APPLIES
- SysAdmin: APPLIES
- DBA: APPLIES
- Security: APPLIES

Section 15 (Docker and Containers):
- Developer: APPLIES — write Dockerfiles, understand container behavior
- DevOps/Platform: PRIMARY — container orchestration, registry, scanning
- SysAdmin: APPLIES — host-level container runtime configuration
- Security: APPLIES — image scanning, runtime security, least privilege

Section 16 (IaC — Infrastructure Provisioning):
- DevOps/Platform: PRIMARY — write and maintain provisioning code (Terraform, Pulumi, CloudFormation, OpenTofu)
- SysAdmin: APPLIES — review and operate provisioned infrastructure
- Security: APPLIES — policy-as-code, compliance scanning, network security rules

Section 16b (IaC — Configuration Management):
- DevOps/Platform: APPLIES — automation pipelines, integration with provisioning
- SysAdmin: PRIMARY — write and maintain configuration code (Ansible, Chef, Puppet, Salt)
- Security: APPLIES — hardening playbooks/recipes, compliance baselines, secret injection

Section 17 (CI/CD):
- Developer: APPLIES — understand pipeline stages, fix pipeline failures
- DevOps/Platform: PRIMARY — design, build, and maintain pipelines
- Security: APPLIES — pipeline security, secret management, SAST/SCA integration

Section 18 (Database):
- Developer: APPLIES — write queries, create migrations, use connection pools
- DevOps/Platform: APPLIES — database provisioning, backup automation
- SysAdmin: APPLIES — OS/storage layer for database hosts
- DBA: PRIMARY — schema design, query optimization, access control, backup/recovery
- Security: APPLIES — database access control, encryption, audit logging

Section 19 (Monitoring):
- Developer: APPLIES — instrument code with metrics, logs, traces
- DevOps/Platform: PRIMARY — monitoring infrastructure, alerting, dashboards
- SysAdmin: APPLIES — host-level monitoring, log forwarding
- DBA: APPLIES — database monitoring, slow query logging
- Security: APPLIES — security event monitoring, audit log analysis

Section 20 (SysAdmin and Ops):
- DevOps/Platform: APPLIES — automation, configuration management
- SysAdmin: PRIMARY — server management, patching, access control
- Security: APPLIES — hardening, compliance, audit

Section 21 (Security Engineering):
- Developer: APPLIES — secure coding, dependency management
- DevOps/Platform: APPLIES — infrastructure security, network segmentation
- SysAdmin: APPLIES — host hardening, patch management
- DBA: APPLIES — database security, encryption
- Security: PRIMARY — all security engineering is your core responsibility

Section 22 (Backup and DR):
- DevOps/Platform: APPLIES — backup automation, DR infrastructure
- SysAdmin: PRIMARY — backup operations, restore testing
- DBA: PRIMARY — database backup, point-in-time recovery
- Security: APPLIES — backup encryption, access control

Section 23 (Runbooks and Docs):
- Developer: APPLIES — document service behavior, API docs
- DevOps/Platform: PRIMARY — operational runbooks, architecture docs
- SysAdmin: PRIMARY — system runbooks, maintenance procedures
- DBA: APPLIES — database runbooks, recovery procedures
- Security: APPLIES — incident response runbooks, security procedures

Section 24 (AI-Assisted Development):
- Developer: PRIMARY — review AI-generated code, prompt hygiene
- DevOps/Platform: APPLIES — review AI-generated IaC and scripts
- SysAdmin: APPLIES — review AI-generated automation
- DBA: APPLIES — review AI-generated queries and migrations
- Security: APPLIES — audit AI-generated code for vulnerabilities

Section 25 (Data Privacy and Compliance):
- Developer: PRIMARY — implement privacy controls in application code
- DevOps/Platform: APPLIES — infrastructure-level data controls, log redaction
- SysAdmin: APPLIES — data retention, storage encryption
- DBA: PRIMARY — data classification, retention, anonymization
- Security: PRIMARY — compliance auditing, privacy impact assessment

Section 26 (Resilience Patterns):
- Developer: PRIMARY — implement circuit breakers, retries, timeouts in code
- DevOps/Platform: APPLIES — infrastructure-level resilience (load balancing, auto-scaling)
- SysAdmin: APPLIES — host-level failover, resource monitoring

Section 27 (Dependency Management):
- Developer: PRIMARY — manage application dependencies, license compliance
- DevOps/Platform: APPLIES — manage IaC dependencies, base image updates
- Security: PRIMARY — supply chain security, vulnerability scanning

Section 28 (Accessibility):
- Developer: PRIMARY — implement WCAG-compliant UI components

---

## 1. Clean Code — Core Principles

### 1.1 Readable Code

- Code should read like well-written prose — anyone can understand it without extra explanation
- Each function does ONE thing only
- Variable, function, and class names must clearly reveal intent — no abbreviations unless universally understood (`id`, `url`, `api`)
- No magic numbers or strings — extract to named constants
- Avoid nesting deeper than 3 levels — use early returns and guard clauses
- Each function should be at most 20 lines (ideal), never exceed 40 lines
- Each file should have ONE primary responsibility

BEFORE (bad — magic numbers, deep nesting, unclear names):

```python
def proc(d, t, x):
    if d > 0:
        if t > 0:
            r = d * (1 + t)
            if r > 1000:
                r = r * 0.9
            if x:
                r = r - 50
            return r
        return 0
    return 0
```

AFTER (good — named constants, early returns, clear names):

```python
BULK_DISCOUNT_THRESHOLD = 1000
BULK_DISCOUNT_RATE = 0.9
LOYALTY_DISCOUNT_AMOUNT = 50

def calculate_total_with_tax(
    base_amount: float,
    tax_rate: float,
    has_loyalty_discount: bool,
) -> float:
    """Calculate total price including tax and applicable discounts."""
    if base_amount <= 0 or tax_rate <= 0:
        return 0.0

    total = base_amount * (1 + tax_rate)

    if total > BULK_DISCOUNT_THRESHOLD:
        total *= BULK_DISCOUNT_RATE

    if has_loyalty_discount:
        total -= LOYALTY_DISCOUNT_AMOUNT

    return total
```

### 1.2 SOLID

- Single Responsibility: each module/class has only ONE reason to change
- Open/Closed: extend via interfaces/base classes, do not modify existing code
- Liskov Substitution: subtypes must be substitutable for their base types without causing errors
- Interface Segregation: small, focused interfaces — do not force implementation of unneeded methods
- Dependency Inversion: depend on abstractions, not on concrete implementations

### 1.3 DRY / KISS / YAGNI

- DRY: duplicated logic must be extracted into shared functions/modules
- KISS: choose the simplest solution that works correctly
- YAGNI: do not build features or abstractions until they are actually needed

---

## 2. Code Cleanup — Keep the Codebase Clean

- Remove dead code and commented-out code — use version control instead of keeping it
- Remove unused imports and variables
- Do not leave `console.log`, `print`, or `debugger` in production code
- Do not leave empty files or placeholder files with no content
- Refactor immediately when you spot code smells: overly long functions, bloated classes, unclear names
- When fixing bugs or adding features, clean up surrounding code if it violates the rules above
- Every PR/commit should leave the codebase cleaner than or at least as clean as before

---

## 3. Naming Conventions

### 3.1 General Rules

- Names must clearly describe meaning and purpose
- Do not use single-character names except for lambda/loop indices (`i`, `j`, `k`)
- Booleans: prefix with `is`, `has`, `can`, `should` (e.g., `isActive`, `hasPermission`)
- Functions that return data: use nouns or `get*` prefix (e.g., `getUser`, `getUserList`)
- Functions that perform actions: use verbs (`create`, `update`, `delete`, `send`, `validate`)
- Avoid double negation: use `isEnabled` instead of `isNotDisabled`
- File names must reflect their content and follow the language's naming convention

### 3.2 Language-Specific Conventions

Use the official style guide of each language first; table below is the default fallback convention:

| Element            | JavaScript / TypeScript      | Python                  | Java / C# / Go          |
|--------------------|------------------------------|-------------------------|--------------------------|
| Variables          | `camelCase`                  | `snake_case`            | `camelCase`              |
| Functions          | `camelCase`                  | `snake_case`            | `camelCase`              |
| Classes            | `PascalCase`                 | `PascalCase`            | `PascalCase`             |
| Constants          | `UPPER_SNAKE_CASE`           | `UPPER_SNAKE_CASE`      | `UPPER_SNAKE_CASE`       |
| Private members    | `_camelCase` or `#private`   | `_snake_case`           | `private` keyword        |
| Interfaces (TS)    | `PascalCase` (no `I` prefix) | N/A                     | `PascalCase`             |
| Enums              | `PascalCase`, values `UPPER_SNAKE_CASE` | `PascalCase` | `PascalCase`             |
| Files (JS/TS)      | `kebab-case.ts` or `PascalCase.tsx` | `snake_case.py`  | `PascalCase.java`        |
| Test files         | `*.test.ts` / `*.spec.ts`   | `test_*.py`             | `*Test.java`             |
| Env variables      | `UPPER_SNAKE_CASE`           | `UPPER_SNAKE_CASE`      | `UPPER_SNAKE_CASE`       |

### 3.3 Frontend Naming (Modular)

- Components: `PascalCase` — e.g., `UserProfile.tsx`, `OrderList.vue`
- Hooks (React): `use` + PascalCase — e.g., `useAuth.ts`, `useOrderFilter.ts`
- Services: `kebab-case.service.ts` — e.g., `auth.service.ts`, `order.service.ts`
- Stores/State: `kebab-case.store.ts` — e.g., `auth.store.ts`, `cart.store.ts`
- Types/Interfaces: `kebab-case.type.ts` — e.g., `user.type.ts`, `order.type.ts`
- Utils/Helpers: `kebab-case.util.ts` — e.g., `date.util.ts`, `format.util.ts`
- Constants: `kebab-case.constant.ts` — e.g., `api.constant.ts`, `route.constant.ts`
- Validators: `kebab-case.validator.ts` — e.g., `email.validator.ts`

---

## 4. Comments & Documentation

All comments MUST be written in English.

For languages not listed below (Go, Rust, Kotlin, PHP, etc.), use that ecosystem's equivalent doc format and keep the same documentation intent.

### 4.1 Commenting Principles

- Comments explain WHY, not WHAT — the code itself should explain what it does
- REQUIRED documentation: public APIs, complex functions, non-obvious business rules
- TODO/FIXME must include context: `// TODO(author): description — ticket/issue ref`
- Remove commented-out code — use git history instead of keeping it

### 4.2 JSDoc / TSDoc (required for public APIs — JS/TS)

```ts
/**
 * Retrieve a user by their unique identifier.
 *
 * @param userId - The unique identifier of the user.
 * @returns The user object if found, or null if not exists.
 * @throws {NotFoundError} When the user does not exist in the database.
 *
 * @example
 * ```ts
 * const user = await getUser('abc-123');
 * ```
 */
async function getUser(userId: string): Promise<User | null> { ... }
```

### 4.3 JavaDoc (required for public APIs — Java)

```java
/**
 * Calculate the total price of an order including tax.
 *
 * @param order the order to calculate
 * @param taxRate the tax rate as a decimal (e.g., 0.1 for 10%)
 * @return the total price including tax
 * @throws IllegalArgumentException if taxRate is negative
 */
public BigDecimal calculateTotal(Order order, BigDecimal taxRate) { ... }
```

### 4.4 Python Docstring (required for public APIs — Python)

```python
def calculate_total(order: Order, tax_rate: float) -> float:
    """Calculate the total price of an order including tax.

    Args:
        order: The order to calculate.
        tax_rate: The tax rate as a decimal (e.g., 0.1 for 10%).

    Returns:
        The total price including tax.

    Raises:
        ValueError: If tax_rate is negative.
    """
```

### 4.5 HCL / Terraform Documentation (required for modules)

```hcl
# Every variable MUST have a description
variable "environment" {
  description = "Deployment environment name (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

# Every output MUST have a description
output "vpc_id" {
  description = "The ID of the created VPC"
  value       = oci_core_vcn.main.id
}
```

### 4.6 File-Level Documentation

Every service/module file MUST have a doc block at the top:

```ts
/**
 * Order processing service.
 *
 * Handles order creation, validation, payment integration,
 * and status transitions throughout the order lifecycle.
 */
```

### 4.7 Large Files — Split, Don't Separate

If a file grows large enough that you feel the need to add visual dividers, that is a signal the file violates Single Responsibility and must be broken up instead.

- Preferred: split into focused modules/files, each with one clear responsibility
- Forbidden: visual comment dividers such as `// ===...` or `// ---...`

If a file genuinely cannot be split (e.g., a top-level config or a generated file), use at most one blank line between logical groups — no decorative comment lines.

---

## 5. Project Structure — Organize by Business Domain

### 5.1 Organization Principles

- Organize code by BUSINESS DOMAIN (feature/domain), not by file type (controllers/, services/, models/)
- Each business module is a folder containing all related files: routes, services, types, tests, etc.
- Shared/common code goes in a `common/` or `shared/` folder
- Each module should be independently developable, testable, and deployable as much as possible
- Folder names and exact layout can vary by framework, but boundaries and responsibilities must stay explicit

### 5.2 Backend Structure (Feature-Based)

Example only (adapt folder/file naming to your backend stack):

```
src/
  common/
    config/
    error/
    util/
    constants/
  auth/
    controller/
    service/
    repository/
    dto/
    model/
    AuthServiceTest.java
  order/
    controller/
    service/
    repository/
    dto/
    model/
    OrderServiceTest.java
  Application.java
```

### 5.3 Frontend Structure (Modular)

Example only (adapt folder/file naming to your frontend stack):

```
src/
  common/
    components/
    hooks/
    utils/
    types/
    constants/
  features/
    auth/
      components/
      hooks/
      services/
      stores/
      types/
      index.ts
    order/
      components/
      hooks/
      services/
      types/
      index.ts
  layouts/
  pages/
  routes/
  App.tsx
```

### 5.4 IaC Structure

Adapt the structure below to your provisioning tool (Terraform, Pulumi, CloudFormation, OpenTofu) and configuration tool (Ansible, Chef, Puppet, Salt). The key principles are: separate modules/roles by domain, separate environments by directory, and keep shared definitions (tags, providers, common variables) in one place.

Infrastructure Provisioning layout (Terraform/OpenTofu example — adapt file extensions and conventions for Pulumi, CDK, CloudFormation):

```
infrastructure/
  modules/
    networking/
      main.tf          # or index.ts (Pulumi) or template.yaml (CFN)
      variables.tf     # or config inputs
      outputs.tf       # or stack exports
    compute/
      main.tf
      variables.tf
      outputs.tf
    storage/
      main.tf
      variables.tf
      outputs.tf
  environments/
    dev/
      main.tf
      terraform.tfvars  # or Pulumi.dev.yaml or dev-params.json
      backend.tf
    staging/
      main.tf
      terraform.tfvars
      backend.tf
    prod/
      main.tf
      terraform.tfvars
      backend.tf
  shared/
    tags.tf
    providers.tf
  policies/
    checkov/
    opa/
```

Configuration Management layout (Ansible example — adapt for Chef cookbooks, Puppet modules, Salt states):

```
configuration/
  inventories/
    dev/
      hosts.yml
      group_vars/
    staging/
      hosts.yml
      group_vars/
    prod/
      hosts.yml
      group_vars/
  roles/
    common/           # shared across all hosts (NTP, logging, hardening)
      tasks/
      handlers/
      templates/
      defaults/
    webserver/        # domain-specific role
      tasks/
      handlers/
      templates/
      defaults/
    database/
      tasks/
      handlers/
      templates/
      defaults/
  playbooks/
    site.yml          # master playbook
    webservers.yml
    databases.yml
  ansible.cfg
  requirements.yml    # role dependencies
```

### 5.5 Module Boundary Rules

- Each module MUST define a clear public API (e.g., `index.ts` in FE, package-level exported services/interfaces in BE, `outputs.tf` in Terraform, stack exports in Pulumi, Outputs in CloudFormation, `defaults/main.yml` in Ansible roles)
- Other modules must depend on that public API, not internal implementation files/classes
- DO NOT import internal files from another module directly
- Cross-module communication via shared types/events, not direct imports
- If 2 modules need to share logic, extract it into `common/`

### 5.6 Reuse & Common Module Rules

- Apply Rule of Three: if similar logic appears in 3 places (or 2 places with clear growth), extract it
- Put only truly cross-domain code into `common/` / `shared/` (utilities, primitives, shared contracts)
- Keep business logic inside feature modules unless it is domain-agnostic
- `common/` MUST stay stable and minimal; avoid adding feature-specific assumptions
- Every extracted shared module must have clear ownership and tests

Extraction priority:

1. Duplicate pure functions -> `common/utils`
2. Duplicate UI primitives -> `common/components`
3. Duplicate validation schemas -> `common/validators`
4. Duplicate data contracts/types -> `common/types`
5. Duplicate cross-feature orchestration -> `common/services`
6. Duplicate backend policies/rules -> `common/domain` or `common/service`
7. Duplicate IaC patterns -> `modules/` with parameterized variables

Do not extract too early. Premature abstraction is harder to maintain than small duplication.

---

## 6. Feature Isolation — Prevent Conflicts Between Features

### 6.1 Principles

- Each feature is developed in its own module — do not modify files belonging to other features
- Shared state must be managed centrally (store/context) with a clear interface
- Do not use global mutable state — each module manages its own state
- Side effects (API calls, event emissions) must be isolated in the service layer

### 6.2 Avoiding Conflicts During Implementation

- Each feature has its own routes, services, and types — do not share route/service files across features
- Application entry points (e.g., `Application.java`, `app.ts`, `App.tsx`) only bootstrap/register modules — no business logic
- Config and middleware are shared, but must be designed so that adding new ones does not require modifying existing code (Open/Closed)
- When adding a new feature: create a new folder, register it in the app entry — do not modify existing feature code

### 6.3 Dependency Rule

```
pages -> features -> common
          |
        services -> external APIs / DB

controller/handler -> domain/service -> repository/gateway
```

- `common` MUST NOT import from `features`
- `features` MUST NOT import directly from other features (use shared types/events)
- `pages` orchestrate features but do not contain business logic

---

## 7. Code Style — Formatting & Imports

### 7.1 Formatting

- Indentation and semicolon rules must follow the formatter/linter configuration of each language
- Trailing commas in multi-line structures
- Max line length: 100-120 characters (soft limit)
- 1 blank line between logical sections, 2 blank lines between top-level definitions
- Prefer `const` / `final` / `readonly` — only use mutable when truly necessary

### 7.2 Imports

- Import order: (1) standard library, (2) third-party, (3) internal modules
- Separate each group with a blank line
- Do not use wildcard imports (`import *`) — import explicitly
- Sort alphabetically within each group
- Frontend: use path aliases (`@/`, `~/`) instead of long relative paths (`../../../`)
- Backend: use stable package/module boundaries; avoid deep cross-package imports into internal implementation

### 7.3 Constants, Enums, and Messages

- No magic values in business logic; extract repeated literals into named constants
- Use enums for closed sets of domain states (status, type, mode, role)
- Use constants for configuration values, limits, and reusable keys
- User-facing messages must come from centralized message/i18n resources, not inline literals
- Error codes must be constants/enums and shared between producer and consumer

Placement rules:

1. Feature-specific constants/enums/messages -> inside that feature module
2. Cross-feature constants/enums/messages -> `common/constants` or `common/types`
3. Environment/runtime values -> centralized config module only
4. Backend localized messages -> centralized message bundles/resources
5. Frontend localized messages -> centralized i18n dictionaries/resources

Naming rules:

1. Constants: `UPPER_SNAKE_CASE`
2. Enums: `PascalCase`; enum members: `UPPER_SNAKE_CASE`
3. Message keys: stable, semantic names (e.g., `ORDER_VALIDATION_REQUIRED_ADDRESS`)

### 7.4 Tooling, Linting, and Automation

- Each stack MUST define and version-control formatter, linter, type-check/static-analysis, and test configuration
- Local developer commands and CI commands must produce consistent results
- Treat linter/type-check violations as quality issues; do not bypass without documented reason
- Auto-formatting is mandatory; manual style debates should be replaced by tool configuration
- Build and test scripts should be standardized in repository docs and executable in CI/CD

---

## 8. Error Handling

### 8.1 General Principles

- NEVER swallow errors silently — at minimum, log them
- Use specific error classes, not generic `Error` / `Exception`
- Fail fast: validate inputs at the beginning of each function
- Error messages must include clear context (but never expose internals to end users)
- API error responses must follow a consistent structure:

```ts
{ ok: false, error: "VALIDATION_ERROR", message: "Email is required" }
```

BEFORE (bad — swallowed exception, no context):

```java
public User getUser(String id) {
    try {
        return userRepository.findById(id);
    } catch (Exception e) {
        return null;
    }
}
```

AFTER (good — specific exception, context preserved, fail-fast):

```java
public User getUser(String userId) {
    Objects.requireNonNull(userId, "userId must not be null");

    try {
        return userRepository.findById(userId)
            .orElseThrow(() -> new UserNotFoundException(userId));
    } catch (DataAccessException ex) {
        throw new ServiceException(
            "Failed to retrieve user",
            Map.of("userId", userId),
            ex
        );
    }
}
```

### 8.2 Async Code

- Always handle asynchronous failures explicitly (promise rejection, exception, callback error, coroutine failure)
- Use partial-failure strategies when acceptable (e.g., `Promise.allSettled`, retry groups, compensation flow)
- Set timeouts on all external calls (HTTP, DB, third-party)

### 8.3 Logging

- Structured logging (JSON format for production)
- Log levels: `debug` (dev), `info` (operations), `warn` (recoverable), `error` (failures)
- Include context: request ID, user ID, operation name
- NEVER log secrets, tokens, passwords, or PII

BEFORE (bad):

```typescript
console.log('User login failed for ' + email);
```

AFTER (good):

```typescript
logger.warn('Authentication failed', {
  event: 'LOGIN_FAILURE',
  email_hash: hashPii(email),
  ip_address: request.ip,
  trace_id: request.headers['x-trace-id'],
  reason: 'INVALID_CREDENTIALS',
});
```


---

## 9. Architecture & Design Patterns

### 9.1 Dependency Injection

- Pass dependencies via constructor or function parameters
- Do not import and instantiate dependencies directly inside business logic
- Enables testability and loose coupling

### 9.2 Layered Architecture

```
Route/Controller -> Service -> Repository/Data Access
  (HTTP concerns)   (Business logic)   (Persistence)

Page/Component -> Hook/ViewModel -> Service/API Client
  (UI render)      (UI-state logic)   (Network/side effects)
```

- Route: parse requests, return responses, set status codes — NO business logic
- Service: pure business logic — NO awareness of HTTP
- Repository: data access — NO business logic
- Page/Component: rendering and event wiring only — NO business rules
- Hook/ViewModel: view-state orchestration, derived state, UI interaction rules
- Service/API client: network calls, serialization, retry/timeout policy

### 9.3 Configuration

- Centralize all configuration in a single module/file
- Parse and validate environment variables at startup
- Use typed config objects with sensible defaults
- DO NOT scatter `process.env` / `os.environ` reads across the codebase

### 9.4 Middleware

- Each middleware handles a single cross-cutting concern
- Use factory functions for configurable middleware
- Order: auth -> rate limiting -> validation -> handler

### 9.5 Shared Service vs Feature Service

- Default: create service inside its feature module first
- Promote to shared service only when multiple features depend on the same behavior
- Shared services must expose a small, stable interface and avoid feature-specific branches
- Feature services can compose shared services, but shared services must not depend on feature services
- Keep side effects at service boundaries; keep shared core logic deterministic where possible

Decision checklist:

1. Is the logic business-domain specific to one feature? Keep it in the feature service.
2. Is the logic reused by multiple features with the same contract? Move to shared service.
3. Does extraction reduce duplication without adding coupling? Extract.
4. Would extraction introduce unstable abstraction? Keep local and revisit later.

---

## 10. Testing

### 10.1 Structure

- Co-locate tests with source files (e.g., `order.service.ts` -> `order.service.test.ts`, `OrderService.java` -> `OrderServiceTest.java`)
- Clear test names describing behavior (e.g., `should calculate total with tax`)
- AAA pattern: Arrange -> Act -> Assert
- Each test case verifies one behavior

### 10.2 Coverage

- Test both happy paths and error/edge cases
- Test boundary values and null/undefined inputs
- Mock external dependencies (HTTP, DB, file system)
- Do not test implementation details — test behavior and contracts

### 10.3 Test Hygiene

- Tests must be independent — no shared mutable state between tests
- Setup in `beforeEach`, cleanup in `afterEach`
- Test code must be as clean as production code

### 10.4 Test Pyramid

- Unit tests: fast, isolated, cover business logic — should be the majority (roughly 70%)
- Integration tests: verify module boundaries, API contracts, database queries (roughly 20%)
- End-to-end tests: critical user flows only — expensive, keep minimal (roughly 10%)
- Contract tests: verify API compatibility between services (use Pact or similar)
- Performance tests: baseline latency and throughput for critical paths; run in CI on schedule

### 10.5 IaC Testing

- Run `terraform validate` and `tflint` on every PR
- Use `terraform plan` output as a required PR artifact — no blind applies
- For complex modules, use `terratest` or `kitchen-terraform` for integration testing
- Test infrastructure changes in a dedicated test environment before staging

---

## 11. Security

### 11.1 Input Validation

- Validate and sanitize ALL user input at system boundaries
- Use allowlists over denylists
- Parameterize database queries — NEVER concatenate user input into queries

### 11.2 Secrets

- NEVER hardcode secrets, tokens, or passwords in source code
- Use environment variables or a secret manager
- NEVER log sensitive values
- `.gitignore` must exclude `.env`, key files, and credentials

### 11.3 Authentication & Authorization

- Use timing-safe comparison for secret/token validation
- Hash passwords with bcrypt/argon2 (never use SHA-256 alone for passwords)
- Apply the principle of least privilege
- Validate authorization on EVERY request

### 11.4 Data Protection

- Use HTTPS/TLS for all external communication
- Encrypt sensitive data at rest
- Sanitize error messages sent to clients — never expose stack traces or internal paths

### 11.5 OWASP Top 10 Awareness

When writing or reviewing code, actively check for these vulnerability categories:

1. Broken Access Control — verify authorization on every endpoint and data access
2. Cryptographic Failures — use strong algorithms, never roll your own crypto
3. Injection — parameterize all queries and commands (SQL, OS, LDAP, XPath)
4. Insecure Design — threat model before implementation, not after
5. Security Misconfiguration — no default credentials, disable unnecessary features
6. Vulnerable Components — scan dependencies, update within SLA
7. Authentication Failures — enforce MFA, rate-limit login attempts, use secure session management
8. Data Integrity Failures — verify software updates, use signed artifacts
9. Logging Failures — log security events, protect log integrity
10. SSRF — validate and restrict outbound requests from server-side code

---

## 12. Performance & Scalability

- Do not optimize prematurely — measure first, then optimize bottlenecks
- Use async/non-blocking I/O for network and file operations
- Cache expensive computations with TTL
- Use pagination for list endpoints — never return unbounded result sets
- Set timeouts on all external calls
- Use connection pooling for databases
- Design stateless services — externalize state for horizontal scaling

---

## 13. API & Contract Design

### 13.1 General Contract Rules

- API/interface contracts must be explicit, versioned when needed, and backward-compatible by default
- Contract schemas must be documented and testable (OpenAPI, GraphQL schema, protobuf, AsyncAPI, JSON schema, etc.)
- Use consistent success/error envelope per service boundary

### 13.2 REST (when using HTTP REST)

- Use plural nouns for resources: `/users`, `/orders`
- HTTP methods: GET (read), POST (create), PUT/PATCH (update), DELETE (remove)
- Use correct status codes: 200, 201, 204, 400, 401, 403, 404, 409, 422, 500
- Consistent response envelope:

```ts
// Success
{ ok: true, data: { ... } }

// Error
{ ok: false, error: "ERROR_CODE", message: "Human-readable description" }
```

- Version APIs when introducing breaking changes: `/api/v1/...`
- Document APIs with OpenAPI/Swagger

### 13.3 Non-REST Interfaces (when applicable)

- GraphQL: keep schema modular, avoid overly broad queries/mutations, enforce auth per resolver
- Event/message-based: use explicit event versioning, idempotency keys, and schema compatibility checks
- RPC/gRPC: define strict protobuf contracts and evolve fields with backward compatibility

---

## 14. Version Control

- Commit messages follow Conventional Commits: `type(scope): description`
- Each commit is one logical change
- Never commit generated files, build artifacts, or secrets
- Branch naming: `feature/*`, `bugfix/*`, `hotfix/*`, `chore/*`, `infra/*`, `ops/*`
- Infrastructure and configuration changes follow the same branch/PR/review process as application code
- Use `.gitignore` and `.gitattributes` appropriate for the stack
- Tag releases with semantic versioning: `v1.2.3`
- Protect the `main`/`master` branch: require PR reviews, passing CI, and no direct pushes
- For IaC repositories, require `terraform plan` or equivalent output as a required PR check

---

## 15. Docker & Containers

### 15.1 Image Standards

- Use multi-stage builds to minimize final image size
- Pin base image versions with digest or exact tag — never use `latest`
- `.dockerignore` must exclude dev files, test files, secrets, and build artifacts
- One process per container — do not run multiple services in a single container
- Run containers as a non-root user unless absolutely required
- Health check (`HEALTHCHECK`) must be defined for every service image
- Configuration via environment variables, not baked into images

### 15.2 Container Security

- Scan images for vulnerabilities in CI before pushing to registry (e.g., Trivy, Grype)
- Do not store secrets in image layers — use runtime secret injection (Vault, AWS Secrets Manager, Kubernetes Secrets)
- Set resource limits (`--memory`, `--cpus`) on all containers
- Use read-only filesystems where possible (`--read-only`)
- Drop unnecessary Linux capabilities (`--cap-drop ALL`, add back only what is needed)
- Generate SBOM for every production image (use syft or cyclonedx-cli)
- Sign images with cosign or notation before pushing to registry

### 15.3 Docker Compose (local / dev)

- Use named volumes, not bind mounts, for persistent data in shared environments
- Define `depends_on` with `condition: service_healthy` to enforce startup order
- Keep `docker-compose.override.yml` for local developer overrides — do not commit local-only settings to the base file

---

## 16. Infrastructure as Code (IaC)

IaC covers two distinct disciplines. Apply the correct subsection based on the task:

- Infrastructure Provisioning (16.1-16.5): creating and managing cloud/on-prem resources — use Terraform, OpenTofu, Pulumi, AWS CDK, CloudFormation, or Bicep
- Configuration Management (16.6-16.8): configuring and maintaining the software state of provisioned hosts — use Ansible, Chef, Puppet, Salt, or cloud-init
- Container Orchestration (16.9): managing containerized workloads — use Kubernetes manifests, Helm, Kustomize
- Policy-as-Code (16.10): enforcing compliance across all IaC tools

### 16.1 General Principles (applies to ALL IaC tools)

- All infrastructure MUST be defined as code — no manual changes to production environments
- IaC files are subject to the same review, testing, and version control standards as application code
- Use modules/roles/templates/constructs to avoid duplication across environments
- Parameterize environment-specific values (dev, staging, prod) — never hardcode them
- Every IaC change must go through PR review with a dry-run/plan output as artifact
- Tag/label all resources with at minimum: `environment`, `owner`, `project`, `managed-by`, `cost-center`
- Separate state/stack per environment — never share state across environments
- Store secrets in a secrets manager — never in IaC source files, variable files, or state

### 16.2 Infrastructure Provisioning — Terraform / OpenTofu

- Pin provider and module versions explicitly in `required_providers` and module `source` blocks
- Use remote state with locking (e.g., S3 + DynamoDB, Terraform Cloud, OCI Object Storage, GCS)
- Separate state per domain (networking, compute, data) — avoid monolith state files
- Run `terraform fmt`, `terraform validate`, and `tflint` in CI before plan/apply
- Use `terraform plan` output as a required PR artifact — no blind applies
- Store sensitive outputs as secrets, not in state output values

BEFORE (bad — monolith, no tags, hardcoded values):

```hcl
resource "oci_core_instance" "web" {
  availability_domain = "AD-1"
  compartment_id      = "ocid1.compartment.oc1..hardcoded"
  shape               = "VM.Standard.E4.Flex"
  display_name        = "web-server"
}
```

AFTER (good — modular, tagged, parameterized):

```hcl
locals {
  required_tags = {
    environment = var.environment
    project     = var.project_name
    owner       = var.team_owner
    managed_by  = "terraform"
    cost_center = var.cost_center
  }
}

resource "oci_core_instance" "web" {
  availability_domain = var.availability_domain
  compartment_id      = var.compartment_id
  shape               = var.instance_shape
  display_name        = "${var.project_name}-web-${var.environment}"

  freeform_tags = merge(local.required_tags, {
    role = "web-server"
  })
}
```

### 16.3 Infrastructure Provisioning — Pulumi

- Pin package versions in the language package manager (package.json, requirements.txt, go.mod)
- Use Pulumi stacks to separate environments — one stack per environment
- Store state in Pulumi Cloud or a self-managed backend (S3, Azure Blob, GCS) with encryption
- Use `pulumi preview` output as a required PR artifact
- Organize code using ComponentResource classes for reusable infrastructure modules
- Use stack configuration (`Pulumi.<stack>.yaml`) for environment-specific values — never hardcode
- Apply the same tagging standards as Terraform (environment, owner, project, managed-by, cost-center)

### 16.4 Infrastructure Provisioning — AWS CloudFormation / CDK

- Use nested stacks or CDK constructs to modularize infrastructure — avoid single monolith templates
- Pin CDK library versions explicitly in package manager
- Use parameters and mappings for environment-specific values
- Run `cfn-lint` and `cfn-guard` in CI before deployment
- Use change sets as required PR artifacts — review before executing
- Enable termination protection on production stacks
- Use `cdk diff` output as PR artifact for CDK projects

### 16.5 Infrastructure Provisioning — General Cloud (Azure Bicep, GCP Deployment Manager, etc.)

- Follow the same principles as 16.1: modularize, parameterize, tag, separate environments
- Use the native linting/validation tool for your platform (e.g., `az bicep build`, `gcloud deployment-manager` validate)
- Pin module/template versions
- Dry-run output is always a required PR artifact

### 16.6 Configuration Management — Ansible

- Use roles to organize tasks — one role per concern (e.g., `common`, `webserver`, `database`, `hardening`)
- Prefer `ansible-lint` in CI; treat warnings as errors
- Use Ansible Vault for all secrets — never store plaintext credentials in playbooks or vars files
- Idempotency is mandatory — every task must be safe to run multiple times
- Use `--check` (dry-run) mode in CI to validate playbooks before applying
- Use `--diff` to show what would change — include in PR artifacts
- Separate inventories per environment (dev, staging, prod) — never share inventory files
- Use `group_vars` and `host_vars` for environment-specific configuration — never hardcode in tasks
- Pin role dependencies in `requirements.yml` with exact versions

BEFORE (bad — hardcoded, no role structure, secrets in plaintext):

```yaml
# playbook.yml — everything in one file
- hosts: all
  tasks:
    - name: Install nginx
      apt:
        name: nginx
        state: present
    - name: Configure nginx
      template:
        src: nginx.conf.j2
        dest: /etc/nginx/nginx.conf
    - name: Set DB password
      lineinfile:
        path: /etc/app/config.yml
        line: "db_password: SuperSecret123"
```

AFTER (good — role-based, vault-encrypted secrets, idempotent):

```yaml
# playbooks/webservers.yml
- hosts: webservers
  become: true
  roles:
    - common
    - webserver

# roles/webserver/tasks/main.yml
- name: Install nginx
  ansible.builtin.apt:
    name: nginx
    state: present
  notify: restart nginx

- name: Deploy nginx configuration
  ansible.builtin.template:
    src: nginx.conf.j2
    dest: /etc/nginx/nginx.conf
    owner: root
    group: root
    mode: "0644"
    validate: "nginx -t -c %s"
  notify: restart nginx

# roles/webserver/defaults/main.yml
nginx_worker_processes: auto
nginx_worker_connections: 1024

# group_vars/webservers/vault.yml (encrypted with ansible-vault)
vault_db_password: !vault |
  $ANSIBLE_VAULT;1.1;AES256
  ...encrypted...
```

### 16.7 Configuration Management — Chef / Puppet

- Chef: organize by cookbooks, one cookbook per concern; pin cookbook versions in `Berksfile` or `Policyfile`
- Puppet: organize by modules, one module per concern; pin module versions in `Puppetfile`
- Both: use test-kitchen (Chef) or rspec-puppet (Puppet) for automated testing in CI
- Both: use data bags (Chef) or Hiera (Puppet) for environment-specific data — never hardcode in recipes/manifests
- Both: encrypt secrets using chef-vault or hiera-eyaml — never store plaintext
- Both: run in dry-run/noop mode in CI to validate changes before applying

### 16.8 Configuration Management — General Principles

- Every configuration change must be idempotent — safe to apply multiple times
- Use a pull model (agent-based) or push model (agentless) consistently — do not mix without clear boundaries
- Configuration drift detection must run on a schedule — alert on drift, auto-remediate where safe
- Document the intended state of every system in version-controlled configuration files
- Use templating for environment-specific values — never hardcode hostnames, IPs, or ports
- Test configuration changes in a dedicated test environment before staging
- Maintain a configuration inventory: which roles/cookbooks/modules apply to which hosts

### 16.9 Container Orchestration — Kubernetes

- All manifests must be stored in version control — no `kubectl apply` from local machines in production
- Use namespaces to isolate environments and teams
- Set resource `requests` and `limits` on every container
- Use `livenessProbe` and `readinessProbe` on every deployment
- Apply NetworkPolicies to restrict pod-to-pod communication by default (deny-all, allow explicitly)
- Use RBAC with least-privilege — no `cluster-admin` for application service accounts
- Prefer Helm charts or Kustomize for templating; avoid raw manifest duplication across environments
- Use GitOps (ArgoCD, Flux) for production deployments where possible

```yaml
resources:
  requests:
    cpu: "100m"
    memory: "128Mi"
  limits:
    cpu: "500m"
    memory: "512Mi"
readinessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 10
```

### 16.10 Policy-as-Code (applies to ALL IaC tools)

- Use policy engines to enforce infrastructure compliance in CI before any apply/deploy:
  - Terraform/OpenTofu: checkov, tfsec, OPA, Sentinel
  - Pulumi: CrossGuard (policy packs)
  - CloudFormation/CDK: cfn-guard, checkov
  - Ansible: ansible-lint custom rules, molecule tests
  - Kubernetes: OPA Gatekeeper, Kyverno
- Required policies at minimum:
  - No public storage buckets (S3, Object Storage, GCS, Azure Blob)
  - No overly permissive security groups/network rules (0.0.0.0/0 ingress)
  - Encryption enabled on all storage and databases
  - Required tags/labels present on all resources
  - No hardcoded secrets in source files
- Run drift detection on a schedule (weekly minimum) — alert on any deviation from declared state
- Integrate cost estimation (Infracost, Pulumi cost estimates) into PR workflow
- Block non-compliant resources before they reach production — policy violations are merge blockers


---

## 17. CI/CD Pipelines

### 17.1 Pipeline Design Principles

- Every pipeline stage must have a single, clear responsibility
- Pipelines are code — store them in version control alongside the application
- Fail fast: run the cheapest checks (lint, format, type-check) before expensive ones (build, test, deploy)
- All pipeline steps must be idempotent and reproducible
- No manual steps in the critical path to production — automate everything

### 17.2 Required Pipeline Stages

| Stage | Purpose | Blocks merge? |
|---|---|---|
| Lint & Format | Code style, IaC lint | Yes |
| Unit Tests | Fast isolated tests | Yes |
| Build | Compile / package | Yes |
| Security Scan | SAST, dependency audit, image scan | Yes |
| Integration Tests | Service-level tests | Yes |
| Deploy to Staging | Automated deploy | Yes |
| Smoke Tests | Basic post-deploy validation | Yes |
| Deploy to Production | Gated by approval or auto on main | Approval required |

### 17.3 Security in Pipelines

- Store all secrets in the CI/CD secret store — never in pipeline YAML files or environment variables committed to source
- Use short-lived credentials (OIDC/workload identity) instead of long-lived API keys where possible
- Pin action/plugin versions by commit SHA, not by tag (e.g., `actions/checkout@abc1234`)
- Restrict pipeline permissions to the minimum required (e.g., GitHub Actions `permissions:` block)

### 17.4 Deployment Standards

- Use blue/green or canary deployments for zero-downtime releases
- Always have a tested rollback procedure — document it in the runbook
- Deploy the same artifact across all environments — never rebuild for each environment
- Gate production deployments behind a manual approval step or automated quality gate
- Use feature flags for progressive delivery — decouple deployment from release

---

## 18. Database Management

### 18.1 Schema & Migration Standards

- All schema changes MUST be managed through versioned migration files (Flyway, Liquibase, Alembic, golang-migrate)
- Migrations must be forward-only in production — avoid destructive rollback migrations
- Every migration file must be: numbered sequentially, named descriptively, and reviewed before merge
- Test migrations against a copy of production data in staging before applying to production
- Never modify an already-applied migration file — create a new one instead

```sql
-- Good migration file name
V20240501_001__add_user_email_index.sql

-- Bad
fix.sql
update_users.sql
```

### 18.2 Query Standards

- Parameterize ALL queries — never concatenate user input (SQL injection prevention)
- Add indexes for all foreign keys and frequently filtered/sorted columns
- Avoid `SELECT *` in application queries — select only needed columns
- Use `EXPLAIN ANALYZE` to review query plans for any query touching large tables
- Set query timeouts on all application database connections
- Use transactions explicitly for multi-step operations that must be atomic

### 18.3 Access Control

- Application accounts must have the minimum required privileges (no `SUPERUSER` or `DBA` role for app users)
- Separate read and write database users where possible
- Rotate database credentials on a schedule and on any suspected compromise
- Never use the root/admin database account from application code

### 18.4 Backup & Recovery

- Automated backups must run daily at minimum; verify restore procedures monthly
- Store backups in a separate account/region from the primary database
- Document and test the RTO (Recovery Time Objective) and RPO (Recovery Point Objective)
- Encrypt backups at rest

---

## 19. Monitoring, Observability & Alerting

### 19.1 The Three Pillars

Every production service MUST implement all three:

| Pillar | Tooling examples | Minimum requirement |
|---|---|---|
| Metrics | Prometheus, CloudWatch, Datadog | RED metrics per service (Rate, Errors, Duration) |
| Logs | ELK, Loki, CloudWatch Logs | Structured JSON logs, centralized aggregation |
| Traces | Jaeger, Zipkin, AWS X-Ray | Distributed tracing for all inter-service calls |

### 19.2 Metrics Standards

- Expose a `/metrics` endpoint (Prometheus format) or push to a metrics backend
- Instrument at minimum: request rate, error rate, latency (p50/p95/p99), saturation (CPU/memory)
- Use consistent label names across services: `service`, `environment`, `version`, `method`, `status_code`
- Do not use high-cardinality labels (e.g., user IDs, request IDs) as metric labels

### 19.3 Logging Standards

- All logs MUST be structured (JSON) in production
- Required fields in every log entry: `timestamp` (ISO 8601), `level`, `service`, `environment`, `trace_id`, `message`
- Log levels: `DEBUG` (dev only), `INFO` (normal operations), `WARN` (recoverable issues), `ERROR` (failures requiring attention)
- NEVER log: passwords, tokens, API keys, PII, credit card numbers, or any sensitive data
- Centralize logs — do not rely on local disk log files in production

```json
{
  "timestamp": "2024-05-01T10:30:00Z",
  "level": "ERROR",
  "service": "order-service",
  "environment": "production",
  "trace_id": "abc-123",
  "message": "Payment gateway timeout",
  "duration_ms": 5001
}
```

### 19.4 Alerting Standards

- Alerts must be actionable — if an alert fires and no action is needed, remove or tune it
- Every alert must have a corresponding runbook entry
- Alert on symptoms (user-facing impact), not just causes (CPU high)
- Define severity levels: `P1` (immediate, production down), `P2` (degraded), `P3` (non-urgent), `P4` (informational)
- Route alerts to the correct on-call channel — do not alert everyone for every event
- Review and tune alert thresholds quarterly

### 19.5 SLO / SLI / Error Budget

- Define SLIs (Service Level Indicators) for every production service: availability, latency, error rate
- Set SLOs (Service Level Objectives) based on business requirements (e.g., 99.9% availability, p99 latency under 500ms)
- Calculate and track error budget: `error_budget = 1 - SLO` (e.g., 99.9% SLO = 0.1% error budget = 43.2 minutes/month)
- When error budget is exhausted: freeze feature releases, focus on reliability
- Review SLOs quarterly with stakeholders — adjust based on actual user impact data

---

## 20. System Administration & Operations

### 20.1 Shell Scripting Standards

- Every script must start with a shebang and `set -euo pipefail`
- Scripts must be idempotent — safe to run multiple times without side effects
- Validate all inputs at the top of the script; fail with a clear error message if invalid
- Use functions to organize logic — avoid monolithic scripts longer than 100 lines
- Add a usage/help block (`--help`) to every script intended for human use
- Quote all variable expansions: `"${variable}"` not `$variable`

```bash
#!/usr/bin/env bash
set -euo pipefail

# Usage: deploy.sh <environment> <version>
usage() {
  echo "Usage: $0 <environment> <version>"
  exit 1
}

[[ $# -lt 2 ]] && usage

ENVIRONMENT="${1}"
VERSION="${2}"
```

### 20.2 Configuration Management

- All server/system configuration must be managed by code (Ansible, Chef, Puppet, cloud-init) — no manual SSH configuration changes in production
- Configuration drift detection must run on a schedule (e.g., Ansible `--check` mode, AWS Config)
- Document the intended state of every system in version-controlled configuration files
- Use templating for environment-specific values — never hardcode hostnames, IPs, or ports

### 20.3 Access & Identity Management

- Apply the principle of least privilege to all user and service accounts
- Use SSO/IdP (e.g., Okta, Azure AD) for human access — no shared accounts
- Enforce MFA for all privileged access (production systems, cloud consoles, VPN)
- Rotate all credentials on a defined schedule and immediately on any suspected compromise
- Audit access logs for privileged operations — retain for a minimum of 90 days
- Disable or remove accounts immediately upon offboarding

### 20.4 Patch & Change Management

- Apply security patches within defined SLAs: critical within 24 hours, high within 7 days, medium within 30 days
- All production changes must go through a change management process (ticket, review, approval)
- Maintain a change log for all production systems
- Test patches in staging before applying to production
- Schedule maintenance windows for disruptive changes; notify stakeholders in advance

### 20.5 On-Call Standards

- On-call rotation: minimum 2 people per rotation, no more than 7 consecutive days
- Handoff document required at every rotation change
- On-call engineer must acknowledge alerts within 15 minutes (P1) / 1 hour (P2)
- Post-on-call review: log all incidents, time-to-acknowledge, time-to-resolve
- Compensate on-call fairly — track hours and incident load per person

### 20.6 Capacity Planning

- Review resource utilization monthly
- Alert when any resource exceeds 70% sustained utilization
- Maintain 30% headroom for traffic spikes
- Document capacity model: current usage, growth rate, projected exhaustion date
- Plan capacity changes at least 1 sprint ahead of projected need

---

## 21. Security Engineering

### 21.1 Secrets Management

- Use a dedicated secrets manager (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault, OCI Vault) — not environment variables in CI or `.env` files committed to source
- Rotate secrets automatically where possible; document rotation procedures where manual
- Audit secret access — log every read of a production secret
- Use short-lived dynamic credentials (e.g., Vault dynamic secrets) over long-lived static ones
- Never pass secrets as command-line arguments (visible in process lists)

### 21.2 Network Security

- Default-deny network policies — allow only explicitly required traffic
- Segment networks by trust zone: public, DMZ, private, data
- Use TLS 1.2+ for all internal and external communication; enforce certificate validation
- Disable unused ports and services on all hosts
- Use a WAF in front of public-facing services
- Scan for open ports and misconfigurations regularly (e.g., weekly automated scans)
- Define and enforce CSP (Content Security Policy) and CORS policies for all web applications

### 21.3 Vulnerability Management

- Run SAST (static analysis) on every PR — block merge on high/critical findings
- Run SCA (software composition analysis) to detect vulnerable dependencies — update within SLA
- Run DAST (dynamic analysis) against staging environments on a schedule
- Conduct penetration testing at least annually for internet-facing systems
- Maintain a vulnerability register; track remediation status and deadlines

### 21.4 Incident Response

- Every team must have a documented incident response runbook
- Define severity levels and escalation paths before an incident occurs
- During an incident: declare, mitigate, communicate, resolve, post-mortem
- Conduct a blameless post-mortem within 5 business days of every P1/P2 incident
- Post-mortem action items must be tracked to completion with owners and deadlines
- Practice incident response with tabletop exercises at least twice a year

---

## 22. Backup, Disaster Recovery & Business Continuity

### 22.1 Backup Standards

- Define and document RPO and RTO for every production system
- Automate all backups — no manual backup procedures for production data
- Store backups in a geographically separate location from the primary system
- Encrypt all backups at rest and in transit
- Test backup restoration on a defined schedule (monthly minimum for critical systems)
- Retain backups according to the data retention policy; automate deletion of expired backups

### 22.2 Disaster Recovery

- Maintain a documented DR plan for every critical system
- DR plan must include: recovery steps, responsible parties, contact list, and estimated recovery time
- Test the DR plan at least annually with a full failover exercise
- Automate failover where possible (e.g., RDS Multi-AZ, cross-region replication)
- Document and test the failback procedure as well as failover

### 22.3 High Availability Design

- Eliminate single points of failure for all production services
- Use load balancers with health checks in front of all stateless services
- Deploy across multiple availability zones (minimum 2) for critical workloads
- Use circuit breakers and retry logic with exponential backoff for inter-service calls
- Design for graceful degradation — partial failure should not cause total system failure

---

## 23. Runbooks & Operational Documentation

### 23.1 Runbook Standards

- Every production service must have a runbook stored in version control alongside the code
- Runbooks must be kept up to date — outdated runbooks are worse than no runbook
- Each runbook must include: service overview, architecture diagram, common failure modes, step-by-step remediation, escalation contacts, and links to dashboards/alerts

### 23.2 Required Runbook Sections

```markdown
# Service Name Runbook

## Overview
Brief description of what the service does and its criticality.

## Architecture
Link to or embed architecture diagram.

## Dependencies
List upstream and downstream dependencies.

## Common Alerts & Remediation
### Alert: HighErrorRate
- Cause: ...
- Impact: ...
- Steps: 1. Check logs ... 2. Restart pod if ... 3. Escalate if ...

## Escalation
- On-call: <pagerduty/opsgenie link>
- Engineering lead: <contact>
- Vendor support: <contact + SLA>

## Useful Commands
# Check service health
kubectl get pods -n <namespace>
# View recent logs
kubectl logs -n <namespace> deployment/<name> --tail=100

## Dashboards & Links
- Metrics: <link>
- Logs: <link>
- Traces: <link>
```

### 23.3 Architecture Decision Records (ADRs)

- Document significant technical decisions as ADRs in `docs/adr/`
- Each ADR must include: context, decision, consequences, and status (proposed/accepted/deprecated)
- ADRs are immutable once accepted — create a new ADR to supersede an old one
- Link ADRs from relevant code, runbooks, and design documents


---

## 24. AI-Assisted Development

### 24.1 Code Generation Review

- AI-generated code MUST pass the same review standards as human-written code
- Reviewer must verify: correctness, security implications, license compliance, and test coverage
- AI output is a draft, not a final product — do not commit without understanding every line
- Document AI-assisted decisions in commit messages: `feat(auth): add JWT refresh — AI-assisted, manually reviewed`

### 24.2 Prompt & Context Hygiene

- Never include secrets, PII, or proprietary business logic in prompts to external AI services
- Use workspace-local AI tools (Kiro, self-hosted models) for sensitive codebases
- When using AI to generate IaC, always run `terraform plan` and review the diff before applying
- AI-generated configurations must be validated against policy-as-code rules before merge

### 24.3 AI-Generated Test Skepticism

- AI-generated tests often test implementation, not behavior — always verify
- Check for: tautological assertions (tests that always pass), missing edge cases, mocked-away logic that hides real bugs
- Prefer writing test cases manually and using AI to help with boilerplate setup

### 24.4 AI Agent Instructions

When an AI agent follows these standards, it must:

- Read existing code before writing new code — match the project's style, conventions, and libraries
- Run linters and formatters after generating code
- Never introduce new dependencies without checking if an existing one covers the need
- Generate code that passes `terraform validate`, `tflint`, or equivalent for IaC
- Include error handling in every generated function — never generate happy-path-only code
- Add comments explaining WHY for non-obvious logic, not WHAT the code does
- Follow the naming conventions in Section 3 for the target language
- Follow the project structure in Section 5 — place files in the correct module/directory
- Generate structured log statements, not console.log/print

---

## 25. Data Privacy & Compliance

### 25.1 Data Classification

Every data field must be classified into one of these categories:

- PUBLIC: no restrictions (e.g., product names, public documentation)
- INTERNAL: not for external sharing but no regulatory impact (e.g., internal project names)
- CONFIDENTIAL: business-sensitive data (e.g., financial reports, contracts)
- RESTRICTED: regulated or highly sensitive data (e.g., PII, PHI, payment card data, credentials)

### 25.2 PII Handling

- Identify and document all PII fields in every data store
- Apply encryption at rest and in transit for all RESTRICTED data
- Implement data minimization — collect only what is needed, retain only as long as required
- Support right-to-erasure: design data models so that user data can be deleted without breaking referential integrity
- Use pseudonymization or anonymization for analytics and non-production environments
- Never use production PII in development or testing environments

### 25.3 Retention & Deletion

- Define retention periods for every data category — document in a data retention policy
- Automate deletion of expired data — do not rely on manual cleanup
- Audit data stores quarterly to verify compliance with retention policy
- Log all deletion operations for compliance audit trail

### 25.4 Consent & Compliance

- Implement consent management for user data collection where required by regulation (GDPR, CCPA, PDPA)
- Track consent status per user per purpose — store consent records immutably
- Provide data export capability (right to portability) for user-owned data
- Conduct Privacy Impact Assessment (PIA) before launching features that process new categories of personal data

---

## 26. Resilience Patterns

### 26.1 Circuit Breaker

- Wrap all external service calls with a circuit breaker
- Configure failure threshold (e.g., 5 failures), reset timeout (e.g., 30 seconds), and half-open probe count
- When circuit is open, fail fast with a meaningful error — do not queue requests indefinitely
- Log circuit state transitions (closed -> open -> half-open -> closed)

BEFORE (bad — naive retry that can cascade failure):

```typescript
async function getPaymentStatus(orderId: string): Promise<PaymentStatus> {
  try {
    const response = await fetch(`${PAYMENT_API}/orders/${orderId}`);
    return response.json();
  } catch (error) {
    return getPaymentStatus(orderId); // infinite retry = self-DDoS
  }
}
```

AFTER (good — circuit breaker with timeout):

```typescript
const PAYMENT_TIMEOUT_MS = 3000;

const paymentBreaker = new CircuitBreaker({
  failureThreshold: 5,
  resetTimeoutMs: 30000,
});

async function getPaymentStatus(orderId: string): Promise<PaymentStatus> {
  return paymentBreaker.execute(async () => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), PAYMENT_TIMEOUT_MS);

    try {
      const response = await fetch(`${PAYMENT_API}/orders/${orderId}`, {
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new PaymentServiceError(
          `Payment API returned ${response.status}`,
          { orderId, statusCode: response.status },
        );
      }

      return response.json();
    } finally {
      clearTimeout(timeoutId);
    }
  });
}
```

### 26.2 Retry with Backoff

- Use exponential backoff with jitter for retries — never use fixed-interval retries
- Set a maximum retry count (typically 3) — do not retry indefinitely
- Define a retry budget per service: no more than 10% of total requests should be retries
- Only retry on transient errors (5xx, timeout, connection reset) — never retry on 4xx client errors

### 26.3 Timeout Policy

- Set explicit timeouts on every external call (HTTP, database, message queue, file I/O)
- Timeout values must be configured, not hardcoded — use environment-specific config
- Cascade timeouts: caller timeout must be shorter than callee timeout to avoid orphaned requests
- Document timeout values in service runbooks

### 26.4 Bulkhead Isolation

- Isolate critical service calls into separate thread pools or connection pools
- A failure in one external dependency must not exhaust resources for other dependencies
- Monitor pool utilization and alert when approaching capacity

### 26.5 Graceful Degradation

- Design fallback behavior for every external dependency
- When a non-critical service is unavailable, serve cached or default data instead of failing entirely
- Communicate degraded state to users clearly (e.g., "Some features are temporarily unavailable")
- Feature flags can control degradation behavior — disable non-essential features under load

---

## 27. Dependency Management & Supply Chain Security

### 27.1 Dependency Selection

- Prefer well-known, actively maintained packages with clear licenses
- Check before adding: last release date, open issue count, maintainer activity, download count
- If a dependency name looks unusual or could be a typosquatting variant, verify it before installing
- Avoid dependencies that pull in excessive transitive dependencies for simple functionality

### 27.2 Version Pinning

- Use exact or pinned versions for all dependencies — no open ranges in production
- Lock files (package-lock.json, poetry.lock, go.sum, .terraform.lock.hcl) MUST be committed to version control
- Review dependency updates in dedicated PRs — do not mix dependency bumps with feature changes
- Use automated tools (Dependabot, Renovate) to propose dependency updates on a schedule

### 27.3 License Compliance

- Maintain an approved license list (e.g., MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC)
- Block dependencies with copyleft licenses (GPL, AGPL) in proprietary projects unless explicitly approved
- Run license scanning in CI — fail on unapproved licenses
- Document any license exceptions with justification in an ADR

### 27.4 Supply Chain Security

- Generate SBOM (Software Bill of Materials) for every release artifact
- Verify package integrity using checksums or signatures where available
- Use a private registry or proxy for production dependencies where possible
- Monitor for known vulnerabilities in dependencies — patch critical within 24 hours, high within 7 days

---

## 28. Accessibility (Frontend)

### 28.1 WCAG Compliance

- All user-facing interfaces must target WCAG 2.1 Level AA compliance at minimum
- Full WCAG validation requires manual testing with assistive technologies and expert accessibility review — automated tools catch only a subset of issues

### 28.2 Implementation Standards

- Use semantic HTML elements (`button`, `nav`, `main`, `header`, `footer`) — do not use `div` for interactive elements
- All images must have meaningful `alt` text (or `alt=""` for decorative images)
- All form inputs must have associated `label` elements
- Ensure sufficient color contrast ratio: 4.5:1 for normal text, 3:1 for large text
- All interactive elements must be keyboard-accessible (Tab, Enter, Escape, Arrow keys)
- Use ARIA attributes only when native HTML semantics are insufficient — do not overuse ARIA
- Test with screen readers (NVDA, VoiceOver, JAWS) for critical user flows
- Support reduced motion preferences: respect `prefers-reduced-motion` media query

### 28.3 Automated Checks

- Run axe-core or similar accessibility linter in CI for every frontend PR
- Include accessibility checks in component-level tests (e.g., jest-axe, testing-library)
- Treat accessibility violations as bugs — track and fix within the same sprint
