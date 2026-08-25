package com.aiops.demo.domain;

/**
 * Lifecycle states of an order.
 *
 * Valid transitions:
 *   PENDING -> CONFIRMED -> SHIPPED -> DELIVERED
 *   PENDING -> CANCELLED
 *   CONFIRMED -> CANCELLED
 */
public enum OrderStatus {
    PENDING,
    CONFIRMED,
    SHIPPED,
    DELIVERED,
    CANCELLED
}
