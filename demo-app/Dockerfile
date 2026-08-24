# Multi-stage build for the order-service demo.
#
# Stages:
#   compile  — compiles the project only, no tests. Always succeeds.
#   test     — compiles + runs all unit tests. Fails with 3 intentional failures.
#   package  — produces a runnable JAR (only reachable after bugs are fixed).
#   runtime  — minimal JRE image for running the app.
#
# Usage:
#   docker build --target compile -t order-service:compile .   # compile only, succeeds
#   docker build --target test    -t order-service:test    .   # compile + test, fails
#   docker build --target package -t order-service:package .   # full build, fails (tests block)

# Stage 1 — compile
# Compiles the source without running tests. Always exits 0.
FROM maven:3.9.6-eclipse-temurin-21-alpine AS compile

WORKDIR /app
COPY pom.xml .
RUN mvn -B dependency:go-offline -q
COPY src ./src
RUN mvn -B compile -q

# Stage 2 — test
# Runs all unit tests on top of the compiled code. Exits non-zero when any
# test fails — exactly what Jenkins needs to trigger post { failure }.
# Three tests are intentionally written to fail.
FROM compile AS test
RUN mvn -B test

# Stage 3 — package (only reached when all tests pass)
FROM maven:3.9.6-eclipse-temurin-21-alpine AS package

WORKDIR /app
COPY pom.xml .
RUN mvn -B dependency:go-offline -q
COPY src ./src
RUN mvn -B package -DskipTests -q

# Stage 4 — runtime (minimal JRE image)
FROM eclipse-temurin:21-jre-alpine AS runtime

WORKDIR /app
COPY --from=package /app/target/order-service-*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
