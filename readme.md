# 311 Data Downloader

This is a Python script that downloads 311 data from the City of Toronto's open data portal. The script uses the `requests` library to download the data from the API.

## Requirements

- Python 3.x
- `requests` library

## Usage

Create a python virtual environment using `venv`, install the libraries and run the script:

```bash
python3 -m venv env
source env/bin/activate  # On Windows use `venv\Scripts\activate`
pip3 install -r requirements.txt
```

Then, run the script to download the 311 data:

```bash
python3 311_downloader.py
```

Exit the virtual environment when done:

```bash
deactivate
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
