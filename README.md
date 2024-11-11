# Energy Management Dashboard

A Streamlit-based energy management dashboard for optimizing battery charging based on Dutch energy prices. The system provides battery configuration management with multiple profile support and automated charge/discharge scheduling.

## Features

- Battery profile management with predefined templates
- Real-time price monitoring and optimization
- Historical data analysis
- Cost savings calculator
- Interactive visualizations
- Usage prediction with seasonal patterns

## Docker Deployment

### Prerequisites

- Docker
- Docker Compose

### Running with Docker

1. Clone the repository:
```bash
git clone <repository-url>
cd energy-management-dashboard
```

2. Build and run the Docker container:
```bash
docker-compose up --build
```

3. Access the dashboard:
Open your browser and navigate to `http://localhost:5000`

### Configuration

The application uses the following default ports:
- Streamlit Dashboard: Port 5000

You can modify these settings in the `docker-compose.yml` file.

### Environment Variables

The following environment variables can be configured:
- `STREAMLIT_SERVER_PORT`: Port for the Streamlit server (default: 5000)
- `STREAMLIT_SERVER_ADDRESS`: Server address (default: 0.0.0.0)

## Local Development

1. Install dependencies:
```bash
pip install streamlit pandas numpy plotly
```

2. Run the application:
```bash
streamlit run main.py
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
