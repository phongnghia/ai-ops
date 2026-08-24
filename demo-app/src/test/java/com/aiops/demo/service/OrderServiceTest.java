package com.aiops.demo.service;

import com.aiops.demo.domain.Order;
import com.aiops.demo.domain.OrderRepository;
import com.aiops.demo.domain.OrderStatus;
import com.aiops.demo.dto.CreateOrderRequest;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.util.Optional;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

/**
 * Unit tests for {@link OrderService}.
 *
 * Three tests are intentionally written to FAIL against the current buggy
 * implementation, demonstrating real CI build failures for AI Ops analysis:
 *
 *   calculateDiscount_shouldThrowNPE_whenAmountIsNull
 *     → FAILS with NullPointerException (BUG #1)
 *
 *   calculateDiscount_shouldApplyPremiumDiscount_whenAmountEqualsThreshold
 *     → FAILS with wrong discount value (BUG #2)
 *
 *   confirmOrder_shouldRejectCancelledOrder
 *     → FAILS because CANCELLED order is incorrectly allowed to confirm (BUG #3)
 */
@ExtendWith(MockitoExtension.class)
class OrderServiceTest {

    @Mock
    private OrderRepository orderRepository;

    @InjectMocks
    private OrderService orderService;

    // Helpers

    private Order orderWithAmount(BigDecimal amount) {
        return new Order("customer-1", amount);
    }

    private Order orderWithAmountAndStatus(BigDecimal amount, OrderStatus status) {
        Order order = new Order("customer-1", amount);
        if (status != OrderStatus.PENDING) {
            order.setStatus(status);
        }
        return order;
    }

    // calculateDiscount — happy paths

    @Nested
    @DisplayName("calculateDiscount")
    class CalculateDiscountTests {

        @Test
        @DisplayName("should return zero discount for amount below standard threshold")
        void calculateDiscount_shouldReturnZero_whenAmountBelowStandardThreshold() {
            Order order = orderWithAmount(new BigDecimal("499.99"));

            BigDecimal discount = orderService.calculateDiscount(order);

            assertThat(discount).isEqualByComparingTo(BigDecimal.ZERO);
        }

        @Test
        @DisplayName("should apply 10% standard discount for amount at standard threshold ($500)")
        void calculateDiscount_shouldApplyStandardDiscount_whenAmountAtStandardThreshold() {
            Order order = orderWithAmount(new BigDecimal("500.00"));

            BigDecimal discount = orderService.calculateDiscount(order);

            // 10% of 500.00 = 50.00
            assertThat(discount).isEqualByComparingTo(new BigDecimal("50.00"));
        }

        @Test
        @DisplayName("should apply 10% standard discount for amount above $500 but below $1000")
        void calculateDiscount_shouldApplyStandardDiscount_whenAmountBetweenThresholds() {
            Order order = orderWithAmount(new BigDecimal("750.00"));

            BigDecimal discount = orderService.calculateDiscount(order);

            // 10% of 750.00 = 75.00
            assertThat(discount).isEqualByComparingTo(new BigDecimal("75.00"));
        }

        @Test
        @DisplayName("should apply 15% premium discount for amount above $1000")
        void calculateDiscount_shouldApplyPremiumDiscount_whenAmountAbovePremiumThreshold() {
            Order order = orderWithAmount(new BigDecimal("1500.00"));

            BigDecimal discount = orderService.calculateDiscount(order);

            // 15% of 1500.00 = 225.00
            assertThat(discount).isEqualByComparingTo(new BigDecimal("225.00"));
        }

        // BUG #2 — off-by-one: > instead of >= at the $1000 premium threshold

        @Test
        @DisplayName("[BUG #2] should apply 15% premium discount when amount equals $1000 threshold")
        void calculateDiscount_shouldApplyPremiumDiscount_whenAmountEqualsThreshold() {
            // An order for exactly $1,000.00 must receive the 15% PREMIUM discount.
            // BUG #2: the condition uses > instead of >=, so the service applies
            // the standard 10% discount instead.
            //
            // Expected: 15% of 1000.00 = 150.00
            // Actual (buggy): 10% of 1000.00 = 100.00
            //
            // This test FAILS on the current implementation.
            Order order = orderWithAmount(new BigDecimal("1000.00"));

            BigDecimal discount = orderService.calculateDiscount(order);

            assertThat(discount)
                .as("Order for exactly $1000 should receive the 15%% premium discount")
                .isEqualByComparingTo(new BigDecimal("150.00"));
        }

        // BUG #1 — NullPointerException when amount is null

        @Test
        @DisplayName("[BUG #1] should throw IllegalArgumentException when order amount is null")
        void calculateDiscount_shouldThrowIllegalArgument_whenAmountIsNull() {
            // When an Order is constructed with a null amount (e.g. a partially
            // built record from a legacy import path), calculateDiscount() should
            // validate the input and throw IllegalArgumentException.
            //
            // BUG #1: instead of validating, the method calls amount.compareTo()
            // on a null reference and throws NullPointerException.
            //
            // This test FAILS on the current implementation because the exception
            // type is NullPointerException, not IllegalArgumentException.
            Order order = orderWithAmount(null);

            assertThatIllegalArgumentException()
                .as("calculateDiscount should reject a null amount with IllegalArgumentException")
                .isThrownBy(() -> orderService.calculateDiscount(order))
                .withMessageContaining("amount");
        }
    }

