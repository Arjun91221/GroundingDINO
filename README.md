
# Grounding-DINO


## Installation

Follow these steps to set up the project

1. Clone the repository

```bash
git clone https://github.com/IDEA-Research/GroundingDINO.git
cd GroundingDINO
```

2. Create a virtual environment

```bash
python3 -m venv venv
source venv\bin\activate
```

3. Install the required packages

```bash
pip install torch==2.3.0 torchvision==0.18.0 --index-url https://download.pytorch.org/whl/cu118
pip install -q -e .
python setup.py develop
```

4. Download Weights

```bash
mkdir weights
cd weights
wget -q https://github.com/IDEA-Research/GroundingDINO/releases/download/v0.1.0-alpha/groundingdino_swint_ogc.pth
wget -q https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth
cd ..
```

## Running the Application

You can run the application using one of the following commands

1. Using Python

```bash
  python main.py
```

2. Using Uvicorn

```bash
  uvicorn main:app --reload --host 0.0.0.0 --port 8001
```


## Usage

After running the application, you can use the provided endpoints to process images and detect hands. Ensure you have the necessary input images and follow the API documentation for more details on how to use the endpoints effectively.


## Acknowledgements

Special thanks to the developers and contributors of Grounding-DINO and other open-source libraries used in this project.

