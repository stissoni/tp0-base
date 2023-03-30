package common

import (
	"archive/zip"
	"bufio"
	"encoding/json"
	"io"
	"net"
	"os"

	"strconv"
	"strings"

	"time"

	log "github.com/sirupsen/logrus"
)

// ClientConfig Configuration used by the client
type ClientConfig struct {
	ID            string
	ServerAddress string
	BatchSize     string
	MaxPacketSize string
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

type PacketToBig struct{}

func (myerr *PacketToBig) Error() string {
	return "Packet to big to send!"
}

func send_data(c *Client, data []byte) ([]byte, error) {
	max_packet_size, err := strconv.Atoi(c.config.MaxPacketSize)
	log.Infof("Max packet size: %v", max_packet_size)
	if err != nil {
		panic(err)
	}
	if len(data) > max_packet_size {
		log.Errorf("Packet to big to send: %v > %vB", len(data), max_packet_size)
		return nil, &PacketToBig{}
	}

	// Write the message to the connection
	_, err = io.WriteString(c.conn, string(data))
	if err != nil {
		log.Errorf("Error sending data:", err)
		return nil, err
	}
	log.Infof("action: data sended | result: waiting for response")
	// Wait for an answer
	msg, err := bufio.NewReader(c.conn).ReadBytes('\n')
	return msg, err
}

func (c *Client) SendBatch(bets []map[string]string) error {
	data, err := json.Marshal(bets)
	if err != nil {
		log.Errorf("Error encoding JSON:", err)
		return err
	}
	log.Infof("action: sending batch | result: waiting for response")
	response, err := send_data(c, data)
	if err != nil {
		log.Errorf("action: receive_message | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
		return err
	} else {
		log.Infof("action: receive_message | result: success | message: %s", response)
	}
	return nil
}

func (c *Client) NotifyBatchDone() {
	request := make(map[string]string)
	request["type"] = "ready"
	request["agencia"] = os.Getenv("CLI_ID")
	data, err := json.Marshal(request)
	if err != nil {
		log.Errorf("Error encoding JSON:", err)
		panic(err)
	}
	response, _ := send_data(c, data)
	log.Infof("action: receive_message | result: success | message: %s",
		response,
	)
}

func (c *Client) RequestWinners() bool {
	request := make(map[string]string)
	request["type"] = "consultar_ganadores"
	request["agencia"] = os.Getenv("CLI_ID")
	data, err := json.Marshal(request)
	if err != nil {
		log.Errorf("Error encoding JSON:", err)
		panic(err)
	}
	response, err := send_data(c, data)
	if err != nil {
		log.Errorf("Error sendig data:", err)
		panic(err)
	}
	m := make(map[string]string)
	err = json.Unmarshal(response, &m)
	if m["type"] == "error" {
		log.Infof("action: receive_message | result: success | message: %s",
			response,
		)
		return false
	}
	if err != nil {
		log.Errorf("Error decoding data:", err)
		panic(err)
	}
	log.Infof("action: consulta_ganadores | result: success | cant_ganadores: %s",
		m["ganadores"],
	)
	c.conn.Close()
	return true
}

func (c *Client) openAndScanFile(filename string) (*bufio.Scanner, error) {
	r, err := zip.OpenReader(".data/dataset.zip")
	if err != nil {
		log.Errorf("error: could not open zip file")
		return nil, err
	}
	log.Infof("action: abrir_zip_file | result: success")

	for _, f := range r.File {
		if f.Name == filename {
			file, err := f.Open()
			if err != nil {
				log.Errorf("error: could not open csv file")
				return nil, err
			}
			log.Infof("action: abrir_csv_file | result: success")
			scanner := bufio.NewScanner(file)
			return scanner, nil
		}
	}
	return nil, nil
}

func (c *Client) GetBetFromLine(agency_num string, line string) map[string]string {
	fields := strings.Split(line, ",")
	new_bet := make(map[string]string)
	for i, field := range fields {
		if i == 0 {
			new_bet["nombre"] = field
		}
		if i == 1 {
			new_bet["apellido"] = field
		}
		if i == 2 {
			new_bet["doc"] = field
		}
		if i == 3 {
			new_bet["nacimiento"] = field
		}
		if i == 4 {
			new_bet["numero"] = field
		}
	}
	new_bet["agencia"] = agency_num
	return new_bet
}

func (c *Client) CloseSocket() {
	c.conn.Close()
}

// StartClientLoop Send messages to the client until some time threshold is met
func (c *Client) StartClientLoop() error {
	batch_size, err := strconv.Atoi(c.config.BatchSize)
	if err != nil {
		panic(err)
	}

	agency_num := os.Getenv("CLI_ID")
	scanner, _ := c.openAndScanFile("agency-" + agency_num + ".csv")
	data := []map[string]string{}

	c.createClientSocket()

	// Read the file line by line and send each line over the socket
	log.Infof("action: scanning_file | result: in_progress")
	for scanner.Scan() {
		line := scanner.Text()
		new_bet := c.GetBetFromLine(agency_num, line)
		data = append(data, new_bet)

		if len(data) == batch_size {
			// Send batch
			err := c.SendBatch(data)
			if err != nil {
				return err
			}
			// Empty the data
			data = []map[string]string{}
		}
	}
	if err := scanner.Err(); err != nil {
		panic(err)
	}
	log.Infof("action: scanning_file | result: success")
	err = c.SendBatch(data)
	if err != nil {
		return err
	}
	return nil
}