    // confirmOrder

    @Nested
    @DisplayName("confirmOrder")
    class ConfirmOrderTests {

        @Test
        @DisplayName("should confirm a PENDING order successfully")
        void confirmOrder_shouldSucceed_whenOrderIsPending() {
            Order order = orderWithAmountAndStatus(new BigDecimal("200.00"), OrderStatus.PENDING);
            when(orderRepository.findById(1L)).thenReturn(Optional.of(order));
            when(orderRepository.save(any())).thenAnswer(inv -> inv.getArgument(0));

            Order confirmed = orderService.confirmOrder(1L);

            assertThat(confirmed.getStatus()).isEqualTo(OrderStatus.CONFIRMED);
        }

        @Test
        @DisplayName("should throw when confirming a SHIPPED order")
        void confirmOrder_shouldThrow_whenOrderIsShipped() {
            Order order = orderWithAmountAndStatus(new BigDecimal("200.00"), OrderStatus.SHIPPED);
            when(orderRepository.findById(2L)).thenReturn(Optional.of(order));

            assertThatIllegalStateException()
                .isThrownBy(() -> orderService.confirmOrder(2L));
        }

        @Test
        @DisplayName("should throw when confirming a DELIVERED order")
        void confirmOrder_shouldThrow_whenOrderIsDelivered() {
            Order order = orderWithAmountAndStatus(new BigDecimal("200.00"), OrderStatus.DELIVERED);
            when(orderRepository.findById(3L)).thenReturn(Optional.of(order));

            assertThatIllegalStateException()
                .isThrownBy(() -> orderService.confirmOrder(3L));
        }

        // BUG #3 — CANCELLED order can be confirmed

        @Test
        @DisplayName("[BUG #3] should throw IllegalStateException when confirming a CANCELLED order")
        void confirmOrder_shouldRejectCancelledOrder() {
            // A cancelled order must never move back to CONFIRMED.
            // BUG #3: the guard condition allows CANCELLED status to pass through,
            // so the order is incorrectly set to CONFIRMED and persisted.
            //
            // This test FAILS on the current implementation.
            Order order = orderWithAmountAndStatus(new BigDecimal("200.00"), OrderStatus.CANCELLED);
            when(orderRepository.findById(4L)).thenReturn(Optional.of(order));

            assertThatIllegalStateException()
                .as("Confirming a CANCELLED order must throw IllegalStateException")
                .isThrownBy(() -> orderService.confirmOrder(4L))
                .withMessageContaining("CANCELLED");
        }
    }

    // cancelOrder

    @Nested
    @DisplayName("cancelOrder")
    class CancelOrderTests {

        @Test
        @DisplayName("should cancel a PENDING order successfully")
        void cancelOrder_shouldSucceed_whenOrderIsPending() {
            Order order = orderWithAmountAndStatus(new BigDecimal("100.00"), OrderStatus.PENDING);
            when(orderRepository.findById(5L)).thenReturn(Optional.of(order));
            when(orderRepository.save(any())).thenAnswer(inv -> inv.getArgument(0));

            Order cancelled = orderService.cancelOrder(5L);

            assertThat(cancelled.getStatus()).isEqualTo(OrderStatus.CANCELLED);
        }

        @Test
        @DisplayName("should throw when cancelling a SHIPPED order")
        void cancelOrder_shouldThrow_whenOrderIsShipped() {
            Order order = orderWithAmountAndStatus(new BigDecimal("100.00"), OrderStatus.SHIPPED);
            when(orderRepository.findById(6L)).thenReturn(Optional.of(order));

            assertThatIllegalStateException()
                .isThrownBy(() -> orderService.cancelOrder(6L));
        }

        @Test
        @DisplayName("should throw when cancelling a DELIVERED order")
        void cancelOrder_shouldThrow_whenOrderIsDelivered() {
            Order order = orderWithAmountAndStatus(new BigDecimal("100.00"), OrderStatus.DELIVERED);
            when(orderRepository.findById(7L)).thenReturn(Optional.of(order));

            assertThatIllegalStateException()
                .isThrownBy(() -> orderService.cancelOrder(7L));
        }
    }

    // createOrder

    @Nested
    @DisplayName("createOrder")
    class CreateOrderTests {

        @Test
        @DisplayName("should create and persist a new PENDING order")
        void createOrder_shouldPersistPendingOrder() {
            CreateOrderRequest request = new CreateOrderRequest("cust-99", new BigDecimal("350.00"));
            when(orderRepository.save(any())).thenAnswer(inv -> inv.getArgument(0));

            Order order = orderService.createOrder(request);

            assertThat(order.getCustomerId()).isEqualTo("cust-99");
            assertThat(order.getAmount()).isEqualByComparingTo(new BigDecimal("350.00"));
            assertThat(order.getStatus()).isEqualTo(OrderStatus.PENDING);
            verify(orderRepository).save(any(Order.class));
        }
    }
}
