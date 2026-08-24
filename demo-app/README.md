# order-service — Demo Spring Boot App

A minimal order management service used to demonstrate real CI/CD build failures for AI Ops log analysis. The project compiles cleanly but **three unit tests intentionally fail**, producing a realistic Maven Surefire failure log that the AI backend analyzes.

## Intentional bugs

| # | Location | Bug | Test that catches it |
|---|---|---|---|
| 1 | `OrderService.calculateDiscount()` | `NullPointerException` when `order.getAmount()` is null — no null check before `amount.compareTo()` | `calculateDiscount_shouldThrowIllegalArgument_whenAmountIsNull` |
| 2 | `OrderService.calculateDiscount()` | Wrong boundary condition: uses `>` instead of `>=` for the $1,000 premium discount threshold — an order for exactly $1,000 gets 10% instead of 15% | `calculateDiscount_shouldApplyPremiumDiscount_whenAmountEqualsThreshold` |
| 3 | `OrderService.confirmOrder()` | Invalid state transition: `CANCELLED` orders are allowed to be confirmed, corrupting the order lifecycle | `confirmOrder_shouldRejectCancelledOrder` |

## Build and test locally

**Không cần cài Java hay Maven** — tất cả chạy trong Docker.

```bash
# Từ thư mục gốc repo
make test-demo

# Hoặc trực tiếp trong demo-app/
docker build --target test -t order-service:test demo-app
```

Docker sẽ pull `maven:3.9.6-eclipse-temurin-21-alpine`, compile, chạy tests. Build sẽ **exit non-zero** vì 3 tests fail — đây là behavior mong muốn cho demo AI analysis.

## Run via Makefile (from repo root)

```bash
make build-demo   # compile + test trong Docker (exit non-zero = expected)
make test-demo    # alias của build-demo
```

## Run via Jenkins

In the pipeline **Build with Parameters**:

```
LOCAL_WORKSPACE  = /mnt/c/works/local/ai-ops
DEMO_PROJECT     = java-order-service
DEMO_FAIL_BUILD  = false
```

The `Test` stage runs `make test-demo`. Maven exits non-zero, the `post { failure }` block preprocesses the Surefire output, and sends it to the AI backend for analysis.

## Project structure

```
demo-app/
  pom.xml
  src/
    main/java/com/aiops/demo/
      OrderServiceApplication.java
      domain/
        Order.java              ← JPA entity
        OrderStatus.java        ← lifecycle enum
        OrderRepository.java    ← Spring Data JPA (includes SQL injection demo)
      service/
        OrderService.java       ← business logic with 3 bugs
        OrderNotFoundException.java
      api/
        OrderController.java    ← REST endpoints
        GlobalExceptionHandler.java
      dto/
        CreateOrderRequest.java
        OrderSummary.java
        ErrorResponse.java
    test/java/com/aiops/demo/
      service/
        OrderServiceTest.java   ← 12 tests, 3 intentionally fail
```
