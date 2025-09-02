// Go Example - HTTP Health Check Service
package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"time"
)

// Config holds application configuration
type Config struct {
	Port         int           `json:"port"`
	ReadTimeout  time.Duration `json:"read_timeout"`
	WriteTimeout time.Duration `json:"write_timeout"`
	Environment  string        `json:"environment"`
}

// HealthResponse represents the health check response
type HealthResponse struct {
	Status    string            `json:"status"`
	Timestamp time.Time         `json:"timestamp"`
	Version   string            `json:"version"`
	Checks    map[string]string `json:"checks"`
}

const (
	defaultPort    = 8080
	defaultTimeout = 10 * time.Second
	version        = "1.2.3"
)

func main() {
	config := loadConfig()
	
	server := &http.Server{
		Addr:         fmt.Sprintf(":%d", config.Port),
		ReadTimeout:  config.ReadTimeout,
		WriteTimeout: config.WriteTimeout,
	}

	http.HandleFunc("/health", healthHandler)
	http.HandleFunc("/ready", readinessHandler)
	
	log.Printf("Starting server on port %d", config.Port)
	if err := server.ListenAndServe(); err != nil {
		log.Fatal("Server failed to start:", err)
	}
}

func loadConfig() *Config {
	port, _ := strconv.Atoi(getEnvOrDefault("PORT", "8080"))
	
	return &Config{
		Port:         port,
		ReadTimeout:  defaultTimeout,
		WriteTimeout: defaultTimeout,
		Environment:  getEnvOrDefault("ENVIRONMENT", "development"),
	}
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	response := HealthResponse{
		Status:    "healthy",
		Timestamp: time.Now(),
		Version:   version,
		Checks: map[string]string{
			"database": "ok",
			"redis":    "ok",
			"storage":  "ok",
		},
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func readinessHandler(w http.ResponseWriter, r *http.Request) {
	// Perform readiness checks here
	ready := true
	
	if !ready {
		w.WriteHeader(http.StatusServiceUnavailable)
		return
	}
	
	w.WriteHeader(http.StatusOK)
	fmt.Fprintln(w, "ready")
}

func getEnvOrDefault(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}