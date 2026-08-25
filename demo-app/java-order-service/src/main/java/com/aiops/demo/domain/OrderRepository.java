package com.aiops.demo.domain;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface OrderRepository extends JpaRepository<Order, Long> {

    List<Order> findByCustomerId(String customerId);

    List<Order> findByStatus(OrderStatus status);

    /**
     * BUG #3 — SQL injection vulnerability.
     *
     * This native query concatenates the customerId parameter directly into the
     * SQL string instead of using a bind parameter. An attacker can pass a
     * crafted customerId such as:
     *   "' OR '1'='1"
     * to return all orders in the database, bypassing the customer filter.
     *
     * Fix: use a JPQL named parameter (:customerId) or Spring Data's method
     * name derivation (findByCustomerId) which uses bind parameters by default.
     */
    @Query(value = "SELECT * FROM orders WHERE customer_id = '" + "' || :customerId || '", nativeQuery = true)
    List<Order> findByCustomerIdUnsafe(String customerId);
}
