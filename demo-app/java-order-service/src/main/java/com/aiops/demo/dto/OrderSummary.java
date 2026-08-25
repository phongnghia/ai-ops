package com.aiops.demo.dto;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * Read-only projection of an order returned to API callers.
 *
 * @param id         the order identifier
 * @param customerId the customer who placed the order
 * @param amount     the order total
 * @param status     the current lifecycle status (string name of {@link com.aiops.demo.domain.OrderStatus})
 * @param createdAt  when the order was created
 */
public record OrderSummary(
    Long id,
    String customerId,
    BigDecimal amount,
    String status,
    LocalDateTime createdAt
) {}
