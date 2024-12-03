# Ganajan Parking

Ganajan Parking is a web-based application designed to manage and monitor parking facilities. It uses webhook data from a FLOW server (either xRoad / FLOW Camera / FLOW enterprise server) and provides a dashboard for viewing parking statistics, searching for vehicles, and managing parking entries. The application is built using Flask for the frontend and backend, and PostgreSQL for the database. Nginx is used as a reverse proxy to manage and route traffic.


## Features

- Real-time parking statistics and analytics
- Vehicle search functionality
- Secure user sessions with Flask
- Dockerized setup for easy deployment

## Setup Instructions

To set up Ganajan Parking on a fresh virtual machine, follow these steps:

### Prerequisites

1. **Install Docker**: Ensure Docker is installed and running on your virtual machine.
   - [Docker Installation Guide](https://docs.docker.com/get-docker/)

2. **Install Docker Compose**: Install Docker Compose to manage multi-container Docker applications.
   - [Docker Compose Installation Guide](https://docs.docker.com/compose/install/)

### Project Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/ganajan-parking.git
   cd ganajan-parking
   ```

2. **Configure Environment Variables**:
   - Create a `.env` file in the root directory with the following content:
     ```env
     DB_PASSWORD=your_secure_password
     POSTGRES_PASSWORD=your_secure_password
     SECRET_KEY=your_secret_key
     DB_USER=flowerist
     DB_NAME=flow
     DB_TABLE=parking
     DB_PORT=5444
     DB_HOST=db
     DB_CONTAINER_NAME=db
     ```

3. **Run Initial Setup**:
   - Execute the `first-run.sh` script to set up the PostgreSQL database.
     ```bash
     ./first-run.sh
     ```

4. **Start the Application**:
   - Use Docker Compose to start all services.
     ```bash
     docker-compose up -d
     ```

5. **Nginx Proxy Configuration**:
   - The Nginx proxy is configured to manage and route traffic:
     - **Port 32211**: Handles webhook traffic, routing requests to the backend service.
     - **Port 32212**: Manages frontend traffic, directing requests to the frontend service.
   - Nginx ensures secure and efficient traffic management, forwarding client information to backend services for accurate logging and processing.

6. **Access the Application**:
   - Open your web browser and navigate to `http://<your-vm-ip>:32212` to access the frontend dashboard.

### Webhook Configuration

The application is configured to receive webhooks on the following endpoints via the Nginx proxy on port 32211:

- **Car In Webhook**: `http://<your-vm-ip>:32211/webhooks/ganajan_car_in`
- **Car Out Webhook**: `http://<your-vm-ip>:32211/webhooks/ganajan_car_out`
- **Bike In Webhook**: `http://<your-vm-ip>:32211/webhooks/ganajan_bike_in`
- **Bike Out Webhook**: `http://<your-vm-ip>:32211/webhooks/ganajan_bike_out`

These endpoints are designed to handle incoming webhook requests and route them to the appropriate backend service for processing.

### Additional Notes

- Ensure the `.env` file is not committed to your version control system for security reasons.
- Check the logs for any errors during setup and operation to troubleshoot issues.

By following these steps, you should have Ganajan Parking up and running on your virtual machine. If you encounter any issues, please refer to the logs or contact the project maintainers for support.