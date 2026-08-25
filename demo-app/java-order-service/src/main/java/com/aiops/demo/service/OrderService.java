package com.aiops.demo.service;

import com.aiops.demo.domain.Order;
import com.aiops.demo.domain.OrderRepository;
import com.aiops.demo.domain.OrderStatus;
import com.aiops.demo.dto.CreateOrderRequest;
import com.aiops.demo.dto.OrderSummary;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.List;

/**
 * Order business logic service.
 *
 * Contains three intentional bugs used to demonstrate AI Ops log analysis:
 *
 *   BUG #1 — NullPointerException in calculateDiscount():
 *     amount.compareTo() is called without a null-check on amount. When a
 *     caller passes an Order whose amount field is null (e.g. a partially
 *     constructed record), the method throws NullPointerException at runtime
 *     instead of returning a safe default.
 *
 *   BUG #2 — Wrong discount boundary in calculateDiscount():
 *     The premium threshold uses > instead of >=. An order for exactly
 *     $1,000.00 should receive the 15% premium discount, but the condition
 *     silently applies only the 10% standard discount. Unit tests catch this
 *     off-by-one error.
 *
 *   BUG #3 — Invalid state transition in confirmOrder():
 *     The guard allows confirming a CANCELLED order. A cancelled order should
 *     never move back to CONFIRMED — doing so corrupts the order lifecycle and
 *     triggers downstream fulfilment for an order the customer already cancelled.
 */
@Service
@Transactional
public class OrderService {

    // Discount thresholds
    private static final BigDecimal STANDARD_THRESHOLD = new BigDecimal("500.00");
    private static final BigDecimal PREMIUM_THRESHOLD  = new BigDecimal("1000.00");

    private static final BigDecimal STANDARD_DISCOUNT_RATE = new BigDecimal("0.10");
    private static final BigDecimal PREMIUM_DISCOUNT_RATE  = new BigDecimal("0.15");

    private final OrderRepository orderRepository;

    public OrderService(OrderRepository orderRepository) {
        this.orderRepository = orderRepository;
    }

    /**
     * Create and persist a new order.
     *
     * @param request the incoming create-order payload
     * @return the persisted order
     */
    public Order createOrder(CreateOrderRequest request) {
        Order order = new Order(request.customerId(), request.amount());
        return orderRepository.save(order);
    }

    /**
     * Confirm a pending order.
     *
     * BUG #3 — accepts CANCELLED status as a valid starting state, allowing
     * resurrection of cancelled orders.
     *
     * @param orderId the order to confirm
     * @return the updated order
     * @throws OrderNotFoundException  if no order with the given id exists
     * @throws IllegalStateException   if the order is already in a non-confirmable state
     */
    public Order confirmOrder(Long orderId) {
        Order order = findOrderById(orderId);

        // BUG #3: condition should be:
        //   order.getStatus() != OrderStatus.PENDING
        // As written, CANCELLED orders also pass this guard and get confirmed.
        if (order.getStatus() != OrderStatus.PENDING
                && order.getStatus() != OrderStatus.CANCELLED) {
            throw new IllegalStateException(
                "Cannot confirm order " + orderId
                + " in status " + order.getStatus());
        }

        order.setStatus(OrderStatus.CONFIRMED);
        return orderRepository.save(order);
    }

    /**
     * Cancel an order.
     *
     * @param orderId the order to cancel
     * @return the updated order
     * @throws OrderNotFoundException if no order with the given id exists
     * @throws IllegalStateException  if the order cannot be cancelled from its current state
     */
    public Order cancelOrder(Long orderId) {
        Order order = findOrderById(orderId);

        if (order.getStatus() == OrderStatus.SHIPPED
                || order.getStatus() == OrderStatus.DELIVERED) {
            throw new IllegalStateException(
                "Cannot cancel order " + orderId
                + " that is already " + order.getStatus());
        }

        order.setStatus(OrderStatus.CANCELLED);
        return orderRepository.save(order);
    }

    /**
     * Calculate the discount amount for an order.
     *
     * BUG #1: amount is dereferenced without a null check. If order.getAmount()
     * returns null, this method throws NullPointerException.
     *
     * BUG #2: the premium threshold condition uses strict greater-than (>)
     * instead of greater-than-or-equal (>=). An order for exactly $1,000.00
     * receives only the standard 10% discount instead of the 15% premium
     * discount.
     *
     * @param order the order to calculate the discount for
     * @return the discount amount (never negative)
     */
    public BigDecimal calculateDiscount(Order order) {
        BigDecimal amount = order.getAmount();

        // BUG #1: no null check — throws NullPointerException when amount is null.
        if (amount.compareTo(PREMIUM_THRESHOLD) > 0) {  // BUG #2: should be >= not >
            return amount.multiply(PREMIUM_DISCOUNT_RATE);
        }

        if (amount.compareTo(STANDARD_THRESHOLD) >= 0) {
            return amount.multiply(STANDARD_DISCOUNT_RATE);
        }

        return BigDecimal.ZERO;
    }

    /**
     * Retrieve a summary list of all orders for a given customer.
     *
     * @param customerId the customer identifier
     * @return list of order summaries, possibly empty
     */
    @Transactional(readOnly = true)
    public List<OrderSummary> getOrdersByCustomer(String customerId) {
        return orderRepository.findByCustomerId(customerId)
            .stream()
            .map(o -> new OrderSummary(
                o.getId(),
                o.getCustomerId(),
                o.getAmount(),
                o.getStatus().name(),
                o.getCreatedAt()))
            .toList();
    }

    /**
     * Find an order by id, throwing {@link OrderNotFoundException} when absent.
     */
    @Transactional(readOnly = true)
    public Order findOrderById(Long orderId) {
        return orderRepository.findById(orderId)
            .orElseThrow(() -> new OrderNotFoundException(orderId));
    }
}
