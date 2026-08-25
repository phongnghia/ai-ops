package com.aiops.demo.dto;

import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.math.BigDecimal;

/**
 * Incoming payload for POST /api/orders.
 *
 * @param customerId the customer placing the order (required, non-blank)
 * @param amount     the order total in USD (required, must be > 0)
 */
public record CreateOrderRequest(
    @NotBlank(message = "customerId is required")
    String customerId,

    @NotNull(message = "amount is required")
    @DecimalMin(value = "0.01", message = "amount must be greater than zero")
    BigDecimal amount
) {}
