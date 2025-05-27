# Water Quality Analysis App

This is an enterprise-grade water quality analysis application that uses Sentinel-2 satellite data for analyzing water quality parameters.

## Features

- Water quality analysis using Sentinel-2 satellite imagery
- Interactive dashboard for water quality metrics
- Sampling point analysis
- Authentication system
- Custom visualizations and reporting

## Deployment to Streamlit Cloud

1. Push your code to GitHub
2. Go to [Streamlit Cloud](https://streamlit.io/cloud)
3. Connect your GitHub repository
4. Set up the following environment variables in Streamlit Cloud:
   - `SENTINELHUB_CLIENT_ID`
   - `SENTINELHUB_CLIENT_SECRET`
   - `SENTINELHUB_INSTANCE_ID`

## Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
streamlit run water_quality_app_v4.py
```

## Project Structure

- `water_quality_app_v4.py`: Main application file
- `.streamlit/`: Streamlit Cloud configuration
- `requirements.txt`: Python dependencies
- `sentinel_data/`: Downloaded satellite data (not included in git)

## Security

- Never commit `.streamlit/secrets.toml` to git
- Keep your Sentinel Hub credentials secure
- Use environment variables for sensitive information
