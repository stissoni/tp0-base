package common

import (
	"bufio"
	"net"
	"time"
	"os"
	"io"
	"encoding/json"
	log "github.com/sirupsen/logrus"
)

// ClientConfig Configuration used by the client
type ClientConfig struct {
	ID            string
	ServerAddress string
	LoopLapse     time.Duration
	LoopPeriod    time.Duration
}

// Client Entity that encapsulates how
type Client struct {
	config ClientConfig
	conn   net.Conn
}

// NewClient Initializes a new client receiving the configuration
// as a parameter
func NewClient(config ClientConfig) *Client {
	client := &Client{
		config: config,
	}
	return client
}

// CreateClientSocket Initializes client socket. In case of
// failure, error is printed in stdout/stderr and exit 1
// is returned
func (c *Client) createClientSocket() error {
	conn, err := net.Dial("tcp", c.config.ServerAddress)
	if err != nil {
		log.Fatalf(
	        "action: connect | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
	}
	c.conn = conn
	return nil
}

// StartClientLoop Send messages to the client until some time threshold is met
func (c *Client) StartClientLoop() {
	
	AGENCIA := os.Getenv("CLI_ID")
	NOMBRE := os.Getenv("NOMBRE")
	APELLIDO := os.Getenv("APELLIDO")
	DOCUMENTO := os.Getenv("DOCUMENTO")
	NACIMIENTO := os.Getenv("NACIMIENTO")
	NUMERO := os.Getenv("NUMERO")
	
	// Create a map with the JSON data
	data := map[string]string{
		"agencia":    AGENCIA,
		"nombre":     NOMBRE,
		"apellido":   APELLIDO,
		"doc":        DOCUMENTO,
		"nacimiento": NACIMIENTO,
		"numero":     NUMERO,
	}

	// Encode the data into JSON
	jsonData, err := json.Marshal(data)
	if err != nil {
		log.Errorf("Error encoding JSON:", err)
		return
	}

	// Create the connection the server in every loop iteration. Send an
	c.createClientSocket()

	// Write the message to the connection
	_, err = io.WriteString(c.conn, string(jsonData))
	if err != nil {
		log.Errorf("Error sending data:", err)
		return
	}
	log.Infof("action: apuesta_enviada | result: success | dni:%v | numero: %v", DOCUMENTO, NUMERO)

	msg, err := bufio.NewReader(c.conn).ReadString('\n')
	c.conn.Close()

	if err != nil {
		log.Errorf("action: receive_message | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
		return
	}
	log.Infof("action: receive_message | result: success | message: %v",
		msg,
	)
	
	log.Infof("action: send_bet_finished | result: success | client_id: %v", c.config.ID)
	
}
