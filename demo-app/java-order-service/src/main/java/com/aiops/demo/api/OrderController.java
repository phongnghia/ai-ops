package com.aiops.demo.api;

import com.aiops.demo.domain.Order;
import com.aiops.demo.dto.CreateOrderRequest;
import com.aiops.demo.dto.OrderSummary;
import com.aiops.demo.service.OrderService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

/**
 * REST controller for the order management API.
 *
 * Routes:
 *   POST   /api/orders                 create a new order
 *   GET    /api/orders?customerId=...  list orders for a customer
 *   POST   /api/orders/{id}/confirm    confirm a pending order
 *   POST   /api/orders/{id}/cancel     cancel an order
 *   GET    /api/orders/{id}/discount   calculate the discount for an order
 */
@RestController
@RequestMapping("/api/orders")
public class OrderController {

    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    @PostMapping
    public ResponseEntity<OrderSummary> createOrder(
            @Valid @RequestBody CreateOrderRequest request) {
        Order order = orderService.createOrder(request);
        return ResponseEntity
            .status(HttpStatus.CREATED)
            .body(toSummary(order));
    }

    @GetMapping
    public ResponseEntity<List<OrderSummary>> listOrders(
            @RequestParam String customerId) {
        return ResponseEntity.ok(orderService.getOrdersByCustomer(customerId));
    }

    @PostMapping("/{id}/confirm")
    public ResponseEntity<OrderSummary> confirmOrder(@PathVariable Long id) {
        return ResponseEntity.ok(toSummary(orderService.confirmOrder(id)));
    }

    @PostMapping("/{id}/cancel")
    public ResponseEntity<OrderSummary> cancelOrder(@PathVariable Long id) {
        return ResponseEntity.ok(toSummary(orderService.cancelOrder(id)));
    }

    @GetMapping("/{id}/discount")
    public ResponseEntity<Map<String, BigDecimal>> getDiscount(@PathVariable Long id) {
        Order order = orderService.findOrderById(id);
        BigDecimal discount = orderService.calculateDiscount(order);
        return ResponseEntity.ok(Map.of(
            "amount",   order.getAmount(),
            "discount", discount,
            "total",    order.getAmount().subtract(discount)
        ));
    }

    private static OrderSummary toSummary(Order o) {
        return new OrderSummary(
            o.getId(),
            o.getCustomerId(),
            o.getAmount(),
            o.getStatus().name(),
            o.getCreatedAt()
        );
    }
}
