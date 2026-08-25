package com.aiops.demo.dto;

/**
 * Consistent error envelope returned for all API errors.
 *
 * @param error   machine-readable error code (e.g. NOT_FOUND, VALIDATION_ERROR)
 * @param message human-readable description safe to expose to clients
 */
public record ErrorResponse(String error, String message) {}
